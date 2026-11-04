from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import numpy as np
import paddle
import paddleocr
from paddleocr import PaddleOCRVL
from v2_guard import assert_input_allowed


MODEL_NAME = "PaddleOCR-VL-1.6"
OFFICIAL_HF_REVISION = "c5630abae1d940eafe0697512a0325494b02ab42"


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
    output: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            output.extend(strings(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            output.extend(strings(item))
    elif isinstance(value, str):
        output.append(value)
    return output


def result_payload(result: Any) -> dict:
    candidate = getattr(result, "json", None)
    if callable(candidate):
        candidate = candidate()
    return candidate if isinstance(candidate, dict) else {"rendered": str(result)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    assert_input_allowed(args.input)
    rows = [json.loads(line) for line in args.input.read_text().splitlines()[: args.limit]]
    paddle.seed(20260911)
    started = time.perf_counter()
    pipeline = PaddleOCRVL(
        pipeline_version="v1.6",
        vl_rec_backend="native",
        device="gpu:0",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_layout_detection=False,
    )
    load_seconds = time.perf_counter() - started
    predictions: list[dict] = []
    timings: list[float] = []
    recalls: list[float] = []
    total_hits: list[bool] = []
    for row in rows:
        paddle.device.synchronize()
        tick = time.perf_counter()
        results = pipeline.predict(row["pages"][0]["image_path"], use_layout_detection=False)
        paddle.device.synchronize()
        elapsed = time.perf_counter() - tick
        timings.append(elapsed)
        payloads = [result_payload(result) for result in results]
        text = normalize(" ".join(part for payload in payloads for part in strings(payload)))
        truth = row["ground_truth"].get("gt_parse", row["ground_truth"])
        leaves = [value for _, value in flatten(truth) if value]
        hits = [value in text for value in leaves]
        total_value = normalize(truth.get("total", {}).get("total_price", ""))
        total_hit = bool(total_value) and total_value in text
        recalls.append(float(np.mean(hits)) if hits else 0.0)
        total_hits.append(total_hit)
        predictions.append(
            {
                "document_id": row["document_id"],
                "extracted_text": text,
                "leaf_value_recall": recalls[-1],
                "total_value_present": total_hit,
                "result_count": len(results),
                "result_top_level_keys": [sorted(payload.keys()) for payload in payloads],
                "latency_seconds": elapsed,
            }
        )
    result = {
        "experiment_id": "V2-E08",
        "model": MODEL_NAME,
        "verified_official_hf_revision": OFFICIAL_HF_REVISION,
        "actual_model_source": "PaddleOCR official model registry via PaddleOCRVL",
        "backend": "native",
        "paddleocr": paddleocr.__version__,
        "paddle": "3.3.0",
        "dataset": "CORD v2",
        "split": "validation",
        "documents": len(rows),
        "device": paddle.device.cuda.get_device_name(),
        "physical_gpu_count": 1,
        "precision": "native backend default",
        "batch_size": 1,
        "load_seconds": load_seconds,
        "runtime_seconds": float(sum(timings)),
        "latency_seconds": timings,
        "peak_vram_bytes": paddle.device.cuda.max_memory_allocated(),
        "leaf_value_recall": float(np.mean(recalls)),
        "total_value_presence": float(np.mean(total_hits)),
        "metric_limitation": "Content-presence recall over canonical leaf values; not official structured CORD F1.",
        "predictions": predictions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in {"predictions", "latency_seconds"}}, sort_keys=True))


if __name__ == "__main__":
    main()
