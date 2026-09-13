# Executive findings

- **Best conditions:** the strongest adequately supported cohorts are text_density_tokens_per_megapixel=low (F1 0.921), image_megapixels=high (F1 0.903), document_text_length=mid (F1 0.893).
- **Worst conditions:** text_density_tokens_per_megapixel=high (F1 0.749), document_text_length=high (F1 0.757), ocr_token_count=high (F1 0.773). FDR-significant and practically adverse cohorts are `document_text_length=high` (q=0.0485), `text_density_tokens_per_megapixel=high` (q=0.0242).
- **Failure predictors:** higher token/text density and complexity are the clearest predeclared retrospective signals; the separate image-only shallow tree is exploratory, with CV balanced accuracy 0.595.
- **Business risk:** repeated monetary item prices make critical-field risk much broader than receipt-total accuracy. Incorrect, missing and spurious values are the most frequent error modes.
- **Confidence:** genuine Donut confidence predicts correctness poorly in raw probability space. Isotonic calibration improves ECE, but calibration alone does not create better selective ranking.
- **Review:** no tested policy reaches low critical residual risk. The least-cost frozen illustrative point uses 50.0% review; this is evidence for conservative human review, not a deployment threshold.
- **Robustness:** the largest development degradation is occlusion high for Donut CORD v2 (-0.220).
- **Latency:** latency should be monitored by document complexity; this study reports cohort means and corruption interactions without claiming a causal production effect.
- **Mix shift:** no ranking reversal occurs under the shared complexity distribution; the paired total-exact conclusion is not driven by composition here.
- **Monitor next:** blur, megapixels/resolution, complexity, genuine confidence/risk, route rates and latency. Fix field alignment/normalization and build routing signals that rank critical errors better.
