# R-FDI: Reliable Financial Document Intelligence

Risk-calibrated, cost-aware, audit-oriented Document AI for payment operations. This repository is a **production-style research simulation using public and synthetic data**, not a bank deployment or compliance claim.

## Verified local results

R-FDI V1 at commit `86a53a61d9a33f54f126e0ed81b859d5ffb70a50` remains governance/pipeline-fixture evidence with its historical **NO_PROMOTION** decision. Its synthetic text metrics are not real-document evidence.

R-FDI V2 is a separate real-document and GPU lineage. On locked CORD v2 test data, Donut reached leaf F1 0.8372 and total exact match 0.9895 on 95 eligible receipts versus 0.4632 for PP-OCRv5 plus rules (absolute +0.5263; paired bootstrap 95% CI [0.4316, 0.6211]). Frozen LayoutLMv3 reached macro-F1 0.7009 on the 50-document FUNSD test set. All ten predeclared V2 gates passed, so the offline research candidate earned **PROMOTE** to further shadow research—not production deployment, bank use, or regulatory approval.

## Reproduce

```bash
cd /mnt/c/Users/bjw-0/Downloads/R-FDI
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m rfdi.cli run --config configs/experiments/core.json
PYTHONPATH=src python3 -m rfdi.cli resume
```

The locked-final commands are governance-protected and must not be rerun for tuning. See [V2 final status](V2_FINAL_STATUS.md), [V2 technical report](reports/v2/FINAL_TECHNICAL_REPORT.md), [V1 final status](FINAL_STATUS.md), [blockers](BLOCKERS.md), and [runbook](docs/RUNBOOK.md).

## Layout

Core logic is under `src/rfdi`; synthetic manifests are under `data/manifests`; measured evidence is under `artifacts/results`; reports explicitly label measured, modeled, external, blocked, or not-run claims. Bulk datasets and model weights are ignored.
