from __future__ import annotations

import argparse
import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score


def fit_predict(train: list[dict], targets: list[dict]) -> list[str]:
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=8000)
    train_matrix = vectorizer.fit_transform([row["text"] for row in train])
    target_matrix = vectorizer.transform([row["text"] for row in targets])
    model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=20260911)
    model.fit(train_matrix, [row["document_type"] for row in train])
    return model.predict(target_matrix).tolist()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", type=Path, required=True)
    parser.add_argument("--cord", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    synthetic = json.loads(args.synthetic.read_text())["predictions"]
    train = [row for row in synthetic if row["split"] == "train"]
    dev = [row for row in synthetic if row["split"] == "dev"]
    cord_source = json.loads(args.cord.read_text())
    cord = [{"text": row["text"], "document_type": "receipt", "document_id": row["document_id"]} for row in cord_source["predictions"]]
    truth = [row["document_type"] for row in dev]
    curve = []
    for size in (25, 50, 100, 150):
        prediction = fit_predict(train[:size], dev)
        curve.append(
            {
                "training_documents": size,
                "macro_f1": f1_score(truth, prediction, average="macro"),
                "balanced_accuracy": balanced_accuracy_score(truth, prediction),
            }
        )
    cord_prediction = fit_predict(train, cord)
    cord_accuracy = sum(prediction == "receipt" for prediction in cord_prediction) / len(cord_prediction)
    saturation = abs(curve[-1]["macro_f1"] - curve[-2]["macro_f1"]) < 0.01
    result = {
        "experiment_id": "V2-E14",
        "task": "TF-IDF document classification over GPU OCR text",
        "synthetic_scaling_curve": curve,
        "predefined_stop_rule": "Stop when the last two macro-F1 points differ by less than 0.01.",
        "stop_rule_satisfied": saturation,
        "larger_conditions_status": "SKIPPED_WITH_REASON" if saturation else "NOT_RUN_COMPUTE_LIMIT",
        "cross_dataset_transfer": {
            "source": "R-FDI Synthetic V2 train",
            "target": "CORD v2 validation (all receipts)",
            "target_documents": len(cord),
            "receipt_accuracy": cord_accuracy,
            "prediction_counts": {label: cord_prediction.count(label) for label in sorted(set(cord_prediction))},
            "limitation": "Document-type transfer only; no incompatible field schemas were pooled.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
