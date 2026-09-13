# Design and protocol

The v3.2 protocol was frozen at commit `239824f` before new v3.2 results and the development candidate/threshold checkpoint was committed at `3532686` before certification or retrospective test evaluation. CORD test is a `RETROSPECTIVE_LOCKED_BENCHMARK`, not a fresh untouched holdout. Extractor weights were unchanged.

The primary target is any supported critical monetary error; secondary targets are line-item monetary errors, row alignment errors, and bounded weighted critical loss. Only `PRE_INFERENCE`, `CHEAP_PREFLIGHT`, and `POST_EXTRACTION` features are eligible. All source-document variants are grouped. Candidate selection uses five-fold grouped CV, AURC, fixed grids, 2,000 document bootstrap replicates, and the frozen review/certification budgets in [`risk_protocol.json`](../../configs/v3_2/risk_protocol.json).

Promotion is shadow-only and requires every frozen gate. No autonomous-action promotion is permitted.
