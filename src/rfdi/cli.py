from __future__ import annotations

import argparse
import json
from pathlib import Path

from rfdi.experiments import ROOT, run_development, run_final


def main() -> None:
    parser = argparse.ArgumentParser(description="R-FDI evidence-producing runner")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", type=Path, default=ROOT / "configs/experiments/core.json")
    final = sub.add_parser("final")
    final.add_argument("--config", type=Path, default=ROOT / "configs/experiments/frozen.json")
    sub.add_parser("resume")
    args = parser.parse_args()
    if args.command == "run":
        result = run_development(args.config)
        print(json.dumps({"status": "COMPLETE", "artifacts": len(result)}, sort_keys=True))
    elif args.command == "final":
        result = run_final(args.config)
        print(json.dumps({"status": "FINAL_EVAL_COMPLETE", "experiment_id": result["experiment_id"]}))
    else:
        state = json.loads((ROOT / "WORKFLOW_STATE.json").read_text(encoding="utf-8"))
        incomplete = [key for key, value in state["phases"].items() if value["status"] not in {"COMPLETE", "BLOCKED", "FAILED", "SKIPPED_WITH_REASON"}]
        print(json.dumps({"evaluation_state": state["evaluation_state"], "incomplete_phases": incomplete}, indent=2))


if __name__ == "__main__":
    main()
