# R-FDI V2 Final Status

## Outcome

Lifecycle: `V2_FINAL_EVAL_COMPLETE`  
Selected system: `V2_FIXED_FAMILY_GATED_WITH_RFDI_CONTROLS`  
Release decision: **PROMOTE**  
Scope: offline production-style research simulation only.

V1 at commit `86a53a61d9a33f54f126e0ed81b859d5ffb70a50` remains intact with its historical **NO_PROMOTION** pipeline-fixture decision. V2 is a separate evidence lineage and does not reinterpret V1.

## Primary verified final metrics

- CORD v2 test (100 documents): Donut leaf F1 0.8372; total exact 0.9895 on 95 eligible receipts; schema failures 0.0%; P95 4.648s.
- PP-OCRv5 CORD test: total exact 0.4632; Donut absolute gain 0.5263, paired bootstrap 95% CI [0.4316, 0.6211].
- FUNSD official test (50 documents): frozen LayoutLMv3 macro-F1 0.7009.
- Rendered synthetic locked final (100 documents): field recall 0.9069; total exact 0.9000.
- Six final attack/control pairs: detector activation 83.3%; structured integrity 83.3%; output deviation/schema violation/compliance signals 0%; unauthorized actions 0 because no action tools existed.

## Hardware actually used

One NVIDIA GeForce RTX 4090 Laptop GPU, 16,376 MiB physical VRAM; PyTorch 2.14.0+cu130 and Paddle 3.3.0 CUDA. Deep work ran outside bubblewrap after `/dev/dxg` was confirmed hidden inside the default sandbox. BF16/FP16/FP32 and peak VRAM are recorded per experiment. No CPU deep fallback, parallel heavy GPU jobs, multi-GPU claim, or paid cloud call occurred.

## Completed and unresolved

Completed: CORD and FUNSD acquisition/conversion/audit; rendered synthetic V2; OCR; document classification; LayoutLMv3 training/test; Donut; PaddleOCR-VL-1.6; Qwen3-VL; calibration; reconciliation; OOD; routing; HITL simulation; scaling/transfer; robustness; security; performance; ablation; statistics; holdout freeze/final/release.

Blocked: DocILE token, REFinD official access, and SROIE official account registration. Textract was not run without a positive AWS budget. Docker runtime validation, active learning, QLoRA, and larger synthetic conditions were skipped with reasons in `V2_WORKFLOW_STATE.json`. Negative results—weak visual OOD and synthetic-to-real transfer—are retained.

No locked-final experiment failed. Pre-final failures retained in the registry/evidence are: PaddleOCR-VL Transformers-version incompatibilities; a native page-layout pilot pruned after exceeding five minutes; an initial synthetic audit failure that found one duplicate continuation page and reused geometry, corrected before freeze; and a recoverable Qwen pilot allocator warning. Each affected successful route was independently completed before selection, and no failed route was presented as measured success.

## Reproduce and verify

```bash
cd /mnt/c/Users/bjw-0/Downloads/R-FDI
PYTHONPATH=src /usr/bin/python3 -m unittest discover -s tests -v
PYTHONPATH=src /usr/bin/python3 scripts/verify_evidence.py
/home/bjw-0/.local/share/rfdi-runtime/venvs/rfdi-v2-cu130/bin/python scripts/v2_package_evidence.py
```

See `reports/v2/REPRODUCIBILITY.md` for exact environment and development-model commands. Locked-final commands are recorded there for provenance and must not be reused for tuning.

The locked final commands are provenance records, not tuning commands. To resume newly authorized external datasets without touching V1 or rerunning V2 final:

```bash
cd /mnt/c/Users/bjw-0/Downloads/R-FDI
git switch gpu-completion-v2
/usr/bin/python3 scripts/v2_acquire.py --help
```
