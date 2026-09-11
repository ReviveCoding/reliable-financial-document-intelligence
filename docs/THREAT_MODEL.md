# Threat Model

## Assets and trust

Document bytes, OCR, and embedded text are untrusted. Protected assets include credentials, business databases, payments, mail, host commands, model/evidence history, and review decisions.

## Attacks

The generator labels visible, tiny, footer, table-cell, fake-system, and image-instruction attacks. Other threats include parser bombs, malformed PDF, resource exhaustion, duplicate replay, model hallucination, ambiguous totals, poisoned feedback, and credential leakage.

## Controls

- Extraction workers possess no action-capable tools or payment/email privileges.
- Untrusted text is delimited, never interpolated into system policy.
- Strict schema, normalization, allowlisted fields, size/time limits, and deterministic validation mediate output.
- Idempotent content hashes prevent duplicate finalized records.
- Review corrections enter a versioned candidate set and do not automatically retrain.
- Secrets are neither logged nor committed; cloud calls are budget-gated.

## Evidence and residual risk

E16 tested 14 development and 7 final generated attacks: 0 unauthorized-action attempts and 0 attack successes under this architecture. This verifies the implemented boundary for fixtures, not universal prompt-injection resistance. Image-based attacks were labeled in text metadata but no VLM was runnable; their semantic resistance remains blocked by accelerator access.
