# V2 Current Desktop Study

Access date: 2026-09-11. Sources are official documentation, repositories, model cards, and dataset pages. Version strings below are external facts unless a V2 artifact is named; they are not project measurements.

## Datasets

| Item | Official source and revision | License/access | V2 relevance, compute, and limitation |
|---|---|---|---|
| CORD v2 | `https://huggingface.co/datasets/naver-clova-ix/cord-v2`, `7f0115a4…` | CC BY 4.0 | Receipt OCR/KIE/LIR; 800/100/100 measured records. Korean/Indonesian receipt domain and repeated official-split text limit generalization. |
| FUNSD | `https://guillaumejaume.github.io/FUNSD/`, official 2019 archive | Public research archive; standalone archive license is not explicit, so citation/attribution is retained | Form-layout domain shift and token classification; 149/50 measured records. Not a financial headline benchmark. |
| SROIE | `https://rrc.cvc.uab.es/?ch=13` | Official download requires RRC registration | Relevant receipt OCR/KIE but `BLOCKED_ACCESS`; no third-party repackaging substituted. |
| DocILE | `https://github.com/rossumai/docile` and `https://docile.rossum.ai/` | Official token/terms required | Primary KILE/LIR/layout benchmark; remains `BLOCKED_ACCESS` without `DOCILE_TOKEN`. |
| REFinD | `https://refind-re.github.io/` | Official access not established | Separate financial-text relation track, not image KIE; remains `BLOCKED_ACCESS`. |
| R-FDI Synthetic V2 | Local deterministic renderer, seed 20260911 | Project-generated synthetic data | Exact fields/cell boxes, seven visual corruptions, attack labels, and split-specific geometry. Synthetic appearance remains less diverse than real documents. |

## Model families

| Family | Official source/revision used | License/usage | Expected burden and limitation |
|---|---|---|---|
| Classical PaddleOCR | `https://github.com/PaddlePaddle/PaddleOCR`; PaddleOCR 3.3.2 then 3.7.0 with explicit PP-OCRv5 models | Apache 2.0 | GPU OCR/rules baseline; confidence is engine-level and not field-calibrated by default. |
| LayoutLMv3 | `https://huggingface.co/microsoft/layoutlmv3-base`, `cfbbbff0…` | Model-card terms | Layout-aware token classification; fine-tuning measured near 4.09 GB allocated VRAM. Requires OCR words and boxes. |
| Donut CORD v2 | `https://huggingface.co/naver-clova-ix/donut-base-finetuned-cord-v2`, `8003d433…` | Model-card terms | OCR-free structured receipt extraction; task-specific schema limits transfer. |
| PaddleOCR-VL-1.6 | `https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6`, `c5630aba…`; official PaddleOCR docs | Apache 2.0 | Current 0.9B document parser. Page-layout native mode had impractical pilot latency; whole-image native mode completed. |
| Qwen3-VL-4B-Instruct | `https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct`, `ebb281ec…` | Apache 2.0 model card | General VLM; BF16 fits one 16 GB GPU but measured latency and 11.62 GB peak allocation make it costly for default routing. |
| AWS Textract AnalyzeExpense | `https://docs.aws.amazon.com/textract/latest/dg/analyzing-document-expense.html` and `https://aws.amazon.com/textract/pricing/` | Paid managed API; regional terms/prices | Adapter/modeled comparator only. No credentials plus positive `RFDI_AWS_BUDGET_USD`; empirical benchmark is `NOT_RUN_NO_CLOUD_AUTHORIZATION`. Current pricing page was rechecked but no paid call was made. |

RoBERTa/DeBERTa text encoders remain valid text-only baselines, but V2 prioritized the actual layout-aware, OCR-free, specialized document-VLM, and general-VLM runs required to resolve the V1 accelerator gap. No unsupported literature score is mixed with project metrics.

## Infrastructure

PyTorch 2.14.0+cu130 was installed from the official CUDA 13.0 wheel channel (`https://pytorch.org/get-started/locally/`); PaddlePaddle GPU 3.3.0 followed the official cu130 command at `https://www.paddlepaddle.org.cn/documentation/docs/en/install/pip/linux-pip_en.html`. The main Torch environment uses Transformers 4.57.1. PaddleOCR-VL required PaddleOCR 3.7.0; its checkpoint-declared Transformers route remained incompatible, while official native inference completed.

FastAPI, PostgreSQL, Redis, MinIO, MLflow, Docker Compose, S3, Step Functions, and CloudWatch remain production-architecture options rather than measured V2 services. V1 already contains the API/state-machine/reviewer fixtures. Docker remains unavailable in this WSL distribution, so V2 does not manufacture service-load or MLflow evidence.
