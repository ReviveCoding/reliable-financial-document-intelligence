from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression


def money(value: object) -> str:
    return re.sub(r"[^0-9]", "", str(value or ""))


def metric_set(probability: np.ndarray, label: np.ndarray, bins: int = 10) -> dict[str, float]:
    clipped = np.clip(probability, 1e-6, 1 - 1e-6)
    ece = 0.0
    for lower in np.linspace(0, 1, bins, endpoint=False):
        selected = (probability >= lower) & (probability < lower + 1 / bins)
        if selected.any():
            ece += selected.mean() * abs(probability[selected].mean() - label[selected].mean())
    order = np.argsort(-probability)
    risks = np.cumsum(1 - label[order]) / np.arange(1, len(label) + 1)
    return {
        "ece": float(ece),
        "brier": float(np.mean((probability - label) ** 2)),
        "nll": float(-np.mean(label * np.log(clipped) + (1 - label) * np.log(1 - clipped))),
        "aurc": float(np.mean(risks)),
    }


def bootstrap_difference(a: np.ndarray, b: np.ndarray, seed: int = 20260911) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    samples = np.empty(10000)
    for index in range(len(samples)):
        take = rng.integers(0, len(a), len(a))
        samples[index] = a[take].mean() - b[take].mean()
    return {
        "absolute_difference": float(a.mean() - b.mean()),
        "ci95_low": float(np.quantile(samples, 0.025)),
        "ci95_high": float(np.quantile(samples, 0.975)),
    }


def policy_capture(scores: np.ndarray, errors: np.ndarray, budget: float) -> dict[str, float]:
    count = max(1, int(round(len(scores) * budget)))
    chosen = np.argsort(-scores)[:count]
    captured = errors[chosen].sum()
    total = errors.sum()
    return {
        "review_rate": count / len(scores),
        "critical_errors_captured": int(captured),
        "critical_error_capture_rate": float(captured / total) if total else 1.0,
        "residual_error_rate": float((total - captured) / len(scores)),
        "straight_through_rate": 1 - count / len(scores),
    }


def random_policy(errors: np.ndarray, budget: float, seed: int = 20260911) -> dict[str, float]:
    count = max(1, int(round(len(errors) * budget)))
    rng = np.random.default_rng(seed)
    captures = np.empty(1000)
    for index in range(len(captures)):
        captures[index] = errors[rng.choice(len(errors), count, replace=False)].sum()
    total = errors.sum()
    mean_capture = float(captures.mean())
    return {
        "review_rate": count / len(errors),
        "mean_critical_errors_captured": mean_capture,
        "critical_error_capture_rate": mean_capture / total if total else 1.0,
        "capture_rate_ci95_low": float(np.quantile(captures / total, 0.025)) if total else 1.0,
        "capture_rate_ci95_high": float(np.quantile(captures / total, 0.975)) if total else 1.0,
        "mean_residual_error_rate": float((total - mean_capture) / len(errors)),
        "straight_through_rate": 1 - count / len(errors),
        "simulations": len(captures),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paddle", type=Path, required=True)
    parser.add_argument("--donut", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paddle = json.loads(args.paddle.read_text())
    donut = json.loads(args.donut.read_text())
    paddle_rows = {row["document_id"]: row for row in paddle["predictions"]}
    donut_rows = {row["document_id"]: row for row in donut["predictions"]}
    ids = sorted(paddle_rows.keys() & donut_rows.keys())

    records = []
    for document_id in ids:
        p_row = paddle_rows[document_id]
        d_row = donut_rows[document_id]
        truth = money(p_row["total_truth"])
        donut_total = d_row.get("prediction", {}).get("total", {}).get("total_price")
        records.append(
            {
                "document_id": document_id,
                "truth": truth,
                "paddle_prediction": money(p_row["total_prediction"]),
                "donut_prediction": money(donut_total),
                "paddle_correct": money(p_row["total_prediction"]) == truth,
                "donut_correct": money(donut_total) == truth,
                "donut_document_exact": d_row.get("leaf_f1", 0.0) == 1.0,
                "donut_leaf_f1": d_row.get("leaf_f1"),
                "donut_confidence": d_row.get("sequence_confidence"),
                "paddle_confidence": p_row["mean_confidence"],
                "paddle_latency": p_row["latency_seconds"],
                "donut_latency": d_row["latency_seconds"],
            }
        )

    probability = np.array([row["paddle_confidence"] for row in records])
    paddle_correct = np.array([row["paddle_correct"] for row in records], dtype=float)
    donut_correct = np.array([row["donut_correct"] for row in records], dtype=float)
    donut_document_exact = np.array([row["donut_document_exact"] for row in records], dtype=float)
    paddle_latency = np.array([row["paddle_latency"] for row in records])
    donut_latency = np.array([row["donut_latency"] for row in records])
    disagreement = np.array([row["paddle_prediction"] != row["donut_prediction"] for row in records], dtype=float)

    calibration_index = np.arange(len(records)) % 2 == 0
    evaluation_index = ~calibration_index
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(probability[calibration_index], paddle_correct[calibration_index])
    calibrated = calibrator.predict(probability)

    thresholds = np.unique(np.r_[0.0, probability[calibration_index], 1.01])
    threshold_trials = []
    for threshold in thresholds:
        use_paddle = probability[calibration_index] >= threshold
        correct = np.where(use_paddle, paddle_correct[calibration_index], donut_correct[calibration_index])
        latency = paddle_latency[calibration_index] + np.where(use_paddle, 0, donut_latency[calibration_index])
        objective = float((1 - correct).mean() + 0.01 * latency.mean())
        threshold_trials.append((objective, -float(use_paddle.mean()), float(threshold)))
    selected_threshold = min(threshold_trials)[2]
    use_paddle_eval = probability[evaluation_index] >= selected_threshold
    cascade_correct = np.where(use_paddle_eval, paddle_correct[evaluation_index], donut_correct[evaluation_index])
    cascade_latency = paddle_latency[evaluation_index] + np.where(use_paddle_eval, 0, donut_latency[evaluation_index])

    errors = 1 - donut_document_exact[evaluation_index]
    donut_confidence = np.array([row["donut_confidence"] if row["donut_confidence"] is not None else 0.5 for row in records])
    risk_confidence = 1 - donut_confidence[evaluation_index]
    risk_disagreement = disagreement[evaluation_index]
    risk_rfdi = risk_confidence + 0.75 * risk_disagreement
    review = {}
    for budget in (0.05, 0.10, 0.20, 0.30, 0.50):
        review[str(budget)] = {
            "random": random_policy(errors, budget),
            "lowest_paddle_confidence": policy_capture(risk_confidence, errors, budget),
            "disagreement_first": policy_capture(risk_disagreement, errors, budget),
            "rfdi_risk": policy_capture(risk_rfdi, errors, budget),
        }

    result = {
        "experiment_id": "V2-E10",
        "dataset": "CORD v2",
        "split": "validation odd/even development partition",
        "documents": len(records),
        "calibration_documents": int(calibration_index.sum()),
        "evaluation_documents": int(evaluation_index.sum()),
        "metrics": {
            "paddle_total_exact_match_all": float(paddle_correct.mean()),
            "donut_total_exact_match_all": float(donut_correct.mean()),
            "paired_bootstrap_donut_minus_paddle": bootstrap_difference(donut_correct, paddle_correct),
            "paddle_raw_calibration_eval": metric_set(probability[evaluation_index], paddle_correct[evaluation_index]),
            "paddle_isotonic_calibration_eval": metric_set(calibrated[evaluation_index], paddle_correct[evaluation_index]),
            "donut_document_exact_match_all": float(donut_document_exact.mean()),
            "donut_document_raw_calibration_eval": metric_set(donut_confidence[evaluation_index], donut_document_exact[evaluation_index]),
            "model_disagreement_rate_all": float(disagreement.mean()),
        },
        "router": {
            "selection_data": "even-index CORD validation documents only",
            "evaluation_data": "odd-index CORD validation documents only",
            "objective": "error rate + 0.01 * measured seconds/document",
            "selected_paddle_confidence_threshold": selected_threshold,
            "fixed_paddle_accuracy": float(paddle_correct[evaluation_index].mean()),
            "fixed_paddle_mean_latency": float(paddle_latency[evaluation_index].mean()),
            "fixed_donut_accuracy": float(donut_correct[evaluation_index].mean()),
            "fixed_donut_mean_latency": float(donut_latency[evaluation_index].mean()),
            "cascade_accuracy": float(cascade_correct.mean()),
            "cascade_mean_latency": float(cascade_latency.mean()),
            "cascade_paddle_coverage": float(use_paddle_eval.mean()),
        },
        "human_review": {"target": "Donut document-level exact leaf extraction errors", "budgets": review},
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, sort_keys=True))


if __name__ == "__main__":
    main()
