from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np


def money(value: object) -> str:
    return re.sub(r"[^0-9]", "", str(value or ""))


def percentile_ci(values: list[float], seed: int = 20260911, draws: int = 10_000) -> list[float]:
    """Deterministic document-level bootstrap confidence interval for a mean."""
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(draws, len(array)))
    means = array[indices].mean(axis=1)
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    read = lambda name: json.loads((args.results / name).read_text())
    frozen = json.loads(args.frozen.read_text())
    donut = read("final_donut.json")
    paddle = read("final_paddleocr.json")
    layout = read("final_layoutlmv3.json")
    synthetic = read("final_synthetic_ocr.json")
    security = read("final_security.json")

    total_relevant = 0
    total_correct = 0
    for row in donut["predictions"]:
        truth = row["truth"].get("total", {})
        if "total_price" not in truth:
            continue
        total_relevant += 1
        total_correct += money(row["prediction"].get("total", {}).get("total_price")) == money(truth["total_price"])
    total_exact = total_correct / total_relevant
    schema_failure = sum(not row.get("schema_valid", False) for row in donut["predictions"]) / donut["documents"]
    donut_p95 = float(np.quantile(donut["latency_seconds"]["values"], 0.95))
    gain = total_exact - paddle["downstream_total_exact_match"]
    donut_doc_f1 = [float(row["leaf_f1"]) for row in donut["predictions"]]
    paddle_by_id = {row["document_id"]: row for row in paddle["predictions"]}
    paired_total_differences = []
    for row in donut["predictions"]:
        truth = row["truth"].get("total", {})
        if "total_price" not in truth or row["document_id"] not in paddle_by_id:
            continue
        donor = float(money(row["prediction"].get("total", {}).get("total_price")) == money(truth["total_price"]))
        base = paddle_by_id[row["document_id"]]
        paddle_correct = float(money(base.get("total_prediction")) == money(base.get("total_truth")))
        paired_total_differences.append(donor - paddle_correct)
    observed = {
        "cord_donut_leaf_f1": donut["leaf_f1"],
        "cord_donut_total_exact": total_exact,
        "cord_total_evaluated": total_relevant,
        "cord_paddle_total_exact": paddle["downstream_total_exact_match"],
        "funsd_layoutlmv3_macro_f1": layout["metrics"]["macro_f1"],
        "synthetic_all_field_recall": synthetic["dev_metrics"]["all_field_value_recall"],
        "synthetic_total_exact": synthetic["dev_metrics"]["total_exact_match"],
        "donut_p95_latency_seconds": donut_p95,
        "schema_failure_rate": schema_failure,
        "security_vlm_output_deviation_rate": security["vlm_output_deviation_rate"],
        "security_unauthorized_actions": security["unauthorized_action_attempts"],
        "operational_total_exact_gain_vs_paddle": gain,
    }
    thresholds = frozen["release_gates"]
    gates = {
        "cord_donut_leaf_f1": observed["cord_donut_leaf_f1"] >= thresholds["cord_donut_leaf_f1_min"],
        "cord_donut_total_exact": observed["cord_donut_total_exact"] >= thresholds["cord_donut_total_exact_min"],
        "funsd_layoutlmv3_macro_f1": observed["funsd_layoutlmv3_macro_f1"] >= thresholds["funsd_layoutlmv3_macro_f1_min"],
        "synthetic_all_field_recall": observed["synthetic_all_field_recall"] >= thresholds["synthetic_all_field_recall_min"],
        "synthetic_total_exact": observed["synthetic_total_exact"] >= thresholds["synthetic_total_exact_min"],
        "donut_p95_latency": observed["donut_p95_latency_seconds"] <= thresholds["donut_p95_latency_seconds_max"],
        "schema_failure_rate": observed["schema_failure_rate"] <= thresholds["schema_failure_rate_max"],
        "security_vlm_output_deviation": observed["security_vlm_output_deviation_rate"] <= thresholds["security_vlm_output_deviation_rate_max"],
        "security_unauthorized_actions": observed["security_unauthorized_actions"] <= thresholds["security_unauthorized_actions_max"],
        "operational_total_exact_gain_vs_paddle": observed["operational_total_exact_gain_vs_paddle"] >= thresholds["operational_total_exact_gain_vs_paddle_min"],
    }
    decision = "PROMOTE" if all(gates.values()) else "NO_PROMOTION"
    result = {
        "experiment_id": "V2-E20",
        "selected_system": frozen["selected_system"],
        "promotion_scope": frozen["promotion_scope"],
        "observed": observed,
        "thresholds": thresholds,
        "gates": gates,
        "release_decision": decision,
        "failed_gates": [name for name, passed in gates.items() if not passed],
        "statistics": {
            "method": "paired/document-level percentile bootstrap; 10,000 draws; seed 20260911",
            "donut_document_leaf_f1_mean": float(np.mean(donut_doc_f1)),
            "donut_document_leaf_f1_mean_95ci": percentile_ci(donut_doc_f1),
            "donut_minus_paddle_total_exact_absolute": float(np.mean(paired_total_differences)),
            "donut_minus_paddle_total_exact_95ci": percentile_ci(paired_total_differences),
            "paired_documents": len(paired_total_differences),
        },
        "integrity": {"frozen_config": str(args.frozen), "decision_rule": frozen["decision_rule"]},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
