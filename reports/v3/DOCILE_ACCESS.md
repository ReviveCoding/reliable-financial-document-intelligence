# DocILE Access Audit

Access checked 2026-09-11. `DOCILE_TOKEN` is absent; no token value was printed. The official process requires obtaining a secret token at <https://docile.rossum.ai/> and using the official repository downloader, initially only for `annotated-trainval`. Therefore `V3-DOCILE` is `HUMAN_ACTION_REQUIRED`; no authentication was bypassed.

Current `docile-benchmark` is 0.3.5 on PyPI and requires Python >=3.11,<3.15, so it must not be installed into the Python 3.10 V2 environments. When authorized, create `$RFDI_RUNTIME_ROOT/venvs/rfdi-v3-docile` with Python 3.11+ and run the official `download_dataset.sh TOKEN annotated-trainval "$RFDI_DATA_ROOT/docile" --unzip` without logging the token. The official evaluator is `docile_evaluate`, with KILE/LIR and `--evaluate-x-shot-subsets "0,1-3,4+"` plus field, synthetic, and text breakdown flags.

Sources: official [DocILE repository](https://github.com/rossumai/docile), [PyPI package](https://pypi.org/project/docile-benchmark/).
