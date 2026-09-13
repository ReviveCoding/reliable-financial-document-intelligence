# V3 Desktop Study Update

Access date: 2026-09-11.

- DocILE: `docile-benchmark` 0.3.5, Python >=3.11,<3.15. Official KILE/LIR evaluation uses localized fields, micro AP/F1/precision/recall, line-item grouping for LIR, and built-in 0-shot/1–3-shot/4+-shot layout breakdowns. Data needs an official token.
- REFinD: about 29K instances, 22 relations, 8 entity-pair types from SEC 10-X filings; CC BY-NC 4.0 and official CodaLab terms restrict use/redistribution.
- PaddleOCR-VL 1.6: current official serving documentation supports `paddleocr genai_server --model_name PaddleOCR-VL-1.6-0.9B` with vLLM, SGLang, or FastDeploy. Official GPU images are large (roughly 13 GB for online vLLM and 43 GB for FastDeploy), so bounded pilots and isolated environments are required.
- MLflow: current tracking-server documentation supports PostgreSQL via `--backend-store-uri` and S3-compatible MinIO via `--artifacts-destination` / endpoint configuration. PostgreSQL stores run metadata and MinIO stores artifacts.
- Docker Compose: health-dependent startup uses `depends_on.condition: service_healthy` and explicit service health checks.

Official sources: [DocILE](https://github.com/rossumai/docile), [REFinD](https://refind-re.github.io/), [PaddleOCR-VL serving](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/PaddleOCR-VL.html), [MLflow tracking server](https://mlflow.org/docs/latest/self-hosting/architecture/tracking-server/), [MLflow artifact stores](https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/), [Docker startup order](https://docs.docker.com/compose/how-tos/startup-order/).
