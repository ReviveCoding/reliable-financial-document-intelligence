# R-FDI v3.1 final analysis report

V3.1 adds an evidence-governed analysis layer without changing model weights or historical outcomes. The canonical table, predeclared slicing, field/error taxonomy, 2,000-replicate uncertainty, paired analysis, calibration, selective risk, controlled GPU robustness, exploratory discovery, simulated drift, policy sensitivity and generated figures are traceable through `V3_1_EVIDENCE_MANIFEST.jsonl`.

## Main findings

- `text_density_tokens_per_megapixel=high`: N=37, F1=0.7485, delta=-0.0968, 95% CI [0.6709, 0.8188], q=0.0242.
- `document_text_length=high`: N=33, F1=0.7566, delta=-0.0887, 95% CI [0.6726, 0.8265], q=0.0485.
- `ocr_token_count=high`: N=31, F1=0.7733, delta=-0.0720, 95% CI [0.6961, 0.8428], q=0.2154.
- `text_density_tokens_per_megapixel=low`: N=29, F1=0.9208, delta=+0.0756, 95% CI [0.8812, 0.9573], q=0.0242.
- `image_megapixels=high`: N=23, F1=0.9029, delta=+0.0576, 95% CI [0.8553, 0.9448], q=0.2154.
- `document_text_length=mid`: N=39, F1=0.8932, delta=+0.0479, 95% CI [0.8488, 0.9335], q=0.2154.

Raw confidence is severely overconfident; development-fit isotonic calibration improves ECE from 0.6330 to 0.1242, but selective ordering does not beat raw confidence. At 50% review, the best raw-confidence evidence still has 18.0% critical false-accept rate among accepted documents. The principal robustness bottleneck is occlusion (high) for Donut CORD v2. The paired model ranking does not reverse after slice standardization.

## Scope

Results use public research datasets, frozen predictions and a development-only corruption cohort. They are not a live production deployment, regulatory certification, or multi-GPU study. Paddle content presence is not structured CORD F1. SROIE and DocILE remain optional human-access blockers.
