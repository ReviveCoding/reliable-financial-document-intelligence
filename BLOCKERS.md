# Blockers

## Active

- `BLOCKED_ACCESS`: DocILE requires official authorization and `DOCILE_TOKEN`; no token availability has been established. Acquisition only is blocked.
- `BLOCKED_ACCESS`: REFinD access has not been established; use only official access.
- `BLOCKED_ACCESS`: SROIE's official RRC route requires account registration. No third-party repackaging was substituted.
- `NOT_RUN_NO_CLOUD_AUTHORIZATION`: AWS Textract empirical calls require both valid credentials and positive `RFDI_AWS_BUDGET_USD`. Neither is assumed.
- Docker is unavailable in this WSL distribution. Compose artifacts can be validated statically; service-stack execution is blocked until Docker Desktop WSL integration is enabled.

## Accelerator diagnosis corrected in V2

V1's in-sandbox NVML failure is historical evidence, not an active accelerator blocker. V2 confirmed `/dev/dxg` is hidden only inside Codex bubblewrap, then used approved escalated commands to run actual PyTorch and Paddle CUDA workloads on one RTX 4090 Laptop GPU. Evidence is in `reports/v2/01_ENVIRONMENT_REPORT.md` and `artifacts/v2/environment/gpu_preflight.json`.

## Resume commands

```bash
cd /mnt/c/Users/bjw-0/Downloads/R-FDI
git switch gpu-completion-v2
/usr/bin/python3 scripts/v2_acquire.py --help
```

Never paste credentials into logs or issue trackers.
