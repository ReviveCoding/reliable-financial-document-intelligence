from __future__ import annotations

from collections import Counter
from math import log
from typing import Iterable


def classification_metrics(y_true: Iterable[str], y_pred: Iterable[str]) -> dict[str, float]:
    true, pred = list(y_true), list(y_pred)
    labels = sorted(set(true) | set(pred))
    per_f1 = []
    correct = 0
    for label in labels:
        tp = sum(a == label and b == label for a, b in zip(true, pred))
        fp = sum(a != label and b == label for a, b in zip(true, pred))
        fn = sum(a == label and b != label for a, b in zip(true, pred))
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        per_f1.append(2 * precision * recall / (precision + recall) if precision + recall else 0)
        correct += tp
    return {"accuracy": correct / len(true) if true else 0, "macro_f1": sum(per_f1) / len(per_f1) if per_f1 else 0}


def brier_score(probabilities: Iterable[float], outcomes: Iterable[bool]) -> float:
    pairs = list(zip(probabilities, outcomes))
    return sum((p - float(y)) ** 2 for p, y in pairs) / len(pairs) if pairs else 0


def expected_calibration_error(probabilities: Iterable[float], outcomes: Iterable[bool], bins: int = 10) -> float:
    pairs = list(zip(probabilities, outcomes))
    if not pairs:
        return 0
    ece = 0.0
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        bucket = [(p, y) for p, y in pairs if low <= p <= high if index == bins - 1 or p < high]
        if bucket:
            confidence = sum(p for p, _ in bucket) / len(bucket)
            accuracy = sum(bool(y) for _, y in bucket) / len(bucket)
            ece += len(bucket) / len(pairs) * abs(confidence - accuracy)
    return ece
