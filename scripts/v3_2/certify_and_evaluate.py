from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.stats import beta
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from scripts.v3_2.train_risk_model import aurc, ece, matrix, score_selected

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = json.loads((ROOT / "configs/v3_2/risk_protocol.json").read_text())
SEED = int(PROTOCOL["determinism"]["seed"])
REPS = int(PROTOCOL["determinism"]["bootstrap_replicates"])
ALPHA = float(PROTOCOL["certification"]["alpha"])


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def binary(row: dict[str, str], name: str) -> float:
    return float(row[name].casefold() == "true")


def safe_auc(y: np.ndarray, score: np.ndarray) -> float | None:
    return float(roc_auc_score(y, score)) if len(set(y)) == 2 else None


def metric_set(y: np.ndarray, score: np.ndarray) -> dict[str, float | None]:
    clipped = np.clip(score, 0, 1)
    return {
        "AURC": aurc(y, score),
        "PR_AUC": float(average_precision_score(y, score)),
        "AUROC": safe_auc(y, score),
        "Brier": float(brier_score_loss(y, clipped)),
        "ECE": ece(y, clipped),
    }


def baseline(rows: list[dict[str, str]], candidate: str) -> np.ndarray:
    confidence = np.array([float(row["sequence_confidence"]) for row in rows])
    if candidate == "R0":
        return 1 - confidence
    conflicts = np.array([float(row["reconciliation_contradiction_count"]) for row in rows])
    return np.clip(1 - confidence + 0.3 * conflicts, 0, 1)


def clopper_pearson_upper(errors: int, n: int) -> float | None:
    if n == 0:
        return None
    return 1.0 if errors == n else float(beta.ppf(1 - ALPHA, errors + 1, n - errors))


def empirical_bernstein_upper(losses: np.ndarray) -> float | None:
    """Maurer-Pontil-style one-sided bound for losses in [0,1]."""
    n = len(losses)
    if n < 2:
        return None
    variance = float(np.var(losses, ddof=1))
    log_term = math.log(2 / ALPHA)
    bound = float(losses.mean()) + math.sqrt(2 * variance * log_term / n) + 7 * log_term / (3 * (n - 1))
    return min(1.0, bound)


def review_table(rows: list[dict[str, str]], scores: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    y = np.array([binary(row, "document_has_critical_error") for row in rows])
    line = np.array([binary(row, "document_has_line_item_critical_error") for row in rows])
    weighted = np.array([float(row["weighted_critical_loss"]) for row in rows])
    total_errors = float(y.sum())
    output: list[dict[str, Any]] = []
    for name, score in scores.items():
        order = np.argsort(-score, kind="stable")
        for budget in PROTOCOL["review_budgets"]:
            reviewed_n = round(len(rows) * float(budget))
            reviewed = order[:reviewed_n]
            accepted = order[reviewed_n:]
            review_cost = reviewed_n / len(rows)
            residual_cost = 25.0 * float(y[accepted].sum()) / len(rows)
            output.append({
                "candidate": name,
                "review_budget": budget,
                "review_rate": reviewed_n / len(rows),
                "automation_coverage": len(accepted) / len(rows),
                "document_selective_risk": float(y[accepted].mean()) if len(accepted) else 0.0,
                "line_item_critical_risk": float(line[accepted].mean()) if len(accepted) else 0.0,
                "weighted_critical_risk": float(weighted[accepted].mean()) if len(accepted) else 0.0,
                "critical_error_capture": float(y[reviewed].sum() / total_errors) if total_errors else 1.0,
                "critical_false_accept_count": int(y[accepted].sum()),
                "critical_false_accept_rate": float(y[accepted].mean()) if len(accepted) else 0.0,
                "expected_normalized_cost": review_cost + residual_cost,
                "cost_note": "Illustrative v3.1 costs: review=1, unsafe critical auto-accept=25; not institutional costs.",
            })
    return output


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def bootstrap_delta(y: np.ndarray, baseline_score: np.ndarray, learned_score: np.ndarray) -> dict[str, Any]:
    rng = np.random.default_rng(SEED)
    absolute: list[float] = []
    relative: list[float] = []
    for _ in range(REPS):
        take = rng.integers(0, len(y), len(y))
        left = aurc(y[take], baseline_score[take])
        right = aurc(y[take], learned_score[take])
        absolute.append(left - right)
        relative.append((left - right) / left if left else 0.0)
    return {
        "replicates": REPS,
        "support_document_groups": len(y),
        "absolute_AURC_reduction": aurc(y, baseline_score) - aurc(y, learned_score),
        "absolute_AURC_reduction_ci95": [float(np.quantile(absolute, 0.025)), float(np.quantile(absolute, 0.975))],
        "relative_AURC_reduction": (aurc(y, baseline_score) - aurc(y, learned_score)) / aurc(y, baseline_score),
        "relative_AURC_reduction_ci95": [float(np.quantile(relative, 0.025)), float(np.quantile(relative, 0.975))],
    }


def calibration_details(y: np.ndarray, score: np.ndarray) -> dict[str, Any]:
    clipped = np.clip(score, 1e-6, 1 - 1e-6)
    logit = np.log(clipped / (1 - clipped))
    fitted = LogisticRegression(C=1e6, max_iter=2000, random_state=SEED).fit(logit.reshape(-1, 1), y)
    return {
        **metric_set(y, score),
        "calibration_intercept": float(fitted.intercept_[0]),
        "calibration_slope": float(fitted.coef_[0, 0]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    development = read_rows(args.development)
    test = read_rows(args.test)
    certification = [row for row in development if row["development_partition"] == "INDEPENDENT_CERTIFICATION"]
    assert len(certification) == 20
    assert all(row["designation"] == "POST_AUDIT_REUSED_CERTIFICATION_PARTITION" for row in certification)
    assert all(row["designation"] == "RETROSPECTIVE_LOCKED_BENCHMARK" for row in test)
    bundle = joblib.load(args.model)
    selection = json.loads(args.selection.read_text())
    features = bundle["features"]

    certification_score = score_selected(bundle, matrix(certification, features), certification)
    certificate_rows: list[dict[str, Any]] = []
    cert_y = np.array([binary(row, "document_has_critical_error") for row in certification])
    cert_weighted = np.array([float(row["weighted_critical_loss"]) for row in certification])
    for frozen in selection["thresholds"]:
        threshold = frozen["threshold"]
        if threshold is None:
            certificate_rows.append({"designation":"POST_AUDIT_REUSED_CERTIFICATION_PARTITION","fresh_confirmatory_evidence":False,"promotion_eligible":False,"target_risk": frozen["target_risk"], "threshold": "", "accepted_n": 0, "coverage": 0.0, "observed_binary_risk": "", "binary_upper_bound_95": "", "observed_weighted_loss": "", "weighted_upper_bound_95": "", "status": "REPLAY_INSUFFICIENT_SUPPORT"})
            continue
        accepted = certification_score <= float(threshold)
        n = int(accepted.sum())
        errors = int(cert_y[accepted].sum())
        binary_upper = clopper_pearson_upper(errors, n)
        weighted_upper = empirical_bernstein_upper(cert_weighted[accepted])
        if n < int(PROTOCOL["certification"]["minimum_accepted_documents"]):
            status = "REPLAY_INSUFFICIENT_SUPPORT"
        else:
            status = "REPLAY_CERTIFIED_STATISTICALLY" if binary_upper is not None and binary_upper <= float(frozen["target_risk"]) else "REPLAY_UNCERTIFIED"
        certificate_rows.append({"designation":"POST_AUDIT_REUSED_CERTIFICATION_PARTITION","fresh_confirmatory_evidence":False,"promotion_eligible":False,"target_risk": frozen["target_risk"], "threshold": threshold, "accepted_n": n, "coverage": n / len(certification), "observed_binary_risk": errors / n if n else "", "binary_upper_bound_95": binary_upper if binary_upper is not None else "", "observed_weighted_loss": float(cert_weighted[accepted].mean()) if n else "", "weighted_upper_bound_95": weighted_upper if weighted_upper is not None else "", "status": status})

    test_x = matrix(test, features)
    learned = score_selected(bundle, test_x, test)
    scores = {"R0_raw_confidence": baseline(test, "R0"), "R1_current_heuristic": baseline(test, "R1"), "R4_best_learned": learned}
    y = np.array([binary(row, "document_has_critical_error") for row in test])
    metric_rows = [{"designation": "RETROSPECTIVE_LOCKED_BENCHMARK", "candidate": name, **metric_set(y, score)} for name, score in scores.items()]
    platt = bundle["platt"].predict_proba(learned.reshape(-1, 1))[:, 1]
    isotonic = bundle["isotonic"].predict(learned)
    calibration = {
        "designation": "RETROSPECTIVE_LOCKED_BENCHMARK",
        "note": "Calibration changes probability estimates, not the learned ranking; fitted on development threshold-selection only.",
        "uncalibrated": calibration_details(y, learned),
        "platt": calibration_details(y, platt),
        "isotonic": calibration_details(y, isotonic),
    }
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "certification_results.csv", certificate_rows)
    write_csv(output / "retrospective_candidate_metrics.csv", metric_rows)
    write_csv(output / "retrospective_review_budgets.csv", review_table(test, scores))
    (output / "retrospective_bootstrap_delta.json").write_text(json.dumps(bootstrap_delta(y, scores["R0_raw_confidence"], learned), indent=2, sort_keys=True) + "\n")
    (output / "retrospective_calibration.json").write_text(json.dumps(calibration, indent=2, sort_keys=True) + "\n")
    combined = development + test
    write_csv(args.development.parent / "risk_feature_table.csv", combined)
    summary = {
        "corrected_replay_frozen_before_reopening_at_commit": "274a2c057ab46cc4f47feac0514be423ffc75e61",
        "certification_support": len(certification),
        "fresh_confirmatory_evidence":False,
        "promotion_eligible":False,
        "certificate_results": certificate_rows,
        "retrospective_test_designation": "RETROSPECTIVE_LOCKED_BENCHMARK",
        "retrospective_test_is_fresh_holdout": False,
        "retrospective_support": len(test),
        "critical_error_prevalence": float(y.mean()),
        "line_item_critical_error_prevalence": float(np.mean([binary(row, "document_has_line_item_critical_error") for row in test])),
        "candidate_metrics": metric_rows,
        "extractor_weights_changed": False,
    }
    (output / "evaluation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
