from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True)
class ReconciliationResult:
    valid: bool
    warnings: tuple[str, ...]


def reconcile_financials(values: Mapping[str, Decimal | date | str], tolerance: Decimal = Decimal("0.01")) -> ReconciliationResult:
    warnings: list[str] = []
    required = ("subtotal", "tax", "discount", "shipping", "total")
    if all(key in values for key in required):
        expected = (Decimal(values["subtotal"]) + Decimal(values["tax"]) +
                    Decimal(values["shipping"]) - Decimal(values["discount"]))
        if abs(expected - Decimal(values["total"])) > tolerance:
            warnings.append("ARITHMETIC_CONFLICT")
    if isinstance(values.get("invoice_date"), date) and isinstance(values.get("due_date"), date):
        if values["invoice_date"] > values["due_date"]:
            warnings.append("INVALID_DATE_ORDER")
    return ReconciliationResult(not warnings, tuple(warnings))


def reconcile_bundle(po: Mapping[str, str], invoice: Mapping[str, str], payment: Mapping[str, str]) -> ReconciliationResult:
    warnings: list[str] = []
    for key, label in (("po_number", "PO_MISMATCH"), ("vendor_id", "VENDOR_MISMATCH"),
                       ("currency", "CURRENCY_MISMATCH"), ("beneficiary", "BENEFICIARY_CHANGE")):
        observed = {record.get(key) for record in (po, invoice, payment) if record.get(key) is not None}
        if len(observed) > 1:
            warnings.append(label)
    if invoice.get("total") != payment.get("total"):
        warnings.append("AMOUNT_MISMATCH")
    return ReconciliationResult(not warnings, tuple(warnings))
