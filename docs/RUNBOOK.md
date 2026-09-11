# Runbook

## Preflight

```bash
cd /mnt/c/Users/bjw-0/Downloads/R-FDI
pwd
git rev-parse --show-toplevel
test -f .rfdi-workspace-root
nvidia-smi
```

The first three paths must equal `/mnt/c/Users/bjw-0/Downloads/R-FDI`. Do not start deep work if CUDA fails; record `BLOCKED_ACCELERATOR`.

## Test and reproduce development evidence

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m rfdi.cli run --config configs/experiments/core.json
PYTHONPATH=src python3 -m rfdi.cli resume
```

Development reruns deterministically replace generated development evidence. Never use final records for tuning. `rfdi final` requires persisted authorization and a frozen config.

## Faults

Malformed inputs become permanent failures; timeouts/OOM/transient service loss become retryable failures with bounded backoff. Replays reuse content identity. Quarantined documents require explicit review. Preserve partial raw output but never finalize it. Do not fault-inject the host, driver, or GPU.

## Resume blocked deep work

Restore WSL GPU access, verify `nvidia-smi`, install a CUDA-compatible environment under `RFDI_RUNTIME_ROOT`, rerun smoke tests, then register each model revision and measured pilot. Dataset tokens remain external and must never be printed.
