from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = "1f83625"
PUBLICATION_SURFACE_EXCEPTIONS = {"README.md"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_base_tree() -> tuple[int, list[str]]:
    rows = subprocess.check_output(["git", "ls-tree", "-r", BASE], cwd=ROOT, text=True).splitlines()
    checked = 0
    excluded = []
    for row in rows:
        metadata, name = row.split("\t", 1)
        if name in PUBLICATION_SURFACE_EXCEPTIONS:
            excluded.append(name)
            continue
        expected = metadata.split()[2]
        path = ROOT / name
        if not path.is_file():
            raise AssertionError(f"base path missing: {name}")
        actual = subprocess.check_output(["git", "hash-object", "--", name], cwd=ROOT, text=True).strip()
        if actual != expected:
            raise AssertionError(f"base path modified: {name}")
        checked += 1
    return checked, excluded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    state = json.loads((ROOT / "V3_WORKFLOW_STATE.json").read_text())
    gates = json.loads((ROOT / "configs/v3/extension_gates.json").read_text())
    summary = json.loads((ROOT / "artifacts/v3/statistics/summary.json").read_text())
    manifest = [json.loads(line) for line in (ROOT / "V3_EVIDENCE_MANIFEST.jsonl").read_text().splitlines()]
    if not manifest:
        raise AssertionError("empty V3 evidence manifest")
    for row in manifest:
        path = ROOT / row["path"]
        if not path.is_file() or sha256(path) != row["sha256"]:
            raise AssertionError(f"manifest mismatch: {row['path']}")
    with (ROOT / "V3_EXPERIMENT_REGISTRY.csv").open(newline="") as stream:
        registry = list(csv.DictReader(stream))
    invalid = [row for row in registry if row["status"] == "INVALID_PRESERVED"]
    if len(invalid) != 1 or "invalid_deduplicated" not in invalid[0]["metrics_artifact"]:
        raise AssertionError("invalid deduplicated GPU evidence is not explicit")
    requirements = summary["requirements"]
    independently_expected = "V3_EXTENSION_SUCCESS" if all(requirements.values()) else (
        "V3_EXTENSION_PARTIAL" if all(requirements[key] for key in ("api_load", "fault_recovery", "expanded_security", "reviewer_application"))
        else "V3_EXTENSION_BLOCKED"
    )
    if state["extension_decision"] != independently_expected or summary["extension_decision"] != independently_expected:
        raise AssertionError("extension decision does not follow frozen rule")
    if gates["decision_rule"].get(independently_expected) is None:
        raise AssertionError("extension decision absent from frozen gates")
    base_files, publication_exceptions = verify_base_tree()
    result = {
        "status": "PASS",
        "base_commit": BASE,
        "immutable_base_files_verified": base_files,
        "publication_surface_exceptions": publication_exceptions,
        "manifest_entries_verified": len(manifest),
        "registry_entries": len(registry),
        "extension_decision": independently_expected,
        "invalid_evidence_entries": len(invalid),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
