# R-FDI CODEX OPERATING POLICY

Authorized workspace:

Windows:
C:\Users\bjw-0\Downloads\R-FDI

WSL:
/mnt/c/Users/bjw-0/Downloads/R-FDI

Before the first mutation and before every major mutating phase:

1. run `pwd`
2. run `git rev-parse --show-toplevel`
3. verify `.rfdi-workspace-root`
4. confirm the Git root is exactly:
   `/mnt/c/Users/bjw-0/Downloads/R-FDI`

If any check disagrees, stop mutations immediately.

Never modify another repository.

## Durable execution

Execute the user's R-FDI master prompt end-to-end.

Do not stop after planning or scaffolding.

Maintain:

- WORKFLOW_STATE.json
- EXPERIMENT_REGISTRY.csv
- EVIDENCE_MANIFEST.jsonl
- BLOCKERS.md
- DECISIONS.md

A blocker in one optional component must not stop unrelated work.

## GPU-first

Use CUDA for every supported deep-learning, Transformer, VLM, embedding,
training, fine-tuning, and deep inference workload.

Never silently substitute a long CPU run after CUDA failure.

CPU may run concurrently for:

- preprocessing
- PDF rendering
- hashing
- synthetic generation
- statistics
- plotting
- orchestration

Prefer batching and vectorized GPU execution.

Independent GPU jobs may run concurrently only after measured pilot tests prove:

- combined peak VRAM plus configured headroom fits;
- aggregate throughput improves;
- temperatures remain stable;
- CUDA remains stable.

Maximum independent GPU jobs is 2, not a target.

Never claim multi-GPU execution unless multiple physical GPUs were actually used.

Honor:

- RFDI_RUNTIME_ROOT
- RFDI_DATA_ROOT
- RFDI_CHECKPOINT_ROOT
- RFDI_GPU_REQUIRED
- RFDI_GPU_PARALLEL_MODE
- RFDI_GPU_MAX_CONCURRENT_JOBS
- RFDI_GPU_VRAM_HEADROOM_PCT
- RFDI_CPU_WORKERS

## Research integrity

Never fabricate metrics or evidence.
Never hide negative results.
Never tune on locked final data.
Never remove stronger baselines.
Never bypass dataset authorization.
Never expose credentials.
Never claim real-bank production deployment.
Never claim regulatory compliance.

Do not incur paid cloud cost without explicit positive
RFDI_AWS_BUDGET_USD and valid credentials.

Do not push or publish remotely.