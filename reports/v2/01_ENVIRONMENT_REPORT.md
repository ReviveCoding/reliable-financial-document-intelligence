# V2 Environment and GPU Diagnosis

Access date: 2026-09-11. V1 evidence and its `NO_PROMOTION` decision remain unchanged.

## Device isolation diagnosis

Sandboxed probe:

- `/dev/dxg`: absent.
- `nvidia-smi`: exit 255, `Failed to initialize NVML: GPU access blocked by the operating system`.

Approved out-of-sandbox probe:

- `/dev/dxg`: character device `10,125`, mode `crw-rw-rw-`.
- `nvidia-smi`: success.
- Physical GPU count: 1.
- GPU: NVIDIA GeForce RTX 4090 Laptop GPU, UUID recorded in restricted raw evidence.
- Memory: 16,376 MiB total, 16,048 MiB free at probe.
- Windows driver / KMD: 616.92; Linux NVIDIA-SMI: 615.71.08; CUDA UMD: 13.4.
- Temperature: 75°C at probe; 0% utilization and 33 W.

Conclusion: the V1 accelerator blocker was a Codex bubblewrap visibility artifact. V2 deep commands must use narrowly approved out-of-sandbox execution.

## Framework smoke

An approved out-of-sandbox CUDA test used Python 3.10.12, PyTorch 2.14.0+cu130, and torch CUDA 13.0. `torch.cuda.is_available()` was true; device count was one; BF16 was supported. A seeded FP32 4096×4096 GEMM completed and synchronized in 0.175350839 seconds. Peak allocated/reserved memory was 209,848,320/224,395,264 bytes. This is actual CUDA execution, not an import-only check. Raw evidence: `artifacts/v2/environment/gpu_preflight.json`.

A separate Paddle environment used PaddlePaddle GPU 3.3.0 cu130. After adding its undeclared `setuptools` import dependency, the same seeded FP32 GEMM completed on `gpu:0` in 2.228364 seconds with 201,340,160 bytes peak allocation. Paddle reported one RTX 4090 Laptop GPU. Raw evidence: `artifacts/v2/environment/paddle_gpu_smoke.json`.
