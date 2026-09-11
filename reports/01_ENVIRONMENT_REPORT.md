# Environment Report

Measured on 2026-09-11 in WSL2, Python 3.10.12, 32 logical CPUs (launcher recommendation: 12 workers). Prelaunch saw one NVIDIA GeForce RTX 4090 Laptop GPU, 16,376 MiB, driver 616.92. Inside the active session, `nvidia-smi` returned 255 because NVML access was blocked. PyTorch and other optional Python dependencies were absent. Docker was unavailable to WSL despite a Windows-side executable path.

Deep workloads are `BLOCKED_ACCELERATOR`; no CPU substitution occurred. The dependency-free deterministic suite uses CPU. Raw probe: `artifacts/results/p01.json`.
