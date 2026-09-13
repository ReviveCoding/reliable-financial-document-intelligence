# V3.2 decisions

- Final decision: `V3_2_RISK_MODEL_NO_PROMOTION`.
- Preserve the corrected-target R4 replay as offline negative evidence; R0 raw confidence remains the stronger evaluated ranker.
- Do not integrate shadow API fields because the frozen development promotion gates failed.
- Treat CORD test only as `RETROSPECTIVE_LOCKED_BENCHMARK`; it is not a fresh holdout and was not used to retune.
- Keep extractor weights unchanged.
- Use E2 permutation-invariant matching as the primary line-item metric and retain E0 for historical comparison.
- Report certification only as a non-confirmatory replay of an already-observed partition; no replay result is promotion-eligible.
- Preserve `1078332` and the pre-correction artifact hashes in the audit trail.
