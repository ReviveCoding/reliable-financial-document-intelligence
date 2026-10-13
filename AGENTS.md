# Development Notes

R-FDI contains several completed, separately evaluated research releases. Keep their data, model selections, evaluation splits, and evidence records distinct.

## Workspace and data

- Confirm the repository root with git rev-parse --show-toplevel and check for .rfdi-workspace-root before modifying files.
- Do not write to other repositories or put datasets, credentials, model weights, virtual environments, or caches under version control.
- Do not run paid cloud services without the repository owner's authorization and a configured budget.
- GPU-dependent experiments require a verified CUDA runtime. Record hardware, model revision, batch size, precision, and measured performance; do not relabel CPU runs as GPU results.

## Reproducibility

- Treat frozen final evaluations and published evidence manifests as immutable.
- Preserve unsuccessful runs and invalidated comparisons. Do not silently replace failed measurements.
- Keep raw, normalized, and reviewed document values separate; verify monetary calculations with Decimal.
- Route uncertain actions through deterministic validation and review controls.
- Maintain the workflow state, experiment registries, evidence manifests, blockers, and decision records required by the relevant version.

## Validation

Before proposing changes, run the applicable unit tests and version-specific evidence verifiers listed in README.md. Describe the effect of any source modification on reproducibility and existing results.

This repository is a local research and engineering prototype, not a financial-production system or compliance certification.
