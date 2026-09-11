from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TERMINAL = {"COMPLETE", "FAILED", "BLOCKED", "SKIPPED_WITH_REASON"}


def main() -> None:
    state = json.loads((ROOT / "WORKFLOW_STATE.json").read_text())
    incomplete = {key: value["status"] for key, value in state["phases"].items() if value["status"] not in TERMINAL}
    if incomplete and set(incomplete) != {"P49", "P50"}:
        raise SystemExit(f"unexpected nonterminal phases: {incomplete}")
    for line_number, line in enumerate((ROOT / "EVIDENCE_MANIFEST.jsonl").read_text().splitlines(), 1):
        item = json.loads(line)
        path = ROOT / item["path"]
        if not path.exists(): raise SystemExit(f"line {line_number}: missing {path}")
        if item.get("sha256"):
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != item["sha256"]: raise SystemExit(f"line {line_number}: hash mismatch {path}")
    final = json.loads((ROOT / "artifacts/results/e20_final.json").read_text())
    assert final["method"] == "P0_rfdi_deterministic_v1"
    assert state["release_decision"] == "NO_PROMOTION"
    print(json.dumps({"status":"VERIFIED","evidence_records":line_number,"permitted_nonterminal":incomplete}, sort_keys=True))


if __name__ == "__main__": main()
