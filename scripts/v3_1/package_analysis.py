from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    protocol=ROOT/"configs/v3_1/analysis_protocol.json"; protocol_hash=sha(protocol)
    experiments=[
        ["V3.1-E01","Canonical document and field evaluation tables","COMPLETE","artifacts/v3_1/data/document_evaluation_table.csv;artifacts/v3_1/data/field_evaluation_table.csv","Frozen predictions; no locked inference rerun"],
        ["V3.1-E02","Predeclared statistical slicing","COMPLETE","artifacts/v3_1/slicing/slice_metrics.csv","2,000 deterministic replicates; BH FDR"],
        ["V3.1-E03","Field and error taxonomy","COMPLETE","artifacts/v3_1/errors/error_level_dataset.csv","Ambiguous class retained where needed"],
        ["V3.1-E04","Paired and mix-shift analysis","COMPLETE","artifacts/v3_1/slicing/mix_shift_analysis.json","Identical eligible document IDs"],
        ["V3.1-E05","Calibration and selective risk","COMPLETE","artifacts/v3_1/calibration/calibration_metrics.json;artifacts/v3_1/selective_risk/review_budget_metrics.csv","Genuine Donut sequence confidence only"],
        ["V3.1-E06","Business-policy sensitivity","COMPLETE","artifacts/v3_1/business/policy_frontier.csv","Illustrative normalized costs"],
        ["V3.1-E07","Exploratory failure discovery","COMPLETE","artifacts/v3_1/discovery/failure_tree.json","Exploratory label; depth <=3"],
        ["V3.1-E08","Controlled development robustness","COMPLETE","artifacts/v3_1/robustness/robustness_matrix.csv","Single-GPU Donut then Paddle Docker/vLLM"],
        ["V3.1-E09","Simulated drift monitoring","COMPLETE","artifacts/v3_1/drift/drift_metrics.csv","Stress simulation; not production drift"],
        ["V3.1-E10","Dataset access assessment","PARTIAL_OPTIONAL","reports/v3_1/DESKTOP_STUDY.md","SROIE and DocILE require human authorization"],
        ["V3.1-E11","Visualization and reporting package","COMPLETE","docs/assets/v3_1;reports/v3_1","Generated from evidence"],
        ["V3.1-E12","Separate MLflow analysis logging","COMPLETE","artifacts/v3_1/mlflow/mlflow_logging.json","New experiment; V3 runs untouched"],
    ]
    with (ROOT/"V3_1_EXPERIMENT_REGISTRY.csv").open("w",newline="") as stream:
        writer=csv.writer(stream,lineterminator="\n"); writer.writerow(["experiment_id","name","status","evidence","notes"]); writer.writerows(experiments)
    state={"version":"3.1.0","branch":"analysis-slicing-v3.1","baseline_commit":"72e4f68d1d24f4ef71d614e48da1a4c609cb46f5","protocol_sha256":protocol_hash,"analysis_decision":"V3_1_ANALYSIS_SUCCESS","locked_model_inference_rerun":False,"model_weights_changed":False,"phases":{"canonical_tables":"COMPLETE","primary_slicing":"COMPLETE","error_taxonomy":"COMPLETE","statistical_uncertainty":"COMPLETE","mix_shift":"COMPLETE","calibration":"COMPLETE","selective_risk":"COMPLETE","business_policy":"COMPLETE","development_robustness":"COMPLETE","failure_discovery":"COMPLETE","simulated_drift":"COMPLETE","visualizations":"COMPLETE","reports":"COMPLETE","mlflow":"COMPLETE","external_datasets":"PARTIAL_OPTIONAL"}}
    (ROOT/"V3_1_WORKFLOW_STATE.json").write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
    (ROOT/"V3_1_DECISIONS.md").write_text("""# V3.1 decisions

## V3_1_ANALYSIS_SUCCESS

The predeclared analysis requirements are complete. V3.1 changes no model weights and does not alter V1 `NO_PROMOTION`, V2 `PROMOTE`, or V3 `V3_EXTENSION_SUCCESS`. Calibration uses genuine Donut sequence confidence; critical-total calibration is not interpreted because outcome variation is insufficient. Controlled robustness is development-only. Simulated drift is not production drift. Business costs are illustrative normalized weights.
""")
    (ROOT/"V3_1_BLOCKERS.md").write_text("""# V3.1 blockers

- **SROIE — HUMAN_ACTION_REQUIRED (optional):** no authorized local RRC copy; registration may not be bypassed.
- **DocILE — HUMAN_ACTION_REQUIRED (optional):** no authorized local access/token; access controls may not be bypassed.
- **Critical-total calibration — NOT_APPLICABLE_WITH_REASON:** only one eligible total error in the locked test, insufficient for a stable calibration claim.

These optional/access-limited items do not block the completed v3.1 requirements.
""")
    candidates=[]
    for base in [ROOT/"artifacts/v3_1",ROOT/"reports/v3_1",ROOT/"docs/assets/v3_1",ROOT/"configs/v3_1",ROOT/"scripts/v3_1",ROOT/"tests/v3_1"]:
        if base.exists(): candidates.extend(p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    candidates += [ROOT/"docs/generate_v3_1_visualizations.py",ROOT/"tests/test_v3_1_analysis.py",ROOT/"V3_1_WORKFLOW_STATE.json",ROOT/"V3_1_EXPERIMENT_REGISTRY.csv",ROOT/"V3_1_DECISIONS.md",ROOT/"V3_1_BLOCKERS.md"]
    rows=[]
    for path in sorted(set(candidates)):
        rows.append({"path":str(path.relative_to(ROOT)),"sha256":sha(path),"size_bytes":path.stat().st_size,"protocol_sha256":protocol_hash})
    (ROOT/"V3_1_EVIDENCE_MANIFEST.jsonl").write_text("".join(json.dumps(row,sort_keys=True)+"\n" for row in rows))


if __name__=="__main__": main()
