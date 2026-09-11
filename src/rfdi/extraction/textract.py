"""Budget-gated Textract adapter and response mapper; no calls occur on import."""
from __future__ import annotations

import os
from decimal import Decimal
from typing import Any


def authorization(max_pages: int, modeled_usd_per_page: Decimal = Decimal("0.01")) -> dict[str, Any]:
    budget = Decimal(os.environ.get("RFDI_AWS_BUDGET_USD", "0"))
    estimate = modeled_usd_per_page * max_pages
    has_credentials = bool(os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_PROFILE"))
    return {"authorized": has_credentials and budget > 0 and estimate <= budget,
            "estimated_max_usd": str(estimate), "declared_budget_usd": str(budget),
            "has_credentials": has_credentials, "estimate_type": "MODELED_OFFICIAL_PRICING"}


def map_analyze_expense(response: dict[str, Any]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    aliases = {"VENDOR_NAME": "vendor_name", "INVOICE_RECEIPT_ID": "invoice_number",
               "TOTAL": "total", "AMOUNT_DUE": "amount_due", "TAX": "tax"}
    for document in response.get("ExpenseDocuments", []):
        for field in document.get("SummaryFields", []):
            key = field.get("Type", {}).get("Text")
            value = field.get("ValueDetection", {}).get("Text")
            if key in aliases and isinstance(value, str): mapped[aliases[key]] = value
    return mapped
