# Slicing analysis

Overall Donut locked-test document-average leaf F1 is 0.8453. The strongest and weakest adequately supported predeclared cohorts are reported together:

- `text_density_tokens_per_megapixel=high`: N=37, F1=0.7485, delta=-0.0968, 95% CI [0.6709, 0.8188], q=0.0242.
- `document_text_length=high`: N=33, F1=0.7566, delta=-0.0887, 95% CI [0.6726, 0.8265], q=0.0485.
- `ocr_token_count=high`: N=31, F1=0.7733, delta=-0.0720, 95% CI [0.6961, 0.8428], q=0.2154.
- `text_density_tokens_per_megapixel=low`: N=29, F1=0.9208, delta=+0.0756, 95% CI [0.8812, 0.9573], q=0.0242.
- `image_megapixels=high`: N=23, F1=0.9029, delta=+0.0576, 95% CI [0.8553, 0.9448], q=0.2154.
- `document_text_length=mid`: N=39, F1=0.8932, delta=+0.0479, 95% CI [0.8488, 0.9335], q=0.2154.

After Benjamini–Hochberg correction, FDR-significant and practically adverse cohorts are `document_text_length=high` (q=0.0485), `text_density_tokens_per_megapixel=high` (q=0.0242). Practical flags follow the frozen absolute 0.05 F1 threshold.

The paired eligible total-exact comparison is Donut 0.9895 versus PP-OCRv5+rules 0.4632. Standardization leaves the ranking unchanged; `ranking_reversal=false`. Because both models use the same 95 eligible IDs, the overall conclusion is not a slice-composition artifact in this analysis.
