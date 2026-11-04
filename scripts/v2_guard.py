from __future__ import annotations

import json
from pathlib import Path


FINAL_ALLOWED_STATES = {"V2_FINAL_EVAL_AUTHORIZED", "V2_FINAL_EVAL_COMPLETE"}


def is_locked_input(path: Path) -> bool:
    lowered = [part.casefold() for part in path.parts]
    name = path.name.casefold()
    return "final" in lowered or name.startswith("final.") or "test" in lowered or name == "test.jsonl"


def assert_input_allowed(path: Path, state_path: Path = Path("V2_WORKFLOW_STATE.json")) -> None:
    if not is_locked_input(path):
        return
    state = json.loads(state_path.read_text())
    lifecycle = state.get("evaluation_state")
    if lifecycle not in FINAL_ALLOWED_STATES:
        raise RuntimeError(f"V2 locked input denied while lifecycle is {lifecycle}: {path}")
