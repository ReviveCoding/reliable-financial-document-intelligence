# V2 Reliability Report

On the development calibration partition, Paddle total ECE fell from 0.3146 to 0.0295 with isotonic calibration; Brier fell from 0.3438 to 0.2449. These are development-only estimates from a small split, not a universal calibration claim.

The cost-sensitive cascade made no accuracy gain and added latency. At a 20% review budget, Donut low-confidence and R-FDI risk each captured 10/30 critical document errors; random review averaged about 20% capture. The visual Mahalanobis detector was negative (AUROC 0.5013) and was excluded before freeze. Reconciliation detected 100/100 injected business corruptions with zero valid-case false positives and caught 1/3 high-confidence OCR total errors.

Final Donut mean document leaf F1 was 0.8453, bootstrap 95% CI [0.8077, 0.8800]. Its paired total exact advantage over PP-OCRv5 rules was 0.5263, 95% CI [0.4316, 0.6211] across 95 documents.
