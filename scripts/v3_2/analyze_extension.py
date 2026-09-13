from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path
from typing import Any

import cv2
import joblib
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from scripts.v3_2.train_risk_model import aurc, matrix, score_selected

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_IMAGES = Path("/home/bjw-0/.local/share/rfdi-runtime/v3_1/robustness/images")


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)


def flag(row: dict[str, str], key: str) -> int:
    return int(row[key].casefold() == "true")


def quantile_band(values: np.ndarray, value: float) -> str:
    q1, q2 = np.quantile(values, [1 / 3, 2 / 3])
    return "low" if value <= q1 else "middle" if value <= q2 else "high"


def mean_or_blank(values: list[float]) -> float | str:
    return float(np.mean(values)) if values else ""


def slices(test: list[dict[str, str]], line: list[dict[str, str]], output: Path) -> None:
    by_id = {row["document_id"]: row for row in line}
    definitions = [
        ("predicted_line_item_count", lambda row: float(row["predicted_line_item_count"])),
        ("foreground_density", lambda row: float(row["foreground_density"])),
        ("blur", lambda row: float(row["blur"])),
        ("repeated_value_density", lambda row: float(row["predicted_repeated_value_density"])),
        ("long_description", lambda row: float(row["predicted_long_description"])),
        ("monetary_density", lambda row: float(row["predicted_monetary_density"])),
        ("image_megapixels", lambda row: float(row["image_megapixels"])),
        ("sequence_confidence", lambda row: float(row["sequence_confidence"])),
        ("reconciliation_residual", lambda row: float(row["reconciliation_residual"])),
    ]
    output_rows: list[dict[str, Any]] = []
    for family, getter in definitions:
        values = np.array([getter(row) for row in test])
        for band in ("low", "middle", "high"):
            selected = [row for row in test if quantile_band(values, getter(row)) == band]
            line_rows = [by_id[row["document_id"]] for row in selected]
            output_rows.append({
                "designation": "RETROSPECTIVE_LOCKED_BENCHMARK",
                "slice_family": family,
                "slice": band,
                "support_n": len(selected),
                "critical_error_rate": mean_or_blank([flag(row, "document_has_critical_error") for row in selected]),
                "line_item_critical_error_rate": mean_or_blank([flag(row, "document_has_line_item_critical_error") for row in selected]),
                "row_structure_failure_rate": mean_or_blank([flag(row, "document_has_row_structure_failure") for row in selected]),
                "row_semantic_association_error_rate": mean_or_blank([flag(row, "document_has_row_semantic_association_error") for row in selected]),
                "row_permutation_only_rate": mean_or_blank([flag(row, "row_permutation_only") for row in selected]),
                "mean_weighted_critical_loss": mean_or_blank([float(row["weighted_critical_loss"]) for row in selected]),
                "mean_E2_matched_row_f1": mean_or_blank([float(row["E2_matched_row_f1"]) for row in line_rows]),
                "mean_E2_matched_field_micro_f1": mean_or_blank([float(row["E2_matched_field_micro_f1"]) for row in line_rows]),
                "support_status": "HEADLINE" if len(selected) >= 20 else "EXPLORATORY" if len(selected) >= 10 else "INSUFFICIENT_SUPPORT",
            })
    write_csv(output / "line_item_slices.csv", output_rows)

    required_modes=["benign_row_permutation_audit_only","semantic_row_association_error","missing_row","spurious_row","incorrect_item_price","missing_item_price","correct_total_wrong_item_price","document_total_error"]
    modes: collections.Counter[str] = collections.Counter({name:0 for name in required_modes})
    representatives: dict[str, list[str]] = collections.defaultdict(list)
    for row in test:
        detail = by_id[row["document_id"]]
        candidates = {
            "benign_row_permutation_audit_only": flag(row, "row_permutation_only"),
            "semantic_row_association_error": flag(row, "document_has_row_semantic_association_error"),
            "missing_row": int(float(detail["unmatched_gt_rows"]) > 0),
            "spurious_row": int(float(detail["spurious_predicted_rows"]) > 0),
            "incorrect_item_price": int(float(detail["incorrect_item_price_count"]) > 0),
            "missing_item_price": int(float(detail["missing_item_price_count"]) > 0),
            "correct_total_wrong_item_price": int(
                flag(row, "document_has_line_item_critical_error")
                and float(row["critical_support_count_document_total"]) > 0
                and float(row["critical_error_count_document_total"]) == 0
                and (float(detail["incorrect_item_price_count"]) > 0 or float(detail["missing_item_price_count"]) > 0)
            ),
            "document_total_error": int(float(row["critical_error_count_document_total"]) > 0),
        }
        for name, present in candidates.items():
            if present:
                modes[name] += 1
                if len(representatives[name]) < 3:
                    representatives[name].append(row["document_id"])
    pareto = [{"error_mode": name, "document_support": count, "prevalence": count / len(test), "classification":"BENIGN_AUDIT_ONLY" if name=="benign_row_permutation_audit_only" else "FAILURE", "included_in_critical_frequency":name!="benign_row_permutation_audit_only", "representative_document_ids": ";".join(representatives[name]), "raw_document_data_published": False} for name, count in modes.most_common()]
    write_csv(output / "line_item_error_pareto.csv", pareto)


def image_features(path: Path) -> dict[str, float]:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(path)
    height, width = image.shape
    _, foreground = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(foreground > 0))
    skew = 0.0
    if len(coords) > 20:
        angle = cv2.minAreaRect(coords[:, ::-1].astype(np.float32))[-1]
        skew = angle if angle <= 45 else angle - 90
    return {
        "image_width": width, "image_height": height, "image_megapixels": width * height / 1e6,
        "aspect_ratio": width / height, "blur": float(cv2.Laplacian(image, cv2.CV_64F).var()),
        "luminance": float(image.mean()), "contrast": float(image.std()), "estimated_skew": abs(float(skew)),
        "edge_density": float((cv2.Canny(image, 100, 200) > 0).mean()), "foreground_density": float((foreground > 0).mean()),
    }


def robustness(development: list[dict[str, str]], bundle: dict[str, Any], output: Path) -> None:
    source = {row["document_id"]: row for row in development}
    donut = json.loads((ROOT / "artifacts/v3_1/robustness/donut_results.json").read_text())["results"]
    result: list[dict[str, Any]] = []
    for observation in donut:
        document_id = observation["document_id"]
        name = f"{document_id}__{observation['corruption']}__{observation['severity']}.png"
        modified = dict(source[document_id])
        modified.update({key: str(value) for key, value in image_features(RUNTIME_IMAGES / name).items()})
        risk = float(score_selected(bundle, matrix([modified], bundle["features"]), [modified])[0])
        result.append({
            "document_id": document_id, "corruption": observation["corruption"], "severity": observation["severity"],
            "critical_content_presence_recall": observation["critical_content_presence_recall"],
            "critical_proxy_error": int(float(observation["critical_content_presence_recall"]) < 1),
            "leaf_f1": observation["leaf_f1"], "risk_score": risk,
            "analysis_scope": "RISK_SENSITIVITY_PROXY_NOT_END_TO_END_INFERENCE",
        })
    clean = {row["document_id"]: float(row["risk_score"]) for row in result if row["corruption"] == "clean"}
    for row in result:
        row["risk_increase_from_source_clean"] = float(row["risk_score"]) - clean[row["document_id"]]
    write_csv(output / "robustness_risk_response_cases.csv", result)
    summary: list[dict[str, Any]] = []
    for (corruption, severity), group in sorted(_groups(result, ("corruption", "severity")).items()):
        y = np.array([float(row["critical_proxy_error"]) for row in group])
        score = np.array([float(row["risk_score"]) for row in group])
        summary.append({
            "corruption": corruption, "severity": severity, "support_document_groups": len(group),
            "mean_leaf_f1": np.mean([float(row["leaf_f1"]) for row in group]),
            "mean_risk_score": score.mean(), "mean_risk_increase_from_clean": np.mean([float(row["risk_increase_from_source_clean"]) for row in group]),
            "critical_proxy_error_rate": y.mean(), "AURC": aurc(y, score),
            "AUROC": roc_auc_score(y, score) if len(set(y)) == 2 else "NOT_APPLICABLE",
            "PR_AUC": average_precision_score(y, score) if y.sum() else "NOT_APPLICABLE",
            "false_negative_critical_errors_below_median_risk": int(((y == 1) & (score <= np.median(score))).sum()),
        })
    write_csv(output / "robustness_risk_response_summary.csv", summary)


def _groups(data: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    output: dict[tuple[Any, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in data:
        output[tuple(row[key] for key in keys)].append(row)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--line-items", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    development, test, line = rows(args.development), rows(args.test), rows(args.line_items)
    bundle = joblib.load(args.model)
    slices(test, line, args.output_dir / "line_item_slicing")
    robustness(development, bundle, args.output_dir / "robustness")
    print(json.dumps({"line_item_slice_rows": 27, "robustness_cases": 130, "gpu_rerun": False, "source": "reused v3.1 frozen development corruption evidence"}, sort_keys=True))


if __name__ == "__main__":
    main()
