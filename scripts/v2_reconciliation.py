from __future__ import annotations

import argparse
import copy
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from v2_guard import assert_input_allowed


def amount(value: object) -> Decimal | None:
    try:
        return Decimal(re.sub(r"[^0-9.-]", "", str(value)))
    except (InvalidOperation, ValueError):
        return None


def arithmetic_valid(fields: dict[str, str], tolerance: Decimal = Decimal("0.02")) -> bool | None:
    values = {key: amount(fields.get(key)) for key in ("subtotal", "tax", "shipping", "discount", "total")}
    if any(value is None for value in values.values()):
        return None
    calculated = values["subtotal"] + values["tax"] + values["shipping"] - values["discount"]
    return abs(calculated - values["total"]) <= tolerance


def validate(observed: dict[str, str], expected: dict[str, str]) -> list[str]:
    warnings: list[str] = []
    if arithmetic_valid(observed) is False:
        warnings.append("ARITHMETIC_CONFLICT")
    try:
        if date.fromisoformat(observed["invoice_date"]) > date.fromisoformat(observed["due_date"]):
            warnings.append("INVALID_DATE_ORDER")
    except (KeyError, ValueError):
        warnings.append("INVALID_DATE")
    for field, warning in (
        ("po_number", "PO_MISMATCH"),
        ("currency", "CURRENCY_MISMATCH"),
        ("beneficiary", "BENEFICIARY_CHANGE"),
        ("account_id", "ACCOUNT_CHANGE"),
    ):
        if observed.get(field) != expected.get(field):
            warnings.append(warning)
    return warnings


def parse_ocr_amounts(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key in ("subtotal", "tax", "discount", "shipping", "total"):
        matches = re.findall(rf"\b{key}\b\s*(?:[A-Z]{{3}}\s*)?([0-9][0-9., ]*)", text, re.I)
        if matches:
            fields[key] = matches[-1].strip()
    return fields


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic-dev", type=Path, required=True)
    parser.add_argument("--ocr-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert_input_allowed(args.synthetic_dev)
    rows = [json.loads(line) for line in args.synthetic_dev.read_text().splitlines()]
    ocr = json.loads(args.ocr_result.read_text())
    ocr_rows = {row["document_id"]: row for row in ocr["predictions"] if row["split"] == "dev"}
    cases: list[dict] = []
    false_positive_count = 0
    detected = 0
    corruption_types = ("total_mismatch", "invalid_date_order", "wrong_po", "currency_mismatch", "beneficiary_change", "account_change")
    for index, row in enumerate(rows):
        expected = {key: spec["text"] for key, spec in row["fields"].items()}
        false_positive_count += bool(validate(expected, expected))
        observed = copy.deepcopy(expected)
        kind = corruption_types[index % len(corruption_types)]
        if kind == "total_mismatch":
            observed["total"] = str(amount(observed["total"]) + Decimal("17.00"))
        elif kind == "invalid_date_order":
            observed["due_date"] = "2020-01-01"
        elif kind == "wrong_po":
            observed["po_number"] = "V2-DV-PO-WRONG"
        elif kind == "currency_mismatch":
            observed["currency"] = "CHF" if expected["currency"] != "CHF" else "EUR"
        elif kind == "beneficiary_change":
            observed["beneficiary"] = "Synthetic Changed Beneficiary"
        elif kind == "account_change":
            observed["account_id"] = "SYN-DV-ACCOUNT-CHANGED"
        warnings = validate(observed, expected)
        caught = bool(warnings)
        detected += caught
        cases.append({"document_id": row["document_id"], "corruption": kind, "warnings": warnings, "detected": caught})

    high_confidence_errors = 0
    high_confidence_errors_caught = 0
    for row in rows:
        prediction = ocr_rows[row["document_id"]]
        if prediction["mean_confidence"] < 0.90 or prediction["total_correct"]:
            continue
        high_confidence_errors += 1
        parsed = parse_ocr_amounts(prediction["text"])
        if arithmetic_valid(parsed) is False:
            high_confidence_errors_caught += 1

    result = {
        "experiment_id": "V2-E12",
        "dataset": "R-FDI Synthetic V2 development",
        "business_corruption_cases": len(cases),
        "business_corruptions_detected": detected,
        "business_corruption_detection_rate": detected / len(cases),
        "valid_false_positives": false_positive_count,
        "high_confidence_ocr_total_errors": high_confidence_errors,
        "high_confidence_ocr_total_errors_caught_by_arithmetic": high_confidence_errors_caught,
        "high_confidence_error_catch_rate": high_confidence_errors_caught / high_confidence_errors if high_confidence_errors else None,
        "risk_interpretation": "Beneficiary/account changes are review signals, not fraud classifications.",
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, sort_keys=True))


if __name__ == "__main__":
    main()
