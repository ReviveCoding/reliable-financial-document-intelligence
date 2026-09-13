#!/usr/bin/env python3
"""Regenerate v3.1 SVGs and the compact findings summary from committed evidence."""
from __future__ import annotations

import csv
import html
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/"artifacts/v3_1"; OUT=ROOT/"docs/assets/v3_1"
NAVY="#183153"; BLUE="#2878b5"; TEAL="#2a9d8f"; GOLD="#e9a23b"; RED="#c44e52"; GRID="#d9e2ec"; TEXT="#243447"


def rows(path: str) -> list[dict[str,str]]:
    return list(csv.DictReader((ART/path).open()))


def svg(title: str, subtitle: str, body: str, width: int=900, height: int=520) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(subtitle)}</desc>
<rect width="100%" height="100%" fill="#ffffff"/><style>text{{font-family:Inter,Segoe UI,Arial,sans-serif;fill:{TEXT}}}.title{{font-size:24px;font-weight:700}}.sub{{font-size:13px;fill:#52667a}}.label{{font-size:12px}}.small{{font-size:10px}}.axis{{stroke:{GRID};stroke-width:1}}</style>
<text x="48" y="40" class="title">{html.escape(title)}</text><text x="48" y="64" class="sub">{html.escape(subtitle)}</text>{body}</svg>\n'''


def bars(title: str, subtitle: str, labels: list[str], values: list[float], filename: str, maximum: float|None=None, colors: list[str]|None=None, percent: bool=False) -> None:
    maximum=maximum if maximum is not None else max(values+[1e-9]); left=260; top=90; height=360; rowh=height/max(1,len(values)); body=[]
    for i,(label,value) in enumerate(zip(labels,values)):
        y=top+i*rowh; w=max(0,value)/maximum*560
        body.append(f'<text x="250" y="{y+rowh*.62:.1f}" text-anchor="end" class="label">{html.escape(label[:34])}</text><rect x="270" y="{y+rowh*.18:.1f}" width="{w:.1f}" height="{rowh*.58:.1f}" rx="3" fill="{(colors or [BLUE])[i%len(colors or [BLUE])]}"/><text x="{278+w:.1f}" y="{y+rowh*.62:.1f}" class="label">{value*100:.1f}%</text>' if percent else f'<text x="250" y="{y+rowh*.62:.1f}" text-anchor="end" class="label">{html.escape(label[:34])}</text><rect x="270" y="{y+rowh*.18:.1f}" width="{w:.1f}" height="{rowh*.58:.1f}" rx="3" fill="{(colors or [BLUE])[i%len(colors or [BLUE])]}"/><text x="{278+w:.1f}" y="{y+rowh*.62:.1f}" class="label">{value:.3f}</text>')
    (OUT/filename).write_text(svg(title,subtitle,"".join(body)))


def line_chart(title: str, subtitle: str, series: dict[str,list[tuple[float,float]]], filename: str, xlab: str, ylab: str, ymax: float=1.0) -> None:
    left,top,w,h=90,90,740,340; palette=[BLUE,TEAL,GOLD,RED,NAVY]; body=[f'<line x1="{left}" y1="{top+h}" x2="{left+w}" y2="{top+h}" class="axis"/><line x1="{left}" y1="{top}" x2="{left}" y2="{top+h}" class="axis"/>']
    for tick in range(6):
        y=top+h-h*tick/5; body.append(f'<line x1="{left}" y1="{y}" x2="{left+w}" y2="{y}" class="axis"/><text x="78" y="{y+4}" text-anchor="end" class="small">{ymax*tick/5:.1f}</text>')
    for j,(name,pts) in enumerate(series.items()):
        color=palette[j%len(palette)]; coords=" ".join(f"{left+x*w:.1f},{top+h-min(y,ymax)/ymax*h:.1f}" for x,y in pts); body.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3"/>')
        body.append(f'<rect x="{left+j*150}" y="458" width="14" height="4" fill="{color}"/><text x="{left+20+j*150}" y="464" class="small">{html.escape(name[:20])}</text>')
    body.append(f'<text x="{left+w/2}" y="495" text-anchor="middle" class="label">{html.escape(xlab)}</text><text x="18" y="{top+h/2}" transform="rotate(-90 18 {top+h/2})" text-anchor="middle" class="label">{html.escape(ylab)}</text>')
    (OUT/filename).write_text(svg(title,subtitle,"".join(body)))


def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    slices=rows("slicing/slice_metrics.csv"); eligible=[r for r in slices if r["metric"]=="leaf_f1" and r["designation"]=="headline"]
    worst=sorted(eligible,key=lambda r:float(r["absolute_delta"]))[:8]; strongest=sorted(eligible,key=lambda r:float(r["absolute_delta"]),reverse=True)[:8]
    bars("Worst adequately supported slices","CORD test · Donut leaf F1 · axes begin at zero",[f"{r['slice_family']}:{r['slice']}" for r in worst],[float(r["value"]) for r in worst],"worst_slice_ranking.svg",1,percent=True)
    combined=worst[:6]+strongest[:6]; bars("Slice performance overview","Predeclared headline slices; absolute leaf F1",[f"{r['slice_family']}:{r['slice']}" for r in combined],[float(r["value"]) for r in combined],"slice_performance_heatmap.svg",1,[RED]*6+[TEAL]*6,True)
    fields=rows("errors/field_family_metrics.csv"); bars("Field-family exact performance","CORD locked test · Donut field-family F1",[r["field_family"] for r in fields],[float(r["f1"]) for r in fields],"field_family_performance.svg",1,percent=True)
    errors=[r for r in rows("errors/error_frequency.csv") if int(r["frequency"])>0]; bars("Error Pareto","CORD locked-test error instances; classifications are deterministic",[r["error_type"] for r in errors],[float(r["fraction"]) for r in errors],"error_pareto.svg",1,[RED,GOLD,BLUE,TEAL,NAVY],True)
    rel=rows("calibration/reliability_bins.csv"); grouped=defaultdict(list)
    for r in rel: grouped[r["method"]].append((float(r["mean_confidence"]),float(r["accuracy"])))
    grouped={"ideal":[(0,0),(1,1)],**grouped}; line_chart("Reliability diagram","Donut sequence confidence; calibration fit on development, evaluated on locked test",grouped,"reliability_diagram.svg","mean confidence","observed document exactness")
    risk=rows("selective_risk/risk_coverage_curve.csv"); grouped=defaultdict(list)
    for r in risk:
        if round(float(r["coverage"])*100)%5==0: grouped[r["policy"]].append((float(r["coverage"]),float(r["selective_risk"])))
    line_chart("Risk–coverage","CORD locked test · document exactness error among automatically accepted rows",dict(grouped),"risk_coverage_curve.svg","automation coverage","selective risk")
    budgets=rows("selective_risk/review_budget_metrics.csv"); grouped=defaultdict(list)
    for r in budgets: grouped[r["policy"]].append((float(r["automation_coverage"]),float(r["critical_false_accept_rate"])))
    line_chart("Automation vs residual critical risk","Illustrative policy frontier; lower is better",dict(grouped),"automation_residual_risk_frontier.svg","automation coverage","critical false-accept rate")
    line_chart("Critical false-accept by review budget","Critical monetary leaf error remains among auto-accepted documents",{k:[(1-x,y) for x,y in v] for k,v in grouped.items()},"critical_false_accept_review_budget.svg","review rate","critical false-accept rate")
    robust=rows("robustness/robustness_matrix.csv"); grouped=defaultdict(list); severity_x={"clean":0.0,"low":0.5,"high":1.0}
    for r in robust:
        if r["metric"]=="critical_content_presence_recall": grouped[f"{r['model']} · {r['corruption']}"] .append((severity_x[r["severity"]],float(r["value"])))
    line_chart("Controlled robustness degradation","10-document development cohort; clean, low, and high severity",dict(grouped),"robustness_degradation_curves.svg","corruption severity","critical content-presence recall")
    docs=rows("data/document_evaluation_table.csv"); dt=[r for r in docs if r["model"]=="Donut" and r["split"]=="test"]; cuts=json.loads((ROOT/"configs/v3_1/analysis_protocol.json").read_text())["cutpoint_derivation"]["values"]["ground_truth_leaf_count"]
    lat=defaultdict(list)
    for r in dt:
        n=float(r["ground_truth_leaf_count"]); band="low" if n<=cuts[0] else "mid" if n<=cuts[1] else "high"; lat[band].append(float(r["latency_seconds"]))
    bars("Latency by complexity slice","Donut locked-test inference; mean seconds",list(lat),[statistics.mean(v) for v in lat.values()],"latency_by_complexity.svg",None)
    drift=rows("drift/drift_metrics.csv"); bars("Simulated drift summary","PSI under transparent development stress simulation; not production drift",[r["feature"] for r in drift],[float(r["psi"]) for r in drift],"drift_summary.svg",None,[RED if r["alert"]=="True" else BLUE for r in drift])
    pp={r["document_id"]:r for r in docs if r["model"]=="PP-OCRv5 + rules" and r["split"]=="test"}; dis=defaultdict(list)
    for r in dt:
        if r["total_exact"]!="" and pp[r["document_id"]]["total_exact"]!="": dis[str(r["total_exact"]!=pp[r["document_id"]]["total_exact"])].append(not (r["document_exact"]=="True"))
    bars("Model disagreement vs error","Serving-compatible total disagreement; document-level Donut error rate",["agree","disagree"],[statistics.mean(dis[k]) if dis[k] else 0 for k in ("False","True")],"model_disagreement_vs_error.svg",1,percent=True)
    summary={"label":"V3.1 compact reproducible findings","strongest_headline_slices":strongest[:3],"weakest_headline_slices":worst[:3],"artifact_inputs":["slicing/slice_metrics.csv","errors/field_family_metrics.csv","errors/error_frequency.csv","calibration/reliability_bins.csv","selective_risk/risk_coverage_curve.csv","selective_risk/review_budget_metrics.csv","robustness/robustness_matrix.csv","data/document_evaluation_table.csv","drift/drift_metrics.csv"]}
    (ART/"statistics").mkdir(exist_ok=True); (ART/"statistics/summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")


if __name__=="__main__": main()
