from __future__ import annotations

from typing import Iterable, Mapping


def field_error_risk(confidence: float, criticality: float, *, ood: float = 0, conflict: bool = False, disagreement: float = 0) -> float:
    if not 0 <= confidence <= 1:
        raise ValueError("confidence outside [0,1]")
    weight = min(1.0, criticality / 5.0)
    score = (1 - confidence) * weight + 0.25 * ood + 0.3 * float(conflict) + 0.2 * disagreement
    return min(1.0, max(0.0, score))


def weighted_critical_error(errors: Iterable[bool], criticalities: Iterable[float]) -> float:
    pairs = list(zip(errors, criticalities))
    denominator = sum(weight for _, weight in pairs)
    return sum(float(error) * weight for error, weight in pairs) / denominator if denominator else 0.0


def residual_risk_curve(records: list[Mapping[str, float | bool]], coverages: Iterable[float]) -> dict[str, float]:
    ordered = sorted(records, key=lambda row: float(row["risk"]))
    result: dict[str, float] = {}
    for coverage in coverages:
        count = max(1, round(len(ordered) * coverage))
        accepted = ordered[:count]
        result[f"{coverage:.2f}"] = weighted_critical_error(
            (bool(row["error"]) for row in accepted),
            (float(row["criticality"]) for row in accepted),
        )
    return result
