# Row-aware line-item evaluation

E0 reproduces historical flat occurrence matching. E1 preserves strict row order. E2, the primary metric, uses maximum-weight bipartite line-item matching and does not require row identifiers to match numerically. Ten synthetic unit cases cover perfect, reordered, duplicated, missing, spurious, cross-row, split-menu, and repeated-value behavior.

| Benchmark | E0 flat F1 | E2 line-item F1 | Field-within-row F1 | Row exact | Alignment failure |
|---|---:|---:|---:|---:|---:|
| Development | 0.8504 | 0.9662 | 0.8583 | 0.6154 | 3.0% |
| Retrospective CORD test | 0.7887 | 0.9534 | 0.8282 | 0.6023 | 10.0% |

E2 raises the perceived test F1 by +0.1647 because it correctly treats harmless row permutations as equivalent. That does not erase structure failures: 10% of test documents have alignment failures, row exact match is 60.23%, with 11 unmatched GT and 22 spurious predicted rows.

![Row matching](../../docs/assets/v3_2/historical_vs_row_aware.svg)
