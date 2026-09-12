# V2 Ablation and Statistics Report

The six mandatory ablations were evaluated component-wise on development data: removing routing reduced latency without reducing selected-route accuracy; removing OOD improved 20% review capture; removing calibration worsened ECE/Brier; removing financial validation lost the independent catch of one of three high-confidence total errors; removing learned synthetic examples reduced document macro-F1 from about 0.900 to the rule baseline 0.648; synthetic augmentation evidence applies to classification and not LayoutLMv3/Donut fine-tuning. Incompatible task metrics were not collapsed into a single score.

Final confidence intervals use deterministic paired/document-level percentile bootstrap with 10,000 draws and seed 20260911. Only one LayoutLMv3 training seed and small VLM/security samples were feasible; p-values and broad significance claims are therefore omitted.
