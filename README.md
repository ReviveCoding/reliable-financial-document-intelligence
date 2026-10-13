# R-FDI: Reliable Financial Document Intelligence

[![CI](https://github.com/ReviveCoding/reliable-financial-document-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/ReviveCoding/reliable-financial-document-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/ReviveCoding/reliable-financial-document-intelligence?display_name=tag)](https://github.com/ReviveCoding/reliable-financial-document-intelligence/releases/latest)

R-FDI is a Python research system for extracting information from financial documents, checking monetary consistency, and routing uncertain results for review. It connects document models with deterministic validation, a local API/worker workflow, a reviewer interface, and reproducible evaluation.

The project uses public and synthetic data. It has been tested locally, not deployed to a bank or used for live financial decisions.

## System design

1. Ingest documents and route them by type and quality.
2. Extract fields and line items with OCR, layout-aware models, or OCR-free vision-language models.
3. Normalize values and verify subtotals, taxes, totals, and row associations.
4. Assess extraction risk and route documents to review or block when appropriate.
5. Record decisions and artifacts for replay, auditing, and evaluation.

The local Docker Compose setup includes FastAPI, a worker, a reviewer interface, PostgreSQL, MinIO, Redis, and MLflow. The application queue uses durable SQLite state; Redis was tested separately for persistence and is **not** the active queue transport.

See [architecture](docs/ARCHITECTURE.md), [runbook](docs/RUNBOOK.md), and [V3 runtime evaluation](reports/v3/INFRASTRUCTURE_AND_RUNTIME.md).

## Measured results

| Evaluation | Result | Scope |
| --- | ---: | --- |
| Donut leaf-level F1 | 0.8372 | Locked CORD receipt test |
| Donut receipt-total exact match | 98.95% | Locked CORD receipt test |
| PP-OCRv5 + rules receipt-total exact match | 46.32% | Matched locked baseline |
| Absolute improvement in receipt-total exactness | +52.63 percentage points | Paired 95% bootstrap CI: +43.16 to +62.11 pp |
| Exact line-item row reconstruction | 60.23% | Retrospective row-aware evaluation |
| Matched-field micro-F1 | 0.8585 | Retrospective row-aware evaluation |
| API and reviewer behavior checks | 7/7 passed | Local execution |
| PaddleOCR-VL mean inference speedup | 1.90x | 20 matched development documents on one RTX 4090 Laptop GPU |

Receipt-total exactness measures one monetary field, **not** complete document correctness or safe autonomous processing. Line-item errors remain even when the final total matches.

### Why the learned review router was not adopted

R-FDI compared raw sequence confidence with a learned model for deciding which extractions should receive human review. In the corrected retrospective analysis, the learned model had worse risk ordering: AURC 0.3314 versus 0.2356 for raw confidence (lower is better). The proposed router was not promoted, and the existing runtime routing was left unchanged.

The retrospective CORD analysis is not a fresh independent holdout. See the [V3.2 report](reports/v3_2/FINAL_REPORT.md) and [methodology correction](reports/v3_2/METHODOLOGY_CORRECTION.md).

## Reliability and evaluation

- Frozen development and evaluation boundaries, paired baselines, and evidence manifests.
- Row-aware metrics that distinguish row matchability from field correctness and exact row reconstruction.
- Calibration, error slicing, robustness checks, and selective-risk analysis.
- Idempotent review commits, artifact persistence, service-restart recovery, and fault injection.
- Explicit preservation of negative and invalid results rather than retroactive changes to evaluation outcomes.

The 7/7 API/reviewer checks cover creation, idempotency, worker completion, review commits, pages, and metrics. PostgreSQL and MinIO were also checked for MLflow run/artifact persistence after service restarts.

## Reproduction

The deterministic checks use Python 3.10 and do not require a GPU:

    git clone https://github.com/ReviveCoding/reliable-financial-document-intelligence.git
    cd reliable-financial-document-intelligence
    python -m compileall -q src scripts tests
    PYTHONPATH=src python -m unittest discover -s tests -v
    python scripts/verify_evidence.py
    python scripts/verify_v2_committed_evidence.py
    python scripts/v3/verify_evidence.py
    python scripts/v3_1/verify_evidence.py
    python scripts/v3_2/verify_evidence.py

Full-data V2 verification requires access to its authorized CORD and FUNSD inputs. The [V3 reproducibility guide](reports/v3/REPRODUCIBILITY.md) documents the local Docker/GPU setup. Frozen final experiments should not be rerun for model selection.

## Reports and project layout

- [V2 model comparison and locked evaluation](reports/v2/FINAL_TECHNICAL_REPORT.md)
- [V3 runtime and fault recovery](reports/v3/FINAL_REPORT.md)
- [V3.1 failure and calibration analysis](reports/v3_1/FINAL_ANALYSIS_REPORT.md)
- [V3.2 row-level and selective-risk analysis](reports/v3_2/FINAL_REPORT.md)
- [Release history](docs/releases/v3.2.0.md)

Source code is in [src/rfdi](src/rfdi), [src/rfdi_v3](src/rfdi_v3), and [services](services). Test cases, configurations, and measured evidence are preserved in their respective directories.

## Scope and limitations

V1 was not promoted. V2 passed its offline extraction gates, V3 validated local runtime functionality, and V3.2 did not promote the learned risk controller. These results have different evaluation scopes and should not be combined into a single production-readiness claim.

The project has not demonstrated long-running customer production operation, regulatory certification, or low-risk unattended document automation. Dataset access restrictions and the one-GPU development setting also limit transfer claims. The next engineering steps are production-safe secret management, an actual queue transport adapter, broader document evaluation, and longer-duration operational testing.
