"""Optional FastAPI adapter. Core logic remains importable without FastAPI."""
from __future__ import annotations

try:
    from fastapi import FastAPI, Header, HTTPException
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Install rfdi[api] to run the HTTP service") from exc

from rfdi.extraction import extract_fields
from rfdi.security import security_signals

app = FastAPI(title="R-FDI", version="0.1.0")


class ExtractRequest(BaseModel):
    document_text: str


@app.post("/extract")
def extract(request: ExtractRequest, idempotency_key: str = Header(...)) -> dict[str, object]:
    signals = security_signals(request.document_text)
    if signals:
        return {"idempotency_key": idempotency_key, "decision": "BLOCK_OR_QUARANTINE", "fields": {}, "warnings": signals}
    return {"idempotency_key": idempotency_key, "decision": "HUMAN_REVIEW", "fields": extract_fields(request.document_text), "warnings": []}
