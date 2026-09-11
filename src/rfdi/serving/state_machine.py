from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from rfdi.schemas import DocumentState


class InvalidTransition(ValueError):
    pass


ALLOWED = {
    DocumentState.RECEIVED: {DocumentState.VALIDATED, DocumentState.PERMANENT_FAILURE},
    DocumentState.VALIDATED: {DocumentState.PARSED, DocumentState.RETRYABLE_FAILURE},
    DocumentState.PARSED: {DocumentState.EXTRACTED, DocumentState.RETRYABLE_FAILURE},
    DocumentState.EXTRACTED: {DocumentState.RECONCILED, DocumentState.RETRYABLE_FAILURE},
    DocumentState.RECONCILED: {DocumentState.RISK_SCORED},
    DocumentState.RISK_SCORED: {DocumentState.AUTO_ACCEPTED, DocumentState.REVIEW_REQUIRED, DocumentState.QUARANTINED},
    DocumentState.AUTO_ACCEPTED: {DocumentState.FINALIZED},
    DocumentState.REVIEW_REQUIRED: {DocumentState.REVIEWED},
    DocumentState.REVIEWED: {DocumentState.FINALIZED, DocumentState.QUARANTINED},
    DocumentState.RETRYABLE_FAILURE: {DocumentState.VALIDATED, DocumentState.PERMANENT_FAILURE},
}


@dataclass(frozen=True)
class StoredDocument:
    document_id: str
    content_hash: str
    state: DocumentState


class DocumentStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.connection = sqlite3.connect(str(path))
        self.connection.execute("CREATE TABLE IF NOT EXISTS documents (document_id TEXT PRIMARY KEY, content_hash TEXT UNIQUE NOT NULL, state TEXT NOT NULL)")
        self.connection.commit()

    def receive(self, content: bytes, idempotency_key: str) -> StoredDocument:
        digest = hashlib.sha256(content).hexdigest()
        document_id = hashlib.sha256((idempotency_key + digest).encode()).hexdigest()[:24]
        self.connection.execute("INSERT OR IGNORE INTO documents VALUES (?, ?, ?)", (document_id, digest, DocumentState.RECEIVED.value))
        self.connection.commit()
        row = self.connection.execute("SELECT document_id, content_hash, state FROM documents WHERE content_hash = ?", (digest,)).fetchone()
        assert row is not None
        return StoredDocument(row[0], row[1], DocumentState(row[2]))

    def transition(self, document_id: str, target: DocumentState) -> StoredDocument:
        row = self.connection.execute("SELECT content_hash, state FROM documents WHERE document_id = ?", (document_id,)).fetchone()
        if row is None:
            raise KeyError(document_id)
        current = DocumentState(row[1])
        if target not in ALLOWED.get(current, set()):
            raise InvalidTransition(f"{current.value} -> {target.value}")
        self.connection.execute("UPDATE documents SET state = ? WHERE document_id = ?", (target.value, document_id))
        self.connection.commit()
        return StoredDocument(document_id, row[0], target)
