# V3.2 methodology correction

The defect was discovered on 2026-09-13 after local commit `1078332` and before remote v3.2 publication. The original protocol at `239824f` remains immutable; the erratum was frozen at `081ba8f` before recomputation.

The old implementation used positional row pairs for E0, duplicated E0 as E1, labeled any changed optimal assignment as a row failure, added a monetary penalty for assignment change alone, and presented matched-row F1 as though it described field accuracy. This mattered because row ordering is not semantic identity and row matchability is not field correctness.

The correction implements historical path-occurrence E0, positional-row E1, separate E2 matched-row and matched-field metrics, and explicit benign-permutation versus semantic/missing/spurious structure diagnostics. Monetary loss now counts actual missing, spurious, incorrect, or demonstrably misbound monetary fields only. Extractor weights, frozen predictions, features, candidate families, grids, seed, partitions, weights, and V1–v3.1 evidence did not change.

All dependent labels, model replay, reused certification statistics, retrospective risk evidence, slices, figures, reports, and governance were regenerated. The audit records 199 unchanged labels, 1 positive→negative, 0 negative→positive, 11 weighted-loss decreases, and 4 increases across 200 development/test documents.

CORD test and the certification partition had already been observed, so nothing in this replay is fresh confirmation or promotion-eligible. Remote publication was withheld until the semantics and audit trail were corrected.
