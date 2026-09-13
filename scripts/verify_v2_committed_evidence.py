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
    assert all(
        item["status"] in {"COMPLETE", "FAILED", "BLOCKED", "SKIPPED_WITH_REASON"}
        for item in state["phases"].values()
    )

    with (ROOT / "V2_EXPERIMENT_REGISTRY.csv").open(newline="") as handle:
        registry = list(csv.DictReader(handle))
    assert registry and len({row["experiment_id"] for row in registry}) == len(registry)
    assert all(row["status"] not in {"PENDING", "RUNNING"} for row in registry)

    records = [
        json.loads(line)
        for line in (ROOT / "V2_EVIDENCE_MANIFEST.jsonl").read_text().splitlines()
        if line.strip()
    ]
    for record in records:
        path = record.get("artifact") or record.get("path")
        if not path:
            continue
        target = ROOT / path
        assert target.exists(), target
        if "sha256" in record:
            assert hashlib.sha256(target.read_bytes()).hexdigest() == record["sha256"], target

    frozen = json.loads((ROOT / "configs/v2/frozen.json").read_text())
    locked_hashes = frozen["locked_inputs"]
    assert set(locked_hashes) == {
        "cord_test_jsonl_sha256",
        "funsd_test_jsonl_sha256",
        "synthetic_final_jsonl_sha256",
    }
    assert all(len(value) == 64 for value in locked_hashes.values())

    decision = json.loads((ROOT / "artifacts/v2/release/decision.json").read_text())
    assert decision["thresholds"] == frozen["release_gates"]
    expected = "PROMOTE" if all(decision["gates"].values()) else "NO_PROMOTION"
    assert decision["release_decision"] == expected
    assert decision["failed_gates"] == [
        name for name, passed in decision["gates"].items() if not passed
    ]
    assert decision["statistics"]["paired_documents"] == 95

    print(
        json.dumps(
            {
                "decision": expected,
                "evidence_records": len(records),
                "experiments": len(registry),
                "locked_input_hashes_declared": len(locked_hashes),
                "mode": "committed-evidence-only",
                "phases": len(state["phases"]),
                "status": "PASS",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
