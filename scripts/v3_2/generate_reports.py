from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/v3_2"
OUT.mkdir(parents=True, exist_ok=True)


def table(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(newline="") as handle:
        return list(csv.DictReader(handle))


line_dev = json.loads((ROOT / "artifacts/v3_2/line_items/development/aggregate_metrics.json").read_text())
line_test = json.loads((ROOT / "artifacts/v3_2/line_items/retrospective_test/aggregate_metrics.json").read_text())
selection = json.loads((ROOT / "artifacts/v3_2/risk_model/development_selection/frozen_selection.json").read_text())
evaluation = json.loads((ROOT / "artifacts/v3_2/risk_control/evaluation_summary.json").read_text())
bootstrap = json.loads((ROOT / "artifacts/v3_2/risk_control/retrospective_bootstrap_delta.json").read_text())
calibration = json.loads((ROOT / "artifacts/v3_2/risk_control/retrospective_calibration.json").read_text())
latency = json.loads((ROOT / "artifacts/v3_2/risk_control/latency_risk_joint.json").read_text())
metrics = {row["candidate"]: row for row in table("artifacts/v3_2/risk_control/retrospective_candidate_metrics.csv")}
budgets = table("artifacts/v3_2/risk_control/retrospective_review_budgets.csv")
certificates = table("artifacts/v3_2/risk_control/certification_results.csv")
slices = [row for row in table("artifacts/v3_2/line_item_slicing/line_item_slices.csv") if int(row["support_n"]) >= 20 and row["critical_error_rate"] != "nan"]
worst = sorted(slices, key=lambda row: float(row["critical_error_rate"]), reverse=True)
best = sorted(slices, key=lambda row: float(row["critical_error_rate"]))
pareto = table("artifacts/v3_2/line_item_slicing/line_item_error_pareto.csv")
robustness = table("artifacts/v3_2/robustness/robustness_risk_response_summary.csv")
importance = table("artifacts/v3_2/risk_model/development_selection/feature_importance.csv")
composition = table("artifacts/v3_2/risk_control/critical_target_composition.csv")


def write(name: str, text: str) -> None:
    (OUT / name).write_text(text.strip() + "\n")


def budget(candidate: str, value: str) -> dict[str, str]:
    return next(row for row in budgets if row["candidate"] == candidate and row["review_budget"] == value)


def slice_lines(rows: list[dict[str, str]]) -> str:
    return "\n".join(f"- `{r['slice_family']}:{r['slice']}` — N={r['support_n']}, critical error {float(r['critical_error_rate']):.1%}, E2 F1 {float(r['mean_E2_line_item_f1']):.4f}." for r in rows[:3])


write("DESIGN_AND_PROTOCOL.md", f"""
# Design and protocol

The v3.2 protocol was frozen at commit `239824f` before new v3.2 results and the development candidate/threshold checkpoint was committed at `3532686` before certification or retrospective test evaluation. CORD test is a `RETROSPECTIVE_LOCKED_BENCHMARK`, not a fresh untouched holdout. Extractor weights were unchanged.

The primary target is any supported critical monetary error; secondary targets are line-item monetary errors, row alignment errors, and bounded weighted critical loss. Only `PRE_INFERENCE`, `CHEAP_PREFLIGHT`, and `POST_EXTRACTION` features are eligible. All source-document variants are grouped. Candidate selection uses five-fold grouped CV, AURC, fixed grids, 2,000 document bootstrap replicates, and the frozen review/certification budgets in [`risk_protocol.json`](../../configs/v3_2/risk_protocol.json).

Promotion is shadow-only and requires every frozen gate. No autonomous-action promotion is permitted.
""")

write("ROW_AWARE_LINE_ITEM_EVALUATION.md", f"""
# Row-aware line-item evaluation

E0 reproduces historical flat occurrence matching. E1 preserves strict row order. E2, the primary metric, uses maximum-weight bipartite line-item matching and does not require row identifiers to match numerically. Ten synthetic unit cases cover perfect, reordered, duplicated, missing, spurious, cross-row, split-menu, and repeated-value behavior.

| Benchmark | E0 flat F1 | E2 line-item F1 | Field-within-row F1 | Row exact | Alignment failure |
|---|---:|---:|---:|---:|---:|
| Development | {line_dev['document_mean_metrics']['E0_historical_flat_f1']:.4f} | {line_dev['document_mean_metrics']['E2_line_item_f1']:.4f} | {line_dev['document_mean_metrics']['field_within_row_micro_f1']:.4f} | {line_dev['document_mean_metrics']['row_exact_match_rate']:.4f} | {line_dev['row_alignment_failure_rate']:.1%} |
| Retrospective CORD test | {line_test['document_mean_metrics']['E0_historical_flat_f1']:.4f} | {line_test['document_mean_metrics']['E2_line_item_f1']:.4f} | {line_test['document_mean_metrics']['field_within_row_micro_f1']:.4f} | {line_test['document_mean_metrics']['row_exact_match_rate']:.4f} | {line_test['row_alignment_failure_rate']:.1%} |

E2 raises the perceived test F1 by {line_test['document_mean_metrics']['E2_line_item_f1']-line_test['document_mean_metrics']['E0_historical_flat_f1']:+.4f} because it correctly treats harmless row permutations as equivalent. That does not erase structure failures: 10% of test documents have alignment failures, row exact match is 60.23%, with {line_test['unmatched_gt_rows']} unmatched GT and {line_test['spurious_predicted_rows']} spurious predicted rows.

![Row matching](../../docs/assets/v3_2/historical_vs_row_aware.svg)
""")

write("CRITICAL_RISK_MODEL.md", f"""
# Critical risk model

R4 shallow gradient boosting is the best learned candidate, selected strictly from development data. Its grouped-CV AURC is {selection['selected_AURC']:.4f}, versus {selection['baseline_R0_AURC']:.4f} for R0: relative improvement {selection['relative_AURC_reduction']:.1%} (negative means worse). The 95% document-bootstrap interval for absolute reduction is [{selection['document_group_bootstrap']['absolute_AURC_reduction_ci95'][0]:.4f}, {selection['document_group_bootstrap']['absolute_AURC_reduction_ci95'][1]:.4f}].

On retrospective CORD test, R0 AURC/PR-AUC/AUROC are {float(metrics['R0_raw_confidence']['AURC']):.4f}/{float(metrics['R0_raw_confidence']['PR_AUC']):.4f}/{float(metrics['R0_raw_confidence']['AUROC']):.4f}; R4 gives {float(metrics['R4_best_learned']['AURC']):.4f}/{float(metrics['R4_best_learned']['PR_AUC']):.4f}/{float(metrics['R4_best_learned']['AUROC']):.4f}. The retrospective R0−R4 AURC reduction is {bootstrap['absolute_AURC_reduction']:.4f}, 95% CI [{bootstrap['absolute_AURC_reduction_ci95'][0]:.4f}, {bootstrap['absolute_AURC_reduction_ci95'][1]:.4f}].

Top nonzero production-safe R4 importances are {', '.join(f"`{r['feature']}` ({float(r['importance']):.3f})" for r in importance[:5])}. They describe the fitted model, not causal effects. The learned combination did not rank failures better than raw confidence.
""")

write("SELECTIVE_AUTOMATION.md", f"""
# Selective automation

At 50% review, R0 captures {float(budget('R0_raw_confidence','0.5')['critical_error_capture']):.1%} of critical errors and leaves {float(budget('R0_raw_confidence','0.5')['critical_false_accept_rate']):.1%} critical risk among accepted documents. R4 captures {float(budget('R4_best_learned','0.5')['critical_error_capture']):.1%} and leaves {float(budget('R4_best_learned','0.5')['critical_false_accept_rate']):.1%}. Neither satisfies the frozen operating gate at or below 50% review.

Even R0 at 80% review retains {float(budget('R0_raw_confidence','0.8')['critical_false_accept_rate']):.1%} critical false-accept risk while capturing {float(budget('R0_raw_confidence','0.8')['critical_error_capture']):.1%}. Therefore v3.2 does not recommend an automatic-accept threshold. The normalized-cost column reuses illustrative v3.1 weights (review=1; unsafe critical acceptance=25), not institutional costs.

![Risk coverage](../../docs/assets/v3_2/risk_coverage_curve.svg)
""")

write("RISK_CERTIFICATION.md", """
# Finite-sample risk certification

Thresholds were selected before opening the 20-document independent certification partition. Results use a one-sided exact 95% Clopper–Pearson upper bound for binary loss and a one-sided empirical-Bernstein bound for bounded weighted loss. These are research certificates conditional on source-document exchangeability and an unchanged pipeline, not regulatory guarantees.

| Target | Accepted | Coverage | Observed risk | Binary upper 95% | Status |
|---:|---:|---:|---:|---:|---|
""" + "\n".join(f"| {float(r['target_risk']):.0%} | {r['accepted_n']} | {float(r['coverage']):.1%} | {float(r['observed_binary_risk']):.1%} | {float(r['binary_upper_bound_95']):.1%} | `{r['status']}` |" for r in certificates) + "\n\nNo automatic-accept region is certified. The 5% target also has insufficient accepted support (N=9).\n")

worst_robust = min(robustness, key=lambda row: float(row["mean_leaf_f1"]))
write("ROBUSTNESS_AND_SHIFT.md", f"""
# Robustness and shift

No GPU inference was rerun: v3.1's frozen 10-document development corruption cohort was reused. To test feature response without inventing extractor outputs, corrupted image descriptors were varied while each document's frozen clean post-extraction features were held fixed. This is a limited risk-sensitivity diagnostic, not a fresh end-to-end robustness benchmark.

High occlusion is the extraction bottleneck (mean leaf F1 {float(worst_robust['mean_leaf_f1']):.4f}); R4 risk rises only {float(worst_robust['mean_risk_increase_from_clean']):+.4f} from clean and its proxy-error AUROC is {float(worst_robust['AUROC']):.4f}, with {worst_robust['false_negative_critical_errors_below_median_risk']} critical proxy errors at or below median risk. Risk response is inconsistent across corruptions, reinforcing no-promotion.

Fresh external LIR evidence remains absent. [DocILE's official toolkit](https://github.com/rossumai/docile) requires an access token and is `HUMAN_ACTION_REQUIRED_OPTIONAL`. WildReceipt was assessed only as KIE/domain shift and was not forced into incompatible CORD line-item metrics.
""")

write("SHADOW_RUNTIME.md", """
# Shadow runtime

Decision: `V3_2_RISK_MODEL_NO_PROMOTION`.

The frozen gates permit runtime integration only after promotion. Because R4 failed development AURC, practical-improvement, and operating gates, the existing V3 runtime and action semantics remain unchanged. The candidate is available only through offline compact evidence; it is not exposed by the API and no MLflow run overwrites V3 or v3.1 history.
""")

write("FINAL_REPORT.md", f"""
# R-FDI v3.2 final report

## Outcome

`V3_2_RISK_MODEL_NO_PROMOTION`. Extractor weights did not change, and CORD test is retrospective—not a fresh holdout.

## Answers

- **How did row awareness change perceived error?** Test E0 F1 {line_test['document_mean_metrics']['E0_historical_flat_f1']:.4f} becomes E2 {line_test['document_mean_metrics']['E2_line_item_f1']:.4f} ({line_test['document_mean_metrics']['E2_line_item_f1']-line_test['document_mean_metrics']['E0_historical_flat_f1']:+.4f}), while row exact match remains {line_test['document_mean_metrics']['row_exact_match_rate']:.1%}.
- **Which errors dominate?** {pareto[0]['error_mode']} affects {float(pareto[0]['prevalence']):.1%}; line-item critical errors affect {float(pareto[1]['prevalence']):.1%}; correct-total/wrong-item-price cases affect {float(pareto[2]['prevalence']):.1%}.
- **Which features rank failures?** {', '.join(r['feature'] for r in importance[:5])}; nevertheless, R4 ranking is inferior to R0.
- **Does learned risk beat raw confidence?** No: retrospective AURC {float(metrics['R4_best_learned']['AURC']):.4f} versus {float(metrics['R0_raw_confidence']['AURC']):.4f}.
- **Does calibration help?** Uncalibrated R4 has Brier {calibration['uncalibrated']['Brier']:.4f}/ECE {calibration['uncalibrated']['ECE']:.4f}. Platt and isotonic worsen retrospective Brier/ECE; calibration does not repair ranking.
- **What review budget is needed?** No budget through 50% passes the operating gate; even 80% review leaves 15% accepted critical risk for R0.
- **Is auto-accept certifiable?** No; 5% is support-insufficient, 10% and 20% are uncertified.
- **Does corruption raise risk?** Only weakly and inconsistently under the pre-inference-only response test; high occlusion adds {float(worst_robust['mean_risk_increase_from_clean']):+.4f} mean risk despite major degradation.
- **Can it enter shadow mode?** No under the frozen gate.
- **What fresh evidence is missing?** Authorized DocILE LIR validation and a larger grouped development/certification set with end-to-end corrupted extraction outputs.

## Slices

Strongest adequately supported cohorts:

{slice_lines(best)}

Weakest adequately supported cohorts:

{slice_lines(worst)}

Latency correlates moderately with predicted line-item count (r={latency['pearson_latency_vs_predicted_line_item_count']:.3f}) but weakly with learned risk (r={latency['pearson_latency_vs_R4_risk']:.3f}); p95 is {latency['latency_p95_seconds']:.3f}s.
""")

write("EXECUTIVE_FINDINGS.md", f"""
# Executive findings

R-FDI v3.2 improves the *measurement* of receipt line items but does not produce a promotable risk controller. Permutation-invariant E2 test F1 is {line_test['document_mean_metrics']['E2_line_item_f1']:.4f}, yet only {line_test['document_mean_metrics']['row_exact_match_rate']:.1%} of rows are exact and critical monetary errors affect {evaluation['critical_error_prevalence']:.1%} of retrospective test documents.

Raw confidence remains the strongest evaluated ranker (AURC {float(metrics['R0_raw_confidence']['AURC']):.4f}, PR-AUC {float(metrics['R0_raw_confidence']['PR_AUC']):.4f}, AUROC {float(metrics['R0_raw_confidence']['AUROC']):.4f}). Learned R4 is worse (AURC {float(metrics['R4_best_learned']['AURC']):.4f}) and no 5/10/20% target is certified. The correct action is `V3_2_RISK_MODEL_NO_PROMOTION`: preserve the candidate offline, keep runtime semantics unchanged, and collect larger, genuinely external line-item evidence before another promotion attempt.

The clearest next fixes are line-item association, wrong item prices despite a correct total, and risk features sensitive to extraction degradation rather than appearance alone.
""")

print(json.dumps({"reports": len(list(OUT.glob("*.md"))), "decision": "V3_2_RISK_MODEL_NO_PROMOTION"}, sort_keys=True))
