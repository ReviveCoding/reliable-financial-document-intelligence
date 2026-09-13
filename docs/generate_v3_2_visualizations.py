from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets/v3_2"
OUT.mkdir(parents=True, exist_ok=True)
COLORS = ["#2563eb", "#0f766e", "#d97706", "#dc2626", "#7c3aed", "#475569"]


def data(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def esc(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def frame(title: str, body: str, subtitle: str = "") -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="500" viewBox="0 0 900 500" role="img" aria-label="{esc(title)}">
<style>text{{font-family:Inter,Arial,sans-serif;fill:#334155}}.title{{font-size:24px;font-weight:700;fill:#0f172a}}.sub{{font-size:13px;fill:#64748b}}.label{{font-size:12px}}.value{{font-size:12px;font-weight:600}}@media(prefers-color-scheme:dark){{text{{fill:#cbd5e1}}.title{{fill:#f8fafc}}.sub{{fill:#94a3b8}}}}</style>
<rect width="900" height="500" rx="16" fill="#ffffff"/><text x="48" y="44" class="title">{esc(title)}</text><text x="48" y="68" class="sub">{esc(subtitle)}</text>{body}</svg>'''


def save(name: str, title: str, body: str, subtitle: str = "") -> None:
    (OUT / name).write_text(frame(title, body, subtitle) + "\n")


def bars(name: str, title: str, entries: Iterable[tuple[str, float]], maximum: float | None = None, subtitle: str = "") -> None:
    entries = list(entries); maximum = maximum or max(value for _, value in entries) or 1
    body = '<line x1="270" y1="90" x2="270" y2="450" stroke="#94a3b8"/>'
    step = min(54, 340 / max(1, len(entries)))
    for index, (label, value) in enumerate(entries):
        y = 100 + index * step; width = 550 * value / maximum
        body += f'<text x="260" y="{y+17}" text-anchor="end" class="label">{esc(label[:34])}</text><rect x="270" y="{y}" width="{width:.2f}" height="24" rx="4" fill="{COLORS[index%len(COLORS)]}"/><text x="{280+width:.2f}" y="{y+17}" class="value">{value:.4f}</text>'
    save(name, title, body, subtitle)


def lines(name: str, title: str, series: dict[str, list[tuple[float, float]]], subtitle: str = "") -> None:
    body = '<line x1="90" y1="430" x2="850" y2="430" stroke="#94a3b8"/><line x1="90" y1="90" x2="90" y2="430" stroke="#94a3b8"/>'
    for index, (label, points) in enumerate(series.items()):
        coords = " ".join(f"{90+760*x:.2f},{430-340*y:.2f}" for x, y in points)
        body += f'<polyline points="{coords}" fill="none" stroke="{COLORS[index]}" stroke-width="3"/><text x="{610+index*120}" y="86" class="label" fill="{COLORS[index]}">{esc(label)}</text>'
    save(name, title, body, subtitle)


def main() -> None:
    line = json.loads((ROOT / "artifacts/v3_2/line_items/retrospective_test/aggregate_metrics.json").read_text())
    m = line["document_mean_metrics"]
    bars("historical_vs_row_aware.svg", "Historical vs row-aware line-item metrics", [("E0 historical flat F1", m["E0_historical_flat_f1"]), ("E2 matched line-item F1", m["E2_line_item_f1"]), ("field-within-row micro F1", m["field_within_row_micro_f1"]), ("row exact match", m["row_exact_match_rate"])], 1, "CORD test — RETROSPECTIVE_LOCKED_BENCHMARK")
    composition = data("artifacts/v3_2/risk_control/critical_target_composition.csv")
    bars("critical_risk_target_composition.svg", "Critical-risk target composition", [(r["component"], float(r["component_error_rate"])) for r in composition if r["component_error_rate"] != "NOT_APPLICABLE"], 1, "Error rate within supported field occurrences")
    cv = data("artifacts/v3_2/risk_model/development_selection/candidate_grouped_cv_metrics.csv")
    bars("risk_model_aurc_comparison.svg", "Development grouped-CV AURC", [(r["candidate"], float(r["AURC"])) for r in cv], None, "Lower is better; model and threshold selection use development evidence only")
    cases = data("artifacts/v3_2/risk_control/per_case_risk_scores.csv")
    ranked = sorted(cases, key=lambda r: float(r["R4_learned_risk"]), reverse=True)
    positives = sum(r["document_has_critical_error"].casefold() == "true" for r in ranked); tp = fp = 0; pr=[]
    for i, row in enumerate(ranked, 1):
        if row["document_has_critical_error"].casefold() == "true": tp += 1
        else: fp += 1
        pr.append((tp / i, tp / positives))
    lines("critical_error_pr_curve.svg", "Critical-error precision–recall", {"R4": pr}, "Retrospective benchmark; axes span 0–1")
    bins=[]
    for low in [i/10 for i in range(10)]:
        group=[r for r in cases if low <= float(r["R4_learned_risk"]) <= (low+.1 if low==.9 else low+.1-1e-12)]
        if group: bins.append((sum(float(r["R4_learned_risk"]) for r in group)/len(group),sum(r["document_has_critical_error"].casefold()=="true" for r in group)/len(group)))
    lines("learned_risk_reliability.svg", "Learned-risk reliability", {"observed": bins, "ideal": [(0,0),(1,1)]}, "Uncalibrated R4; retrospective benchmark")
    budgets = data("artifacts/v3_2/risk_control/retrospective_review_budgets.csv")
    wanted=["R0_raw_confidence","R4_best_learned"]
    lines("risk_coverage_curve.svg", "Risk–coverage curve", {name:[(float(r["automation_coverage"]),float(r["document_selective_risk"])) for r in budgets if r["candidate"]==name] for name in wanted}, "Coverage and risk axes span 0–1")
    lines("critical_false_accept_by_review_budget.svg", "Critical false-accept by review budget", {name:[(float(r["review_budget"]),float(r["critical_false_accept_rate"])) for r in budgets if r["candidate"]==name] for name in wanted})
    lines("critical_capture_by_review_budget.svg", "Critical-error capture by review budget", {name:[(float(r["review_budget"]),float(r["critical_error_capture"])) for r in budgets if r["candidate"]==name] for name in wanted})
    cert=data("artifacts/v3_2/risk_control/certification_results.csv")
    lines("certification_coverage_frontier.svg", "Finite-sample certification frontier", {"coverage":[(float(r["target_risk"]),float(r["coverage"])) for r in cert],"upper bound":[(float(r["target_risk"]),float(r["binary_upper_bound_95"]) if r["binary_upper_bound_95"] else 1) for r in cert]}, "No target certified; x is target risk")
    pareto=data("artifacts/v3_2/line_item_slicing/line_item_error_pareto.csv")
    bars("line_item_error_pareto.svg", "Line-item error Pareto", [(r["error_mode"],float(r["prevalence"])) for r in pareto], 1, "Document prevalence; categories overlap")
    robust=data("artifacts/v3_2/robustness/robustness_risk_response_summary.csv")
    severe=[r for r in robust if r["severity"] in {"clean","high"}]
    bars("risk_by_corruption_severity.svg", "Risk score by corruption", [(f"{r['corruption']} {r['severity']}",float(r["mean_risk_score"])) for r in severe], 1, "Frozen clean extraction features; only pre-inference image descriptors vary")
    importance=data("artifacts/v3_2/risk_model/development_selection/feature_importance.csv")[:10]
    bars("feature_importance.svg", "R4 global feature importance", [(r["feature"],float(r["importance"])) for r in importance], None, "Development-fitted shallow gradient boosting")
    points=[(min(1,float(r["latency_seconds"])/8),float(r["R4_learned_risk"])) for r in cases]
    body='<line x1="90" y1="430" x2="850" y2="430" stroke="#94a3b8"/><line x1="90" y1="90" x2="90" y2="430" stroke="#94a3b8"/>' + ''.join(f'<circle cx="{90+760*x:.2f}" cy="{430-340*y:.2f}" r="4" fill="#2563eb" opacity=".55"/>' for x,y in points)
    save("latency_risk_joint.svg", "Latency and learned risk", body, "x: latency / 8 seconds (clipped); y: R4 risk; retrospective benchmark")
    schematic='<rect x="80" y="120" width="220" height="70" rx="8" fill="#dbeafe"/><text x="190" y="160" text-anchor="middle">GT row A: item + 10.00</text><rect x="80" y="260" width="220" height="70" rx="8" fill="#dbeafe"/><text x="190" y="300" text-anchor="middle">GT row B: item + 20.00</text><rect x="600" y="120" width="220" height="70" rx="8" fill="#fee2e2"/><text x="710" y="160" text-anchor="middle">Pred row: item + 20.00</text><rect x="600" y="260" width="220" height="70" rx="8" fill="#fee2e2"/><text x="710" y="300" text-anchor="middle">Pred row: item + 10.00</text><path d="M300 155 C450 155 450 295 600 295" fill="none" stroke="#dc2626" stroke-width="3"/><path d="M300 295 C450 295 450 155 600 155" fill="none" stroke="#dc2626" stroke-width="3"/><text x="450" y="390" text-anchor="middle" class="sub">E2 matches by maximum field agreement and exposes cross-row association.</text>'
    save("row_misalignment_schematic.svg", "Row-misalignment diagnostic", schematic, "Conceptual example; no raw receipt content")
    slices=data("artifacts/v3_2/line_item_slicing/line_item_slices.csv")
    eligible=sorted([r for r in slices if int(r["support_n"])>=20 and r["critical_error_rate"]!="nan"],key=lambda r:float(r["critical_error_rate"]),reverse=True)[:8]
    bars("line_item_risk_slices.svg", "Highest-support critical-risk slices", [(f"{r['slice_family']}:{r['slice']}",float(r["critical_error_rate"])) for r in eligible], 1, "Only slices with N ≥ 20")
    print(json.dumps({"assets": len(list(OUT.glob("*.svg"))), "output": str(OUT.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
