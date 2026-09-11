# R-FDI: Reliable Financial Document Intelligence

Risk-calibrated, cost-aware, audit-oriented Document AI for payment operations. This repository is a **production-style research simulation using public and synthetic data**, not a bank deployment or compliance claim.

## Verified local result

The only completed empirical extractor is B0 (anchored regex plus deterministic normalization) on regular, generated text. Locked synthetic final: 120 documents, 720 evaluated fields, normalized exact match 1.000, schema-failure rate 0, P95 in-memory extraction latency 0.082 ms, 17/17 injected financial conflicts detected, and 0/7 generated injection attacks succeeded under the no-action capability boundary. These figures do **not** establish real-document performance. Release decision: **NO_PROMOTION**, because no real-data or deep-model comparison established meaningful operational improvement.

## Reproduce

```bash
cd /mnt/c/Users/bjw-0/Downloads/R-FDI
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m rfdi.cli run --config configs/experiments/core.json
PYTHONPATH=src python3 -m rfdi.cli resume
```

The locked-final command is governance-protected and should not be rerun for tuning. See [FINAL_STATUS.md](FINAL_STATUS.md), [technical report](reports/FINAL_TECHNICAL_REPORT.md), [blockers](BLOCKERS.md), and [runbook](docs/RUNBOOK.md).

## Layout

Core logic is under `src/rfdi`; synthetic manifests are under `data/manifests`; measured evidence is under `artifacts/results`; reports explicitly label measured, modeled, external, blocked, or not-run claims. Bulk datasets and model weights are ignored.
