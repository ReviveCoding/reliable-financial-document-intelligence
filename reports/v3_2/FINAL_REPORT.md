# R-FDI v3.2 corrected final report

## Decision

`V3_2_RISK_MODEL_NO_PROMOTION`. This is a methodology-correction replay, not a new model study or fresh confirmation.

- Old reported E0 was 0.7887; corrected E0 path-occurrence F1 is 0.8016. E1 positional F1 is 0.7887.
- E2 matched-row F1 is 0.9534; distinct matched-field micro F1 is 0.8585; row exact rate is 0.6023.
- Benign permutation-only rate is 0.0%; semantic association error is 10.0%. Benign permutation is excluded from failures and risk.
- Retrospective critical prevalence remains 41.0%; line-item critical prevalence is 33.0%. Mean weighted loss changed from 0.173106 to 0.173622.
- Across development and test, 1 label changed positive→negative, 0 negative→positive, 11 losses decreased, and 4 increased. No observed real document was a pure-permutation-only case.
- Failure prevalence: semantic association 10.0%, missing row 6.0%, spurious row 10.0%, incorrect item price 18.0%, missing item price 10.0%, correct total/wrong item price 22.0%, document-total error 10.0%.
- R4 remains inferior to R0; calibration does not repair ranking. No operating or certification replay gate supports promotion.
- Latency has r=0.533 with predicted row count and p95 4.648s.
