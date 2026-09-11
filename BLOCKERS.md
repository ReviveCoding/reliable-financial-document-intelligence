# Blockers

## Active

- `BLOCKED_ACCELERATOR`: Active WSL session cannot initialize NVML (`GPU access blocked by the operating system`). Deep CUDA-capable experiments P14–P17 and any deep training/inference cannot run until WSL/GPU access is restored. No CPU fallback is authorized.
- `BLOCKED_ACCESS`: DocILE requires official authorization and `DOCILE_TOKEN`; no token availability has been established. Acquisition only is blocked.
- `BLOCKED_ACCESS`: REFinD access has not been established; use only official access.
- `NOT_RUN_NO_CLOUD_AUTHORIZATION`: AWS Textract empirical calls require both valid credentials and positive `RFDI_AWS_BUDGET_USD`. Neither is assumed.
- Docker is unavailable in this WSL distribution. Compose artifacts can be validated statically; service-stack execution is blocked until Docker Desktop WSL integration is enabled.

## Resume commands

```bash
cd /mnt/c/Users/bjw-0/Downloads/R-FDI
nvidia-smi
python -m rfdi.cli resume
```

Never paste credentials into logs or issue trackers.
