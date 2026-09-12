from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Processor

from v2_guard import assert_input_allowed
from v2_layoutlmv3 import FunsdDataset, evaluate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=2)
    args = parser.parse_args()
    assert_input_allowed(args.input)
    rows = [json.loads(line) for line in args.input.read_text().splitlines()]
    torch.manual_seed(20260911)
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    processor = LayoutLMv3Processor.from_pretrained(args.checkpoint, apply_ocr=False)
    model = LayoutLMv3ForTokenClassification.from_pretrained(args.checkpoint).to("cuda")
    load_seconds = time.perf_counter() - started
    loader = DataLoader(FunsdDataset(rows, processor), batch_size=args.batch_size, num_workers=2, pin_memory=True)
    metrics = evaluate(model, loader)
    result = {
        "experiment_id": "V2-E18-LAYOUT",
        "model": "microsoft/layoutlmv3-base fine-tuned V2 checkpoint",
        "base_revision": "cfbbbff0762e6aab37086fdd4739ad14fe7d5db4",
        "checkpoint": str(args.checkpoint),
        "dataset": "FUNSD",
        "split": "official test",
        "documents": len(rows),
        "device": torch.cuda.get_device_name(0),
        "physical_gpu_count": 1,
        "precision": "FP32 evaluation of FP16-autocast-trained checkpoint",
        "batch_size": args.batch_size,
        "load_seconds": load_seconds,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "metrics": metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({**{key: value for key, value in result.items() if key != "metrics"}, "metrics": {key: value for key, value in metrics.items() if key not in {"predictions", "labels", "latency_seconds"}}}, sort_keys=True))


if __name__ == "__main__":
    main()
