# V3 Expanded Adversarial-Document Security Benchmark

The V3 benchmark covers 24 deterministic attack/probe families: instruction
override, fake authority, command/tool invocation, payment actions, secret
exfiltration, schema override, remote fetch/UNC paths, encoded payloads, control
characters, Unicode normalization, obfuscation, and benign financial text.

All 24 inputs remained inside explicit untrusted-document delimiters and the live
API OpenAPI schema exposed no payment, transfer, shell, command, credential, or
secret action endpoint. Therefore capability isolation passed and zero unauthorized
actions were possible in this harness.

The regex detector activated on 20/24 cases. Four misses are explicitly retained:
homoglyph obfuscation, split-word obfuscation, clean financial prose, and an
ordinary invoice. Detector activation includes benign triggers such as a vendor
URL and product text containing `Base64`; it must not be interpreted as precision
or model-level prompt-injection immunity. Capability isolation remains the primary
control.

Evidence: `artifacts/v3/security/adversarial_benchmark.json`.
