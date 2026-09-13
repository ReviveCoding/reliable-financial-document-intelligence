# Data and slice definition

The canonical tables contain 340 document/model rows and 2,645 Donut field rows. Locked inference was not rerun. Predictions, latency, model confidence, truth and manifests come from frozen committed evidence; reproducible image descriptors come from authorized local CORD images. Provenance hashes are in `artifacts/v3_1/data/provenance.json`.

All cut points were derived from the 100-document CORD validation split and committed in `configs/v3_1/analysis_protocol.json` before locked slice results were inspected. Headline support is N>=20; N=10–19 is exploratory; lower support is only marked insufficient. Paired comparisons retain document IDs. V1/V2/V3 outcomes are immutable.

Critical monetary fields include total, subtotal, tax, discount and item price. Medium-impact and descriptive mappings are explicit in the protocol. Missing features are blank, never invented or imputed.
