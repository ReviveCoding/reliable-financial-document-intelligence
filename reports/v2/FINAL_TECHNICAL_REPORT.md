# R-FDI V2 Final Technical Report

## 1. Executive summary

R-FDI V2 completed the real-document and GPU study that V1 could not. V1 commit `86a53a61d9a33f54f126e0ed81b859d5ffb70a50` remains immutable governance/pipeline-fixture evidence with **NO_PROMOTION**. V2 independently evaluated CORD v2, FUNSD, and a newly rendered synthetic corpus using PP-OCRv5, LayoutLMv3, Donut, PaddleOCR-VL-1.6, and Qwen3-VL-4B-Instruct on one RTX 4090 Laptop GPU.

The frozen V2 decision is **PROMOTE**, scoped only to the offline research candidate `V2_FIXED_FAMILY_GATED_WITH_RFDI_CONTROLS`. It is not production deployment, bank use, regulatory compliance, or permission for unattended payments.

## 2. Business problem and research questions

The objective is selective document automation under accuracy, critical risk, review, cost, latency, OOD, and security constraints—not extraction F1 alone.

- RQ1: Task-specific evidence favors Donut for CORD KIE and LayoutLMv3 for FUNSD forms; Qwen was accurate on a narrow compatible-field sample but much slower. Direct pooled ranking is invalid.
- RQ2: No. The tested adaptive cascade added latency and selected Donut for every development document.
- RQ3: Yes, narrowly: arithmetic reconciliation caught 1/3 high-confidence OCR total errors.
- RQ4: Yes on the held-out development calibration split; isotonic calibration materially reduced ECE/Brier. Sample size limits generalization.
- RQ5: Partially. Synthetic scaling improved document classification; synthetic-to-real receipt transfer was poor and extractor augmentation was not established.
- RQ6: No. The tested visual Mahalanobis novelty method was near chance and did not improve review capture.
- RQ7: Confidence-first and R-FDI risk were best/tied at the main 20% development budget; OOD-first underperformed.
- RQ8: Donut balanced quality and latency best for receipts; Qwen and PaddleOCR-VL had substantially higher latency, while PP-OCRv5 was faster but weaker for total extraction.
- RQ9: The no-tools boundary contained side effects. On six final pairs, attack/control output deviation was zero, but structured integrity was only 5/6; containment is not perfect extraction.
- RQ10: No. The most accurate narrow VLM result was not selected because latency, task breadth, and evidence size mattered.

## 3. Desktop study and requirements

Current official sources, revisions, licenses, infrastructure versions, and modeled cloud pricing are catalogued in `reports/v2/00_DESKTOP_STUDY.md`. Paid Textract was not run because no positive cloud budget was authorized. Requirements included public/synthetic-only data, exact provenance, fail-closed holdout access, CUDA for deep work, and separate raw/normalized/review histories.

## 4. Data, integrity, leakage, and EDA

CORD v2 (800/100/100) and FUNSD (149/50 official train/test, with 120/29 internal train/dev) were acquired from public official routes and integrity checked. Synthetic V2 contains 300/100/100 documents with multiple layouts, vendors, document types, line items, bounding boxes, multipage continuation pages, visual/business/security corruptions, and split-specific geometry.

No exact cross-split image overlap was found. CORD contained seven exact normalized OCR-text train/test overlaps and eleven highly similar test texts; these official-split risks are disclosed. Synthetic near-dHash matches remained but vendor/layout identifiers and exact images were disjoint. A pre-freeze audit found and corrected one continuation-page duplicate and reused geometry; all affected development experiments were rerun before selection.

## 5. Preprocessing and models

Canonical JSONL preserves document IDs, images, OCR/text, fields, boxes, relations/corruptions, and provenance. Money stays raw plus normalized and is not guessed when ambiguous. Deep routes were revision pinned; weights, datasets, environments, and checkpoints live outside Git under the runtime root.

Measured final results are in `artifacts/v2/tables/model_comparison.csv`. Donut reached leaf F1 0.8372 on 100 CORD test receipts. LayoutLMv3 reached macro-F1 0.7009 on 50 FUNSD test forms. PP-OCRv5 reached CER 0.1983, WER 0.3716, and total exact 0.4632. These metrics are task-specific.

## 6. LIR, financial NLP, and reconciliation

CORD menu leaves supplied line-item evidence through Donut, and rendered line-item row recall was 0.8792; official DocILE LIR remained blocked by authorized access. REFinD relation extraction also remained blocked, so no empirical relation F1 is claimed. Deterministic validation detected all 100 injected business-corruption cases with zero valid-case false positives and caught one of three high-confidence OCR total errors.

## 7. Calibration, OOD, routing, and HITL

Development isotonic calibration reduced Paddle total ECE from 0.3146 to 0.0295. Visual OOD was negative (AUROC 0.5013). The adaptive route was therefore excluded; confidence-first review and deterministic risk controls were retained. Review comparisons are budget-matched simulations, not a live annotator trial.

## 8. Robustness and transfer

Rendered final field recall was 0.9069; low resolution fell to 0.7372. Synthetic-to-CORD classifier transfer was only 0.11. These failures are retained, and no fake common cross-dataset score is used.

## 9. Security and operations

Final VLM attack testing separated detector activation (83.3%), structured integrity (83.3%), output deviation (0.0%), schema violation (0.0%), and unauthorized actions (0). The extractor had no action capabilities. GPU device, precision, runtime, and peak allocation are preserved per experiment. AWS cost is modeled only; no paid calls occurred.

## 10. Ablation and statistics

Negative ablations led to a simpler fixed family-gated system: removing adaptive routing reduced latency; removing weak visual OOD improved review capture. Bootstrap statistics appear in the release artifact. The CORD total exact advantage was 0.5263, paired 95% CI [0.4316, 0.6211].

## 11. Locked final and release decision

The method was selected and frozen before final labels were exposed to evaluators. All ten frozen gates passed. Donut total exact was 0.9895 versus 0.4632; Donut P95 was 4.648s; schema failures were zero. Synthetic final field recall/total exact were 0.9069/0.9000. Decision: **PROMOTE** for offline research only.

## 12. Error analysis, limitations, and threats to validity

Final errors include OCR misses, missing/spurious Donut leaves, and line-item row misses; counts are in `artifacts/v2/statistics/final_error_taxonomy.json`. Limitations include single-seed LayoutLM training, small Qwen/PaddleOCR-VL samples, task-incompatible metrics, official CORD text similarity, weak OOD, synthetic-to-real transfer failure, no DocILE/SROIE/REFinD, no empirical Textract, no live human study, no Docker stack execution, and no energy-metered cost.

## 13. Production roadmap and future work

Promotion means only that the frozen offline candidate earned further shadow evaluation. A real deployment would require authorized datasets, larger vendor/layout samples, multiple training seeds, calibrated field-criticality with stakeholders, monitored reviewer studies, privacy/security assessment, infrastructure load tests, rollback exercises, and explicit payment-system separation.

## 14. Reproducibility appendix

Exact commands and external runtime paths are in `V2_FINAL_STATUS.md`; frozen inputs/hashes are in `configs/v2/frozen.json`. Every numerical claim above resolves to V2 JSON artifacts, tables, or the V2 evidence manifest. V1 and V2 conclusions are deliberately separate.

## 15. Specification cross-reference

The master-report topics map as follows: executive summary (section 1); business problem and research questions (section 2); desktop study and requirements (section 3); data, integrity/leakage controls, and EDA (section 4); preprocessing, baselines, proposed R-FDI method, experimental design, and KIE results (section 5 and the frozen configuration); LIR and financial NLP (section 6); financial reconciliation (section 6); calibration, OOD, selective automation, and human review (section 7); robustness and cross-document limitations (sections 6 and 8); security and operations (section 9); ablation and statistics (section 10); locked final evaluation and release decision (section 11); error analysis, limitations, and threats to validity (section 12); production roadmap, future work, and conclusion (section 13); reproducibility (section 14). Detailed evidence is in the sibling V2 reports.
