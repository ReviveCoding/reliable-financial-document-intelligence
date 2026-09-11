# Data Card

## Scope

Public benchmark manifests and project-generated synthetic financial records only. No private banking or personal data is used.

## Generated data

Version 1.0.0 contains 360 text records: 120 train, 120 development, and 120 locked final. Vendor and template identifiers are split-scoped and disjoint. Types: invoice 54; each of purchase order, receipt, remittance, payment instruction, payment record, and statement 51. Currencies are balanced at 120 USD/EUR/GBP. Total amounts range 85.73–5357.80, median 2955.87.

There are 30 arithmetic mismatches, 21 invalid date orders, and 21 security-attack records across all splits. Account/routing identifiers are visibly prefixed `SYN-` and are not usable credentials.

## Limitations

Records are regular text templates, not rendered page images. Visual corruptions, OCR boxes, tables, multipage layouts, realistic vendor diversity, and annotation uncertainty are absent. Consequently the perfect B0 result is expected and must not be generalized. Public datasets were not acquired during this run.
