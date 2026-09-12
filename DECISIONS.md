# Decisions

## D001 — Research characterization

The system is described as a **production-style research simulation using public and synthetic data**. No production-bank or regulatory claim is permitted.

## D002 — Accelerator fail-closed behavior

Deep CUDA-capable workloads are blocked when CUDA/NVML is unavailable. CPU execution remains valid for deterministic baselines, generation, audits, statistics, and orchestration.

## D003 — Locked-final isolation

Final examples are deterministically generated into a physically separate locked path. Development commands reject that path unless the persisted lifecycle is `FINAL_EVAL_AUTHORIZED` or `FINAL_EVAL_COMPLETE`.

## D004 — Cloud spending

Textract empirical evaluation is not run without both explicit positive budget and valid credentials. Modeled estimates must be labeled modeled.

## D005 — Pre-freeze baseline correction

The first development integration run revealed that an unanchored invoice-number regex matched `Invoice Date`. The baseline label patterns were anchored, a regression test was added, and all affected development artifacts were regenerated before candidate selection. No final result was accessed to make this correction.

## D006 — Candidate and release gates frozen

Selected `P0_rfdi_deterministic_v1`: B0 anchored extraction plus normalization, independent reconciliation, risk routing, schema enforcement, and capability-isolated security boundary. Frozen thresholds are review risk 0.36, quarantine risk 0.78, and OOD 0.62. Gates are: critical false-accept rate ≤ 0.01, schema-failure rate = 0, P95 extraction latency ≤ 100 ms, security attack success = 0, and a meaningful improvement in automation coverage, review efficiency, operating cost, or OOD robustness. The last condition prevents promotion on gate compliance alone.

The locked synthetic final SHA-256 observed before authorization was `4011f1a110173382b82d2df55c8910f3c6eac54677f9de78518b6fa824f90a90`; only the checksum, not record content, was used before freeze.

## D007 — V2 corrects accelerator diagnosis without rewriting V1

V1 and commit `86a53a61d9a33f54f126e0ed81b859d5ffb70a50` remain immutable governance/pipeline-fixture evidence with `NO_PROMOTION`. V2 established that bubblewrap hid `/dev/dxg`; an approved escalated probe and actual PyTorch/Paddle GEMMs succeeded on one RTX 4090 Laptop GPU. This supersedes the active accelerator blocker for V2 without altering V1's historical execution record.

## D008 — V2 candidate and gates frozen

Development selected `V2_FIXED_FAMILY_GATED_WITH_RFDI_CONTROLS`. Fixed Donut and the frozen LayoutLMv3 checkpoint are task-gated; deterministic reconciliation and confidence-first review remain controls. Adaptive routing and visual-OOD routing are excluded because both were negative on development. Qwen3-VL and PaddleOCR-VL remain empirical comparators but are excluded from the default path because of latency. Exact final hashes, model revisions, gates, and the binary decision rule are frozen in `configs/v2/frozen.json` before final inference.

## D009 — Post-freeze evaluator-only corrections

After freeze, the evaluators were changed only to derive the displayed split name from the locked input, label the synthetic evaluation partition `final`, and compute a deterministic document-level bootstrap. The completed Donut prediction artifact's incorrect literal `validation` label was corrected in place to `official test`; no prediction, model, input, threshold, or gate changed and no model run was repeated for this metadata correction.

## D010 — V2 release decision

Exactly one authorized locked-final sequence was executed. All ten predeclared gates passed, producing **PROMOTE** for the offline research candidate only. This authorizes further shadow research, not production deployment, payment actions, bank use, or regulatory claims. Negative development results for adaptive routing, visual OOD, and synthetic-to-real transfer remain part of the evidence.
