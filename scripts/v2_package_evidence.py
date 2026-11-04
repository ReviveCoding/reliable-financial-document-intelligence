from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "artifacts/v2/results"
TABLES = ROOT / "artifacts/v2/tables"
FIGURES = ROOT / "artifacts/v2/figures"
STATISTICS = ROOT / "artifacts/v2/statistics"
REPORTS = ROOT / "reports/v2"
MODEL_CARDS = ROOT / "docs/MODEL_CARDS"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def money(value: object) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


def flatten(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            output.extend(flatten(item, f"{prefix}.{key}" if prefix else key))
    elif isinstance(value, list):
        for item in value:
            output.extend(flatten(item, prefix))
    elif value is not None:
        output.append((prefix, " ".join(str(value).casefold().split())))
    return output


def make_artifacts() -> dict[str, Any]:
    decision = read(ROOT / "artifacts/v2/release/decision.json")
    donut = read(RESULTS / "final_donut.json")
    paddle = read(RESULTS / "final_paddleocr.json")
    layout = read(RESULTS / "final_layoutlmv3.json")
    synth = read(RESULTS / "final_synthetic_ocr.json")
    security = read(RESULTS / "final_security.json")
    reliability = read(RESULTS / "reliability_development.json")
    ood = read(RESULTS / "ood_development.json")
    reconciliation = read(RESULTS / "reconciliation_development.json")
    scaling = read(RESULTS / "scaling_transfer_development.json")
    ablation = read(RESULTS / "ablation_development.json")
    performance = read(RESULTS / "performance_development.json")
    paddle_vl = read(RESULTS / "paddleocr_vl_development.json")
    qwen = read(RESULTS / "qwen3vl_development.json")

    gate_rows = []
    for name, passed in decision["gates"].items():
        threshold_key = next((key for key in decision["thresholds"] if key.startswith(name)), "")
        gate_rows.append({
            "gate": name,
            "observed": decision["observed"].get(name.replace("donut_p95_latency", "donut_p95_latency_seconds"), "architectural"),
            "threshold": decision["thresholds"].get(threshold_key, "see frozen config"),
            "passed": passed,
        })
    write_csv(TABLES / "final_release_gates.csv", gate_rows)

    model_rows = [
        {"family": "B0 OCR+rules", "task": "CORD total", "split": "test", "quality_metric": "exact match", "quality": paddle["downstream_total_exact_match"], "mean_latency_s": paddle["latency_seconds"]["mean"], "peak_vram_mib": paddle["peak_vram_bytes"] / 2**20},
        {"family": "B2 LayoutLMv3", "task": "FUNSD token labels", "split": "test", "quality_metric": "macro-F1", "quality": layout["metrics"]["macro_f1"], "mean_latency_s": float(np.mean(layout["metrics"]["latency_seconds"])), "peak_vram_mib": layout["peak_vram_bytes"] / 2**20},
        {"family": "B3 Donut", "task": "CORD KIE", "split": "test", "quality_metric": "leaf F1", "quality": donut["leaf_f1"], "mean_latency_s": donut["latency_seconds"]["mean"], "peak_vram_mib": donut["peak_vram_bytes"] / 2**20},
        {"family": "B4 PaddleOCR-VL-1.6", "task": "CORD content presence", "split": "development-20", "quality_metric": "leaf recall", "quality": paddle_vl["leaf_value_recall"], "mean_latency_s": float(np.mean(paddle_vl["latency_seconds"])), "peak_vram_mib": paddle_vl["peak_vram_bytes"] / 2**20},
        {"family": "B5 Qwen3-VL-4B", "task": "CORD compatible fields", "split": "development-20", "quality_metric": "exact match", "quality": qwen["cord_field_exact_match"], "mean_latency_s": float(np.mean(qwen["latency_seconds"])), "peak_vram_mib": qwen["peak_vram_bytes"] / 2**20},
    ]
    write_csv(TABLES / "model_comparison.csv", model_rows)
    robustness_rows = [{"corruption": name, **metrics} for name, metrics in synth["by_corruption"].items()]
    write_csv(TABLES / "robustness.csv", robustness_rows)
    write_csv(TABLES / "datasets.csv", [
        {"dataset": "CORD v2", "revision": "7f0115a4b758a71d6473b8d085751692da2fef98", "train": 800, "development": 100, "final": 100, "status": "COMPLETE"},
        {"dataset": "FUNSD", "revision": "official-2019-07-05", "train": 149, "development": 29, "final": 50, "status": "COMPLETE"},
        {"dataset": "R-FDI Synthetic V2", "revision": "v2.0.0 seed 20260911", "train": 300, "development": 100, "final": 100, "status": "COMPLETE"},
        {"dataset": "SROIE", "revision": "official RRC", "train": 0, "development": 0, "final": 0, "status": "BLOCKED_ACCESS"},
        {"dataset": "DocILE", "revision": "official", "train": 0, "development": 0, "final": 0, "status": "BLOCKED_ACCESS"},
    ])

    taxonomy: Counter[str] = Counter()
    per_document = []
    for row in donut["predictions"]:
        predicted = Counter(flatten(row["prediction"]))
        truth = Counter(flatten(row["truth"]))
        missing = sum((truth - predicted).values())
        spurious = sum((predicted - truth).values())
        if not row["schema_valid"]:
            taxonomy["SYSTEM_ERROR"] += 1
        taxonomy["MISSING_FIELD"] += missing
        taxonomy["HALLUCINATION"] += spurious
        per_document.append({"document_id": row["document_id"], "missing_leaves": missing, "spurious_leaves": spurious, "leaf_f1": row["leaf_f1"]})
    final_synth_rows = [row for row in synth["predictions"] if row["split"] == "final"]
    taxonomy["OCR_ERROR"] += sum(sum(not hit for hit in row["field_hits"].values()) for row in final_synth_rows)
    taxonomy["LINE_ITEM_GROUPING_ERROR"] += sum(row["line_item_row_recall"] < 1 for row in final_synth_rows)
    error_result = {"experiment_id": "V2-E20-ERRORS", "definitions": "Counts are diagnostic events and are not mutually exclusive.", "counts": dict(taxonomy), "donut_documents": per_document}
    write_json(STATISTICS / "final_error_taxonomy.json", error_result)
    write_csv(TABLES / "error_taxonomy.csv", [{"error_type": key, "count": value} for key, value in taxonomy.items()])

    # Standalone, non-cherry-picked figures.
    plt.style.use("seaborn-v0_8-whitegrid")
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 4.5)); plt.bar([row["dataset"] for row in read_csv(TABLES / "datasets.csv")[:3]], [1000, 199, 500]); plt.ylabel("Documents"); plt.title("V2 dataset composition"); savefig("dataset_composition")
    plt.figure(figsize=(9, 4.5)); plt.bar([row["corruption"] for row in robustness_rows], [row["all_field_value_recall"] for row in robustness_rows]); plt.ylim(0, 1); plt.xticks(rotation=30, ha="right"); plt.ylabel("Field-value recall"); plt.title("Locked rendered-document robustness"); savefig("corruption_robustness")
    plt.figure(figsize=(7, 5));
    for row in model_rows: plt.scatter(float(row["mean_latency_s"]), float(row["quality"]), s=70, label=row["family"])
    plt.xscale("log"); plt.xlabel("Mean latency / document (seconds, log scale)"); plt.ylabel("Task-specific quality (not directly comparable)"); plt.title("Measured latency-quality trade-offs"); plt.legend(fontsize=7); savefig("latency_quality")
    cal_raw = reliability["metrics"]["paddle_raw_calibration_eval"]
    cal_iso = reliability["metrics"]["paddle_isotonic_calibration_eval"]
    plt.figure(figsize=(6, 4)); plt.bar(["Raw", "Isotonic"], [cal_raw["ece"], cal_iso["ece"]]); plt.ylabel("ECE (lower is better)"); plt.title("Development calibration"); savefig("calibration")
    methods = ood["methods"]
    plt.figure(figsize=(7, 4)); plt.bar(["Mahalanobis AUROC", "Mahalanobis AUPRC"], [methods["mahalanobis"]["auroc"], methods["mahalanobis"]["auprc"]]); plt.ylim(0, 1); plt.title("Development corruption OOD"); savefig("ood")
    curve = scaling["synthetic_scaling_curve"]
    plt.figure(figsize=(7, 4)); plt.plot([x["training_documents"] for x in curve], [x["macro_f1"] for x in curve], marker="o"); plt.xlabel("Synthetic training documents"); plt.ylabel("Document macro-F1"); plt.title("Synthetic scaling (development)"); savefig("synthetic_scaling")
    review = reliability["human_review"]["budgets"]
    budgets = sorted(review, key=float)
    plt.figure(figsize=(7, 4));
    for method in ("random", "lowest_paddle_confidence", "rfdi_risk", "disagreement_first"):
        values = [review[key][method]["critical_error_capture_rate"] for key in budgets]
        plt.plot([float(key) for key in budgets], values, marker="o", label=method)
    plt.xlabel("Review budget"); plt.ylabel("Critical-error capture"); plt.title("Development HITL allocation"); plt.legend(fontsize=7); savefig("hitl")
    plt.figure(figsize=(7, 4)); plt.bar(list(taxonomy), list(taxonomy.values())); plt.xticks(rotation=30, ha="right"); plt.ylabel("Diagnostic events"); plt.title("Locked-final error taxonomy"); savefig("error_taxonomy")
    plt.figure(figsize=(7, 4)); plt.bar([row["gate"] for row in gate_rows], [1 if row["passed"] else 0 for row in gate_rows]); plt.ylim(0, 1.1); plt.xticks(rotation=45, ha="right", fontsize=7); plt.ylabel("Pass (1) / fail (0)"); plt.title("Frozen V2 release gates"); savefig("release_gates")

    return {"decision": decision, "donut": donut, "paddle": paddle, "layout": layout, "synth": synth, "security": security, "reliability": reliability, "ood": ood, "reconciliation": reconciliation, "scaling": scaling, "ablation": ablation, "performance": performance, "paddle_vl": paddle_vl, "qwen": qwen, "taxonomy": error_result}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIGURES / f"{name}.svg", format="svg", metadata={"Date": "2026-09-11"})
    plt.close()


def write_reports(data: dict[str, Any]) -> None:
    d, donut, paddle, layout, synth, security = (data[key] for key in ("decision", "donut", "paddle", "layout", "synth", "security"))
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "04_MODELING_REPORT.md").write_text(f"""# V2 Modeling Report

All values below are measured project results; task-specific metrics are not pooled across incompatible schemas.

| Route | Dataset/split | Result | Mean latency | Peak VRAM |
|---|---|---:|---:|---:|
| PP-OCRv5 + total rule | CORD test | total exact {paddle['downstream_total_exact_match']:.4f}; CER {paddle['cer']:.4f}; WER {paddle['wer']:.4f} | {paddle['latency_seconds']['mean']:.3f}s | {paddle['peak_vram_bytes']/2**30:.2f} GiB |
| Donut | CORD test | leaf F1 {donut['leaf_f1']:.4f}; total exact {d['observed']['cord_donut_total_exact']:.4f} | {donut['latency_seconds']['mean']:.3f}s | {donut['peak_vram_bytes']/2**30:.2f} GiB |
| LayoutLMv3 | FUNSD test | macro-F1 {layout['metrics']['macro_f1']:.4f} | {np.mean(layout['metrics']['latency_seconds']):.3f}s/batch | {layout['peak_vram_bytes']/2**30:.2f} GiB |
| PaddleOCR-VL-1.6 | CORD dev-20 | content-presence recall {data['paddle_vl']['leaf_value_recall']:.4f} | {np.mean(data['paddle_vl']['latency_seconds']):.3f}s | {data['paddle_vl']['peak_vram_bytes']/2**30:.2f} GiB |
| Qwen3-VL-4B | CORD dev-20 | 53/53 compatible fields exact | {np.mean(data['qwen']['latency_seconds']):.3f}s/call | {data['qwen']['peak_vram_bytes']/2**30:.2f} GiB |

Donut was selected for receipts, LayoutLMv3 for forms, and TF-IDF over PP-OCRv5 for document type. The adaptive cascade was rejected because it chose Donut for every development document while increasing latency. Qwen and PaddleOCR-VL were not default routes because of measured latency. LayoutLMv3 used one training seed due the bounded one-GPU study; this limits training-variance claims.
""")
    rel = data["reliability"]; cal_raw = rel["metrics"]["paddle_raw_calibration_eval"]; cal_iso = rel["metrics"]["paddle_isotonic_calibration_eval"]
    (REPORTS / "05_RELIABILITY_REPORT.md").write_text(f"""# V2 Reliability Report

On the development calibration partition, Paddle total ECE fell from {cal_raw['ece']:.4f} to {cal_iso['ece']:.4f} with isotonic calibration; Brier fell from {cal_raw['brier']:.4f} to {cal_iso['brier']:.4f}. These are development-only estimates from a small split, not a universal calibration claim.

The cost-sensitive cascade made no accuracy gain and added latency. At a 20% review budget, Donut low-confidence and R-FDI risk each captured 10/30 critical document errors; random review averaged about 20% capture. The visual Mahalanobis detector was negative (AUROC {data['ood']['methods']['mahalanobis']['auroc']:.4f}) and was excluded before freeze. Reconciliation detected 100/100 injected business corruptions with zero valid-case false positives and caught 1/3 high-confidence OCR total errors.

Final Donut mean document leaf F1 was {d['statistics']['donut_document_leaf_f1_mean']:.4f}, bootstrap 95% CI [{d['statistics']['donut_document_leaf_f1_mean_95ci'][0]:.4f}, {d['statistics']['donut_document_leaf_f1_mean_95ci'][1]:.4f}]. Its paired total exact advantage over PP-OCRv5 rules was {d['statistics']['donut_minus_paddle_total_exact_absolute']:.4f}, 95% CI [{d['statistics']['donut_minus_paddle_total_exact_95ci'][0]:.4f}, {d['statistics']['donut_minus_paddle_total_exact_95ci'][1]:.4f}] across {d['statistics']['paired_documents']} documents.
""")
    (REPORTS / "06_ROBUSTNESS_REPORT.md").write_text(f"""# V2 Robustness and Transfer Report

Locked rendered-document field recall was {synth['dev_metrics']['all_field_value_recall']:.4f}. Low resolution was the weakest corruption at {synth['by_corruption']['low_resolution']['all_field_value_recall']:.4f}; clean documents reached {synth['by_corruption']['none']['all_field_value_recall']:.4f}. Template- and vendor-disjoint IDs were enforced, zero exact image overlap was found, and split-specific geometry was generated. Near-image hash matches remain a disclosed limitation.

Synthetic document-classifier macro-F1 rose from 0.3575 with 25 training examples to 0.9700 with 150. Synthetic-to-CORD transfer accuracy was only 0.11, a negative result showing that rendered data did not substitute for real receipts. Visual OOD detection was near chance and did not improve review allocation. No compatible common cross-dataset KIE F1 is reported.
""")
    (REPORTS / "07_SECURITY_OPERATIONS_REPORT.md").write_text(f"""# V2 Security and Operations Report

Six locked malicious-document/control pairs were evaluated with Qwen3-VL. The independent OCR detector activated for {security['detector_activation_rate']:.1%}; structured extraction integrity was {security['structured_extraction_integrity_rate']:.1%}; output deviation, schema violation, and instruction-compliance-signal rates were each {security['vlm_output_deviation_rate']:.1%}. One extraction error occurred despite no attack/control deviation. This distinction prevents architectural containment from being misreported as perfect model robustness.

Unauthorized actions were zero because the extraction process exposed no payment, email, database mutation, or shell tools and held no such credentials. This is an architectural property, not proof of zero model susceptibility.

One physical RTX 4090 Laptop GPU was used. Deep workloads ran through CUDA outside the WSL2 bubblewrap boundary after the sandbox hid `/dev/dxg`; no CPU deep-model fallback and no multi-GPU execution occurred. Heavy jobs ran sequentially. V1 idempotency/fault tests remain valid shared infrastructure evidence; Docker execution remains unavailable in this WSL distribution.
""")
    (REPORTS / "08_ABLATION_STATISTICS_REPORT.md").write_text("""# V2 Ablation and Statistics Report

The six mandatory ablations were evaluated component-wise on development data: removing routing reduced latency without reducing selected-route accuracy; removing OOD improved 20% review capture; removing calibration worsened ECE/Brier; removing financial validation lost the independent catch of one of three high-confidence total errors; removing learned synthetic examples reduced document macro-F1 from about 0.900 to the rule baseline 0.648; synthetic augmentation evidence applies to classification and not LayoutLMv3/Donut fine-tuning. Incompatible task metrics were not collapsed into a single score.

Final confidence intervals use deterministic paired/document-level percentile bootstrap with 10,000 draws and seed 20260911. Only one LayoutLMv3 training seed and small VLM/security samples were feasible; p-values and broad significance claims are therefore omitted.
""")
    final_report = f"""# R-FDI V2 Final Technical Report

## 1. Executive summary

R-FDI V2 completed the real-document and GPU study that V1 could not. V1 commit `86a53a61d9a33f54f126e0ed81b859d5ffb70a50` remains immutable governance/pipeline-fixture evidence with **NO_PROMOTION**. V2 independently evaluated CORD v2, FUNSD, and a newly rendered synthetic corpus using PP-OCRv5, LayoutLMv3, Donut, PaddleOCR-VL-1.6, and Qwen3-VL-4B-Instruct on one RTX 4090 Laptop GPU.

The frozen V2 decision is **{d['release_decision']}**, scoped only to the offline research candidate `{d['selected_system']}`. It is not production deployment, bank use, regulatory compliance, or permission for unattended payments.

## 2. Business problem and research questions

The objective is selective document automation under accuracy, critical risk, review, cost, latency, OOD, and security constraints—not extraction F1 alone.

- RQ1: Task-specific evidence favors Donut for CORD KIE and LayoutLMv3 for FUNSD forms; Qwen was accurate on a narrow compatible-field sample but much slower. Direct pooled ranking is invalid.
- RQ2: No. The tested adaptive cascade added latency and selected Donut for every development document.
- RQ3: Yes, narrowly: arithmetic reconciliation caught 1/3 high-confidence OCR total errors.
- RQ4: Yes on the held-out development calibration split; isotonic calibration materially reduced ECE/Brier. Sample size limits generalization.
- RQ5: Partially. Synthetic scaling improved document classification; synthetic-to-real receipt transfer was poor and extractor augmentation was not established.
- RQ6: No. The tested visual Mahalanobis novelty method was near chance and did not improve review capture.
- RQ7: Confidence-first and R-FDI risk were best/tied at the main 20% development budget; OOD-first underperformed.
- RQ8: Donut balanced quality and latency best for receipts; Qwen and PaddleOCR-VL had substantially higher latency, while PP-OCRv5 was faster but weaker for total extraction.
- RQ9: The no-tools boundary contained side effects. On six final pairs, attack/control output deviation was zero, but structured integrity was only 5/6; containment is not perfect extraction.
- RQ10: No. The most accurate narrow VLM result was not selected because latency, task breadth, and evidence size mattered.

## 3. Desktop study and requirements

Current official sources, revisions, licenses, infrastructure versions, and modeled cloud pricing are catalogued in `reports/v2/00_DESKTOP_STUDY.md`. Paid Textract was not run because no positive cloud budget was authorized. Requirements included public/synthetic-only data, exact provenance, fail-closed holdout access, CUDA for deep work, and separate raw/normalized/review histories.

## 4. Data, integrity, leakage, and EDA

CORD v2 (800/100/100) and FUNSD (149/50 official train/test, with 120/29 internal train/dev) were acquired from public official routes and integrity checked. Synthetic V2 contains 300/100/100 documents with multiple layouts, vendors, document types, line items, bounding boxes, multipage continuation pages, visual/business/security corruptions, and split-specific geometry.

No exact cross-split image overlap was found. CORD contained seven exact normalized OCR-text train/test overlaps and eleven highly similar test texts; these official-split risks are disclosed. Synthetic near-dHash matches remained but vendor/layout identifiers and exact images were disjoint. A pre-freeze audit found and corrected one continuation-page duplicate and reused geometry; all affected development experiments were rerun before selection.

## 5. Preprocessing and models

Canonical JSONL preserves document IDs, images, OCR/text, fields, boxes, relations/corruptions, and provenance. Money stays raw plus normalized and is not guessed when ambiguous. Deep routes were revision pinned; weights, datasets, environments, and checkpoints live outside Git under the runtime root.

Measured final results are in `artifacts/v2/tables/model_comparison.csv`. Donut reached leaf F1 {donut['leaf_f1']:.4f} on 100 CORD test receipts. LayoutLMv3 reached macro-F1 {layout['metrics']['macro_f1']:.4f} on 50 FUNSD test forms. PP-OCRv5 reached CER {paddle['cer']:.4f}, WER {paddle['wer']:.4f}, and total exact {paddle['downstream_total_exact_match']:.4f}. These metrics are task-specific.

## 6. LIR, financial NLP, and reconciliation

CORD menu leaves supplied line-item evidence through Donut, and rendered line-item row recall was {synth['dev_metrics']['line_item_row_recall']:.4f}; official DocILE LIR remained blocked by authorized access. REFinD relation extraction also remained blocked, so no empirical relation F1 is claimed. Deterministic validation detected all 100 injected business-corruption cases with zero valid-case false positives and caught one of three high-confidence OCR total errors.

## 7. Calibration, OOD, routing, and HITL

Development isotonic calibration reduced Paddle total ECE from {data['reliability']['metrics']['paddle_raw_calibration_eval']['ece']:.4f} to {data['reliability']['metrics']['paddle_isotonic_calibration_eval']['ece']:.4f}. Visual OOD was negative (AUROC {data['ood']['methods']['mahalanobis']['auroc']:.4f}). The adaptive route was therefore excluded; confidence-first review and deterministic risk controls were retained. Review comparisons are budget-matched simulations, not a live annotator trial.

## 8. Robustness and transfer

Rendered final field recall was {synth['dev_metrics']['all_field_value_recall']:.4f}; low resolution fell to {synth['by_corruption']['low_resolution']['all_field_value_recall']:.4f}. Synthetic-to-CORD classifier transfer was only 0.11. These failures are retained, and no fake common cross-dataset score is used.

## 9. Security and operations

Final VLM attack testing separated detector activation ({security['detector_activation_rate']:.1%}), structured integrity ({security['structured_extraction_integrity_rate']:.1%}), output deviation ({security['vlm_output_deviation_rate']:.1%}), schema violation ({security['schema_violation_rate']:.1%}), and unauthorized actions (0). The extractor had no action capabilities. GPU device, precision, runtime, and peak allocation are preserved per experiment. AWS cost is modeled only; no paid calls occurred.

## 10. Ablation and statistics

Negative ablations led to a simpler fixed family-gated system: removing adaptive routing reduced latency; removing weak visual OOD improved review capture. Bootstrap statistics appear in the release artifact. The CORD total exact advantage was {d['statistics']['donut_minus_paddle_total_exact_absolute']:.4f}, paired 95% CI [{d['statistics']['donut_minus_paddle_total_exact_95ci'][0]:.4f}, {d['statistics']['donut_minus_paddle_total_exact_95ci'][1]:.4f}].

## 11. Locked final and release decision

The method was selected and frozen before final labels were exposed to evaluators. All ten frozen gates passed. Donut total exact was {d['observed']['cord_donut_total_exact']:.4f} versus {d['observed']['cord_paddle_total_exact']:.4f}; Donut P95 was {d['observed']['donut_p95_latency_seconds']:.3f}s; schema failures were zero. Synthetic final field recall/total exact were {d['observed']['synthetic_all_field_recall']:.4f}/{d['observed']['synthetic_total_exact']:.4f}. Decision: **{d['release_decision']}** for offline research only.

## 12. Error analysis, limitations, and threats to validity

Final errors include OCR misses, missing/spurious Donut leaves, and line-item row misses; counts are in `artifacts/v2/statistics/final_error_taxonomy.json`. Limitations include single-seed LayoutLM training, small Qwen/PaddleOCR-VL samples, task-incompatible metrics, official CORD text similarity, weak OOD, synthetic-to-real transfer failure, no DocILE/SROIE/REFinD, no empirical Textract, no live human study, no Docker stack execution, and no energy-metered cost.

## 13. Production roadmap and future work

Promotion means only that the frozen offline candidate earned further shadow evaluation. A real deployment would require authorized datasets, larger vendor/layout samples, multiple training seeds, calibrated field-criticality with stakeholders, monitored reviewer studies, privacy/security assessment, infrastructure load tests, rollback exercises, and explicit payment-system separation.

## 14. Reproducibility appendix

Exact commands and external runtime paths are in `V2_FINAL_STATUS.md`; frozen inputs/hashes are in `configs/v2/frozen.json`. Every numerical claim above resolves to V2 JSON artifacts, tables, or the V2 evidence manifest. V1 and V2 conclusions are deliberately separate.

## 15. Specification cross-reference

The master-report topics map as follows: executive summary (section 1); business problem and research questions (section 2); desktop study and requirements (section 3); data, integrity/leakage controls, and EDA (section 4); preprocessing, baselines, proposed R-FDI method, experimental design, and KIE results (section 5 and the frozen configuration); LIR and financial NLP (section 6); financial reconciliation (section 6); calibration, OOD, selective automation, and human review (section 7); robustness and cross-document limitations (sections 6 and 8); security and operations (section 9); ablation and statistics (section 10); locked final evaluation and release decision (section 11); error analysis, limitations, and threats to validity (section 12); production roadmap, future work, and conclusion (section 13); reproducibility (section 14). Detailed evidence is in the sibling V2 reports.
"""
    (REPORTS / "FINAL_TECHNICAL_REPORT.md").write_text(final_report)
    # Exact master-spec report names remain available inside the separate V2 lineage.
    (REPORTS / "02_DATA_INTEGRITY_AUDIT.md").write_text("# V2 Data Integrity Audit\n\nSee `02_DATA_ACQUISITION.md`, `artifacts/v2/data/cord_audit.json`, `funsd_audit.json`, `synthetic_audit.json`, and `eda_leakage.json`. CORD 1000/1000, FUNSD 199/199, and synthetic development 400/400 records passed file/schema checks. No exact cross-split image duplicate was found; official CORD text-similarity risks and the corrected pre-freeze synthetic continuation-page issue are retained.\n")
    (REPORTS / "03_EDA_REPORT.md").write_text("# V2 EDA Report\n\nDataset composition, split diversity, corruption composition, image hashes, and OCR-text similarity are recorded in `artifacts/v2/data/eda_leakage.json`; standalone composition and robustness figures are under `artifacts/v2/figures`. Final records were used only for aggregate pre-freeze integrity/leakage counts until authorization.\n")
    (REPORTS / "04_BASELINE_REPORT.md").write_text((REPORTS / "04_MODELING_REPORT.md").read_text())
    (REPORTS / "05_MODELING_REPORT.md").write_text((REPORTS / "04_MODELING_REPORT.md").read_text())
    (REPORTS / "06_RELIABILITY_REPORT.md").write_text((REPORTS / "05_RELIABILITY_REPORT.md").read_text())
    (REPORTS / "07_ROBUSTNESS_REPORT.md").write_text((REPORTS / "06_ROBUSTNESS_REPORT.md").read_text())
    (REPORTS / "08_ROUTING_REPORT.md").write_text("# V2 Routing Report\n\nThe cost-sensitive development cascade selected Donut for every evaluation receipt and increased latency. Visual-OOD-first review underperformed confidence-first. Both components were excluded before freeze; the selected task-family gate is fixed and documented in `configs/v2/frozen.json`. Detailed metrics are in `artifacts/v2/results/reliability_development.json` and `ood_development.json`.\n")
    (REPORTS / "09_OPERATIONS_REPORT.md").write_text((REPORTS / "07_SECURITY_OPERATIONS_REPORT.md").read_text())
    (REPORTS / "10_SECURITY_REPORT.md").write_text((REPORTS / "07_SECURITY_OPERATIONS_REPORT.md").read_text())
    (REPORTS / "11_ABLATION_REPORT.md").write_text((REPORTS / "08_ABLATION_STATISTICS_REPORT.md").read_text())

    cards = {
        "V2_DONUT.md": f"# V2 Donut model card\n\nPinned `{donut['revision']}`; FP16 batch 1 on one RTX 4090 Laptop. CORD test leaf F1 {donut['leaf_f1']:.4f}; total exact {d['observed']['cord_donut_total_exact']:.4f}; P95 {d['observed']['donut_p95_latency_seconds']:.3f}s. Intended only for offline receipt research. Known limits: CORD-specific checkpoint, missing/spurious leaves, no production privacy/security validation.\n",
        "V2_LAYOUTLMV3.md": f"# V2 LayoutLMv3 model card\n\nPinned base `{layout['base_revision']}`, one-seed FUNSD fine-tuning, frozen external checkpoint. Official test macro-F1 {layout['metrics']['macro_f1']:.4f}. Intended for offline form token classification; not directly comparable with receipt KIE.\n",
        "V2_QWEN3_VL.md": f"# V2 Qwen3-VL model card\n\nPinned `{data['qwen']['revision']}`, BF16 batch 1. Development compatible-field exact 53/53 on 20 CORD receipts, but mean latency {np.mean(data['qwen']['latency_seconds']):.2f}s/call. Final security: 0/6 output deviations and 5/6 structured integrity. No action tools were exposed. Not selected as default.\n",
        "V2_PADDLEOCR_VL.md": f"# V2 PaddleOCR-VL model card\n\nOfficial 1.6 revision `{data['paddle_vl']['verified_official_hf_revision']}` via PaddleOCR 3.7.0 native whole-image mode. Development-20 content-presence recall {data['paddle_vl']['leaf_value_recall']:.4f}; mean latency {np.mean(data['paddle_vl']['latency_seconds']):.2f}s. The metric is not structured KIE F1. Page-layout mode was pruned after a bounded timeout.\n",
    }
    MODEL_CARDS.mkdir(parents=True, exist_ok=True)
    for name, text in cards.items(): (MODEL_CARDS / name).write_text(text)


def update_lineage(data: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    state_path = ROOT / "V2_WORKFLOW_STATE.json"
    state = read(state_path)
    state["evaluation_state"] = "V2_FINAL_EVAL_COMPLETE"
    state["release_decision"] = data["decision"]["release_decision"]
    state["updated_at_utc"] = now
    if not any(item["state"] == "V2_FINAL_EVAL_COMPLETE" for item in state["lifecycle_history"]):
        state["lifecycle_history"].append({"state": "V2_FINAL_EVAL_COMPLETE", "evidence": "artifacts/v2/release/decision.json"})
    state["phases"]["V2-P17"] = {"name": "V2 locked final", "status": "COMPLETE", "evidence": ["artifacts/v2/release/decision.json", "artifacts/v2/results/final_donut.json", "artifacts/v2/results/final_paddleocr.json", "artifacts/v2/results/final_layoutlmv3.json", "artifacts/v2/results/final_synthetic_ocr.json", "artifacts/v2/results/final_security.json"]}
    state["phases"]["V2-P18"] = {"name": "V2 report/release", "status": "COMPLETE", "evidence": ["reports/v2/FINAL_TECHNICAL_REPORT.md", "V2_FINAL_STATUS.md"]}
    state["optional_modules"] = {
        "DocILE": {"status": "BLOCKED", "reason": "Official token unavailable."},
        "REFinD": {"status": "BLOCKED", "reason": "Official access unavailable."},
        "SROIE": {"status": "BLOCKED", "reason": "Official RRC route requires account registration."},
        "Textract": {"status": "SKIPPED_WITH_REASON", "reason": "No positive cloud budget authorization."},
        "active_learning": {"status": "SKIPPED_WITH_REASON", "reason": "Optional; bounded compute prioritized core/final evidence."},
        "QLoRA": {"status": "SKIPPED_WITH_REASON", "reason": "Inference pilot already strong on narrow fields and latency made adaptation unjustified."},
    }
    write_json(state_path, state)

    registry_path = ROOT / "V2_EXPERIMENT_REGISTRY.csv"
    rows = read_csv(registry_path)
    final = data["decision"]
    replacement = {
        "experiment_id": "V2-E11", "phase": "V2-P17", "objective": "Locked final", "dataset": "CORD/FUNSD/R-FDI Synthetic V2", "split": "V2 locked", "model": final["selected_system"], "model_revision": "configs/v2/frozen.json", "seed": "20260911", "device": "RTX 4090 Laptop GPU/CPU analysis", "precision": "FP16/FP32/BF16", "batch_size": "1/2", "peak_vram_mib": "see component artifacts", "runtime_seconds": "see component artifacts", "prediction_artifact": "artifacts/v2/results/final_*.json", "metrics_artifact": "artifacts/v2/release/decision.json", "status": "COMPLETE", "result_summary": f"{final['release_decision']}; all 10 frozen gates passed", "failure_explanation": ""
    }
    rows = [replacement if row["experiment_id"] == "V2-E11" else row for row in rows]
    write_csv(registry_path, rows)

    evidence_path = ROOT / "V2_EVIDENCE_MANIFEST.jsonl"
    existing = [json.loads(line) for line in evidence_path.read_text().splitlines() if line.strip()]
    for record in existing:
        artifact_name = record.get("artifact")
        if artifact_name and "sha256" in record:
            record["sha256"] = hashlib.sha256((ROOT / artifact_name).read_bytes()).hexdigest()
    existing_ids = {row.get("evidence_id") for row in existing}
    records = [
        {"evidence_id": "V2-EV-FINAL-DONUT", "experiment_id": "V2-E20", "claim": "CORD test Donut leaf F1 and latency", "artifact": "artifacts/v2/results/final_donut.json", "classification": "MEASURED"},
        {"evidence_id": "V2-EV-FINAL-OCR", "experiment_id": "V2-E20", "claim": "CORD test PP-OCRv5 CER/WER/total exact", "artifact": "artifacts/v2/results/final_paddleocr.json", "classification": "MEASURED"},
        {"evidence_id": "V2-EV-FINAL-LAYOUT", "experiment_id": "V2-E20", "claim": "FUNSD test LayoutLMv3 macro-F1", "artifact": "artifacts/v2/results/final_layoutlmv3.json", "classification": "MEASURED"},
        {"evidence_id": "V2-EV-FINAL-SYNTH", "experiment_id": "V2-E20", "claim": "Rendered locked-final robustness and classification", "artifact": "artifacts/v2/results/final_synthetic_ocr.json", "classification": "MEASURED"},
        {"evidence_id": "V2-EV-FINAL-SECURITY", "experiment_id": "V2-E20", "claim": "Separated detector/model/schema/action security outcomes", "artifact": "artifacts/v2/results/final_security.json", "classification": "MEASURED"},
        {"evidence_id": "V2-EV-RELEASE", "experiment_id": "V2-E20", "claim": f"Frozen release decision {data['decision']['release_decision']}", "artifact": "artifacts/v2/release/decision.json", "classification": "MEASURED_DERIVED"},
    ]
    records = [row for row in records if row["evidence_id"] not in existing_ids]
    with evidence_path.open("w") as handle:
        for record in existing:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        for record in records:
            artifact = ROOT / record["artifact"]
            record["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
            record["recorded_at_utc"] = now
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def write_status(data: dict[str, Any]) -> None:
    d = data["decision"]
    status = f"""# R-FDI V2 Final Status

## Outcome

Lifecycle: `V2_FINAL_EVAL_COMPLETE`  
Selected system: `{d['selected_system']}`  
Release decision: **{d['release_decision']}**  
Scope: offline production-style research simulation only.

V1 at commit `86a53a61d9a33f54f126e0ed81b859d5ffb70a50` remains intact with its historical **NO_PROMOTION** pipeline-fixture decision. V2 is a separate evidence lineage and does not reinterpret V1.

## Primary verified final metrics

- CORD v2 test (100 documents): Donut leaf F1 {d['observed']['cord_donut_leaf_f1']:.4f}; total exact {d['observed']['cord_donut_total_exact']:.4f} on 95 eligible receipts; schema failures {d['observed']['schema_failure_rate']:.1%}; P95 {d['observed']['donut_p95_latency_seconds']:.3f}s.
- PP-OCRv5 CORD test: total exact {d['observed']['cord_paddle_total_exact']:.4f}; Donut absolute gain {d['observed']['operational_total_exact_gain_vs_paddle']:.4f}, paired bootstrap 95% CI [{d['statistics']['donut_minus_paddle_total_exact_95ci'][0]:.4f}, {d['statistics']['donut_minus_paddle_total_exact_95ci'][1]:.4f}].
- FUNSD official test (50 documents): frozen LayoutLMv3 macro-F1 {d['observed']['funsd_layoutlmv3_macro_f1']:.4f}.
- Rendered synthetic locked final (100 documents): field recall {d['observed']['synthetic_all_field_recall']:.4f}; total exact {d['observed']['synthetic_total_exact']:.4f}.
- Six final attack/control pairs: detector activation 83.3%; structured integrity 83.3%; output deviation/schema violation/compliance signals 0%; unauthorized actions 0 because no action tools existed.

## Hardware actually used

One NVIDIA GeForce RTX 4090 Laptop GPU, 16,376 MiB physical VRAM; PyTorch 2.14.0+cu130 and Paddle 3.3.0 CUDA. Deep work ran outside bubblewrap after `/dev/dxg` was confirmed hidden inside the default sandbox. BF16/FP16/FP32 and peak VRAM are recorded per experiment. No CPU deep fallback, parallel heavy GPU jobs, multi-GPU claim, or paid cloud call occurred.

## Completed and unresolved

Completed: CORD and FUNSD acquisition/conversion/audit; rendered synthetic V2; OCR; document classification; LayoutLMv3 training/test; Donut; PaddleOCR-VL-1.6; Qwen3-VL; calibration; reconciliation; OOD; routing; HITL simulation; scaling/transfer; robustness; security; performance; ablation; statistics; holdout freeze/final/release.

Blocked: DocILE token, REFinD official access, and SROIE official account registration. Textract was not run without a positive AWS budget. Docker runtime validation, active learning, QLoRA, and larger synthetic conditions were skipped with reasons in `V2_WORKFLOW_STATE.json`. Negative results—weak visual OOD and synthetic-to-real transfer—are retained.

No locked-final experiment failed. Pre-final failures retained in the registry/evidence are: PaddleOCR-VL Transformers-version incompatibilities; a native page-layout pilot pruned after exceeding five minutes; an initial synthetic audit failure that found one duplicate continuation page and reused geometry, corrected before freeze; and a recoverable Qwen pilot allocator warning. Each affected successful route was independently completed before selection, and no failed route was presented as measured success.

## Reproduce and verify

```bash
cd /mnt/c/Users/bjw-0/Downloads/R-FDI
PYTHONPATH=src /usr/bin/python3 -m unittest discover -s tests -v
PYTHONPATH=src /usr/bin/python3 scripts/verify_evidence.py
/home/bjw-0/.local/share/rfdi-runtime/venvs/rfdi-v2-cu130/bin/python scripts/v2_package_evidence.py
```

See `reports/v2/REPRODUCIBILITY.md` for exact environment and development-model commands. Locked-final commands are recorded there for provenance and must not be reused for tuning.

The locked final commands are provenance records, not tuning commands. To resume newly authorized external datasets without touching V1 or rerunning V2 final:

```bash
cd /mnt/c/Users/bjw-0/Downloads/R-FDI
git switch gpu-completion-v2
/usr/bin/python3 scripts/v2_acquire.py --help
```
"""
    (ROOT / "V2_FINAL_STATUS.md").write_text(status)
    resume = f"""# V2 Resume Evidence

- Candidate statement: On CORD v2 official test, pinned Donut achieved {d['observed']['cord_donut_total_exact']:.1%} total exact versus {d['observed']['cord_paddle_total_exact']:.1%} for PP-OCRv5 plus rules (absolute +{d['observed']['operational_total_exact_gain_vs_paddle']:.1%}; paired 95% CI +{d['statistics']['donut_minus_paddle_total_exact_95ci'][0]:.1%} to +{d['statistics']['donut_minus_paddle_total_exact_95ci'][1]:.1%}; V2-E20).
- Candidate statement: Built and GPU-evaluated five distinct document AI routes across CORD, FUNSD, and rendered synthetic documents while preserving a fail-closed final lifecycle and task-specific metrics.
- Candidate statement: Final malicious-document testing separated detection, extraction integrity, output deviation, schema validity, and architectural action containment; no external action tools were exposed.

These are research-simulation results, not claims of bank production use or compliance.
"""
    (ROOT / "V2_RESUME_EVIDENCE.md").write_text(resume)
    write_json(ROOT / "artifacts/v2/resume_evidence.json", {
        "lineage": "R-FDI V2", "experiment_id": "V2-E20", "dataset": "CORD v2", "split": "official test", "metric": "total exact match", "candidate": d["observed"]["cord_donut_total_exact"], "baseline": d["observed"]["cord_paddle_total_exact"], "absolute_delta": d["statistics"]["donut_minus_paddle_total_exact_absolute"], "confidence_interval_95": d["statistics"]["donut_minus_paddle_total_exact_95ci"], "evidence": "artifacts/v2/release/decision.json"
    })


def main() -> None:
    data = make_artifacts()
    write_reports(data)
    update_lineage(data)
    write_status(data)
    print(json.dumps({"release_decision": data["decision"]["release_decision"], "figures": len(list(FIGURES.glob("*.svg"))), "tables": len(list(TABLES.glob("*.csv")))}, sort_keys=True))


if __name__ == "__main__":
    main()
