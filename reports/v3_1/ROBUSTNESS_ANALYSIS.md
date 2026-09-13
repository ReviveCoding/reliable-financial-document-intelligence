# Controlled robustness analysis

Ten development receipts were selected deterministically across frozen complexity bands from the same 20-document frame supported by prior PaddleOCR-VL evidence. Donut and PaddleOCR-VL Docker/vLLM processed identical clean and corrupted images: Gaussian blur, rotation, downsampling, JPEG compression, contrast reduction and partial occlusion at two frozen severities. One heavy GPU job ran at a time; no CPU fallback was used.

The largest measured critical-content degradation is `Donut CORD v2` under `occlusion` `high`: -0.2200 from its clean development reference. These content-presence metrics are not official structured CORD F1. With N=10, robustness comparisons are descriptive development evidence, not locked-final model claims.
