# Robustness and shift

No GPU inference was rerun: v3.1's frozen 10-document development corruption cohort was reused. To test feature response without inventing extractor outputs, corrupted image descriptors were varied while each document's frozen clean post-extraction features were held fixed. This is a limited risk-sensitivity diagnostic, not a fresh end-to-end robustness benchmark.

High occlusion is the extraction bottleneck (mean leaf F1 0.5752); R4 risk rises only +0.0437 from clean and its proxy-error AUROC is 0.4167, with 2 critical proxy errors at or below median risk. Risk response is inconsistent across corruptions, reinforcing no-promotion.

Fresh external LIR evidence remains absent. [DocILE's official toolkit](https://github.com/rossumai/docile) requires an access token and is `HUMAN_ACTION_REQUIRED_OPTIONAL`. WildReceipt was assessed only as KIE/domain shift and was not forced into incompatible CORD line-item metrics.
