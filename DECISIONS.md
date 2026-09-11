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
