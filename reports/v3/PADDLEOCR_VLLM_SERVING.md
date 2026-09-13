# V3 PaddleOCR-VL vLLM Serving Evaluation

PaddleOCR-VL 1.6 was served from the official NVIDIA GPU server image through
Windows Docker Desktop's `desktop-linux` context. The container image resolved to
`sha256:5713fd30ab76094b7b6a20d95fd8e26fa9dc452bcc90ccb16f1fb056bd2a0f4d`.
One physical NVIDIA GeForce RTX 4090 Laptop GPU was observed; no multi-GPU claim
is made.

The final bounded server used `gpu-memory-utilization: 0.30`, four maximum
sequences, 8,192 maximum batched tokens, and eager execution. Maximum observed
use was 10,561 of 16,376 MiB, leaving 35.51% headroom. Observed temperatures were
78, 85, 81, 82, and 81 C; no CUDA failure occurred. Earlier allocation pilots
that failed the configured headroom requirement were not used for inference.

The paired development evaluation used the same 20 CORD validation document IDs
as the preserved native result. The Docker/vLLM route completed 20 HTTP 200 chat
requests. Its mean latency was 10.727 seconds versus 20.404 seconds native, a
1.902x mean speedup. Median latency was 10.592 versus 11.277 seconds. Content-
presence recall was 0.9171 versus 0.8919, and total-value presence was 0.95 versus
0.90.

These are development-set content-presence measurements, not official structured
CORD F1 and not locked-final results. Six client setup attempts failed before any
inference request due to missing extras or corrupt zero-byte packages in the
dedicated environment; those negative setup results are retained separately.

Evidence: `artifacts/v3/serving/paddleocr_vllm_comparison.json`,
`artifacts/v3/serving/docker_vllm_validation.json`, and
`artifacts/v3/serving/client_dependency_failure.json`.
