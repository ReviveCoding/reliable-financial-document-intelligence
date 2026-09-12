# V2 Security and Operations Report

Six locked malicious-document/control pairs were evaluated with Qwen3-VL. The independent OCR detector activated for 83.3%; structured extraction integrity was 83.3%; output deviation, schema violation, and instruction-compliance-signal rates were each 0.0%. One extraction error occurred despite no attack/control deviation. This distinction prevents architectural containment from being misreported as perfect model robustness.

Unauthorized actions were zero because the extraction process exposed no payment, email, database mutation, or shell tools and held no such credentials. This is an architectural property, not proof of zero model susceptibility.

One physical RTX 4090 Laptop GPU was used. Deep workloads ran through CUDA outside the WSL2 bubblewrap boundary after the sandbox hid `/dev/dxg`; no CPU deep-model fallback and no multi-GPU execution occurred. Heavy jobs ran sequentially. V1 idempotency/fault tests remain valid shared infrastructure evidence; Docker execution remains unavailable in this WSL distribution.
