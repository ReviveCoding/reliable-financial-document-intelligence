from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import paddle
import paddleocr
from paddleocr import PaddleOCR
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score
from v2_guard import assert_input_allowed


CRITICAL_FIELDS = ("invoice_number", "po_number", "total", "currency", "beneficiary")


def compact(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def contains_value(text: str, value: object) -> bool:
    needle = compact(value)
    return bool(needle) and needle in compact(text)


def extract_total(text: str) -> str | None:
    matches = re.findall(r"(?:grand\s+)?total\s*[:|\-]?\s*(?:[A-Z]{3}\s*)?([0-9][0-9., ]*)", text, re.I)
    return compact(matches[-1]) if matches else None


def classify_rule(text: str) -> str:
    upper = text.upper()
    for label, marker in (
        ("purchase_order", "PURCHASE ORDER"),
        ("remittance", "REMITTANCE"),
        ("payment_record", "PAYMENT RECORD"),
        ("receipt", "RECEIPT"),
        ("invoice", "INVOICE"),
    ):
        if marker in upper:
            return label
    return "other"


def load_rows(path: Path, limit: int) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    return rows[:limit] if limit else rows


def summarize(groups: dict[str, list[dict]]) -> dict[str, dict[str, float | int]]:
    output: dict[str, dict[str, float | int]] = {}
    for name, rows in sorted(groups.items()):
        output[name] = {
            "documents": len(rows),
            "all_field_value_recall": float(np.mean([r["field_value_recall"] for r in rows])),
            "critical_field_value_recall": float(np.mean([r["critical_field_value_recall"] for r in rows])),
            "total_exact_match": float(np.mean([r["total_correct"] for r in rows])),
            "line_item_row_recall": float(np.mean([r["line_item_row_recall"] for r in rows])),
        }
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--dev", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-limit", type=int, default=150)
    parser.add_argument("--dev-limit", type=int, default=100)
    parser.add_argument("--evaluation-split-name", default="dev")
    args = parser.parse_args()
    assert_input_allowed(args.train)
    assert_input_allowed(args.dev)

    train = load_rows(args.train, args.train_limit)
    dev = load_rows(args.dev, args.dev_limit)
    paddle.seed(20260911)
    started = time.perf_counter()
    ocr = PaddleOCR(
        device="gpu:0",
        text_detection_model_name="PP-OCRv5_server_det",
        text_recognition_model_name="PP-OCRv5_server_rec",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    load_seconds = time.perf_counter() - started
    predictions: list[dict] = []
    timings: list[float] = []

    evaluation_split = args.evaluation_split_name
    for split, rows in (("train", train), (evaluation_split, dev)):
        for row in rows:
            paddle.device.synchronize()
            tick = time.perf_counter()
            results = list(ocr.predict(row["pages"][0]))
            paddle.device.synchronize()
            elapsed = time.perf_counter() - tick
            timings.append(elapsed)
            payload = results[0].json["res"]
            text = " ".join(item for item in payload["rec_texts"] if item)
            field_hits = {key: contains_value(text, spec["text"]) for key, spec in row["fields"].items()}
            critical_hits = [field_hits[key] for key in CRITICAL_FIELDS]
            line_hits = []
            for item in row["line_items"]:
                line_hits.append(all(contains_value(text, item[key]) for key in ("description", "quantity", "unit_price", "amount")))
            total_guess = extract_total(text)
            total_truth = compact(row["fields"]["total"]["text"])
            predictions.append(
                {
                    "split": split,
                    "document_id": row["document_id"],
                    "document_type": row["document_type"],
                    "corruption": row["corruption"],
                    "text": text,
                    "mean_confidence": float(np.mean(payload["rec_scores"])) if payload["rec_scores"] else 0.0,
                    "field_hits": field_hits,
                    "field_value_recall": float(np.mean(list(field_hits.values()))),
                    "critical_field_value_recall": float(np.mean(critical_hits)),
                    "line_item_row_recall": float(np.mean(line_hits)),
                    "total_prediction": total_guess,
                    "total_truth": total_truth,
                    "total_correct": total_guess == total_truth,
                    "rule_document_type": classify_rule(text),
                    "latency_seconds": elapsed,
                }
            )

    train_pred = [row for row in predictions if row["split"] == "train"]
    dev_pred = [row for row in predictions if row["split"] == evaluation_split]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=8000)
    train_matrix = vectorizer.fit_transform([row["text"] for row in train_pred])
    dev_matrix = vectorizer.transform([row["text"] for row in dev_pred])
    classifier = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=20260911)
    classifier.fit(train_matrix, [row["document_type"] for row in train_pred])
    tfidf_predictions = classifier.predict(dev_matrix).tolist()
    for row, prediction in zip(dev_pred, tfidf_predictions):
        row["tfidf_document_type"] = prediction

    truth = [row["document_type"] for row in dev_pred]
    rule_predictions = [row["rule_document_type"] for row in dev_pred]
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in dev_pred:
        groups[row["corruption"]["type"]].append(row)

    result = {
        "experiment_id": "V2-E05",
        "dataset": "R-FDI Synthetic V2",
        "split": f"train/{evaluation_split}",
        "ocr_model": "PP-OCRv5_server_det+PP-OCRv5_server_rec",
        "model_revisions": {
            "PP-OCRv5_server_det": "ca867c897ecbca8873081573a802ad70d499cb94",
            "PP-OCRv5_server_rec": "b26c3587fda8da3c8ec0ce357214b4d661ff1558",
        },
        "paddleocr": paddleocr.__version__,
        "paddle": "3.3.0",
        "device": paddle.device.cuda.get_device_name(),
        "physical_gpu_count": 1,
        "precision": "framework default FP32",
        "batch_size": 1,
        "train_documents": len(train_pred),
        "dev_documents": len(dev_pred),
        "load_seconds": load_seconds,
        "runtime_seconds": float(sum(timings)),
        "latency_seconds": timings,
        "peak_vram_bytes": paddle.device.cuda.max_memory_allocated(),
        "dev_metrics": {
            "all_field_value_recall": float(np.mean([row["field_value_recall"] for row in dev_pred])),
            "critical_field_value_recall": float(np.mean([row["critical_field_value_recall"] for row in dev_pred])),
            "total_exact_match": float(np.mean([row["total_correct"] for row in dev_pred])),
            "line_item_row_recall": float(np.mean([row["line_item_row_recall"] for row in dev_pred])),
            "rule_document_macro_f1": f1_score(truth, rule_predictions, average="macro"),
            "rule_document_balanced_accuracy": balanced_accuracy_score(truth, rule_predictions),
            "tfidf_document_macro_f1": f1_score(truth, tfidf_predictions, average="macro"),
            "tfidf_document_balanced_accuracy": balanced_accuracy_score(truth, tfidf_predictions),
        },
        "by_corruption": summarize(groups),
        "predictions": predictions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in {"predictions", "latency_seconds"}}, sort_keys=True))


if __name__ == "__main__":
    main()
