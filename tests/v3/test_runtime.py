from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from rfdi_v3.runtime import RuntimeStore, Worker


TEXT = b"Invoice: INV-100\nSubtotal: 10.00\nTax: 2.00\nTotal: 12.00\nCurrency: USD\n"


def wait_result(store: RuntimeStore, document_id: str, seconds: float = 3) -> dict:
    deadline = time.time() + seconds
    while time.time() < deadline:
        result = store.result(document_id)
        if result:
            return result
        time.sleep(0.01)
    raise AssertionError("result not ready")


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = RuntimeStore(Path(self.tmp.name))
        self.worker = Worker(self.store)
        self.worker.start()

    def tearDown(self) -> None:
        self.worker.stop()
        self.tmp.cleanup()

    def test_idempotency_content_and_key(self) -> None:
        first, created = self.store.ingest(content=TEXT, idempotency_key="same", media_type="text/plain", route="cheap", fault_once=None)
        second, created_again = self.store.ingest(content=TEXT, idempotency_key="same", media_type="text/plain", route="cheap", fault_once=None)
        third, content_created = self.store.ingest(content=TEXT, idempotency_key="different", media_type="text/plain", route="cheap", fault_once=None)
        self.assertTrue(created); self.assertFalse(created_again); self.assertFalse(content_created)
        self.assertEqual(first, second); self.assertEqual(first, third)
        wait_result(self.store, first)
        self.assertEqual(self.store.metrics()["finalization_commits"], 1)

    def test_crash_after_extract_retries_exactly_once(self) -> None:
        document_id, _ = self.store.ingest(content=TEXT, idempotency_key="crash", media_type="text/plain", route="cheap", fault_once="crash_after_extraction")
        result = wait_result(self.store, document_id)
        self.assertEqual(result["decision"], "AUTO_ACCEPTED")
        self.assertEqual(self.store.metrics()["finalization_commits"], 1)

    def test_review_and_replay_do_not_duplicate_finalization(self) -> None:
        document_id, _ = self.store.ingest(content=TEXT, idempotency_key="review", media_type="text/plain", route="cheap", fault_once=None)
        wait_result(self.store, document_id)
        self.store.review(document_id, "EDIT", {"total": "12.00"}, "verified", "test-reviewer")
        self.store.replay(document_id)
        time.sleep(0.2)
        self.assertEqual(self.store.get(document_id)["state"], "REVIEWED")
        self.assertEqual(self.store.metrics()["finalization_commits"], 1)


if __name__ == "__main__":
    unittest.main()
