from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; BASE="72e4f68d1d24f4ef71d614e48da1a4c609cb46f5"


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen() -> int:
    prefixes=("artifacts/","reports/","configs/"); names=("WORKFLOW_STATE.json","EXPERIMENT_REGISTRY.csv","EVIDENCE_MANIFEST.jsonl","BLOCKERS.md","DECISIONS.md","V2_WORKFLOW_STATE.json","V2_EXPERIMENT_REGISTRY.csv","V2_EVIDENCE_MANIFEST.jsonl","V2_BLOCKERS.md","V2_DECISIONS.md","V3_WORKFLOW_STATE.json","V3_EXPERIMENT_REGISTRY.csv","V3_EVIDENCE_MANIFEST.jsonl","V3_BLOCKERS.md","V3_DECISIONS.md")
    checked=0
    for line in subprocess.check_output(["git","ls-tree","-r",BASE],cwd=ROOT,text=True).splitlines():
        metadata,name=line.split("\t",1)
        if (name.startswith(prefixes) and not any(name.startswith(f"{p}v3_1/") for p in prefixes)) or name in names:
            path=ROOT/name
            if not path.is_file(): raise AssertionError(f"frozen path missing: {name}")
            actual=subprocess.check_output(["git","hash-object","--",name],cwd=ROOT,text=True).strip()
            if actual!=metadata.split()[2]: raise AssertionError(f"frozen scientific artifact changed: {name}")
            checked+=1
    return checked


def main() -> None:
    state=json.loads((ROOT/"V3_1_WORKFLOW_STATE.json").read_text()); protocol=json.loads((ROOT/"configs/v3_1/analysis_protocol.json").read_text())
    assert state["analysis_decision"]=="V3_1_ANALYSIS_SUCCESS" and protocol["created_before_locked_slice_results"] is True
    assert protocol["bootstrap"]["replicates"]==2000 and protocol["minimum_support"]["headline"]==20
    manifest=[json.loads(line) for line in (ROOT/"V3_1_EVIDENCE_MANIFEST.jsonl").read_text().splitlines()]; assert manifest
    protocol_hash=sha(ROOT/"configs/v3_1/analysis_protocol.json")
    for row in manifest:
        path=ROOT/row["path"]
        if not path.is_file() or sha(path)!=row["sha256"] or row["protocol_sha256"]!=protocol_hash: raise AssertionError(f"manifest mismatch: {row['path']}")
    with (ROOT/"artifacts/v3_1/data/document_evaluation_table.csv").open(newline="") as h: docs=list(csv.DictReader(h))
    with (ROOT/"artifacts/v3_1/data/field_evaluation_table.csv").open(newline="") as h: fields=list(csv.DictReader(h))
    with (ROOT/"artifacts/v3_1/slicing/slice_metrics.csv").open(newline="") as h: slices=list(csv.DictReader(h))
    with (ROOT/"artifacts/v3_1/robustness/robustness_matrix.csv").open(newline="") as h: robust=list(csv.DictReader(h))
    assert len(docs)==340 and len(fields)==2645 and slices and robust
    assert {r["model"] for r in robust}=={"Donut CORD v2","PaddleOCR-VL-1.6-0.9B"}
    sample=json.loads((ROOT/"artifacts/v3_1/robustness/robustness_sample.json").read_text()); assert len(sample["documents"])==10 and len(sample["cases"])==130
    for name in ["donut_results.json","paddle_results.json"]:
        result=json.loads((ROOT/"artifacts/v3_1/robustness"/name).read_text()); assert result["cases"]==130 and result["maximum_temperature_c"]<=87 and result["maximum_nvidia_smi_memory_used_mib"]/result["gpu_memory_total_mib"]<=.70
    frozen=verify_frozen(); print(json.dumps({"decision":state["analysis_decision"],"manifest_entries":len(manifest),"frozen_scientific_paths_verified":frozen,"documents":len(docs),"fields":len(fields),"robustness_cases_per_model":130},sort_keys=True))


if __name__=="__main__": main()
