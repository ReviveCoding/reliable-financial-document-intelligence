# Data Integrity and Leakage Audit

Measured E0 over 240 development records: 240 `VALID`, zero duplicate IDs/content hashes, empty annotations, and impossible monetary values. Locked final was excluded from development content reads. The separately invoked leakage audit verified zero SHA-256, vendor-ID, and template-ID overlap for train↔dev, train↔final, and dev↔final.

Visual pHash, OCR MinHash/embedding similarity, malformed bbox, page completeness, and label-quality audits are not meaningful for text-only generated records and remain blocked/not measured until image/public datasets exist. Evidence: `artifacts/results/e0.json`, `artifacts/results/e0_leakage.json`.
