from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


TERMINAL = {"AUTO_ACCEPTED", "REVIEW_REQUIRED", "QUARANTINED", "REVIEWED", "FINALIZED", "PERMANENT_FAILURE"}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class RuntimeStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.objects = root / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)
        root.mkdir(parents=True, exist_ok=True)
        self.db_path = root / "rfdi-v3.sqlite3"
        self.lock = threading.RLock()
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=20, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                  id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL,
                  content_sha256 TEXT UNIQUE NOT NULL, object_path TEXT NOT NULL,
                  media_type TEXT NOT NULL, route TEXT NOT NULL, state TEXT NOT NULL,
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, finalized_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS jobs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL,
                  state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                  available_at REAL NOT NULL, fault_once TEXT, fault_consumed INTEGER NOT NULL DEFAULT 0,
                  queue_entered REAL NOT NULL, claimed_at REAL, error TEXT,
                  FOREIGN KEY(document_id) REFERENCES documents(id)
                );
                CREATE TABLE IF NOT EXISTS predictions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL,
                  model TEXT NOT NULL, model_version TEXT NOT NULL, raw_json TEXT NOT NULL,
                  normalized_json TEXT NOT NULL, confidence REAL NOT NULL,
                  reconciliation_json TEXT NOT NULL, risk REAL NOT NULL, decision TEXT NOT NULL,
                  queue_wait_ms REAL NOT NULL, inference_ms REAL NOT NULL, db_ms REAL NOT NULL,
                  created_at TEXT NOT NULL, UNIQUE(document_id, model_version),
                  FOREIGN KEY(document_id) REFERENCES documents(id)
                );
                CREATE TABLE IF NOT EXISTS reviews (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL,
                  action TEXT NOT NULL, corrections_json TEXT NOT NULL, reason TEXT NOT NULL,
                  reviewer TEXT NOT NULL, prediction_version TEXT NOT NULL, created_at TEXT NOT NULL,
                  FOREIGN KEY(document_id) REFERENCES documents(id)
                );
                CREATE TABLE IF NOT EXISTS events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL,
                  event_type TEXT NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                """
            )

    def ingest(self, *, content: bytes, idempotency_key: str, media_type: str, route: str, fault_once: str | None) -> tuple[str, bool]:
        digest = hashlib.sha256(content).hexdigest()
        document_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"rfdi-v3:{digest}"))
        suffix = ".pdf" if "pdf" in media_type else ".png" if "image" in media_type else ".txt"
        path = self.objects / f"{digest}{suffix}"
        with self.lock, self.connect() as db:
            prior = db.execute("SELECT id FROM documents WHERE idempotency_key=? OR content_sha256=?", (idempotency_key, digest)).fetchone()
            if prior:
                return str(prior["id"]), False
            path.write_bytes(content)
            now = utcnow()
            db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,0)", (document_id, idempotency_key, digest, str(path), media_type, route, "RECEIVED", now, now))
            db.execute("INSERT INTO jobs(document_id,state,available_at,fault_once,queue_entered) VALUES (?,?,?,?,?)", (document_id, "PENDING", time.time(), fault_once, time.perf_counter()))
            db.execute("INSERT INTO events(document_id,event_type,detail_json,created_at) VALUES (?,?,?,?)", (document_id, "INGESTED", json.dumps({"route": route}), now))
        return document_id, True

    def claim(self) -> dict[str, Any] | None:
        with self.lock, self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE state='PENDING' AND available_at<=? ORDER BY id LIMIT 1", (time.time(),)).fetchone()
            if not row:
                return None
            claimed_at = time.perf_counter()
            changed = db.execute("UPDATE jobs SET state='RUNNING', attempts=attempts+1, claimed_at=? WHERE id=? AND state='PENDING'", (claimed_at, row["id"])).rowcount
            if not changed:
                return None
            document = db.execute("SELECT * FROM documents WHERE id=?", (row["document_id"],)).fetchone()
            if document["state"] not in TERMINAL:
                db.execute("UPDATE documents SET state='VALIDATED',updated_at=? WHERE id=?", (utcnow(), row["document_id"]))
            job = dict(row)
            job["claimed_at"] = claimed_at
            job["attempts"] = int(job["attempts"]) + 1
            return {"job": job, "document": dict(document)}

    def retry(self, job_id: int, document_id: str, error: str, consume_fault: bool = True) -> None:
        with self.lock, self.connect() as db:
            attempts = int(db.execute("SELECT attempts FROM jobs WHERE id=?", (job_id,)).fetchone()[0])
            if attempts >= 3:
                db.execute("UPDATE jobs SET state='DEAD',error=?,fault_consumed=1 WHERE id=?", (error, job_id))
                db.execute("UPDATE documents SET state='PERMANENT_FAILURE',updated_at=? WHERE id=?", (utcnow(), document_id))
            else:
                db.execute("UPDATE jobs SET state='PENDING',available_at=?,error=?,fault_consumed=? WHERE id=?", (time.time() + min(0.05 * 2**attempts, 0.2), error, int(consume_fault), job_id))
                db.execute("UPDATE documents SET state='RETRYABLE_FAILURE',updated_at=? WHERE id=?", (utcnow(), document_id))
            db.execute("INSERT INTO events(document_id,event_type,detail_json,created_at) VALUES (?,?,?,?)", (document_id, "RETRY", json.dumps({"error": error, "attempt": attempts}), utcnow()))

    def commit_prediction(self, job: dict[str, Any], raw: dict[str, Any], normalized: dict[str, Any], confidence: float, inference_ms: float) -> None:
        started = time.perf_counter()
        warnings = reconcile(normalized)
        missing = sum(normalized.get(key) in (None, "") for key in ("invoice_number", "total", "currency"))
        risk = min(1.0, (1 - confidence) * 0.5 + 0.18 * missing + 0.25 * bool(warnings))
        decision = "QUARANTINED" if risk >= 0.78 else "REVIEW_REQUIRED" if risk >= 0.36 else "AUTO_ACCEPTED"
        document_id = job["document"]["id"]
        queue_wait_ms = max(0.0, (job["job"]["claimed_at"] - job["job"]["queue_entered"]) * 1000)
        with self.lock, self.connect() as db:
            existing = db.execute("SELECT id FROM predictions WHERE document_id=? AND model_version=?", (document_id, model_version(job["document"]["route"]))).fetchone()
            if not existing:
                db.execute(
                    "INSERT INTO predictions(document_id,model,model_version,raw_json,normalized_json,confidence,reconciliation_json,risk,decision,queue_wait_ms,inference_ms,db_ms,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (document_id, job["document"]["route"], model_version(job["document"]["route"]), json.dumps(raw), json.dumps(normalized), confidence, json.dumps(warnings), risk, decision, queue_wait_ms, inference_ms, 0.0, utcnow()),
                )
                db.execute("UPDATE documents SET state=?,updated_at=?,finalized_count=finalized_count+1 WHERE id=? AND finalized_count=0", (decision, utcnow(), document_id))
            db.execute("UPDATE jobs SET state='COMPLETE' WHERE id=?", (job["job"]["id"],))
            db.execute("INSERT INTO events(document_id,event_type,detail_json,created_at) VALUES (?,?,?,?)", (document_id, "DECIDED", json.dumps({"decision": decision, "risk": risk}), utcnow()))
            db_ms = (time.perf_counter() - started) * 1000
            db.execute("UPDATE predictions SET db_ms=? WHERE document_id=?", (db_ms, document_id))

    def get(self, document_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
            return dict(row) if row else None

    def result(self, document_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM predictions WHERE document_id=? ORDER BY id DESC LIMIT 1", (document_id,)).fetchone()
            if not row:
                return None
            output = dict(row)
            for key in ("raw_json", "normalized_json", "reconciliation_json"):
                output[key.removesuffix("_json")] = json.loads(output.pop(key))
            return output

    def review(self, document_id: str, action: str, corrections: dict[str, Any], reason: str, reviewer: str) -> None:
        result = self.result(document_id)
        if result is None:
            raise ValueError("prediction not ready")
        with self.lock, self.connect() as db:
            db.execute("INSERT INTO reviews(document_id,action,corrections_json,reason,reviewer,prediction_version,created_at) VALUES (?,?,?,?,?,?,?)", (document_id, action, json.dumps(corrections), reason, reviewer, result["model_version"], utcnow()))
            db.execute("UPDATE documents SET state='REVIEWED',updated_at=? WHERE id=?", (utcnow(), document_id))
            db.execute("INSERT INTO events(document_id,event_type,detail_json,created_at) VALUES (?,?,?,?)", (document_id, "REVIEWED", json.dumps({"action": action, "reason": reason}), utcnow()))

    def replay(self, document_id: str) -> None:
        with self.lock, self.connect() as db:
            pending = db.execute("SELECT 1 FROM jobs WHERE document_id=? AND state IN ('PENDING','RUNNING')", (document_id,)).fetchone()
            if not pending:
                db.execute("INSERT INTO jobs(document_id,state,available_at,queue_entered) VALUES (?,?,?,?)", (document_id, "PENDING", time.time(), time.perf_counter()))
                db.execute("INSERT INTO events(document_id,event_type,detail_json,created_at) VALUES (?,?,?,?)", (document_id, "REPLAY_REQUESTED", "{}", utcnow()))

    def metrics(self) -> dict[str, Any]:
        with self.connect() as db:
            states = {row[0]: row[1] for row in db.execute("SELECT state,count(*) FROM documents GROUP BY state")}
            count = db.execute("SELECT count(*) FROM documents").fetchone()[0]
            finalized = db.execute("SELECT coalesce(sum(finalized_count),0) FROM documents").fetchone()[0]
            pending = db.execute("SELECT count(*) FROM jobs WHERE state='PENDING'").fetchone()[0]
            return {"documents": count, "states": states, "finalization_commits": finalized, "pending_jobs": pending}


def model_version(route: str) -> str:
    return "8003d433113256b4ce3a0f5bf604b29ff78a7451" if route == "donut" else "v3-regex-1"


def cheap_extract(content: bytes) -> tuple[dict[str, Any], float]:
    text = content.decode("utf-8", errors="replace")
    patterns = {
        "invoice_number": r"(?im)^\s*invoice(?:\s+number|\s*#|\s+no\.?|)\s*[:#-]\s*([^\n]+)",
        "total": r"(?im)^\s*(?:grand\s+)?total\s*[:$-]\s*([A-Z]{3}\s*)?([0-9][0-9.,]*)",
        "currency": r"\b(USD|EUR|GBP|CAD|AUD|JPY)\b",
        "subtotal": r"(?im)^\s*subtotal\s*[:$-]\s*([0-9][0-9.,]*)",
        "tax": r"(?im)^\s*tax\s*[:$-]\s*([0-9][0-9.,]*)",
    }
    result: dict[str, Any] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            result[key] = (match.group(match.lastindex or 1) or "").strip()
    confidence = max(0.1, 0.98 - 0.15 * sum(key not in result for key in ("invoice_number", "total", "currency")))
    return {"text": text, "fields": result}, confidence


def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    fields = dict(raw.get("fields", raw))
    for key in ("total", "subtotal", "tax"):
        if key in fields and fields[key] is not None:
            value = re.sub(r"[^0-9.-]", "", str(fields[key]))
            try:
                fields[key] = f"{float(value):.2f}"
            except ValueError:
                fields[key] = None
    if "currency" in fields and fields["currency"]:
        fields["currency"] = str(fields["currency"]).upper()
    return fields


def reconcile(fields: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if all(fields.get(key) is not None for key in ("subtotal", "tax", "total")):
        if abs(float(fields["subtotal"]) + float(fields["tax"]) - float(fields["total"])) > 0.02:
            warnings.append("ARITHMETIC_CONFLICT")
    return warnings


def donut_extract(path: str) -> tuple[dict[str, Any], float]:
    endpoint = os.environ.get("V3_DONUT_URL", "http://127.0.0.1:8120/extract")
    request = urllib.request.Request(endpoint, data=json.dumps({"image_path": path}).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read())
    return payload["prediction"], float(payload["confidence"])


class Worker:
    def __init__(self, store: RuntimeStore, poll_seconds: float = 0.01) -> None:
        self.store = store
        self.poll_seconds = poll_seconds
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=5)

    def run(self) -> None:
        while not self.stop_event.is_set():
            item = self.store.claim()
            if item is None:
                time.sleep(self.poll_seconds)
                continue
            job, document = item["job"], item["document"]
            fault = job.get("fault_once") if not job.get("fault_consumed") else None
            try:
                content = Path(document["object_path"]).read_bytes()
                if document["media_type"].startswith("image") and len(content) < 32:
                    raise ValueError("malformed image")
                if fault == "inference_timeout":
                    raise TimeoutError("controlled inference timeout")
                started = time.perf_counter()
                raw, confidence = donut_extract(document["object_path"]) if document["route"] == "donut" else cheap_extract(content)
                inference_ms = (time.perf_counter() - started) * 1000
                normalized = normalize(raw)
                if fault == "crash_after_extraction":
                    raise RuntimeError("controlled crash after extraction")
                self.store.commit_prediction(item, raw, normalized, confidence, inference_ms)
            except ValueError as error:
                self.store.retry(job["id"], document["id"], str(error), consume_fault=True)
            except Exception as error:
                self.store.retry(job["id"], document["id"], f"{type(error).__name__}: {error}", consume_fault=True)


def decode_content(content_b64: str) -> bytes:
    return base64.b64decode(content_b64, validate=True)
