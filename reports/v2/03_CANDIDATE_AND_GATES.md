# V2 Candidate Selection and Frozen Gates

## Decision basis

Selection used only CORD validation, a deterministic holdout within FUNSD training, and R-FDI Synthetic V2 train/development. CORD test, FUNSD test, and synthetic final record content were unavailable to modeling code. The leakage audit reduced locked labels to aggregate overlap counts and found no exact image overlap, while exposing seven exact normalized CORD train–test text overlaps that limit independence claims.

The selected offline research system is `V2_FIXED_FAMILY_GATED_WITH_RFDI_CONTROLS`:

- pinned Donut for CORD-compatible receipts;
- the frozen LayoutLMv3 checkpoint for FUNSD-style forms;
- TF-IDF classification over pinned PP-OCRv5 text for document-type evidence;
- strict schemas, deterministic reconciliation, confidence-first review, and no action capabilities.

Adaptive routing is deliberately excluded. On the held-out routing partition it selected Donut for every item, retained 1.0 total accuracy, and increased mean latency from 2.81 to 4.58 seconds. Visual OOD is also excluded from the selected review policy: Mahalanobis OOD-first captured 13/30 critical-error documents at 20% review, versus 15/30 for OCR confidence. These negative results are preserved.

## Development evidence

Donut reached leaf F1 0.88, total exact match 1.0, and full-document exact match 0.44 on 100 CORD validation receipts. LayoutLMv3 reached macro-F1 0.6727 on a 29-document FUNSD training holdout. PP-OCRv5 reached 0.9192 all-field recall and 0.94 total exact match on 100 truly geometry/template/vendor-disjoint rendered documents. Qwen3-VL matched 53/53 compatible fields on 20 CORD receipts but averaged 25.43 seconds per inference call; PaddleOCR-VL whole-image parsing reached 0.8919 value-presence recall but had P95 29.95 seconds.

## Frozen release gates

The exact numeric gates are stored in `configs/v2/frozen.json`. They require CORD leaf F1 at least 0.83, total exact match at least 0.95, FUNSD macro-F1 at least 0.57, synthetic all-field recall at least 0.82, synthetic total exact match at least 0.75, Donut P95 at most 8 seconds, schema failures at most 1%, Qwen attacked-versus-clean output deviation at most 10%, zero unauthorized actions, and at least 0.20 absolute total-exact gain over PP-OCRv5.

Every gate must pass for `PROMOTE`; otherwise the result is `NO_PROMOTION`. Promotion means offline research-candidate promotion only.
