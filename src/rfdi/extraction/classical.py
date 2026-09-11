from __future__ import annotations

import re

FIELD_PATTERNS = {
    "invoice_number": r"^(?:invoice\s+(?:no|number))[\s:#-]*([A-Z0-9-]+)\s*$",
    "po_number": r"^(?:purchase order|po)[\s:#-]*([A-Z0-9-]+)\s*$",
    "total": r"^(?:amount due|grand total|total)[\s:]*([$€£]?[0-9][0-9,.' ]*(?:\.\d{2})?)\s*$",
    "currency": r"\b(USD|EUR|GBP|JPY)\b|([$€£¥])",
    "invoice_date": r"invoice date[\s:]*(\d{4}[-/]\d{2}[-/]\d{2})",
    "due_date": r"due date[\s:]*(\d{4}[-/]\d{2}[-/]\d{2})",
}


def extract_fields(text: str) -> dict[str, tuple[str, float]]:
    found: dict[str, tuple[str, float]] = {}
    for field, pattern in FIELD_PATTERNS.items():
        matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
        if len(matches) == 1:
            groups = tuple(group for group in matches[0].groups() if group)
            found[field] = (groups[0], 0.91 if field in {"invoice_number", "po_number"} else 0.86)
        elif len(matches) > 1:
            # Ambiguity is explicit and lowers confidence; never silently guess.
            groups = tuple(group for group in matches[-1].groups() if group)
            found[field] = (groups[0], 0.42)
    return found
