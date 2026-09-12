# V2 Modeling Report

All values below are measured project results; task-specific metrics are not pooled across incompatible schemas.

| Route | Dataset/split | Result | Mean latency | Peak VRAM |
|---|---|---:|---:|---:|
| PP-OCRv5 + total rule | CORD test | total exact 0.4632; CER 0.1983; WER 0.3716 | 1.002s | 6.15 GiB |
| Donut | CORD test | leaf F1 0.8372; total exact 0.9895 | 1.489s | 0.79 GiB |
| LayoutLMv3 | FUNSD test | macro-F1 0.7009 | 0.128s/batch | 0.77 GiB |
| PaddleOCR-VL-1.6 | CORD dev-20 | content-presence recall 0.8919 | 20.404s | 5.88 GiB |
| Qwen3-VL-4B | CORD dev-20 | 53/53 compatible fields exact | 25.427s/call | 10.82 GiB |

Donut was selected for receipts, LayoutLMv3 for forms, and TF-IDF over PP-OCRv5 for document type. The adaptive cascade was rejected because it chose Donut for every development document while increasing latency. Qwen and PaddleOCR-VL were not default routes because of measured latency. LayoutLMv3 used one training seed due the bounded one-GPU study; this limits training-variance claims.
