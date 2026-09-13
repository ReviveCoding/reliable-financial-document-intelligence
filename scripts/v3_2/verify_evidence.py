from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "00cf00516fc28a4716d29a9c65f49cc482d57db7"
DECISION = "V3_2_RISK_MODEL_NO_PROMOTION"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_history() -> int:
    prefixes = ("artifacts/", "reports/", "configs/")
    governance = ("WORKFLOW_STATE.json", "EXPERIMENT_REGISTRY.csv", "EVIDENCE_MANIFEST.jsonl", "BLOCKERS.md", "DECISIONS.md", "V2_", "V3_", "V3_1_")
    checked = 0
    listing = subprocess.check_output(["git", "ls-tree", "-r", BASELINE], cwd=ROOT, text=True)
    for line in listing.splitlines():
        metadata, name = line.split("\t", 1)
        scientific = name.startswith(prefixes) or name in governance[:5] or name.startswith(governance[5:])
        if not scientific or "/v3_2/" in name or name.startswith("V3_2_"):
            continue
        path = ROOT / name
        if not path.is_file():
            raise AssertionError(f"frozen historical path missing: {name}")
        if subprocess.check_output(["git", "hash-object", "--", name], cwd=ROOT, text=True).strip() != metadata.split()[2]:
            raise AssertionError(f"frozen historical artifact changed: {name}")
        checked += 1
    return checked


def read(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    protocol_path = ROOT / "configs/v3_2/risk_protocol.json"
    protocol = json.loads(protocol_path.read_text())
    protocol_hash = sha(protocol_path)
    state = json.loads((ROOT / "V3_2_WORKFLOW_STATE.json").read_text())
    assert state["decision"] == DECISION and state["status"] == "COMPLETE"
    assert state["protocol_sha256"] == protocol_hash
    assert protocol["scientific_scope"]["cord_test_designation"] == "RETROSPECTIVE_LOCKED_BENCHMARK"
    assert protocol["scientific_scope"]["cord_test_is_fresh_holdout"] is False
    assert protocol["scientific_scope"]["extractor_weights_changed"] is False
    assert protocol["determinism"]["bootstrap_replicates"] == 2000

    manifest = [json.loads(line) for line in (ROOT / "V3_2_EVIDENCE_MANIFEST.jsonl").read_text().splitlines()]
    assert len(manifest) == state["manifest_entries"] >= 50
    for row in manifest:
        path = ROOT / row["path"]
        assert path.is_file(), f"manifest file missing: {row['path']}"
        assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"], f"manifest mismatch: {row['path']}"
        assert row["protocol_sha256"] == protocol_hash

    dictionary = read("artifacts/v3_2/data/risk_feature_dictionary.csv")
    allowed = set(protocol["feature_policy"]["allowed_tags"])
    eligible = [row for row in dictionary if row["eligible_for_risk_model"] == "True"]
    assert eligible and all(row["availability_tag"] in allowed for row in eligible)
    forbidden = set(protocol["feature_policy"]["ground_truth_features_forbidden"])
    assert not forbidden.intersection(row["feature"] for row in eligible)
    assert not any("disagreement" in row["feature"] for row in eligible)

    development = read("artifacts/v3_2/data/development_risk_feature_table.csv")
    test = read("artifacts/v3_2/data/retrospective_risk_feature_table.csv")
    assert len(development) == 100 and len(test) == 100
    assert {row["designation"] for row in test} == {"RETROSPECTIVE_LOCKED_BENCHMARK"}
    partitions = {name: sum(row["development_partition"] == name for row in development) for name in ("FIT", "THRESHOLD_SELECTION", "INDEPENDENT_CERTIFICATION")}
    assert partitions == {"FIT": 60, "THRESHOLD_SELECTION": 20, "INDEPENDENT_CERTIFICATION": 20}

    line = json.loads((ROOT / "artifacts/v3_2/line_items/retrospective_test/aggregate_metrics.json").read_text())
    assert line["documents"] == 100 and line["designation"] == "RETROSPECTIVE_LOCKED_BENCHMARK"
    assert line["document_mean_metrics"]["E2_line_item_f1"] > line["document_mean_metrics"]["E0_historical_flat_f1"]
    selection = json.loads((ROOT / "artifacts/v3_2/risk_model/development_selection/frozen_selection.json").read_text())
    assert selection["selected_candidate"] == "R4" and selection["best_overall_candidate"] == "R0"
    assert selection["certification_outcomes_evaluated"] is False and selection["retrospective_test_accessed"] is False
    assert selection["model_artifact_sha256"] == sha(ROOT / "artifacts/v3_2/risk_model/development_selection/selected_risk_model.joblib")
    gates = json.loads((ROOT / "artifacts/v3_2/risk_control/promotion_gates.json").read_text())
    assert gates["decision"] == DECISION and gates["production_feature_leakage_count"] == 0
    certificates = read("artifacts/v3_2/risk_control/certification_results.csv")
    assert {row["status"] for row in certificates} == {"INSUFFICIENT_CERTIFICATION_SUPPORT", "UNCERTIFIED"}
    runtime = json.loads((ROOT / "artifacts/v3_2/risk_control/shadow_runtime_status.json").read_text())
    assert runtime["candidate_exposed_in_api"] is False and runtime["existing_action_semantics_changed"] is False
    assert len(list((ROOT / "docs/assets/v3_2").glob("*.svg"))) == 15
    frozen = frozen_history()
    print(json.dumps({"decision": DECISION, "manifest_entries": len(manifest), "frozen_historical_paths_verified": frozen, "development_documents": len(development), "retrospective_documents": len(test), "line_evaluator_cases": 10, "leakage_count": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
