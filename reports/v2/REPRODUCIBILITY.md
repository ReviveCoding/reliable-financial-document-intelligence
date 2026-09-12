# V2 Reproducibility

Run from `/mnt/c/Users/bjw-0/Downloads/R-FDI`. Bulk inputs, environments, caches, and checkpoints are intentionally external under `/home/bjw-0/.local/share/rfdi-runtime`.

## Read-only verification

```bash
PYTHONPATH=src /usr/bin/python3 -m unittest discover -s tests -v
PYTHONPATH=src /usr/bin/python3 scripts/verify_evidence.py
/usr/bin/python3 scripts/v2_verify_evidence.py
MPLCONFIGDIR=/home/bjw-0/.local/share/rfdi-runtime/tmp/matplotlib /home/bjw-0/.local/share/rfdi-runtime/venvs/rfdi-v2-cu130/bin/python scripts/v2_package_evidence.py
```

## Development model commands

GPU commands require approved execution outside Codex bubblewrap on WSL2 because `/dev/dxg` is hidden inside workspace-write.

```bash
HF_HOME=/home/bjw-0/.local/share/rfdi-runtime/hf-cache /home/bjw-0/.local/share/rfdi-runtime/venvs/rfdi-v2-cu130/bin/python scripts/v2_donut.py --input /home/bjw-0/.local/share/rfdi-runtime/data/processed/cord_v2/7f0115a4b758a71d6473b8d085751692da2fef98/validation.jsonl --output artifacts/v2/results/donut_development.json --limit 100

HF_HOME=/home/bjw-0/.local/share/rfdi-runtime/hf-cache /home/bjw-0/.local/share/rfdi-runtime/venvs/rfdi-v2-cu130/bin/python scripts/v2_layoutlmv3.py --input /home/bjw-0/.local/share/rfdi-runtime/data/processed/funsd/official-2019/train.jsonl --output artifacts/v2/results/layoutlmv3_development.json

PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True PADDLE_PDX_CACHE_HOME=/home/bjw-0/.local/share/rfdi-runtime/paddle-cache /home/bjw-0/.local/share/rfdi-runtime/venvs/rfdi-v2-paddle-cu130/bin/python scripts/v2_paddleocr.py --input /home/bjw-0/.local/share/rfdi-runtime/data/processed/cord_v2/7f0115a4b758a71d6473b8d085751692da2fef98/validation.jsonl --output artifacts/v2/results/paddleocr_development.json --limit 100
```

Other routes use the corresponding `scripts/v2_qwen.py`, `v2_paddleocr_vl.py`, `v2_synthetic_ocr.py`, `v2_reliability.py`, `v2_reconciliation.py`, `v2_ood.py`, `v2_scaling_transfer.py`, and `v2_ablation.py` entry points. Their inputs, revisions, seeds, device, precision, batch size, output paths, and outcomes are preserved in `V2_EXPERIMENT_REGISTRY.csv` and each JSON artifact.

## Locked-final provenance

The exact locked inputs and release method are frozen in `configs/v2/frozen.json`; their hashes are rechecked by `scripts/v2_verify_evidence.py`. The completed final commands used `scripts/v2_donut.py`, `v2_paddleocr.py`, `v2_layoutlmv3_eval.py`, `v2_synthetic_ocr.py`, `v2_qwen.py`, `v2_security_analysis.py`, and `v2_finalize.py` against those inputs. Do not rerun them to tune, select, or replace the completed V2 result.
