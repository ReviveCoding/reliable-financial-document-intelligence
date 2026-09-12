# V2 Robustness and Transfer Report

Locked rendered-document field recall was 0.9069. Low resolution was the weakest corruption at 0.7372; clean documents reached 0.9467. Template- and vendor-disjoint IDs were enforced, zero exact image overlap was found, and split-specific geometry was generated. Near-image hash matches remain a disclosed limitation.

Synthetic document-classifier macro-F1 rose from 0.3575 with 25 training examples to 0.9700 with 150. Synthetic-to-CORD transfer accuracy was only 0.11, a negative result showing that rendered data did not substitute for real receipts. Visual OOD detection was near chance and did not improve review allocation. No compatible common cross-dataset KIE F1 is reported.
