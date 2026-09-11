# Desktop Study

Accessed 2026-09-11. Versions are the live official-page state observed on that date; dynamic `main` pages require revalidation on resume.

## Datasets

| Item | Official source / revision | License/access | Relevance, burden, limitation |
|---|---|---|---|
| DocILE | https://github.com/rossumai/docile (`main`, ICDAR 2023) | Official token required; terms at https://docile.rossum.ai/ | Primary KILE/LIR and 0/few/many-shot layouts; substantial PDF/OCR/model compute; blocked without token. |
| CORD v2 | https://huggingface.co/datasets/naver-clova-ix/cord-v2 (`main`) | Metadata states CC BY 4.0; verify assets | 1,000 receipts (800/100/100) and hierarchical parsing; ~4.6 GB reported total size; receipt-only domain. |
| SROIE | https://arxiv.org/abs/2103.10213 (ICDAR 2019) | Competition terms at https://rrc.cvc.uab.es/?ch=13 | 1,000 receipt images for OCR/KIE/robustness; older, geographically narrow benchmark. |
| FUNSD | https://github.com/crcresearch/FUNSD and https://arxiv.org/abs/1905.13538 | Verify archive terms | Noisy-form OOD/domain shift; only 199 forms and not primarily financial. |
| REFinD | https://refind-re.github.io/ and https://arxiv.org/abs/2305.18322 (2023) | Official access/terms only | Separate financial relation track over SEC 10-X text; not image KIE and access absent. |

## Models and OCR

| Family | Official source / verified status | Relevance, expected burden, limitations |
|---|---|---|
| OCR + rules | Tesseract project / local package check | Mandatory interpretable B0; light CPU; brittle to OCR/layout variation. Tesseract binary was not present in this environment. |
| RoBERTa/DeBERTa | https://huggingface.co/docs/transformers/ | Text baselines need OCR and CUDA fine-tuning; lose layout unless engineered. |
| LayoutLMv3 | https://arxiv.org/abs/2204.08387 and https://github.com/microsoft/unilm | Multimodal layout baseline; CUDA training/inference and OCR boxes required. |
| Donut | https://github.com/clovaai/donut (`master`, MIT) | Official OCR-free ECCV 2022 implementation; GPU-heavy and generated output lacks native bbox provenance. |
| PaddleOCR-VL-1.6 | https://www.paddleocr.ai/main/en/version3.x/algorithm/PaddleOCR-VL/PaddleOCR-VL-1.6.html | Official current stable page describes a 0.9B model and 96.33% external OmniDocBench v1.6 result. This is literature/vendor evidence, not R-FDI measurement. CUDA/Paddle environment required. |
| Qwen3-VL-4B-Instruct | https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct | Official model card exists; inference-only pilot is appropriate. 4B VLM requires CUDA, revision pinning, and injection-safe prompting. |
| Textract AnalyzeExpense | https://docs.aws.amazon.com/textract/latest/APIReference/API_AnalyzeExpense.html | Returns summary and line-item fields. Paid empirical calls were unauthorized. Official pricing example at https://aws.amazon.com/textract/pricing/ models $0.01/page for the first 1M Analyze Expense pages in us-west-2; region/tier must be rechecked. |

## Infrastructure

| Component | Official page observed | Decision / limitation |
|---|---|---|
| PyTorch | https://pytorch.org/get-started/locally/ | Official site displayed stable 2.7.0 and Python ≥3.10, while release pages appeared newer/inconsistent; pin only after CUDA compatibility test. Not installed. |
| Transformers | https://huggingface.co/docs/transformers/ | Pin per model card after GPU pilot; Qwen card may require a newer source/release. |
| PaddleOCR/PaddlePaddle | https://www.paddleocr.ai/main/en/ | Separate environment to avoid PyTorch conflicts. |
| MLflow | https://mlflow.org/releases | Latest page advertised 3.15.0; Compose pins it, but stack not run. |
| FastAPI | https://fastapi.tiangolo.com/release-notes/ | Official notes showed 0.141.1; optional adapter not installed locally. |
| PostgreSQL | https://www.postgresql.org/docs/ | PostgreSQL 18 current; official page reported 18.6 on 2026-08-13. |
| Redis | https://redis.io/docs/latest/develop/whats-new/ | Official docs reported Redis 8.10 in Q3 2026; Compose uses major tag 8 and should pin digest for deployment. |
| MinIO / Docker Compose | https://min.io/docs/ and https://docs.docker.com/compose/ | Object/runtime target only; Docker unavailable in active WSL. |
| AWS S3 / Step Functions / CloudWatch | https://docs.aws.amazon.com/ | Production roadmap components; no calls made and no cost incurred. |

## Conclusion

PaddleOCR-VL-1.6 and Qwen3-VL-4B-Instruct remain the verified candidates requested by the specification. Environment and access blockers restricted empirical work to CPU-safe synthetic/deterministic experiments; external benchmark numbers above are never mixed with measured R-FDI results.
