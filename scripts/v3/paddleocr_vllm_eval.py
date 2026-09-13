from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from pathlib import Path
from typing import Any

from paddleocr import PaddleOCRVL


def normalize(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip().casefold())


def flatten(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            output.extend(flatten(item, f"{prefix}.{key}" if prefix else key))
    elif isinstance(value, list):
        for item in value:
            output.extend(flatten(item, prefix))
    elif value is not None:
        output.append((prefix, normalize(value)))
    return output


def strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [part for item in value.values() for part in strings(item)]
    if isinstance(value, (list, tuple)):
        return [part for item in value for part in strings(item)]
    return [value] if isinstance(value, str) else []


def result_payload(result: Any) -> dict[str, Any]:
    candidate = getattr(result, "json", None)
    if callable(candidate):
        candidate = candidate()
    return candidate if isinstance(candidate, dict) else {"rendered": str(result)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--server-url", default="http://127.0.0.1:8118/v1")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text().splitlines()[: args.limit]]
    native = json.loads(args.native.read_text())
    native_by_id = {row["document_id"]: row for row in native["predictions"]}
    missing = [row["document_id"] for row in rows if row["document_id"] not in native_by_id]
    if missing:
        raise SystemExit(f"native comparison rows missing: {missing}")

    started = time.perf_counter()
    pipeline = PaddleOCRVL(
        pipeline_version="v1.6",
        vl_rec_backend="vllm-server",
        vl_rec_server_url=args.server_url,
        vl_rec_api_model_name="PaddleOCR-VL-1.6-0.9B",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_layout_detection=False,
    )
    load_seconds = time.perf_counter() - started
    predictions, latencies, recalls, total_hits = [], [], [], []
    for row in rows:
        tick = time.perf_counter()
        results = pipeline.predict(row["pages"][0]["image_path"], use_layout_detection=False)
        elapsed = time.perf_counter() - tick
        payloads = [result_payload(result) for result in results]
        text = normalize(" ".join(part for payload in payloads for part in strings(payload)))
        truth = row["ground_truth"].get("gt_parse", row["ground_truth"])
        leaves = [value for _, value in flatten(truth) if value]
        recall = sum(value in text for value in leaves) / len(leaves) if leaves else 0.0
        total_value = normalize(truth.get("total", {}).get("total_price", ""))
        total_hit = bool(total_value) and total_value in text
        latencies.append(elapsed)
        recalls.append(recall)
        total_hits.append(total_hit)
        predictions.append({"document_id": row["document_id"], "extracted_text": text,
                            "leaf_value_recall": recall, "total_value_present": total_hit,
                            "latency_seconds": elapsed, "result_count": len(results)})
    native_rows = [native_by_id[row["document_id"]] for row in rows]
    native_latencies = [float(row["latency_seconds"]) for row in native_rows]
    result = {
        "experiment_id": "V3-E08",
        "model": "PaddleOCR-VL-1.6-0.9B",
        "backend": "Docker vLLM server",
        "server_url": args.server_url,
        "dataset": "CORD v2",
        "split": "validation development",
        "documents": len(rows),
        "same_document_ids_as_native": True,
        "load_seconds": load_seconds,
        "runtime_seconds": sum(latencies),
        "mean_latency_seconds": statistics.mean(latencies),
        "median_latency_seconds": statistics.median(latencies),
        "leaf_value_recall": statistics.mean(recalls),
        "total_value_presence": statistics.mean(total_hits),
        "native_comparison": {
            "artifact": str(args.native),
            "mean_latency_seconds": statistics.mean(native_latencies),
            "median_latency_seconds": statistics.median(native_latencies),
            "leaf_value_recall": statistics.mean(float(row["leaf_value_recall"]) for row in native_rows),
            "total_value_presence": statistics.mean(bool(row["total_value_present"]) for row in native_rows),
        },
        "speedup_mean": statistics.mean(native_latencies) / statistics.mean(latencies),
        "metric_limitation": "Content-presence recall over canonical leaf values; not official structured CORD F1.",
        "predictions": predictions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "predictions"}, sort_keys=True))


if __name__ == "__main__":
    main()
