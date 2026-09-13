from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "configs/v3_2/risk_protocol.json"
ERRATUM = ROOT / "configs/v3_2/methodology_erratum.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


protocol_sha = sha(PROTOCOL)
erratum_sha = sha(ERRATUM)
evidence_paths = sorted(
    [path for base in (ROOT / "artifacts/v3_2", ROOT / "reports/v3_2", ROOT / "docs/assets/v3_2") for path in base.rglob("*") if path.is_file()]
    + [PROTOCOL,ERRATUM]
)
manifest = []
for path in evidence_paths:
    manifest.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path), "bytes": path.stat().st_size, "original_protocol_sha256": protocol_sha,"methodology_erratum_sha256":erratum_sha,"correction_replay_designation":"METHODOLOGY_CORRECTION_REPLAY"})
(ROOT / "V3_2_EVIDENCE_MANIFEST.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in manifest))

registry = [
    ["V3.2-E00", "protocol_freeze", "COMPLETE", "239824f", "configs/v3_2/risk_protocol.json"],
    ["V3.2-E01", "synthetic_line_item_evaluator", "PASS_15_CASES", "METHODOLOGY_CORRECTION", "tests/test_v3_2_line_item_evaluation.py"],
    ["V3.2-E02", "corrected_row_aware_line_item_evaluation", "COMPLETE", "METHODOLOGY_CORRECTION_REPLAY", "artifacts/v3_2/line_items/retrospective_test/aggregate_metrics.json"],
    ["V3.2-E03", "production_safe_feature_table", "COMPLETE_NO_LEAKAGE", "CORRECTION_REPLAY_AND_RETROSPECTIVE", "artifacts/v3_2/data/risk_feature_table.csv"],
    ["V3.2-E04", "grouped_cv_risk_model_correction_replay", "R4_BEST_LEARNED_R0_BEST_OVERALL", "DEVELOPMENT_CORRECTION_REPLAY", "artifacts/v3_2/risk_model/development_selection/frozen_selection.json"],
    ["V3.2-E05", "finite_sample_certification_replay", "NO_FRESH_CERTIFICATE", "POST_AUDIT_REUSED_CERTIFICATION_PARTITION", "artifacts/v3_2/risk_control/certification_results.csv"],
    ["V3.2-E06", "retrospective_risk_benchmark", "COMPLETE_NO_RETUNING", "RETROSPECTIVE_LOCKED_BENCHMARK", "artifacts/v3_2/risk_control/evaluation_summary.json"],
    ["V3.2-E07", "risk_ranker_robustness", "COMPLETE_REUSED_V3_1", "RISK_SENSITIVITY_PROXY_NOT_END_TO_END_INFERENCE", "artifacts/v3_2/robustness/robustness_risk_response_summary.csv"],
    ["V3.2-E08", "shadow_runtime", "NOT_INTEGRATED_GATE_FAILED", "OFFLINE_ONLY", "artifacts/v3_2/risk_control/shadow_runtime_status.json"],
    ["V3.2-E09", "external_validation", "HUMAN_ACTION_REQUIRED_OPTIONAL", "NOT_BLOCKING", "artifacts/v3_2/external_validation/readiness.json"],
    ["V3.2-E10", "mlflow_analysis_logging", "COMPLETE", "LOCAL_COMPOSE", "artifacts/v3_2/mlflow/analysis_run.json"],
    ["V3.2-E11", "methodology_erratum", "FROZEN_BEFORE_CORRECTION", "AUDIT", "configs/v3_2/methodology_erratum.json"],
    ["V3.2-E12", "label_transition_audit", "COMPLETE", "METHODOLOGY_CORRECTION_REPLAY", "artifacts/v3_2/audit/label_transition_summary.json"],
]
with (ROOT / "V3_2_EXPERIMENT_REGISTRY.csv").open("w", newline="") as handle:
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(["experiment_id", "experiment", "status", "designation", "evidence"])
    writer.writerows(registry)

state = {
    "workflow": "R-FDI v3.2 Critical Risk Control & Line-Item Reliability",
    "status": "COMPLETE",
    "decision": "V3_2_RISK_MODEL_NO_PROMOTION",
    "baseline_commit": "00cf00516fc28a4716d29a9c65f49cc482d57db7",
    "protocol_commit": "239824f",
    "methodology_erratum_commit":"081ba8f",
    "corrected_replay_freeze_commit":"274a2c0",
    "original_selection_freeze_commit": "3532686",
    "protocol_sha256": protocol_sha,
    "methodology_erratum_sha256":erratum_sha,
    "correction_replay_designation":"METHODOLOGY_CORRECTION_REPLAY",
    "fresh_confirmatory_evidence":False,
    "promotion_eligible":False,
    "extractor_weights_changed": False,
    "cord_test_designation": "RETROSPECTIVE_LOCKED_BENCHMARK",
    "cord_test_is_fresh_holdout": False,
    "shadow_runtime_integrated": False,
    "manifest_entries": len(manifest),
    "optional_blockers": ["DocILE authorized access/token absent"],
}
(ROOT / "V3_2_WORKFLOW_STATE.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
(ROOT / "V3_2_DECISIONS.md").write_text("""# V3.2 decisions

- Final decision: `V3_2_RISK_MODEL_NO_PROMOTION`.
- Preserve the corrected-target R4 replay as offline negative evidence; R0 raw confidence remains the stronger evaluated ranker.
- Do not integrate shadow API fields because the frozen development promotion gates failed.
- Treat CORD test only as `RETROSPECTIVE_LOCKED_BENCHMARK`; it is not a fresh holdout and was not used to retune.
- Keep extractor weights unchanged.
- Use E2 permutation-invariant matching as the primary line-item metric and retain E0 for historical comparison.
- Report certification only as a non-confirmatory replay of an already-observed partition; no replay result is promotion-eligible.
- Preserve `1078332` and the pre-correction artifact hashes in the audit trail.
""")
(ROOT / "V3_2_BLOCKERS.md").write_text("""# V3.2 blockers

- **DocILE — `HUMAN_ACTION_REQUIRED_OPTIONAL`:** no authorized local dataset/token is available. Official access controls were not bypassed. This does not block the v3.2 retrospective analysis or its no-promotion decision.
- **Fresh external LIR validation:** still missing. Corrected replay cannot support promotion; reconsideration requires a larger genuinely fresh grouped certification sample and authorized external line-item evidence.
- No mandatory implementation blocker remains.
""")
print(json.dumps({"decision": state["decision"], "manifest_entries": len(manifest), "protocol_sha256": protocol_sha,"methodology_erratum_sha256":erratum_sha}, sort_keys=True))
