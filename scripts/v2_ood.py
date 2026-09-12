from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import StandardScaler


def features(row: dict) -> list[float]:
    text = row["text"]
    non_ascii = sum(ord(character) > 127 for character in text) / max(1, len(text))
    return [row["mean_confidence"], np.log1p(len(text)), np.log1p(row["latency_seconds"]), non_ascii]


def review_result(score: np.ndarray, errors: np.ndarray, budget: float = 0.2) -> dict[str, float]:
    count = int(round(len(score) * budget))
    chosen = np.argsort(-score)[:count]
    total = errors.sum()
    caught = errors[chosen].sum()
    return {
        "review_rate": count / len(score),
        "critical_errors_captured": int(caught),
        "critical_error_capture_rate": float(caught / total) if total else 1.0,
        "residual_critical_error_rate": float((total - caught) / len(errors)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.input.read_text())
    train = [row for row in source["predictions"] if row["split"] == "train"]
    dev = [row for row in source["predictions"] if row["split"] == "dev"]
    train_in = [row for row in train if row["corruption"]["type"] == "none"]
    matrix_train = np.asarray([features(row) for row in train_in])
    matrix_dev = np.asarray([features(row) for row in dev])
    labels = np.asarray([row["corruption"]["type"] != "none" for row in dev], dtype=int)
    critical_errors = np.asarray([row["critical_field_value_recall"] < 1.0 for row in dev], dtype=int)

    scaler = StandardScaler().fit(matrix_train)
    train_scaled = scaler.transform(matrix_train)
    dev_scaled = scaler.transform(matrix_dev)
    center = train_scaled.mean(axis=0)
    covariance_inverse = np.linalg.pinv(np.cov(train_scaled, rowvar=False) + np.eye(train_scaled.shape[1]) * 1e-5)
    delta = dev_scaled - center
    mahalanobis = np.sqrt(np.einsum("ij,jk,ik->i", delta, covariance_inverse, delta))
    forest = IsolationForest(n_estimators=300, contamination="auto", random_state=20260911).fit(train_scaled)
    isolation = -forest.score_samples(dev_scaled)
    confidence_risk = 1 - matrix_dev[:, 0]

    methods = {}
    for name, score in (("mahalanobis", mahalanobis), ("isolation_forest", isolation), ("ocr_confidence", confidence_risk)):
        methods[name] = {
            "auroc": roc_auc_score(labels, score),
            "auprc": average_precision_score(labels, score),
            "review_at_20pct": review_result(score, critical_errors),
        }
    rng = np.random.default_rng(20260911)
    methods["random_no_ood"] = {"review_at_20pct": review_result(rng.random(len(dev)), critical_errors)}
    result = {
        "experiment_id": "V2-E13",
        "dataset": "R-FDI Synthetic V2",
        "ood_definition": "Any controlled visual corruption versus uncorrupted rendered documents",
        "observable_features": ["OCR mean confidence", "OCR text length", "OCR latency", "non-ASCII fraction"],
        "in_domain_training_documents": len(train_in),
        "development_documents": len(dev),
        "development_ood_documents": int(labels.sum()),
        "critical_error_documents": int(critical_errors.sum()),
        "methods": methods,
        "layout_novelty_limitation": "All V2 development templates and vendors are disjoint from training, so layout novelty AUROC has no in-split negative class and is not estimated.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
