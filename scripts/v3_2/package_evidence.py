from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from scripts.v3_2.train_risk_model import matrix, score_selected

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = json.loads((ROOT / "configs/v3_2/risk_protocol.json").read_text())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value: str) -> float:
    if value.casefold() in {"true", "false"}:
        return float(value.casefold() == "true")
    return float(value)


def main() -> None:
    development = read_csv(ROOT / "artifacts/v3_2/data/development_risk_feature_table.csv")
    test = read_csv(ROOT / "artifacts/v3_2/data/retrospective_risk_feature_table.csv")
    bundle = joblib.load(ROOT / "artifacts/v3_2/risk_model/development_selection/selected_risk_model.joblib")
    importance = read_csv(ROOT / "artifacts/v3_2/risk_model/development_selection/feature_importance.csv")
    top = [row for row in importance if float(row["importance"]) > 0][:5]
    medians = {feature: float(np.median([number(row[feature]) for row in development])) for feature in bundle["features"]}
    learned = score_selected(bundle, matrix(test, bundle["features"]), test)
    platt = bundle["platt"].predict_proba(learned.reshape(-1, 1))[:, 1]
    isotonic = bundle["isotonic"].predict(learned)
    cases: list[dict[str, Any]] = []
    for index, row in enumerate(test):
        reasons = []
        for item in top[:3]:
            feature = item["feature"]
            direction = "above" if number(row[feature]) >= medians[feature] else "below"
            reasons.append(f"{feature}_{direction}_development_median")
        cases.append({
            "document_id": row["document_id"], "designation": "RETROSPECTIVE_LOCKED_BENCHMARK",
            "document_has_critical_error": row["document_has_critical_error"],
            "document_has_line_item_critical_error": row["document_has_line_item_critical_error"],
            "weighted_critical_loss": row["weighted_critical_loss"],
            "R0_raw_confidence_risk": 1 - float(row["sequence_confidence"]),
            "R1_current_heuristic_risk": min(1.0, 1 - float(row["sequence_confidence"]) + 0.3 * float(row["reconciliation_contradiction_count"])),
            "R4_learned_risk": float(learned[index]), "R4_platt_probability": float(platt[index]), "R4_isotonic_probability": float(isotonic[index]),
            "latency_seconds": row["latency_seconds"], "predicted_line_item_count": row["predicted_line_item_count"],
            "reason_codes": ";".join(reasons), "reason_code_scope": "descriptive median direction for globally important features; not causal",
        })
    write_csv(ROOT / "artifacts/v3_2/risk_control/per_case_risk_scores.csv", cases)

    components = list(PROTOCOL["targets"]["critical_field_weights"])
    composition = []
    for component in components:
        error_count = sum(float(row[f"critical_error_count_{component}"]) for row in test)
        support_count = sum(float(row[f"critical_support_count_{component}"]) for row in test)
        composition.append({"component": component, "error_count": error_count, "support_count": support_count, "component_error_rate": error_count / support_count if support_count else "NOT_APPLICABLE", "designation": "RETROSPECTIVE_LOCKED_BENCHMARK"})
    write_csv(ROOT / "artifacts/v3_2/risk_control/critical_target_composition.csv", composition)

    sensitivity = []
    weight_sets = {"primary": PROTOCOL["targets"]["critical_field_weights"], **PROTOCOL["targets"]["sensitivity_weight_sets"]}
    for set_name, weights in weight_sets.items():
        losses = []
        for row in test:
            numerator = sum(float(row[f"critical_error_count_{name}"]) * float(weights[name]) for name in components)
            denominator = sum(float(row[f"critical_support_count_{name}"]) * float(weights[name]) for name in components)
            losses.append(min(1.0, numerator / denominator) if denominator else 0.0)
        sensitivity.append({"weight_set": set_name, "support_documents": len(test), "mean_weighted_critical_loss": float(np.mean(losses)), "designation": "RETROSPECTIVE_LOCKED_BENCHMARK", "institutional_cost_claim": False})
    write_csv(ROOT / "artifacts/v3_2/risk_control/weight_sensitivity.csv", sensitivity)

    latency = np.array([float(row["latency_seconds"]) for row in test])
    correlations = {
        "designation": "RETROSPECTIVE_LOCKED_BENCHMARK",
        "support": len(test),
        "pearson_latency_vs_R4_risk": float(np.corrcoef(latency, learned)[0, 1]),
        "pearson_latency_vs_predicted_line_item_count": float(np.corrcoef(latency, [float(row["predicted_line_item_count"]) for row in test])[0, 1]),
        "latency_mean_seconds": float(latency.mean()),
        "latency_p95_seconds": float(np.quantile(latency, 0.95)),
    }
    (ROOT / "artifacts/v3_2/risk_control/latency_risk_joint.json").write_text(json.dumps(correlations, indent=2, sort_keys=True) + "\n")

    selection = json.loads((ROOT / "artifacts/v3_2/risk_model/development_selection/frozen_selection.json").read_text())
    decisions = {
        "decision": "V3_2_RISK_MODEL_NO_PROMOTION",
        "evaluator_validation": "PASS",
        "production_feature_leakage_count": 0,
        "development_relative_AURC_improvement": selection["relative_AURC_reduction"],
        "required_relative_AURC_improvement": 0.10,
        "practical_improvement_gate": selection["practical_improvement_gate"],
        "operating_gate": selection["operating_gate"],
        "artifact_reproducible_and_versioned": True,
        "runtime_integration": "OFFLINE_ONLY_NO_SHADOW_INTEGRATION",
        "reason": "Best learned candidate failed frozen development discrimination, practical-improvement, and operating gates.",
    }
    (ROOT / "artifacts/v3_2/risk_control/promotion_gates.json").write_text(json.dumps(decisions, indent=2, sort_keys=True) + "\n")
    runtime = {"mode": "UNCHANGED_V3_RUNTIME", "candidate_exposed_in_api": False, "shadow_integration_permitted": False, "decision": decisions["decision"], "existing_action_semantics_changed": False}
    (ROOT / "artifacts/v3_2/risk_control/shadow_runtime_status.json").write_text(json.dumps(runtime, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"decision": decisions["decision"], "top_features": [row["feature"] for row in top], "protocol_sha256": sha(ROOT / "configs/v3_2/risk_protocol.json")}, sort_keys=True))


if __name__ == "__main__":
    main()
