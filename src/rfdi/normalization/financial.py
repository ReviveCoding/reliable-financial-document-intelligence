from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN


def normalize_money(raw: str) -> Decimal:
    text = raw.strip().replace(" ", "")
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[^0-9,.'+-]", "", text).replace("'", "")
    if not text:
        raise ValueError("money value is empty or ambiguous")
    if "," in text and "." in text:
        decimal_sep = "," if text.rfind(",") > text.rfind(".") else "."
        thousands_sep = "." if decimal_sep == "," else ","
        text = text.replace(thousands_sep, "").replace(decimal_sep, ".")
    elif text.count(",") == 1 and len(text.rsplit(",", 1)[1]) == 2:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid money value: {raw!r}") from exc
    return (-value if negative else value).quantize(Decimal("0.01"), ROUND_HALF_EVEN)


def normalize_currency(raw: str) -> str:
    mapping = {"$": "USD", "US$": "USD", "USD": "USD", "€": "EUR", "EUR": "EUR",
               "£": "GBP", "GBP": "GBP", "¥": "JPY", "JPY": "JPY"}
    key = raw.strip().upper() if raw.strip().isalpha() else raw.strip()
    if key not in mapping:
        raise ValueError(f"unknown or ambiguous currency: {raw!r}")
    return mapping[key]


def normalize_date(raw: str) -> date:
    formats = ("%Y-%m-%d", "%Y/%m/%d", "%d %b %Y", "%d %B %Y")
    for fmt in formats:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"ambiguous or invalid date: {raw!r}")
