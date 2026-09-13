# Finite-sample risk certification

Thresholds were selected before opening the 20-document independent certification partition. Results use a one-sided exact 95% Clopper–Pearson upper bound for binary loss and a one-sided empirical-Bernstein bound for bounded weighted loss. These are research certificates conditional on source-document exchangeability and an unchanged pipeline, not regulatory guarantees.

| Target | Accepted | Coverage | Observed risk | Binary upper 95% | Status |
|---:|---:|---:|---:|---:|---|
| 5% | 9 | 45.0% | 33.3% | 65.5% | `INSUFFICIENT_CERTIFICATION_SUPPORT` |
| 10% | 18 | 90.0% | 33.3% | 55.4% | `UNCERTIFIED` |
| 20% | 18 | 90.0% | 33.3% | 55.4% | `UNCERTIFIED` |

No automatic-accept region is certified. The 5% target also has insufficient accepted support (N=9).
