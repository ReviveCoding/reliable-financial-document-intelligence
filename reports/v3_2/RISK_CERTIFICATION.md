# Certification correction replay

Every row is `POST_AUDIT_REUSED_CERTIFICATION_PARTITION`, `fresh_confirmatory_evidence=false`, and `promotion_eligible=false`. Thresholds were frozen at corrected replay commit `274a2c0`, but this partition had already been observed before correction.

| Target | Accepted | Coverage | Observed | One-sided upper 95% | Replay status |
|---:|---:|---:|---:|---:|---|
| 5% | 9 | 45.0% | 22.2% | 55.0% | `REPLAY_INSUFFICIENT_SUPPORT` |
| 10% | 18 | 90.0% | 27.8% | 49.8% | `REPLAY_UNCERTIFIED` |
| 20% | 18 | 90.0% | 27.8% | 49.8% | `REPLAY_UNCERTIFIED` |

No target supplies fresh certification. A genuinely fresh external dataset is required.
