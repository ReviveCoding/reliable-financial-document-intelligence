# Architecture

## Decision flow

`RECEIVED → VALIDATED → PARSED → EXTRACTED → RECONCILED → RISK_SCORED`

The risk state selects `AUTO_ACCEPTED`, `REVIEW_REQUIRED`, or `QUARANTINED`. Accepted/reviewed records may become `FINALIZED`; retryable and permanent failures remain explicit. Stable content hashes make replay idempotent.

## Boundaries

- Input: immutable document bytes/text plus idempotency key.
- Extraction: common `/extract` contract; output is schema-bound and provenance-carrying.
- Deterministic controls: normalization, arithmetic/date/cross-document reconciliation, duplicate detection, injection signals.
- Decision: transparent weighted risk and review/quarantine thresholds.
- Storage: raw extraction, normalized extraction, and reviewed result are separate logical records.
- Infrastructure target: FastAPI, Redis queue, PostgreSQL state, MinIO objects, MLflow evidence. The dependency-free local evidence run uses SQLite; Compose could not execute because Docker was unavailable.

Document content never becomes an instruction and extractors receive no shell, mail, payment, or database-mutation capability.
