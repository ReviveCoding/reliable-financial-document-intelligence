from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from rfdi_v3.runtime import RuntimeStore, Worker


TEXT = b"Invoice: V3-FAULT\nSubtotal: 10.00\nTax: 2.00\nTotal: 12.00\nCurrency: USD\n"


def wait(store: RuntimeStore, document_id: str, timeout: float = 5) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if store.result(document_id): return True
        if store.get(document_id)["state"] == "PERMANENT_FAILURE": return False
        time.sleep(.01)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rfdi-v3-fault-") as directory:
        store = RuntimeStore(Path(directory)); worker = Worker(store); worker.start(); cases = []
        first, created = store.ingest(content=TEXT, idempotency_key="dup", media_type="text/plain", route="cheap", fault_once=None)
        second, created2 = store.ingest(content=TEXT, idempotency_key="dup", media_type="text/plain", route="cheap", fault_once=None)
        third, created3 = store.ingest(content=TEXT, idempotency_key="different", media_type="text/plain", route="cheap", fault_once=None)
        wait(store, first); cases.append({"fault": "duplicate event and key", "passed": first == second == third and created and not created2 and not created3 and store.metrics()["finalization_commits"] == 1})
        malformed, _ = store.ingest(content=b"bad", idempotency_key="malformed", media_type="image/png", route="cheap", fault_once=None)
        cases.append({"fault": "malformed image", "passed": not wait(store, malformed) and store.get(malformed)["state"] == "PERMANENT_FAILURE"})
        crashed, _ = store.ingest(content=TEXT + b"crash", idempotency_key="crash", media_type="text/plain", route="cheap", fault_once="crash_after_extraction")
        cases.append({"fault": "crash after extraction", "passed": wait(store, crashed) and store.get(crashed)["finalized_count"] == 1})
        timed, _ = store.ingest(content=TEXT + b"timeout", idempotency_key="timeout", media_type="text/plain", route="cheap", fault_once="inference_timeout")
        cases.append({"fault": "inference timeout", "passed": wait(store, timed) and store.get(timed)["finalized_count"] == 1})
        missing, _ = store.ingest(content=TEXT + b"object", idempotency_key="object", media_type="text/plain", route="cheap", fault_once=None)
        object_path = Path(store.get(missing)["object_path"]); held = object_path.with_suffix(".held"); object_path.rename(held); time.sleep(.1); held.rename(object_path)
        cases.append({"fault": "object-store temporary interruption", "passed": wait(store, missing) and store.get(missing)["finalized_count"] == 1})
        worker.stop()
        restart, _ = store.ingest(content=TEXT + b"restart", idempotency_key="restart", media_type="text/plain", route="cheap", fault_once=None)
        worker = Worker(store); worker.start(); cases.append({"fault": "worker restart", "passed": wait(store, restart)})
        store.replay(first); time.sleep(.2); cases.append({"fault": "replay finalized document", "passed": store.get(first)["finalized_count"] == 1})
        worker.stop()
        cases.extend([
            {"fault": "Redis interruption", "passed": None, "status": "BLOCKED_DOCKER"},
            {"fault": "PostgreSQL restart", "passed": None, "status": "BLOCKED_DOCKER"},
            {"fault": "MinIO interruption", "passed": None, "status": "BLOCKED_DOCKER"},
            {"fault": "GPU model process restart", "passed": None, "status": "NOT_RUN_BOUNDED_CORE_FIRST"},
        ])
        result = {"experiment_id": "V3-E07", "backend": "SQLite durable queue + filesystem object store", "cases": cases, "executed_passed": sum(case.get("passed") is True for case in cases), "executed_total": sum(case.get("passed") is not None for case in cases), "all_executed_passed": all(case["passed"] for case in cases if case.get("passed") is not None), "metrics": store.metrics(), "initial_failure": "Replay state regression and claimed_at propagation bugs were discovered by tests and corrected before this confirmation."}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n"); print(json.dumps(result, sort_keys=True))


if __name__ == "__main__": main()
