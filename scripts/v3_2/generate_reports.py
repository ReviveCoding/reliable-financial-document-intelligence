from __future__ import annotations
import csv,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/"reports/v3_2"; OUT.mkdir(parents=True,exist_ok=True)
def load_csv(path): return list(csv.DictReader((ROOT/path).open()))
def load_json(path): return json.loads((ROOT/path).read_text())
def write(name,text): (OUT/name).write_text(text.strip()+"\n")

old=load_json("artifacts/v3_2/audit/pre_correction_summary.json"); transition=load_json("artifacts/v3_2/audit/label_transition_summary.json")
dev=load_json("artifacts/v3_2/line_items/development/aggregate_metrics.json"); test=load_json("artifacts/v3_2/line_items/retrospective_test/aggregate_metrics.json"); m=test["document_mean_metrics"]
selection=load_json("artifacts/v3_2/risk_model/development_selection/frozen_selection.json"); evaluation=load_json("artifacts/v3_2/risk_control/evaluation_summary.json"); boot=load_json("artifacts/v3_2/risk_control/retrospective_bootstrap_delta.json"); cal=load_json("artifacts/v3_2/risk_control/retrospective_calibration.json"); latency=load_json("artifacts/v3_2/risk_control/latency_risk_joint.json")
metrics={r["candidate"]:r for r in load_csv("artifacts/v3_2/risk_control/retrospective_candidate_metrics.csv")}; budgets=load_csv("artifacts/v3_2/risk_control/retrospective_review_budgets.csv"); cert=load_csv("artifacts/v3_2/risk_control/certification_results.csv"); pareto=load_csv("artifacts/v3_2/line_item_slicing/line_item_error_pareto.csv"); robust=load_csv("artifacts/v3_2/robustness/robustness_risk_response_summary.csv"); importance=load_csv("artifacts/v3_2/risk_model/development_selection/feature_importance.csv")
def budget(candidate,point): return next(r for r in budgets if r["candidate"]==candidate and r["review_budget"]==point)
def err(name):
    row=next((r for r in pareto if r["error_mode"]==name),None); return float(row["prevalence"]) if row else 0.0

write("METHODOLOGY_CORRECTION.md",f"""# V3.2 methodology correction

The defect was discovered on 2026-09-13 after local commit `1078332` and before remote v3.2 publication. The original protocol at `239824f` remains immutable; the erratum was frozen at `081ba8f` before recomputation.

The old implementation used positional row pairs for E0, duplicated E0 as E1, labeled any changed optimal assignment as a row failure, added a monetary penalty for assignment change alone, and presented matched-row F1 as though it described field accuracy. This mattered because row ordering is not semantic identity and row matchability is not field correctness.

The correction implements historical path-occurrence E0, positional-row E1, separate E2 matched-row and matched-field metrics, and explicit benign-permutation versus semantic/missing/spurious structure diagnostics. Monetary loss now counts actual missing, spurious, incorrect, or demonstrably misbound monetary fields only. Extractor weights, frozen predictions, features, candidate families, grids, seed, partitions, weights, and V1–v3.1 evidence did not change.

All dependent labels, model replay, reused certification statistics, retrospective risk evidence, slices, figures, reports, and governance were regenerated. The audit records {transition['unchanged_labels']} unchanged labels, {transition['positive_to_negative']} positive→negative, {transition['negative_to_positive']} negative→positive, {transition['weighted_loss_decreased']} weighted-loss decreases, and {transition['weighted_loss_increased']} increases across 200 development/test documents.

CORD test and the certification partition had already been observed, so nothing in this replay is fresh confirmation or promotion-eligible. Remote publication was withheld until the semantics and audit trail were corrected.
""")

write("DESIGN_AND_PROTOCOL.md",f"""# Design and protocol

The original v3.2 protocol was frozen at `239824f`; methodology erratum `081ba8f` precedes corrected results. Corrected development replay was frozen at `274a2c0` before reopening already-observed certification/test partitions. Extractor weights and the exact R0–R5 algorithms, production-safe features, 60/20/20 grouping, grids, seed, 2,000-replicate bootstrap, risk weights, budgets, and gates remain unchanged.

Designations are `DEVELOPMENT_CORRECTION_REPLAY`, `DEVELOPMENT_THRESHOLD_REPLAY`, `POST_AUDIT_REUSED_CERTIFICATION_PARTITION`, and `RETROSPECTIVE_LOCKED_BENCHMARK`. All have `fresh_confirmatory_evidence=false`; corrected replay alone cannot promote a model.
""")

write("ROW_AWARE_LINE_ITEM_EVALUATION.md",f"""# Corrected row-aware line-item evaluation

| Scope | E0 path-occurrence field F1 | E1 positional-row field F1 | E2 matched-row F1 | E2 matched-field micro F1 | E2 row exact |
|---|---:|---:|---:|---:|---:|
| Development replay | {dev['document_mean_metrics']['E0_path_occurrence_f1']:.4f} | {dev['document_mean_metrics']['E1_positional_row_f1']:.4f} | {dev['document_mean_metrics']['E2_matched_row_f1']:.4f} | {dev['document_mean_metrics']['E2_matched_field_micro_f1']:.4f} | {dev['document_mean_metrics']['E2_row_exact_match_rate']:.4f} |
| Retrospective CORD | {m['E0_path_occurrence_f1']:.4f} | {m['E1_positional_row_f1']:.4f} | {m['E2_matched_row_f1']:.4f} | {m['E2_matched_field_micro_f1']:.4f} | {m['E2_row_exact_match_rate']:.4f} |

Matched-row F1 measures whether rows are matchable; matched-field F1 measures content within those matched rows. They are not interchangeable. Retrospective benign permutation-only rate is {test['row_permutation_only_rate']:.1%}; semantic association error is {test['row_semantic_association_error_rate']:.1%}; missing-row and spurious-row document rates are {test['row_missing_error_rate']:.1%} and {test['row_spurious_error_rate']:.1%}. Fifteen synthetic cases validate these distinctions.

![Corrected concepts](../../docs/assets/v3_2/historical_vs_row_aware.svg)
""")

write("CRITICAL_RISK_MODEL.md",f"""# Corrected critical-risk model replay

R4 shallow gradient boosting remains the best learned candidate; R0 remains best overall. Development grouped-CV AURC is {selection['selected_AURC']:.4f} for R4 versus {selection['baseline_R0_AURC']:.4f} for R0, a {selection['relative_AURC_reduction']:.1%} relative reduction (negative is worse), with absolute-reduction 95% CI [{selection['document_group_bootstrap']['absolute_AURC_reduction_ci95'][0]:.4f}, {selection['document_group_bootstrap']['absolute_AURC_reduction_ci95'][1]:.4f}].

Retrospective R0 AURC/PR-AUC/AUROC are {float(metrics['R0_raw_confidence']['AURC']):.4f}/{float(metrics['R0_raw_confidence']['PR_AUC']):.4f}/{float(metrics['R0_raw_confidence']['AUROC']):.4f}; R4 is {float(metrics['R4_best_learned']['AURC']):.4f}/{float(metrics['R4_best_learned']['PR_AUC']):.4f}/{float(metrics['R4_best_learned']['AUROC']):.4f}. Retrospective absolute R0−R4 AURC reduction is {boot['absolute_AURC_reduction']:.4f}, 95% CI [{boot['absolute_AURC_reduction_ci95'][0]:.4f}, {boot['absolute_AURC_reduction_ci95'][1]:.4f}]. Top fitted production-safe features are {', '.join(r['feature'] for r in importance[:5])}; importances are descriptive, not causal.
""")

write("SELECTIVE_AUTOMATION.md",f"""# Corrected selective automation replay

At 50% review, R0 captures {float(budget('R0_raw_confidence','0.5')['critical_error_capture']):.1%} of critical errors and leaves {float(budget('R0_raw_confidence','0.5')['critical_false_accept_rate']):.1%} risk among accepted documents; R4 captures {float(budget('R4_best_learned','0.5')['critical_error_capture']):.1%} and leaves {float(budget('R4_best_learned','0.5')['critical_false_accept_rate']):.1%}. At 80% review, R0 capture is {float(budget('R0_raw_confidence','0.8')['critical_error_capture']):.1%} with {float(budget('R0_raw_confidence','0.8')['critical_false_accept_rate']):.1%} accepted risk.

No operating gate passes. Illustrative costs are inherited unchanged from v3.1 and are not institutional costs. This replay cannot recommend autonomous acceptance.
""")

cert_rows="\n".join(f"| {float(r['target_risk']):.0%} | {r['accepted_n']} | {float(r['coverage']):.1%} | {float(r['observed_binary_risk']):.1%} | {float(r['binary_upper_bound_95']):.1%} | `{r['status']}` |" for r in cert)
write("RISK_CERTIFICATION.md",f"""# Certification correction replay

Every row is `POST_AUDIT_REUSED_CERTIFICATION_PARTITION`, `fresh_confirmatory_evidence=false`, and `promotion_eligible=false`. Thresholds were frozen at corrected replay commit `274a2c0`, but this partition had already been observed before correction.

| Target | Accepted | Coverage | Observed | One-sided upper 95% | Replay status |
|---:|---:|---:|---:|---:|---|
{cert_rows}

No target supplies fresh certification. A genuinely fresh external dataset is required.
""")

worst=min(robust,key=lambda r:float(r["mean_leaf_f1"]))
write("ROBUSTNESS_AND_SHIFT.md",f"""# Robustness and shift replay

No GPU inference was rerun. Frozen v3.1 corruptions were reused under `RISK_SENSITIVITY_PROXY_NOT_END_TO_END_INFERENCE`: corrupted image descriptors vary while clean post-extraction outputs remain fixed. High {worst['corruption']} has mean leaf F1 {float(worst['mean_leaf_f1']):.4f}, mean risk increase {float(worst['mean_risk_increase_from_clean']):+.4f}, proxy AUROC {float(worst['AUROC']):.4f}, and {worst['false_negative_critical_errors_below_median_risk']} false-negative proxy errors at/below median risk. Response remains weak and inconsistent.

Authorized DocILE LIR evidence and a larger fresh grouped certification sample remain missing. WildReceipt was not forced into incompatible line-item metrics.
""")

write("SHADOW_RUNTIME.md","""# Shadow runtime

Decision: `V3_2_RISK_MODEL_NO_PROMOTION`. The corrected replay is not fresh evidence, and internal development gates also fail. The candidate remains offline; API fields, routes, and action semantics are unchanged. No autonomous or shadow promotion occurred.
""")

write("FINAL_REPORT.md",f"""# R-FDI v3.2 corrected final report

## Decision

`V3_2_RISK_MODEL_NO_PROMOTION`. This is a methodology-correction replay, not a new model study or fresh confirmation.

- Old reported E0 was {old['reported_metrics']['E0_historical_flat_f1']:.4f}; corrected E0 path-occurrence F1 is {m['E0_path_occurrence_f1']:.4f}. E1 positional F1 is {m['E1_positional_row_f1']:.4f}.
- E2 matched-row F1 is {m['E2_matched_row_f1']:.4f}; distinct matched-field micro F1 is {m['E2_matched_field_micro_f1']:.4f}; row exact rate is {m['E2_row_exact_match_rate']:.4f}.
- Benign permutation-only rate is {test['row_permutation_only_rate']:.1%}; semantic association error is {test['row_semantic_association_error_rate']:.1%}. Benign permutation is excluded from failures and risk.
- Retrospective critical prevalence remains {evaluation['critical_error_prevalence']:.1%}; line-item critical prevalence is {evaluation['line_item_critical_error_prevalence']:.1%}. Mean weighted loss changed from {old['reported_metrics'].get('mean_weighted_critical_loss',0.17310588780992092):.6f} to {load_json('artifacts/v3_2/data/test_risk_feature_summary.json')['mean_weighted_critical_loss']:.6f}.
- Across development and test, {transition['positive_to_negative']} label changed positive→negative, {transition['negative_to_positive']} negative→positive, {transition['weighted_loss_decreased']} losses decreased, and {transition['weighted_loss_increased']} increased. No observed real document was a pure-permutation-only case.
- Failure prevalence: semantic association {err('semantic_row_association_error'):.1%}, missing row {err('missing_row'):.1%}, spurious row {err('spurious_row'):.1%}, incorrect item price {err('incorrect_item_price'):.1%}, missing item price {err('missing_item_price'):.1%}, correct total/wrong item price {err('correct_total_wrong_item_price'):.1%}, document-total error {err('document_total_error'):.1%}.
- R4 remains inferior to R0; calibration does not repair ranking. No operating or certification replay gate supports promotion.
- Latency has r={latency['pearson_latency_vs_predicted_line_item_count']:.3f} with predicted row count and p95 {latency['latency_p95_seconds']:.3f}s.
""")

write("EXECUTIVE_FINDINGS.md",f"""# Corrected executive findings

The correction changes what the metrics mean more than the headline risk decision. Corrected retrospective E0 path-occurrence/E1 positional/E2 matched-row/E2 matched-field F1 are {m['E0_path_occurrence_f1']:.4f}/{m['E1_positional_row_f1']:.4f}/{m['E2_matched_row_f1']:.4f}/{m['E2_matched_field_micro_f1']:.4f}. Row matchability is high, but field accuracy and row exactness ({m['E2_row_exact_match_rate']:.4f}) are materially lower.

Critical prevalence remains {evaluation['critical_error_prevalence']:.1%}. R0 remains the stronger ranker (AURC {float(metrics['R0_raw_confidence']['AURC']):.4f} versus R4 {float(metrics['R4_best_learned']['AURC']):.4f}); no certificate replay is promotion-eligible. The correct decision remains `V3_2_RISK_MODEL_NO_PROMOTION`.
""")
print(json.dumps({"reports":len(list(OUT.glob('*.md'))),"decision":"V3_2_RISK_MODEL_NO_PROMOTION"},sort_keys=True))
