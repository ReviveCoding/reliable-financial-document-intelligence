from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def summarize(name: str, source: dict, latencies: list[float], units: int) -> dict:
    values = np.asarray(latencies)
    runtime = float(values.sum())
    return {
        "model": name,
        "units": units,
        "cold_load_seconds": source.get("load_seconds"),
        "warm_latency_p50_seconds": float(np.quantile(values, 0.50)),
        "warm_latency_p95_seconds": float(np.quantile(values, 0.95)),
        "warm_latency_p99_seconds": float(np.quantile(values, 0.99)),
        "mean_latency_seconds": float(values.mean()),
        "throughput_units_per_second": units / runtime,
        "peak_vram_bytes": source.get("peak_vram_bytes"),
        "precision": source.get("precision"),
        "batch_size": source.get("batch_size"),
        "device": source.get("device"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    load = lambda name: json.loads((args.results / name).read_text())
    paddle = load("paddleocr_development.json")
    donut = load("donut_development.json")
    qwen = load("qwen3vl_development.json")
    paddle_vl = load("paddleocr_vl_development.json")
    layout = load("layoutlmv3_development.json")
    models = [
        summarize("PP-OCRv5", paddle, paddle["latency_seconds"]["values"], paddle["documents"]),
        summarize("Donut CORD v2", donut, donut["latency_seconds"]["values"], donut["documents"]),
        summarize("Qwen3-VL-4B-Instruct", qwen, qwen["latency_seconds"], len(qwen["latency_seconds"])),
        summarize("PaddleOCR-VL-1.6 whole-image", paddle_vl, paddle_vl["latency_seconds"], paddle_vl["documents"]),
        summarize("LayoutLMv3 evaluation batch", layout, layout["metrics"]["latency_seconds"], len(layout["metrics"]["latency_seconds"])),
    ]
    physical_vram = 16376 * 1024 * 1024
    headroom = 0.30 * physical_vram
    qwen_donut = qwen["peak_vram_bytes"] + donut["peak_vram_bytes"] + headroom
    result = {
        "experiment_id": "V2-E15",
        "physical_gpu": "NVIDIA GeForce RTX 4090 Laptop GPU",
        "physical_gpu_count": 1,
        "physical_vram_bytes_from_nvidia_smi": physical_vram,
        "models": models,
        "concurrency": {
            "qwen_plus_donut_with_30pct_headroom_bytes": qwen_donut,
            "fits_physical_vram": qwen_donut < physical_vram,
            "independent_heavy_jobs_authorized": 1,
            "reason": "The heaviest useful pair fails the configured VRAM formula; no alternate pair was throughput-validated concurrently.",
        },
        "cost_scope": "Measured GPU seconds and throughput only; no electricity tariff was assumed and no paid API was called.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
