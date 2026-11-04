from __future__ import annotations

import argparse
import collections
import json
import re
import time
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor

from v2_guard import assert_input_allowed


MODEL_ID = "PaddlePaddle/PaddleOCR-VL-1.6"
REVISION = "c5630abae1d940eafe0697512a0325494b02ab42"


def flatten(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            output.extend(flatten(item, f"{prefix}.{key}" if prefix else key))
    elif isinstance(value, list):
        for item in value:
            output.extend(flatten(item, prefix))
    elif value is not None:
        output.append((prefix, re.sub(r"\s+", " ", str(value).strip().casefold())))
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    assert_input_allowed(args.input)
    rows = [json.loads(line) for line in args.input.read_text().splitlines()[: args.limit]]
    torch.manual_seed(20260911)
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        attn_implementation="sdpa",
    ).to("cuda").eval()
    processor = AutoProcessor.from_pretrained(args.model_path, trust_remote_code=True)
    load_seconds = time.perf_counter() - started
    predictions: list[dict] = []
    timings: list[float] = []
    totals = [0, 0, 0]
    total_hits: list[bool] = []
    for row in rows:
        image = Image.open(row["pages"][0]["image_path"]).convert("RGB")
        messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": "OCR:"}]}]
        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            images_kwargs={"size": {"shortest_edge": processor.image_processor.min_pixels, "longest_edge": 1280 * 28 * 28}},
        ).to("cuda")
        torch.cuda.synchronize()
        tick = time.perf_counter()
        with torch.inference_mode():
            generated = model.generate(**inputs, max_new_tokens=512, do_sample=False)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - tick
        timings.append(elapsed)
        text = processor.decode(generated[0][inputs["input_ids"].shape[-1] : -1], skip_special_tokens=True)
        normalized = re.sub(r"\s+", " ", text.strip().casefold())
        truth = row["ground_truth"].get("gt_parse", row["ground_truth"])
        leaves = collections.Counter(flatten(truth))
        matched = sum(count for (_, value), count in leaves.items() if value and value in normalized)
        totals[0] += matched
        totals[1] += matched
        totals[2] += sum(leaves.values())
        total_value = re.sub(r"\s+", " ", str(truth.get("total", {}).get("total_price", "")).strip().casefold())
        total_hit = bool(total_value) and total_value in normalized
        total_hits.append(total_hit)
        predictions.append(
            {
                "document_id": row["document_id"],
                "raw_text": text,
                "matched_leaf_values": matched,
                "gold_leaf_values": sum(leaves.values()),
                "leaf_value_recall": matched / sum(leaves.values()) if leaves else 0.0,
                "total_value_present": total_hit,
                "latency_seconds": elapsed,
            }
        )
    matched, predicted_proxy, gold = totals
    recall = matched / gold if gold else 0.0
    result = {
        "experiment_id": "V2-E08",
        "model": MODEL_ID,
        "revision": REVISION,
        "backend": "Transformers element-level OCR",
        "transformers": __import__("transformers").__version__,
        "dataset": "CORD v2",
        "split": "validation",
        "documents": len(rows),
        "device": torch.cuda.get_device_name(0),
        "physical_gpu_count": 1,
        "precision": "BF16",
        "batch_size": 1,
        "load_seconds": load_seconds,
        "runtime_seconds": sum(timings),
        "latency_seconds": timings,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "leaf_value_recall": recall,
        "total_value_presence": sum(total_hits) / len(total_hits),
        "metric_limitation": "Value-presence recall from whole-image OCR output; not official structured CORD F1 or page-level PaddleOCR-VL parsing.",
        "predictions": predictions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in {"predictions", "latency_seconds"}}, sort_keys=True))


if __name__ == "__main__":
    main()
