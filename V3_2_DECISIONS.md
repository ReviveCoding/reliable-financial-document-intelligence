# V3.2 decisions

- Final decision: `V3_2_RISK_MODEL_NO_PROMOTION`.
- Preserve the R4 candidate as offline negative evidence; R0 raw confidence remains the stronger evaluated ranker.
- Do not integrate shadow API fields because the frozen development promotion gates failed.
- Treat CORD test only as `RETROSPECTIVE_LOCKED_BENCHMARK`; it is not a fresh holdout and was not used to retune.
- Keep extractor weights unchanged.
- Use E2 permutation-invariant matching as the primary line-item metric and retain E0 for historical comparison.
- Report all finite-sample certificates as observed: 5% support-insufficient; 10% and 20% uncertified.
