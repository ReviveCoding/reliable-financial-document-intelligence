from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    read = lambda name: json.loads((args.results / name).read_text())
    reliability = read("reliability_development.json")
    ood = read("ood_development.json")
    reconciliation = read("reconciliation_development.json")
    synthetic = read("synthetic_ocr_development.json")
    router = reliability["router"]
    raw = reliability["metrics"]["paddle_raw_calibration_eval"]
    calibrated = reliability["metrics"]["paddle_isotonic_calibration_eval"]
    ood_full = ood["methods"]["mahalanobis"]["review_at_20pct"]
    ood_removed = ood["methods"]["ocr_confidence"]["review_at_20pct"]
    result = {
        "experiment_id": "V2-E16",
        "design": "Component-scoped one-removal ablations; incompatible task metrics are not collapsed into a fake global score.",
        "ablations": [
            {
                "condition": "FULL",
                "scope": "measured V2 reliability components",
                "metrics": {
                    "calibrated_total_ece": calibrated["ece"],
                    "ood_review_error_capture_20pct": ood_full["critical_error_capture_rate"],
                    "financial_high_confidence_errors_caught": reconciliation["high_confidence_ocr_total_errors_caught_by_arithmetic"],
                    "synthetic_document_macro_f1": synthetic["dev_metrics"]["tfidf_document_macro_f1"],
                },
            },
            {
                "condition": "minus adaptive routing",
                "scope": "CORD total extraction",
                "result": "Fixed Donut retained identical accuracy and reduced mean latency.",
                "full_cascade_accuracy": router["cascade_accuracy"],
                "fixed_donut_accuracy": router["fixed_donut_accuracy"],
                "full_cascade_latency": router["cascade_mean_latency"],
                "fixed_donut_latency": router["fixed_donut_mean_latency"],
            },
            {
                "condition": "minus OOD",
                "scope": "synthetic visual-corruption review at 20% budget",
                "full_error_capture": ood_full["critical_error_capture_rate"],
                "without_ood_error_capture": ood_removed["critical_error_capture_rate"],
            },
            {
                "condition": "minus calibration",
                "scope": "Paddle total correctness on held-out odd-index CORD validation",
                "full_ece": calibrated["ece"],
                "without_calibration_ece": raw["ece"],
                "full_brier": calibrated["brier"],
                "without_calibration_brier": raw["brier"],
            },
            {
                "condition": "minus financial validation",
                "scope": "high-confidence synthetic OCR total errors",
                "full_errors_caught": reconciliation["high_confidence_ocr_total_errors_caught_by_arithmetic"],
                "without_validation_errors_caught": 0,
                "eligible_errors": reconciliation["high_confidence_ocr_total_errors"],
            },
            {
                "condition": "minus synthetic augmentation",
                "scope": "rendered synthetic document-type classification",
                "full_tfidf_macro_f1": synthetic["dev_metrics"]["tfidf_document_macro_f1"],
                "without_learned_synthetic_examples_rule_macro_f1": synthetic["dev_metrics"]["rule_document_macro_f1"],
                "limitation": "This isolates learned synthetic examples versus rules, not synthetic augmentation of LayoutLMv3.",
            },
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
