from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = json.loads((ROOT / "V2_WORKFLOW_STATE.json").read_text())
    assert state["evaluation_state"] == "V2_FINAL_EVAL_COMPLETE"
    assert state["release_decision"] in {"PROMOTE", "NO_PROMOTION"}
    assert all(item["status"] in {"COMPLETE", "FAILED", "BLOCKED", "SKIPPED_WITH_REASON"} for item in state["phases"].values())

    with (ROOT / "V2_EXPERIMENT_REGISTRY.csv").open(newline="") as handle:
        registry = list(csv.DictReader(handle))
    assert registry and len({row["experiment_id"] for row in registry}) == len(registry)
    assert all(row["status"] not in {"PENDING", "RUNNING"} for row in registry)

    records = [json.loads(line) for line in (ROOT / "V2_EVIDENCE_MANIFEST.jsonl").read_text().splitlines() if line.strip()]
    for record in records:
        path = record.get("artifact") or record.get("path")
        if not path:
            continue
        target = ROOT / path
        assert target.exists(), target
        if "sha256" in record:
            assert hashlib.sha256(target.read_bytes()).hexdigest() == record["sha256"], target

    frozen = json.loads((ROOT / "configs/v2/frozen.json").read_text())
    runtime_data = Path("/home/bjw-0/.local/share/rfdi-runtime/data/processed")
    locked_inputs = {
        "cord_test_jsonl_sha256": runtime_data / "cord_v2/7f0115a4b758a71d6473b8d085751692da2fef98/test.jsonl",
        "funsd_test_jsonl_sha256": runtime_data / "funsd/official-2019/test.jsonl",
        "synthetic_final_jsonl_sha256": runtime_data / "rfdi_synthetic_v2/final.jsonl",
    }
    for key, path in locked_inputs.items():
        assert path.exists(), path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == frozen["locked_inputs"][key], path
    decision = json.loads((ROOT / "artifacts/v2/release/decision.json").read_text())
    assert decision["thresholds"] == frozen["release_gates"]
    assert decision["release_decision"] == ("PROMOTE" if all(decision["gates"].values()) else "NO_PROMOTION")
    assert decision["failed_gates"] == [name for name, passed in decision["gates"].items() if not passed]
    assert decision["statistics"]["paired_documents"] == 95

    print(json.dumps({"decision": decision["release_decision"], "evidence_records": len(records), "experiments": len(registry), "locked_input_hashes": len(locked_inputs), "phases": len(state["phases"]), "status": "PASS"}, sort_keys=True))


if __name__ == "__main__":
    main()
