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

## V2 WSL2 GPU procedure

Inside Codex workspace-write, `/dev/dxg` may be hidden and `nvidia-smi` may fail even when WSL CUDA works. Record the sandbox result, then use an approved narrowly scoped escalated `nvidia-smi` probe. Only declare accelerator blocking if that external probe also fails. V2 environments are under `/home/bjw-0/.local/share/rfdi-runtime/venvs`; heavyweight GPU jobs run sequentially.

Do not rerun the V2 locked final to tune or replace results. Verification is read-only:

```bash
cd /mnt/c/Users/bjw-0/Downloads/R-FDI
PYTHONPATH=src /usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 scripts/v2_verify_evidence.py
```

To resume an externally authorized dataset, stay on `gpu-completion-v2`, acquire only through the official route into `RFDI_DATA_ROOT`, add a new versioned experiment ID, and do not modify `configs/v2/frozen.json` or the completed V2 final artifacts.
