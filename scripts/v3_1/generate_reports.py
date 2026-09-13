from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; ART=ROOT/"artifacts/v3_1"; OUT=ROOT/"reports/v3_1"


def csvrows(path: str) -> list[dict[str,str]]: return list(csv.DictReader((ART/path).open()))
def write(name: str, text: str) -> None: (OUT/name).write_text(text.strip()+"\n")
def pct(x: str|float) -> str: return f"{float(x)*100:.1f}%"


def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    slices=csvrows("slicing/slice_metrics.csv"); headline=[r for r in slices if r["metric"]=="leaf_f1" and r["designation"]=="headline"]
    weak=sorted(headline,key=lambda r:float(r["absolute_delta"]))[:3]; strong=sorted(headline,key=lambda r:float(r["absolute_delta"]),reverse=True)[:3]
    errors=csvrows("errors/error_frequency.csv"); fields=csvrows("errors/field_family_metrics.csv"); cal=json.loads((ART/"calibration/calibration_metrics.json").read_text()); budgets=csvrows("selective_risk/review_budget_metrics.csv"); robust=csvrows("robustness/robustness_matrix.csv"); drift=csvrows("drift/drift_metrics.csv"); mix=json.loads((ART/"slicing/mix_shift_analysis.json").read_text()); tree=json.loads((ART/"discovery/failure_tree.json").read_text())
    rcritical=[r for r in robust if r["metric"]=="critical_content_presence_recall" and r["corruption"]!="clean"]
    worst_rob=min(rcritical,key=lambda r:float(r["absolute_delta"])); best_budget=min(budgets,key=lambda r:float(r["normalized_expected_cost"])); raw50=next(r for r in budgets if r["policy"]=="raw_confidence" and r["review_budget"]=="0.5")
    sig_adverse=[r for r in headline if r["statistical_significance"]=="True" and r["practical_significance"]=="True" and float(r["absolute_delta"])<0]
    sig_sentence=("FDR-significant and practically adverse cohorts are " + ", ".join(f"`{r['slice_family']}={r['slice']}` (q={float(r['q_value']):.4f})" for r in sig_adverse) + ".") if sig_adverse else "No adverse headline cohort remains both FDR-significant and practically meaningful after correction."
    slice_lines="\n".join(f"- `{r['slice_family']}={r['slice']}`: N={r['support_n']}, F1={float(r['value']):.4f}, delta={float(r['absolute_delta']):+.4f}, 95% CI [{float(r['ci95_low']):.4f}, {float(r['ci95_high']):.4f}], q={float(r['q_value']):.4f}." for r in weak+strong)
    write("DESKTOP_STUDY.md",f"""# V3.1 desktop study

This extension analyzes frozen V2/V3 predictions and one controlled CORD development robustness cohort. It changes no model weights and makes no production-deployment claim. Experiments ran locally on one NVIDIA GeForce RTX 4090 Laptop GPU; CPU work was limited to preprocessing, statistics, plotting, and orchestration.

CORD v2 and FUNSD use their already authorized frozen local revisions. [Official XFUND](https://github.com/doc-analysis/XFUND) is CC BY-NC-SA 4.0 and supports multilingual semantic-entity/relation tasks; it was assessed but not downloaded or forced into incompatible CORD receipt metrics. [SROIE](https://rrc.cvc.uab.es/?ch=13) requires RRC registration, and [DocILE](https://docile.rossum.ai/) requires an official research access request. No authorized local copy of either was present; both remain `HUMAN_ACTION_REQUIRED` and neither blocks this analysis.
""")
    write("DATA_AND_SLICE_DEFINITION.md",f"""# Data and slice definition

The canonical tables contain 340 document/model rows and 2,645 Donut field rows. Locked inference was not rerun. Predictions, latency, model confidence, truth and manifests come from frozen committed evidence; reproducible image descriptors come from authorized local CORD images. Provenance hashes are in `artifacts/v3_1/data/provenance.json`.

All cut points were derived from the 100-document CORD validation split and committed in `configs/v3_1/analysis_protocol.json` before locked slice results were inspected. Headline support is N>=20; N=10–19 is exploratory; lower support is only marked insufficient. Paired comparisons retain document IDs. V1/V2/V3 outcomes are immutable.

Critical monetary fields include total, subtotal, tax, discount and item price. Medium-impact and descriptive mappings are explicit in the protocol. Missing features are blank, never invented or imputed.
""")
    write("SLICING_ANALYSIS.md",f"""# Slicing analysis

Overall Donut locked-test document-average leaf F1 is {float(weak[0]['overall_reference']):.4f}. The strongest and weakest adequately supported predeclared cohorts are reported together:

{slice_lines}

After Benjamini–Hochberg correction, {sig_sentence} Practical flags follow the frozen absolute 0.05 F1 threshold.

The paired eligible total-exact comparison is Donut {mix['raw_performance']['Donut']:.4f} versus PP-OCRv5+rules {mix['raw_performance']['PP-OCRv5 + rules']:.4f}. Standardization leaves the ranking unchanged; `ranking_reversal={str(mix['ranking_reversal']).lower()}`. Because both models use the same 95 eligible IDs, the overall conclusion is not a slice-composition artifact in this analysis.
""")
    write("ERROR_ANALYSIS.md",f"""# Error analysis

The leading deterministic test error categories are {errors[0]['error_type']} ({errors[0]['frequency']} instances), {errors[1]['error_type']} ({errors[1]['frequency']}), and {errors[2]['error_type']} ({errors[2]['frequency']}). Numeric-normalization errors remain separate from substantive value errors. Ambiguous errors may remain `UNCLASSIFIED`; no category is forced.

The weakest field-family F1 is `{min(fields,key=lambda r:float(r['f1']))['field_family']}` at {float(min(fields,key=lambda r:float(r['f1']))['f1']):.4f}; item-name and item-price errors dominate more business-relevant repeated structures. Representative evidence publishes document IDs and normalized values, not raw document images.

The image-only exploratory depth-3 tree achieved mean five-fold balanced accuracy {tree['cross_validation_balanced_accuracy_mean']:.4f}. Its readable quality/layout rules are retained in the evidence artifact, but every rule is labeled `EXPLORATORY_DISCOVERED_SLICE` and is not a confirmatory finding. Annotated token/box counts and target-derived structure were excluded from discovery.
""")
    write("CALIBRATION_AND_SELECTIVE_RISK.md",f"""# Calibration and selective risk

Donut exposes genuine sequence probability. On the untouched 100-document CORD test set, raw ECE is {cal['metrics']['raw']['ece']:.4f} and Brier score {cal['metrics']['raw']['brier']:.4f}. Development-fitted isotonic calibration improves these to ECE {cal['metrics']['isotonic']['ece']:.4f} and Brier {cal['metrics']['isotonic']['brier']:.4f}; temperature scaling reaches ECE {cal['metrics']['temperature_scaling']['ece']:.4f}, with the selected temperature at the predeclared search boundary ({cal['temperature']:.1f}), indicating severe overconfidence rather than a settled parametric calibration fit. Critical-total calibration has insufficient outcome variation and is explicitly not interpreted.

Calibration improves probability quality but does not improve ranking enough to beat raw-confidence selective routing. At 50% review, raw confidence leaves {pct(raw50['critical_false_accept_rate'])} critical false accepts among auto-accepted documents and captures {pct(raw50['critical_error_capture'])} of critical-error documents. No studied policy achieves a genuinely low residual critical risk, so the evidence does not support unattended high-coverage automation. Under the frozen illustrative cost model, the lowest measured point is `{best_budget['policy']}` at {pct(best_budget['review_budget'])} review, not an institution-specific recommendation.
""")
    write("ROBUSTNESS_ANALYSIS.md",f"""# Controlled robustness analysis

Ten development receipts were selected deterministically across frozen complexity bands from the same 20-document frame supported by prior PaddleOCR-VL evidence. Donut and PaddleOCR-VL Docker/vLLM processed identical clean and corrupted images: Gaussian blur, rotation, downsampling, JPEG compression, contrast reduction and partial occlusion at two frozen severities. One heavy GPU job ran at a time; no CPU fallback was used.

The largest measured critical-content degradation is `{worst_rob['model']}` under `{worst_rob['corruption']}` `{worst_rob['severity']}`: {float(worst_rob['absolute_delta']):+.4f} from its clean development reference. These content-presence metrics are not official structured CORD F1. With N=10, robustness comparisons are descriptive development evidence, not locked-final model claims.
""")
    alerts=[r for r in drift if r['alert']=='True']
    write("DRIFT_MONITORING_SIMULATION.md",f"""# Drift monitoring simulation

This is simulated stress-test drift, not observed bank production drift. A clean validation reference is compared with a transparently selected lower-blur/higher-complexity cohort. Alerts fired for {', '.join(f"`{r['feature']}` (PSI {float(r['psi']):.3f}, SMD {float(r['standardized_mean_difference']):+.3f})" for r in alerts)}.

Production-style monitoring should track blur, contrast, skew, resolution, token and line-item counts, aspect ratio, genuine confidence/risk, review route and latency. Alerts should trigger investigation and cohort-level evaluation, not automatic claims of model failure.
""")
    write("BUSINESS_POLICY_ANALYSIS.md",f"""# Business-policy analysis

All costs are transparent normalized examples—not JPMorgan, bank, or deployment costs. The protocol assigns review=1, low-impact error=2, medium-impact error=5, critical-field error=10 and unsafe automatic acceptance=25, with sensitivity scenarios.

Within the evaluated budgets, illustrative expected cost falls as review increases because critical errors dominate. The minimum measured base point is `{best_budget['policy']}` with {pct(best_budget['review_budget'])} review and normalized expected cost {float(best_budget['normalized_expected_cost']):.3f}. Even that point retains material critical false-accept risk, so R-FDI routing has value as prioritization but does not justify autonomous acceptance for this broad critical-field definition. Institutions must replace these weights and set limits before use.
""")
    write("FINAL_ANALYSIS_REPORT.md",f"""# R-FDI v3.1 final analysis report

V3.1 adds an evidence-governed analysis layer without changing model weights or historical outcomes. The canonical table, predeclared slicing, field/error taxonomy, 2,000-replicate uncertainty, paired analysis, calibration, selective risk, controlled GPU robustness, exploratory discovery, simulated drift, policy sensitivity and generated figures are traceable through `V3_1_EVIDENCE_MANIFEST.jsonl`.

## Main findings

{slice_lines}

Raw confidence is severely overconfident; development-fit isotonic calibration improves ECE from {cal['metrics']['raw']['ece']:.4f} to {cal['metrics']['isotonic']['ece']:.4f}, but selective ordering does not beat raw confidence. At 50% review, the best raw-confidence evidence still has {pct(raw50['critical_false_accept_rate'])} critical false-accept rate among accepted documents. The principal robustness bottleneck is {worst_rob['corruption']} ({worst_rob['severity']}) for {worst_rob['model']}. The paired model ranking does not reverse after slice standardization.

## Scope

Results use public research datasets, frozen predictions and a development-only corruption cohort. They are not a live production deployment, regulatory certification, or multi-GPU study. Paddle content presence is not structured CORD F1. SROIE and DocILE remain optional human-access blockers.
""")
    write("EXECUTIVE_FINDINGS.md",f"""# Executive findings

- **Best conditions:** the strongest adequately supported cohorts are {', '.join(f"{r['slice_family']}={r['slice']} (F1 {float(r['value']):.3f})" for r in strong)}.
- **Worst conditions:** {', '.join(f"{r['slice_family']}={r['slice']} (F1 {float(r['value']):.3f})" for r in weak)}. {sig_sentence}
- **Failure predictors:** higher token/text density and complexity are the clearest predeclared retrospective signals; the separate image-only shallow tree is exploratory, with CV balanced accuracy {tree['cross_validation_balanced_accuracy_mean']:.3f}.
- **Business risk:** repeated monetary item prices make critical-field risk much broader than receipt-total accuracy. Incorrect, missing and spurious values are the most frequent error modes.
- **Confidence:** genuine Donut confidence predicts correctness poorly in raw probability space. Isotonic calibration improves ECE, but calibration alone does not create better selective ranking.
- **Review:** no tested policy reaches low critical residual risk. The least-cost frozen illustrative point uses {pct(best_budget['review_budget'])} review; this is evidence for conservative human review, not a deployment threshold.
- **Robustness:** the largest development degradation is {worst_rob['corruption']} {worst_rob['severity']} for {worst_rob['model']} ({float(worst_rob['absolute_delta']):+.3f}).
- **Latency:** latency should be monitored by document complexity; this study reports cohort means and corruption interactions without claiming a causal production effect.
- **Mix shift:** no ranking reversal occurs under the shared complexity distribution; the paired total-exact conclusion is not driven by composition here.
- **Monitor next:** blur, megapixels/resolution, complexity, genuine confidence/risk, route rates and latency. Fix field alignment/normalization and build routing signals that rank critical errors better.
""")


if __name__=="__main__": main()
