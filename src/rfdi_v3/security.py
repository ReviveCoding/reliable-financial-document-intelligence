"""V3 document-boundary controls; detection complements capability isolation."""
from __future__ import annotations

import re
import unicodedata


PATTERNS = {
    "instruction_override": r"ignore\s+(?:all\s+)?(?:previous|prior|extraction)",
    "fake_authority": r"(?:system|developer|administrator)\s*(?:message|instruction|override)",
    "tool_execution": r"(?:execute|run|invoke)\s+(?:this\s+)?(?:command|tool|shell|powershell)",
    "payment_action": r"(?:send|issue|approve|release)\s+(?:a\s+)?(?:payment|transfer|wire)",
    "secret_exfiltration": r"(?:reveal|print|upload|exfiltrate)\s+(?:the\s+)?(?:secret|token|credential|key)",
    "schema_override": r"(?:output|return)\s+(?:only\s+)?(?:json|\{)",
    "remote_fetch": r"(?:curl|wget|https?://|\\\\[a-z0-9_.-]+\\)",
    "encoded_payload": r"(?:base64|decode\s+this|data:text/)",
}


def normalize_for_detection(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = "".join(ch for ch in normalized if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    return re.sub(r"\s+", " ", normalized)


def security_signals(text: str) -> tuple[str, ...]:
    normalized = normalize_for_detection(text)
    return tuple(name for name, pattern in PATTERNS.items() if re.search(pattern, normalized, re.I))


def sanitize_document_text(text: str) -> str:
    clean = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    return f"<UNTRUSTED_DOCUMENT_DATA>\n{clean}\n</UNTRUSTED_DOCUMENT_DATA>"
