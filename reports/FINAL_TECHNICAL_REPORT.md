# R-FDI Final Technical Report

## 1. Executive summary

R-FDI is a production-style research simulation using public manifests and synthetic data. The completed dependency-free pathway validates schemas, deterministic extraction/reconciliation, selective routing mechanics, security isolation, idempotency, and locked-final governance. The release decision is **NO_PROMOTION**: no authorized real dataset or CUDA deep baseline was available, so the required meaningful operational improvement was not established.

## 2. Business problem

The target is maximum safe automation subject to critical error, review, cost, latency, and OOD constraints—not F1 alone.

## 3. Research questions

RQ1–RQ10 were frozen in `MASTER_EXECUTION_SPEC.md`. RQ3 receives fixture-level positive evidence; RQ9 receives architecture/fixture evidence. RQ1/2/4–8/10 remain unresolved on realistic data.

## 4. Desktop study

`reports/00_DESKTOP_STUDY.md` records current primary sources and distinguishes external claims from measurements.

## 5. Requirements

Typed canonical records, strict normalization, deterministic reconciliation, provenance, risk decisions, idempotency, security isolation, CUDA-first deep execution, and a locked-final lifecycle were implemented.

## 6. Data

R-FDI Synthetic v1.0.0 has 360 generated text records with split-disjoint vendors/templates. Public dataset metadata is manifest-only; no public raw dataset was acquired.

## 7. Integrity/leakage controls

E0 found zero duplicate IDs/content and zero train/dev/final exact, vendor, or template overlap. Image/text near-duplicate methods were not available.

## 8. EDA

See `reports/03_EDA_REPORT.md`. The corpus is balanced by currency and near-balanced by document type, but has no rendered pages.

## 9. Preprocessing

Raw values remain separate from normalized values. Money uses `Decimal`; ambiguous dates/currencies fail closed. Dataset checksums fingerprint generated caches.

## 10. Baselines

Only B0 was measured. B1–B5 were accelerator-blocked; B6 lacked paid authorization. No fabricated comparison is supplied.

## 11. Proposed R-FDI method

`P0_rfdi_deterministic_v1` adds schema, reconciliation, risk routing, security boundaries, and state/idempotency controls around B0 extraction.

## 12. Experimental design

Seed 1729; 240 development documents; 120 untouched final documents. Method and gates were frozen before final authorization. The final checksum remained unchanged.

## 13. KIE results

Locked final B0: 720/720 fields, normalized exact match/F1 1.000 and schema failure 0. This is measured on regular synthetic text and should be read as a pipeline test, not model validation (`artifacts/results/e20_final.json`).

## 14. LIR results

Not run: there are no generated table geometries and DocILE access is blocked.

## 15. Financial NLP

REFinD was unavailable, so relation models were not run.

## 16. Financial reconciliation

Rules detected 34/34 development and 17/17 final injected arithmetic/date conflicts with no false positives in generated labels.

## 17. Calibration

Final ECE 0.1233, Brier 0.01577, NLL 0.13199. Perfect correctness with conservative raw confidence explains nonzero calibration error; no post-hoc calibration was justified.

## 18. OOD

Split-scoped novelty scores yield AUROC/AUPRC 1.0 by construction. This only validates split labeling and is not a real OOD model result.

## 19. Robustness

Visual robustness was not run because image generation/rendering dependencies were unavailable. No degradation curve is claimed.

## 20. Selective automation

Residual extraction error was zero at evaluated coverages on synthetic final. This prevents a meaningful comparison of selective methods.

## 21. Human review

The lightweight reviewer UI exists, but comparative review allocation is statistically non-informative with zero extraction errors.

## 22. Cross-document validation

Cross-document rules and tests are implemented. A full bundle experiment was skipped because the generated corpus does not yet persist linked PO→invoice→remittance→payment entities.

## 23. Security

Seven final generated attacks had zero attack success and zero unauthorized-action attempts under capability isolation. This is not proof of VLM prompt-injection robustness.

## 24. Operations

Final in-memory B0 P95 latency was 0.0824 ms; throughput was 12,021.6 docs/s. It excludes all realistic pipeline overhead. SQLite idempotency produced no duplicate final output under replay.

## 25. Ablation

Removing financial validation necessarily removes all conflict detections. Other ablations were not meaningful or runnable and are marked skipped.

## 26. Statistics

A 2,000-resample development bootstrap for review-capture difference returned 0.0 [0.0, 0.0] because there were no extraction errors. This is a degenerate negative result, not evidence of equivalence.

## 27. Locked final evaluation

The frozen configuration SHA-256 was recorded in E20. The final data checksum before and after evaluation was `4011f1a110173382b82d2df55c8910f3c6eac54677f9de78518b6fa824f90a90`.

## 28. Release decision

**NO_PROMOTION.** Numeric fixture gates passed, but the mandatory meaningful-improvement gate did not: there is no stronger empirical baseline, realistic OOD result, or real-data evidence.

## 29. Error analysis

Final extraction had no errors; therefore error composition cannot explain model differences. This is a dataset-easiness limitation.

## 30. Limitations

No images/OCR/public benchmark, no deep model, no empirical AWS, no real queue/database stack, no table geometry, no relation track, and a single deterministic run.

## 31. Threats to validity

Synthetic regularity, construction-derived OOD labels, tiny attack suite, excluded I/O latency, and absence of stochastic model seeds dominate internal/external validity.

## 32. Production roadmap

Restore CUDA; acquire datasets through official terms; render/corrupt synthetic pages; run OCR/deep pilots; establish real development errors; compare routes at matched risk; validate Compose and failure recovery; only then select a new candidate.

## 33. Future work

DocILE KILE/LIR, CORD/SROIE robustness, FUNSD shift, REFinD, calibrated deep confidence, visual novelty, line-item fusion, and properly powered HITL studies.

## 34. Conclusion

The repository establishes a reproducible safety/governance substrate and reports a constrained negative promotion result without overstating fixture metrics.

## 35. Reproducibility appendix

Run `make test`, `make smoke`, then inspect `artifacts/results/development_summary.json`. Blocked work resumes with the exact commands in `FINAL_STATUS.md`; locked final must not be used for iteration.
