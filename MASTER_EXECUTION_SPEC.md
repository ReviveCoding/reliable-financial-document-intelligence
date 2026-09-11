# R-FDI Master Execution Specification

Status: authoritative recovery specification  
Frozen research questions: RQ1–RQ10 as supplied in the 2026-09-11 master execution program.  
Runtime characterization: **production-style research simulation using public and synthetic data**.

This repository must execute the user-supplied **R-FDI MASTER EXECUTION PROGRAM** end-to-end. The complete program in the initiating conversation is normative; this file preserves its operational requirements in durable, compact form for resumption.

## Objective

Build and evaluate reliable financial-document intelligence across extraction quality, critical risk, automation coverage, review burden, latency, compute/API cost, OOD layouts, robustness, reconciliation, and prompt-injection containment. Compare B0 classical, B1 text-only, B2 LayoutLMv3, B3 Donut, B4 stable PaddleOCR-VL, B5 suitable Qwen3-VL 4B-class instruct, B6 Textract, and P0 adaptive R-FDI wherever access and compute permit.

## Non-negotiable controls

- Public and synthetic data only; never bypass dataset authorization or expose credentials.
- Never fabricate measurements, GPU use, cloud calls, significance, deployment, or compliance.
- CUDA is required for supported deep workloads; CUDA failure yields `BLOCKED_ACCELERATOR`, never a long CPU fallback.
- Paid AWS calls require valid credentials and positive `RFDI_AWS_BUDGET_USD`; otherwise only adapter fixtures and modeled cost are permitted.
- Preserve raw, normalized, and reviewed values separately with provenance; use `Decimal` for money and fail closed on ambiguity.
- Final data is inaccessible for method development. Lifecycle: `DEVELOPMENT → CANDIDATE_SELECTED → METHOD_FROZEN → FINAL_EVAL_AUTHORIZED → FINAL_EVAL_COMPLETE`.
- After freeze, do not tune from final results. Release result is exactly `PROMOTE` or `NO_PROMOTION`.
- Document text is untrusted data. Models have no action capabilities; schema and deterministic application controls mediate output.
- Never commit bulk raw data, weights, checkpoints, secrets, or caches.

## Required execution

Execute phases P00–P50 from the initiating program and assign every phase one of `PENDING`, `RUNNING`, `COMPLETE`, `FAILED`, `BLOCKED`, or `SKIPPED_WITH_REASON`. Maintain `WORKFLOW_STATE.json`, `EXPERIMENT_REGISTRY.csv`, `EVIDENCE_MANIFEST.jsonl`, `BLOCKERS.md`, and `DECISIONS.md`. Optional blockers must not stop unrelated work.

The work covers: current desktop study; authorized dataset manifests; integrity, leakage, EDA, preprocessing; transaction-consistent synthetic invoices/POs/receipts/remittances/payments/statements with visual, business, and security corruptions; OCR, classification, KIE, LIR, relations; reconciliation; OOD; field calibration; risk and routing; selective automation/HITL; robustness and transfer; security; production-style local API/state machine/idempotency; fault and performance tests; lifecycle simulations; ablations/statistics; final tables/figures/report; resume evidence; self-review and reproducibility.

## Evaluation contract

Track standard extraction metrics, calibration (ECE/Brier/NLL/AURC), OOD (AUROC/AUPRC), weighted critical error, critical false accepts, residual risk at coverage, review efficiency, latency/throughput/cost, and security outcomes. Use development-derived criticality weights and sensitivity analysis. Use paired/bootstrap inference when sample size supports it, explicitly distinguishing measured, modeled, and literature values. Every numerical report claim must resolve through `EVIDENCE_MANIFEST.jsonl` to an artifact.

## Compute and experiment policy

Use pilot → prune → confirm. Record physical device/count, CUDA/framework, precision, batch size, peak VRAM, runtime, seed, and configuration. Independent GPU concurrency is at most two and only after measured VRAM/headroom, throughput, temperature, and stability pilots. CPU remains valid for generation, hashing, rendering, lightweight OCR, statistics, plots, and orchestration.

## Completion contract

Before completion: re-read `AGENTS.md` and this file; ensure every P00–P50 state is justified; run tests and reproducibility smoke tests; verify holdout integrity and numerical evidence; inspect Git state; and write evidence-complete `FINAL_STATUS.md` with completed/blocked/failed work, selected system, exact release result, verified metrics, actual hardware, limitations, access requirements, reproduction commands, and resume commands.
