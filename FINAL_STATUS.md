# Final Status

> This file is the preserved R-FDI V1 final status. V1 remains **NO_PROMOTION**. The separate R-FDI V2 real-document/GPU study completed with an offline-research **PROMOTE** decision; see [V2_FINAL_STATUS.md](V2_FINAL_STATUS.md) and [reports/v2/FINAL_TECHNICAL_REPORT.md](reports/v2/FINAL_TECHNICAL_REPORT.md). V2 does not rewrite the evidence below.

## Outcome

Evaluation lifecycle: `FINAL_EVAL_COMPLETE`  
Selected system: `P0_rfdi_deterministic_v1`  
Release decision: **NO_PROMOTION**

Numeric fixture gates passed, but the required meaningful operational-improvement gate failed because no real-document or deep-model comparison was executable. This is a production-style research simulation using public manifests and synthetic data—not a real-bank deployment or compliance claim.

## Completed work

Completed: workspace/environment recovery; primary-source desktop study; dependency/runtime design; dataset manifests; canonical schema and normalization; deterministic synthetic text corpus; integrity/EDA/leakage checks; B0 KIE; reconciliation; raw calibration metrics; synthetic construction OOD check; G3 routing mechanics; HITL simulation/UI; security boundary; in-memory performance; idempotency/fault fixture; bootstrap analysis; candidate/gates/freeze; locked final; shadow/canary lifecycle simulation; release decision; reports/tables/figures/resume evidence; final audit and tests.

All 51 P00–P50 phases have a terminal state in `WORKFLOW_STATE.json`.

## Blocked and skipped work

- `BLOCKED_ACCELERATOR`: LayoutLMv3, Donut, PaddleOCR-VL-1.6, Qwen3-VL-4B-Instruct, deep OCR, relation encoders, and trainable scaling. The active WSL session could not initialize NVML; no CPU fallback was used.
- `BLOCKED_ACCESS`: DocILE and REFinD were not authorized/acquired.
- `NOT_RUN_NO_CLOUD_AUTHORIZATION`: empirical Textract. No AWS cost was incurred.
- Docker service stack: unavailable in active WSL.
- Visual robustness/transfer/LIR/meaningful ablations/active learning were skipped because required images, public data, errors, or models were absent.

No registered experiment ended `FAILED`. One pre-freeze integration run exposed an invoice-label regex collision; it was corrected, regression-tested, and rerun (D005).

## Primary verified metrics

Locked R-FDI Synthetic v1.0.0 final, 120 documents / 720 fields:

- normalized exact match and F1: 1.000
- critical-total exact match: 1.000
- schema-failure rate: 0
- financial inconsistency detection: 17/17, 0 false positives
- raw-confidence ECE: 0.12333; Brier: 0.01577
- in-memory B0 latency P50/P95/P99: 0.0587/0.0824/0.7730 ms
- generated security attacks: 0/7 successes; 0 unauthorized action attempts

These measurements are pipeline-fixture evidence only. OOD AUROC/AUPRC 1.0 is construction-derived and not real-world evidence. HITL statistics are degenerate because extraction errors were zero.

## Hardware/device actually used

All measured experiments ran on CPU under WSL2 with Python 3.10.12. Prelaunch detected one RTX 4090 Laptop GPU (16,376 MiB), but the active session blocked NVML. **No GPU experiment ran and no multi-GPU claim is made.**

## Validation

Final audit passed 9/9 unit tests, Python compilation, 16 pinned evidence records, JSON/JSONL parsing, 22 experiment rows, 51 phase rows, and holdout checksum verification. Final checksum remained `4011f1a110173382b82d2df55c8910f3c6eac54677f9de78518b6fa824f90a90`.

## Reproduction commands

```bash
cd /mnt/c/Users/bjw-0/Downloads/R-FDI
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/verify_evidence.py
PYTHONPATH=src python3 -m rfdi.cli resume
```

Development regeneration only (never use locked final to tune):

```bash
PYTHONPATH=src python3 -m rfdi.cli run --config configs/experiments/core.json
```

## Exact blocked-work resume

After restoring WSL GPU access and obtaining authorization through official channels:

```bash
cd /mnt/c/Users/bjw-0/Downloads/R-FDI
nvidia-smi
PYTHONPATH=src python3 -m rfdi.cli resume
```

Then create revision-pinned CUDA environments under `RFDI_RUNTIME_ROOT`, run smoke/pilot tests, and update only the affected blocked experiments. Never paste tokens or keys into repository files or logs. Do not rerun E20 for model selection.
