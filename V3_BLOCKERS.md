# V3 Blockers

## Active external access blockers

- `V3-DOCILE`: `HUMAN_ACTION_REQUIRED`; an official DocILE token is absent.
- `V3-REFIND`: `HUMAN_ACTION_REQUIRED`; interactive official terms/access are required.
- `V3-TEXTRACT`: `SKIPPED_WITH_REASON`; no positive AWS budget and credentials were established.

These optional blockers do not stop unrelated V3 work.

## Recovered interruption

- The prior process exited with status 135. No retained diagnostic establishes
  root cause, so it is recorded as `RECOVERED_UNKNOWN_CAUSE`.

## Non-blocking limitations

- The preserved application uses SQLite polling rather than Redis as job transport.
- The Docker-visible PaddleOCR model cache is not visible as ordinary WSL files
  through the same UNC bind path; cache persistence was verified within Docker.
- PaddleOCR-VL results use a development content-presence metric, not official
  structured CORD F1 or locked-final evaluation.
- Compose credentials are explicit local-development values and exposed service
  ports are suitable only for this bounded desktop study, not production deployment.
