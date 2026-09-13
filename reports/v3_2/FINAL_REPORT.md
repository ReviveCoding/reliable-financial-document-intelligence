# R-FDI v3.2 final report

## Outcome

`V3_2_RISK_MODEL_NO_PROMOTION`. Extractor weights did not change, and CORD test is retrospective—not a fresh holdout.

## Answers

- **How did row awareness change perceived error?** Test E0 F1 0.7887 becomes E2 0.9534 (+0.1647), while row exact match remains 60.2%.
- **Which errors dominate?** row_not_exact affects 52.0%; line-item critical errors affect 32.0%; correct-total/wrong-item-price cases affect 25.0%.
- **Which features rank failures?** foreground_density, missing_discount, sequence_confidence, edge_density, predicted_long_description; nevertheless, R4 ranking is inferior to R0.
- **Does learned risk beat raw confidence?** No: retrospective AURC 0.3314 versus 0.2356.
- **Does calibration help?** Uncalibrated R4 has Brier 0.2288/ECE 0.0978. Platt and isotonic worsen retrospective Brier/ECE; calibration does not repair ranking.
- **What review budget is needed?** No budget through 50% passes the operating gate; even 80% review leaves 15% accepted critical risk for R0.
- **Is auto-accept certifiable?** No; 5% is support-insufficient, 10% and 20% are uncertified.
- **Does corruption raise risk?** Only weakly and inconsistently under the pre-inference-only response test; high occlusion adds +0.0437 mean risk despite major degradation.
- **Can it enter shadow mode?** No under the frozen gate.
- **What fresh evidence is missing?** Authorized DocILE LIR validation and a larger grouped development/certification set with end-to-end corrupted extraction outputs.

## Slices

Strongest adequately supported cohorts:

- `sequence_confidence:high` — N=33, critical error 9.1%, E2 F1 1.0000.
- `image_megapixels:high` — N=26, critical error 30.8%, E2 F1 0.9749.
- `predicted_line_item_count:low` — N=40, critical error 35.0%, E2 F1 0.9583.

Weakest adequately supported cohorts:

- `sequence_confidence:low` — N=34, critical error 76.5%, E2 F1 0.8956.
- `predicted_line_item_count:high` — N=20, critical error 65.0%, E2 F1 0.9036.
- `reconciliation_residual:high` — N=20, critical error 55.0%, E2 F1 0.9219.

Latency correlates moderately with predicted line-item count (r=0.533) but weakly with learned risk (r=0.184); p95 is 4.648s.
