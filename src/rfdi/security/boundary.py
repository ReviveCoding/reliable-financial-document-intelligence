"""Detection is defense-in-depth; capability isolation is the primary control."""
from __future__ import annotations

import re

PATTERNS = (
    r"ignore\s+(all\s+)?previous",
    r"system\s*message",
    r"execute\s+(this\s+)?command",
    r"send\s+(a\s+)?payment",
    r"reveal\s+(the\s+)?secret",
)


def security_signals(text: str) -> tuple[str, ...]:
    return tuple(f"SECURITY_INJECTION:{i}" for i, pattern in enumerate(PATTERNS)
                 if re.search(pattern, text, re.IGNORECASE))


def sanitize_document_text(text: str) -> str:
    # Delimit untrusted content and strip ASCII controls; it is never interpolated into instructions.
    clean = "".join(char for char in text if char in "\n\t" or ord(char) >= 32)
    return f"<UNTRUSTED_DOCUMENT_DATA>\n{clean}\n</UNTRUSTED_DOCUMENT_DATA>"
