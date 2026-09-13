# V3 Decisions

## V3-D001 — Resume and evidence preservation

V3 resumes from the existing untracked working state on base commit `1f83625`.
Recovered completed results are preserved byte-for-byte and are not rerun without
an integrity reason. Pre-mutation hashes are retained under `artifacts/v3/recovery/`.

## V3-D002 — Exit 135 attribution

Record the previous exit 135 as an interruption of unknown cause. Do not infer a
hardware, CUDA, memory, filesystem, WSL, or Docker root cause without evidence.

## V3-D003 — Docker interoperability

Use the Windows Docker CLI from WSL on context `desktop-linux`; Ubuntu-native
Docker integration is not a requirement. Preserve discrepancies between Docker
Desktop status output and engine API availability as observed evidence.

## V3-D004 — Infrastructure semantics

Treat PostgreSQL and MinIO as the verified MLflow metadata and artifact stores.
Redis persistence is independently verified, but do not describe Redis as the
application queue: the preserved API/worker implementation reports and uses a
SQLite durable queue plus filesystem object storage.

## V3-D005 — Accelerated-serving resource bound

Use one Docker GPU job with at least 30% measured VRAM headroom. The accepted
PaddleOCR-VL server configuration uses 0.30 vLLM utilization, eager mode, four
maximum sequences, and 8,192 maximum batched tokens. Allocation pilots that did
not satisfy headroom were excluded from inference.

## V3-D006 — Extension outcome

Apply the frozen extension gates without post-result changes. With the real
Compose stack, cross-store MLflow persistence, API/reviewer checks, load and fault
studies, Docker GPU execution, accelerated serving, and expanded security
benchmark complete, the result is `V3_EXTENSION_SUCCESS`. Optional external data
and paid-service blockers remain explicit and do not change that decision.
