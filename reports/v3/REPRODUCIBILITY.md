# V3 Reproducibility

Run commands from `/mnt/c/Users/bjw-0/Downloads/R-FDI` on branch
`financial-domain-production-v3`. Honor the configured `RFDI_*` runtime, data,
checkpoint, GPU, and CPU environment variables. The Docker control plane used in
this run was the Windows CLI invoked through `powershell.exe` with context
`desktop-linux`.

Core deterministic validation:

```bash
PYTHONPATH=src /usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 scripts/verify_evidence.py
/usr/bin/python3 scripts/v2_verify_evidence.py
/usr/bin/python3 scripts/v3/verify_evidence.py
```

Stack startup and application probe:

```bash
powershell.exe -NoProfile -Command "docker --context desktop-linux compose -p rfdi-v3 -f configs/v3/docker-compose.yml up -d --build"
PYTHONPATH=src /usr/bin/python3 scripts/v3/stack_probe.py --output artifacts/v3/runtime/docker_api_reviewer.json
```

The PaddleOCR comparison requires the official GPU image identified in
`artifacts/v3/serving/docker_vllm_validation.json`, the configuration in
`configs/v3/paddleocr_vllm.yaml`, PaddleOCR 3.7.0 with PaddleX 3.7.2 OCR and GenAI
client extras, and the authorized local CORD development data. The exact evaluator
is `scripts/v3/paddleocr_vllm_eval.py`. Do not run it on CPU after a CUDA failure.

Regenerate the V3 summary, workflow state, registry, and manifest only after all
referenced evidence and reports are final:

```bash
/usr/bin/python3 scripts/v3/package_v3.py
/usr/bin/python3 scripts/v3/verify_evidence.py
```
