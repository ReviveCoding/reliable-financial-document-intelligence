from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from rfdi_v3.runtime import RuntimeStore, Worker, decode_content


RUNTIME_ROOT = Path(os.environ.get("RFDI_V3_SERVICE_ROOT", "/home/bjw-0/.local/share/rfdi-runtime/v3-service"))
store = RuntimeStore(RUNTIME_ROOT)
worker = Worker(store)


@asynccontextmanager
async def lifespan(_: FastAPI):
    embedded = os.environ.get("RFDI_EMBEDDED_WORKER", "true").casefold() == "true"
    if embedded:
        worker.start()
    yield
    if embedded:
        worker.stop()


app = FastAPI(title="R-FDI V3", version="3.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)


class DocumentRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=200)
    content_b64: str
    media_type: str = "text/plain"
    route: Literal["cheap", "donut"] = "cheap"
    fault_once: Literal["crash_after_extraction", "inference_timeout"] | None = None


class ReviewRequest(BaseModel):
    action: Literal["ACCEPT", "EDIT", "REJECT", "ESCALATE"]
    corrections: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=1, max_length=1000)
    reviewer: str = Field(min_length=1, max_length=100)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "backend": "sqlite-durable-queue+filesystem-object-store", **store.metrics()}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    values = store.metrics()
    lines = [f"rfdi_documents_total {values['documents']}", f"rfdi_finalization_commits_total {values['finalization_commits']}", f"rfdi_pending_jobs {values['pending_jobs']}"]
    lines.extend(f'rfdi_documents_state{{state="{state}"}} {count}' for state, count in values["states"].items())
    return "\n".join(lines) + "\n"


@app.post("/documents", status_code=202)
def create_document(request: DocumentRequest) -> dict[str, Any]:
    try:
        content = decode_content(request.content_b64)
    except Exception as error:
        raise HTTPException(422, f"invalid base64: {error}") from error
    document_id, created = store.ingest(content=content, idempotency_key=request.idempotency_key, media_type=request.media_type, route=request.route, fault_once=request.fault_once)
    return {"document_id": document_id, "created": created}


@app.get("/documents/{document_id}")
def get_document(document_id: str) -> dict[str, Any]:
    document = store.get(document_id)
    if document is None:
        raise HTTPException(404, "unknown document")
    return document


@app.get("/documents/{document_id}/result")
def get_result(document_id: str) -> dict[str, Any]:
    result = store.result(document_id)
    if result is None:
        raise HTTPException(409, "result not ready")
    return result


@app.post("/documents/{document_id}/review")
def review(document_id: str, request: ReviewRequest) -> dict[str, Any]:
    if store.get(document_id) is None:
        raise HTTPException(404, "unknown document")
    try:
        store.review(document_id, request.action, request.corrections, request.reason, request.reviewer)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return {"document_id": document_id, "state": "REVIEWED"}


@app.post("/documents/{document_id}/replay", status_code=202)
def replay(document_id: str) -> dict[str, Any]:
    if store.get(document_id) is None:
        raise HTTPException(404, "unknown document")
    store.replay(document_id)
    return {"document_id": document_id, "replay": "accepted"}


@app.get("/review", response_class=HTMLResponse)
def review_ui() -> str:
    return (Path(__file__).parent / "review.html").read_text()
