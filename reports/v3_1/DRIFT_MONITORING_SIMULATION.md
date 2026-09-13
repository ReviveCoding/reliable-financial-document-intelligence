# Drift monitoring simulation

This is simulated stress-test drift, not observed bank production drift. A clean validation reference is compared with a transparently selected lower-blur/higher-complexity cohort. Alerts fired for `blur` (PSI 0.668, SMD -0.375), `image_megapixels` (PSI 0.215, SMD -0.027), `text_token_count` (PSI 3.017, SMD +0.613), `confidence` (PSI 0.294, SMD -0.156), `risk_score` (PSI 0.317, SMD +0.156), `latency_seconds` (PSI 0.647, SMD +0.535).

Production-style monitoring should track blur, contrast, skew, resolution, token and line-item counts, aspect ratio, genuine confidence/risk, review route and latency. Alerts should trigger investigation and cohort-level evaluation, not automatic claims of model failure.
