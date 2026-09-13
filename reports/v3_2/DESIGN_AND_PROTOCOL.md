# Design and protocol

The original v3.2 protocol was frozen at `239824f`; methodology erratum `081ba8f` precedes corrected results. Corrected development replay was frozen at `274a2c0` before reopening already-observed certification/test partitions. Extractor weights and the exact R0–R5 algorithms, production-safe features, 60/20/20 grouping, grids, seed, 2,000-replicate bootstrap, risk weights, budgets, and gates remain unchanged.

Designations are `DEVELOPMENT_CORRECTION_REPLAY`, `DEVELOPMENT_THRESHOLD_REPLAY`, `POST_AUDIT_REUSED_CERTIFICATION_PARTITION`, and `RETROSPECTIVE_LOCKED_BENCHMARK`. All have `fresh_confirmatory_evidence=false`; corrected replay alone cannot promote a model.
