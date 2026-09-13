# Robustness and shift replay

No GPU inference was rerun. Frozen v3.1 corruptions were reused under `RISK_SENSITIVITY_PROXY_NOT_END_TO_END_INFERENCE`: corrupted image descriptors vary while clean post-extraction outputs remain fixed. High occlusion has mean leaf F1 0.5752, mean risk increase +0.0437, proxy AUROC 0.4167, and 2 false-negative proxy errors at/below median risk. Response remains weak and inconsistent.

Authorized DocILE LIR evidence and a larger fresh grouped certification sample remain missing. WildReceipt was not forced into incompatible line-item metrics.
