# R-FDI V3 Final Report

## Outcome

The frozen V3 extension rule evaluates to `V3_EXTENSION_SUCCESS`. The work resumed
the existing `financial-domain-production-v3` branch in place and retained prior
V3 evidence, including the invalid deduplicated GPU benchmark as explicitly invalid.
All 206 files from V2 commit `1f83625` match their committed blob IDs.

## Completed evidence

- The production-style Compose stack ran through the Windows Docker CLI with
  PostgreSQL, Redis, MinIO, MLflow, API, worker, and reviewer services healthy.
- MLflow metadata was queried directly from PostgreSQL and the matching artifact
  was found directly in MinIO for run `ebaf889519954ed387676f5a0a04e474`.
- Redis, PostgreSQL, and MinIO stop/restart probes all recovered; the preserved
  seven-case executable fault study remains 7/7 passed.
- API creation, idempotency, worker completion, review commit, reviewer pages, and
  metrics passed. Preserved cached-route and corrected Donut GPU load evidence is
  retained without rerun.
- Docker exposed one RTX 4090 Laptop GPU. PaddleOCR-VL 1.6 vLLM serving completed
  a same-document 20-record CORD development comparison with 1.902x mean speedup
  while retaining at least 30% observed VRAM headroom.
- The 24-case security benchmark preserved all trust boundaries and capability
  isolation. Regex activated on 20 cases; known misses and benign triggers remain
  explicit.

## Limitations and blockers

Redis is not the active application job transport. PaddleOCR results are a
development content-presence metric, not official CORD F1. DocILE and REFinD need
human-authorized access. Textract was skipped because no positive AWS budget and
valid credentials were established. The Compose credentials and published ports
are local-development settings, not a production security configuration. No paid
cloud cost, remote push, production bank deployment, regulatory-compliance claim,
or multi-GPU claim was made.
