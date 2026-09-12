# V2 Public Dataset Acquisition

Accessed 2026-09-11 through official public sources. Raw images and canonical JSONL are stored under the external runtime data root; only compact manifests/audits are durable in Git.

## CORD v2

Official Hugging Face dataset `naver-clova-ix/cord-v2`, pinned revision `7f0115a4b758a71d6473b8d085751692da2fef98`, tagged CC BY 4.0. All six parquet shards were downloaded and SHA-256 hashed. Counts are 800 train, 100 validation, and 100 test. Canonical conversion preserved the official PNG bytes and parsed the structured `ground_truth`. All 1,000 images passed Pillow verification; dimensions range 204–3,024 px wide and 336–4,224 px high.

## FUNSD

Official project archive `https://guillaumejaume.github.io/FUNSD/dataset.zip`, last-modified source date 2019-07-05. Archive size 16,838,830 bytes; SHA-256 `c31735649e4f441bcbb4fd0f379574f7520b42286e80b01d80b445649d54761f`. Counts are 149 train and 50 test. All 199 images passed verification. The canonical representation retains official word/entity boxes, labels, links, and per-annotation hashes.

## SROIE decision

The official Robust Reading Competition page remains available at `https://rrc.cvc.uab.es/?ch=13`; its download page explicitly requires registration before dataset access. The site also presented an untrusted certificate chain to the local command-line client on 2026-09-11. V2 did not create an external account, bypass the gate, or replace the official distribution with an unverified third-party repackaging. SROIE acquisition is therefore `BLOCKED_ACCESS`, independently of completed CORD and FUNSD work.

## Governance

CORD test and FUNSD test are not used for V2 model selection. A later V2 final protocol will be authorized only after model-family and non-degeneracy prerequisites pass. DocILE remains token-gated; REFinD remains separate. SROIE provenance review is still pending.
