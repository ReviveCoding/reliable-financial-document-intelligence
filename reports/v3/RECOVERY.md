# V3 Recovery Record

Recovery resumed in place on `financial-domain-production-v3` at base commit
`1f83625`. Before mutation, the Git root was exactly
`/mnt/c/Users/bjw-0/Downloads/R-FDI`, `.rfdi-workspace-root` existed, and all
recovered V3 paths were untracked. The preservation hashes are in
`artifacts/v3/recovery/pre_mutation_inventory.sha256`.

The previous session is known to have ended with exit status 135. No retained
workspace log, kernel diagnostic, or application traceback was found that
attributes that status to a specific cause. The interruption is therefore
recorded as `RECOVERED_UNKNOWN_CAUSE`; it must not be described as a bus error,
CUDA failure, Docker failure, out-of-memory event, or any other inferred cause.

Recovered evidence was reconciled as follows:

- FastAPI/reviewer smoke evidence: preserved without rerun.
- SQLite/filesystem 7/7 executable fault study: preserved without rerun.
- Cached-route load evidence: preserved without rerun.
- Corrected Donut GPU load evidence: preserved without rerun.
- Deduplicated Donut load evidence: preserved and explicitly invalid.
- DocILE, REFinD, and Textract access decisions: preserved without bypass or paid call.
- Docker, accelerated PaddleOCR-VL, expanded adversarial security, runtime/reviewer,
  statistics, packaging, and final verification were identified as the remaining
  V3 work at recovery time.

Docker Desktop reported a contradictory control-plane observation on recovery:
`docker desktop status` returned `stopped`, while the Windows Docker CLI on
context `desktop-linux` successfully returned Server version 29.7.2 / Docker
Desktop 4.90.0. This is retained as an observation, not interpreted as a cause
of the prior interruption.
