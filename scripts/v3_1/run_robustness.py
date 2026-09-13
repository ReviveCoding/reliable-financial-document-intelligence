from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = json.loads((ROOT / "configs/v3_1/analysis_protocol.json").read_text())
SEED = int(PROTOCOL["robustness"]["seed"])
MODEL_ID = "naver-clova-ix/donut-base-finetuned-cord-v2"
MODEL_REVISION = "8003d433113256b4ce3a0f5bf604b29ff78a7451"


def normalize(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip().casefold())


def flatten(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            out.extend(flatten(item, f"{prefix}.{key}" if prefix else key))
    elif isinstance(value, list):
        for item in value:
            out.extend(flatten(item, prefix))
    elif value is not None:
        out.append((prefix, normalize(value)))
    return out


def score(prediction: Any, truth: Any) -> tuple[int, int, int]:
    pred = collections.Counter(flatten(prediction)); gold = collections.Counter(flatten(truth))
    return sum((pred & gold).values()), sum(pred.values()), sum(gold.values())


def content_recall(text: str, truth: Any, critical_only: bool = False) -> float:
    prefixes = tuple(PROTOCOL["field_criticality"]["critical_monetary"])
    leaves = [v for k, v in flatten(truth) if v and (not critical_only or any(k == p or k.startswith(p + ".") for p in prefixes))]
    return sum(v in text for v in leaves) / len(leaves) if leaves else 1.0


def gpu_state() -> tuple[int, int, int]:
    line = subprocess.check_output(["nvidia-smi", "--query-gpu=temperature.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"], text=True).splitlines()[0]
    return tuple(int(part.strip()) for part in line.split(","))  # type: ignore[return-value]


def cool_if_needed() -> tuple[int, int, int]:
    state = gpu_state()
    while state[0] > int(PROTOCOL["robustness"]["gpu_pause_temperature_c"]):
        time.sleep(15); state = gpu_state()
    return state


def corrupt(image: np.ndarray, name: str, params: dict[str, Any], rng: np.random.Generator) -> np.ndarray:
    h, w = image.shape[:2]
    if name == "gaussian_blur":
        k = int(params["kernel"]); return cv2.GaussianBlur(image, (k, k), float(params["sigma"]))
    if name == "rotation":
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), float(params["degrees"]), 1); return cv2.warpAffine(image, matrix, (w, h), borderValue=(255, 255, 255))
    if name == "downsampling":
        scale = float(params["scale"]); small = cv2.resize(image, (max(1, round(w * scale)), max(1, round(h * scale))), interpolation=cv2.INTER_AREA); return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    if name == "jpeg":
        ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, int(params["quality"])]); assert ok; return cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if name == "contrast":
        return np.clip((image.astype(np.float32) - 127.5) * float(params["factor"]) + 127.5, 0, 255).astype(np.uint8)
    if name == "occlusion":
        out = image.copy(); fraction = float(params["area_fraction"]); oh = max(1, round(h * np.sqrt(fraction))); ow = max(1, round(w * np.sqrt(fraction))); x = int(rng.integers(0, max(1, w - ow + 1))); y = int(rng.integers(0, max(1, h - oh + 1))); out[y:y+oh, x:x+ow] = 255; return out
    raise ValueError(name)


def prepare(input_path: Path, runtime_dir: Path, output: Path) -> None:
    rows = [json.loads(x) for x in input_path.read_text().splitlines()[:20]]
    cuts = PROTOCOL["cutpoint_derivation"]["values"]["ground_truth_leaf_count"]
    by_band: dict[str, list[dict[str, Any]]] = {"low": [], "mid": [], "high": []}
    for row in rows:
        n = len(flatten(row["ground_truth"].get("gt_parse", row["ground_truth"])))
        band = "low" if n <= cuts[0] else "mid" if n <= cuts[1] else "high"; by_band[band].append(row)
    rng = np.random.default_rng(SEED); selected=[]
    # The predeclared 20-document Paddle comparison frame contains 7/11/2
    # low/mid/high cases, so allocate 4/4/2 without replacement.
    for band, count in (("low", 4), ("mid", 4), ("high", 2)):
        selected.extend(by_band[band][i] for i in sorted(rng.choice(len(by_band[band]), count, replace=False).tolist()))
    runtime_dir.mkdir(parents=True, exist_ok=True); cases=[]
    for doc_index, row in enumerate(selected):
        source = Path(row["pages"][0]["image_path"]); image = cv2.imread(str(source)); assert image is not None
        variants = [("clean", "clean", {}, image)]
        for corruption, levels in PROTOCOL["robustness"]["corruptions"].items():
            for level in levels:
                params = {k: v for k, v in level.items() if k != "severity"}
                variant_rng = np.random.default_rng(SEED + doc_index * 100 + len(variants))
                variants.append((corruption, level["severity"], params, corrupt(image, corruption, params, variant_rng)))
        for corruption, severity, params, pixels in variants:
            path = runtime_dir / f"{row['document_id']}__{corruption}__{severity}.png"; cv2.imwrite(str(path), pixels)
            cases.append({"document_id": row["document_id"], "image_path": str(path), "source_image_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "corruption": corruption, "severity": severity, "parameters": params, "truth": row["ground_truth"].get("gt_parse", row["ground_truth"])})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"experiment_id":"V3.1-E08","label":"DEVELOPMENT_ONLY_CONTROLLED_ROBUSTNESS","seed":SEED,"selection_frame":"first 20 frozen CORD validation documents, matching available PaddleOCR-VL development evidence","selection":"deterministic stratification across protocol-frozen leaf-count bands","documents":[r["document_id"] for r in selected],"cases":cases}, indent=2, sort_keys=True)+"\n")


def donut(manifest: Path, output: Path) -> None:
    import torch
    from transformers import DonutProcessor, VisionEncoderDecoderModel
    payload=json.loads(manifest.read_text()); torch.manual_seed(SEED); torch.cuda.reset_peak_memory_stats()
    processor=DonutProcessor.from_pretrained(MODEL_ID,revision=MODEL_REVISION); model=VisionEncoderDecoderModel.from_pretrained(MODEL_ID,revision=MODEL_REVISION,torch_dtype=torch.float16).to("cuda").eval()
    decoder_input_ids=processor.tokenizer("<s_cord-v2>",add_special_tokens=False,return_tensors="pt").input_ids.to("cuda"); results=[]; max_temp=0; max_used=0; total_mem=0
    for case in payload["cases"]:
        temp,used,total=cool_if_needed(); max_temp=max(max_temp,temp); max_used=max(max_used,used); total_mem=total
        pixels=processor(Image.open(case["image_path"]).convert("RGB"),return_tensors="pt").pixel_values.to("cuda",dtype=torch.float16); torch.cuda.synchronize(); tick=time.perf_counter()
        with torch.inference_mode():
            generated=model.generate(pixels,decoder_input_ids=decoder_input_ids,max_length=model.decoder.config.max_position_embeddings,early_stopping=True,pad_token_id=processor.tokenizer.pad_token_id,eos_token_id=processor.tokenizer.eos_token_id,use_cache=True,bad_words_ids=[[processor.tokenizer.unk_token_id]])
        torch.cuda.synchronize(); latency=time.perf_counter()-tick; sequence=processor.batch_decode(generated)[0].replace(processor.tokenizer.eos_token,"").replace(processor.tokenizer.pad_token,""); sequence=re.sub(r"<.*?>","",sequence,count=1).strip()
        try: parsed=processor.token2json(sequence)
        except Exception: parsed={"_parse_failure":sequence}
        tp,pred,gold=score(parsed,case["truth"]); precision=tp/pred if pred else 0; recall=tp/gold if gold else 0
        results.append({k:case[k] for k in ("document_id","corruption","severity")} | {"latency_seconds":latency,"leaf_f1":2*precision*recall/(precision+recall) if precision+recall else 0,"content_presence_recall":content_recall(normalize(sequence),case["truth"]),"critical_content_presence_recall":content_recall(normalize(sequence),case["truth"],True),"schema_valid":"_parse_failure" not in parsed})
    output.write_text(json.dumps({"experiment_id":"V3.1-E08-DONUT","model":"Donut CORD v2","revision":MODEL_REVISION,"device":torch.cuda.get_device_name(0),"precision":"FP16","cases":len(results),"maximum_temperature_c":max_temp,"maximum_nvidia_smi_memory_used_mib":max_used,"gpu_memory_total_mib":total_mem,"peak_torch_allocated_bytes":torch.cuda.max_memory_allocated(),"results":results},indent=2,sort_keys=True)+"\n")


def result_payload(result: Any) -> dict[str, Any]:
    candidate=getattr(result,"json",None); candidate=candidate() if callable(candidate) else candidate
    return candidate if isinstance(candidate,dict) else {"rendered":str(result)}


def paddle(manifest: Path, output: Path, server_url: str) -> None:
    from paddleocr import PaddleOCRVL
    payload=json.loads(manifest.read_text()); pipeline=PaddleOCRVL(pipeline_version="v1.6",vl_rec_backend="vllm-server",vl_rec_server_url=server_url,vl_rec_api_model_name="PaddleOCR-VL-1.6-0.9B",use_doc_orientation_classify=False,use_doc_unwarping=False,use_layout_detection=False)
    results=[]; max_temp=0; max_used=0; total_mem=0
    for case in payload["cases"]:
        temp,used,total=cool_if_needed(); max_temp=max(max_temp,temp); max_used=max(max_used,used); total_mem=total; tick=time.perf_counter(); predictions=pipeline.predict(case["image_path"],use_layout_detection=False); latency=time.perf_counter()-tick
        text=normalize(" ".join(part for item in predictions for part in strings(result_payload(item))))
        results.append({k:case[k] for k in ("document_id","corruption","severity")} | {"latency_seconds":latency,"content_presence_recall":content_recall(text,case["truth"]),"critical_content_presence_recall":content_recall(text,case["truth"],True),"result_count":len(predictions)})
    output.write_text(json.dumps({"experiment_id":"V3.1-E08-PADDLE","model":"PaddleOCR-VL-1.6-0.9B","backend":"Docker/vLLM CUDA","server_url":server_url,"cases":len(results),"maximum_temperature_c":max_temp,"maximum_nvidia_smi_memory_used_mib":max_used,"gpu_memory_total_mib":total_mem,"results":results},indent=2,sort_keys=True)+"\n")


def strings(value: Any) -> list[str]:
    if isinstance(value,dict): return [part for item in value.values() for part in strings(item)]
    if isinstance(value,(list,tuple)): return [part for item in value for part in strings(item)]
    return [value] if isinstance(value,str) else []


def aggregate(manifest: Path, inputs: list[Path], output: Path) -> None:
    sample=json.loads(manifest.read_text())
    rows=[]
    for path in inputs:
        payload=json.loads(path.read_text()); model=payload["model"]
        grouped: dict[tuple[str,str],list[dict[str,Any]]]={}
        for row in payload["results"]: grouped.setdefault((row["corruption"],row["severity"]),[]).append(row)
        clean=grouped[("clean","clean")]
        for (corruption,severity), values in grouped.items():
            for metric in ("content_presence_recall","critical_content_presence_recall","latency_seconds") + (("leaf_f1",) if model.startswith("Donut") else ()):
                val=statistics.mean(float(r[metric]) for r in values); base=statistics.mean(float(r[metric]) for r in clean)
                rows.append({"model":model,"corruption":corruption,"severity":severity,"support_n":len(values),"metric":metric,"value":val,"clean_reference":base,"absolute_delta":val-base,"development_only":True})
    output.parent.mkdir(parents=True,exist_ok=True)
    import csv
    with output.open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    for case in sample["cases"]:
        case.pop("image_path",None)
    sample["runtime_images"]="Generated outside the repository; rerun the prepare command from authorized inputs."
    manifest.write_text(json.dumps(sample,indent=2,sort_keys=True)+"\n")


def main() -> None:
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("prepare"); p.add_argument("--input",type=Path,required=True); p.add_argument("--runtime-dir",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
    for name in ("donut","paddle"):
        p=sub.add_parser(name); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--server-url",default="http://127.0.0.1:8118/v1")
    p=sub.add_parser("aggregate"); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--inputs",type=Path,nargs="+",required=True); p.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.command=="prepare": prepare(args.input,args.runtime_dir,args.output)
    elif args.command=="donut": donut(args.manifest,args.output)
    elif args.command=="paddle": paddle(args.manifest,args.output,args.server_url)
    else: aggregate(args.manifest,args.inputs,args.output)


if __name__=="__main__": main()
