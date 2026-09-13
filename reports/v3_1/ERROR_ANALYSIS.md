# Error analysis

The leading deterministic test error categories are incorrect value (100 instances), missing field (86), and spurious field (76). Numeric-normalization errors remain separate from substantive value errors. Ambiguous errors may remain `UNCLASSIFIED`; no category is forced.

The weakest field-family F1 is `free_text` at 0.6111; item-name and item-price errors dominate more business-relevant repeated structures. Representative evidence publishes document IDs and normalized values, not raw document images.

The image-only exploratory depth-3 tree achieved mean five-fold balanced accuracy 0.5945. Its readable quality/layout rules are retained in the evidence artifact, but every rule is labeled `EXPLORATORY_DISCOVERED_SLICE` and is not a confirmatory finding. Annotated token/box counts and target-derived structure were excluded from discovery.
