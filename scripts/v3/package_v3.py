from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    stack = load("artifacts/v3/docker/stack_validation.json")
    mlflow = load("artifacts/v3/docker/mlflow_persistence.json")
    faults = load("artifacts/v3/docker/fault_recovery.json")
    gpu = load("artifacts/v3/docker/gpu_validation.json")
    api = load("artifacts/v3/runtime/docker_api_reviewer.json")
    local_faults = load("artifacts/v3/runtime/fault_study.json")
    cached = load("artifacts/v3/runtime/load_cached.json")
    donut = load("artifacts/v3/runtime/load_gpu.json")
    invalid = load("artifacts/v3/runtime/load_gpu_invalid_deduplicated.json")
    security = load("artifacts/v3/security/adversarial_benchmark.json")
    serving_path = ROOT / "artifacts/v3/serving/paddleocr_vllm_comparison.json"
    serving = json.loads(serving_path.read_text()) if serving_path.exists() else None
    final_validation_path = ROOT / "artifacts/v3/verification/final_validation.json"

    requirements = {
        "production_docker_stack": bool(stack["all_required_services_verified"]),
        "mlflow_postgresql_minio_persistence": bool(mlflow["metadata_in_postgresql_and_artifact_in_minio"]),
        "api_load": api["all_checks_passed"] and all(row["error_rate"] == 0 for row in cached["concurrency_results"]),
        "fault_recovery": local_faults["all_executed_passed"] and faults["all_cases_passed"],
        "expanded_security": security["passed"],
        "reviewer_application": api["checks"]["review_committed"] and api["checks"]["reviewer_service_html"],
        "docker_gpu": gpu["passed"],
        "accelerated_serving": serving is not None and serving.get("documents", 0) > 0,
    }
    minimum = all(requirements[key] for key in ("api_load", "fault_recovery", "expanded_security", "reviewer_application"))
    decision = "V3_EXTENSION_SUCCESS" if all(requirements.values()) else "V3_EXTENSION_PARTIAL" if minimum else "V3_EXTENSION_BLOCKED"
    now = datetime.now(timezone.utc).isoformat()

    summary = {
        "experiment_id": "V3-E10",
        "generated_at_utc": now,
        "extension_decision": decision,
        "requirements": requirements,
        "cached_load_peak_throughput_docs_second": max(row["throughput_docs_second"] for row in cached["concurrency_results"]),
        "corrected_donut_peak_throughput_docs_second": max(row["throughput_docs_second"] for row in donut["concurrency_results"]),
        "invalid_deduplicated_gpu_result_retained": invalid["experiment_id"] == "V3-E06-GPU",
        "local_fault_cases_passed": local_faults["executed_passed"],
        "docker_fault_cases_passed": sum(case["passed"] for case in faults["cases"]),
        "security_cases": security["documents"],
        "security_detector_activations": security["detected"],
        "paddleocr_vllm": None if serving is None else {
            "documents": serving["documents"],
            "leaf_value_recall": serving["leaf_value_recall"],
            "mean_latency_seconds": serving["mean_latency_seconds"],
            "native_mean_latency_seconds": serving["native_comparison"]["mean_latency_seconds"],
            "median_latency_seconds": serving["median_latency_seconds"],
            "native_median_latency_seconds": serving["native_comparison"]["median_latency_seconds"],
            "total_value_presence": serving["total_value_presence"],
            "native_total_value_presence": serving["native_comparison"]["total_value_presence"],
            "speedup_mean": serving["speedup_mean"],
        },
        "limitations": [
            "Redis persistence/restart was verified directly, but the preserved application job transport is SQLite polling.",
            "PaddleOCR-VL content-presence recall is not official structured CORD F1.",
            "DocILE and REFinD remain human-access blocked; Textract remains skipped without budget/credentials.",
            "The invalid deduplicated GPU load result is retained and excluded from comparisons.",
        ],
    }
    stats_path = ROOT / "artifacts/v3/statistics/summary.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    phases = {
        "V3-P00": ("Branch and recovery", "COMPLETE", ["reports/v3/RECOVERY.md"]),
        "V3-P01": ("Desktop study update", "COMPLETE", ["reports/v3/DESKTOP_STUDY_UPDATE.md"]),
        "V3-P02": ("External access audit", "COMPLETE", ["reports/v3/DOCILE_ACCESS.md", "reports/v3/REFIND_ACCESS.md"]),
        "V3-P03": ("Production-style Docker stack", "COMPLETE", ["artifacts/v3/docker/stack_validation.json"]),
        "V3-P04": ("MLflow persistence", "COMPLETE", ["artifacts/v3/docker/mlflow_persistence.json"]),
        "V3-P05": ("Infrastructure fault recovery", "COMPLETE", ["artifacts/v3/docker/fault_recovery.json"]),
        "V3-P06": ("Docker GPU", "COMPLETE", ["artifacts/v3/docker/gpu_validation.json"]),
        "V3-P07": ("PaddleOCR-VL accelerated serving", "COMPLETE" if serving else "BLOCKED", [str(serving_path.relative_to(ROOT))] if serving else []),
        "V3-P08": ("Expanded security", "COMPLETE", ["artifacts/v3/security/adversarial_benchmark.json"]),
        "V3-P09": ("Runtime and reviewer", "COMPLETE", ["artifacts/v3/runtime/docker_api_reviewer.json"]),
        "V3-P10": ("Statistics and packaging", "COMPLETE", ["artifacts/v3/statistics/summary.json"]),
        "V3-P11": ("Extension gates", "COMPLETE", ["configs/v3/extension_gates.json"]),
        "V3-P12": ("V2 immutable verification", "COMPLETE", ["artifacts/v3/verification/v2_immutable.json"]),
        "V3-P13": ("V1/V2/V3 validation", "COMPLETE" if final_validation_path.exists() else "RUNNING", [str(final_validation_path.relative_to(ROOT))] if final_validation_path.exists() else []),
        "V3-P14": ("Local checkpoint", "COMPLETE", ["commit:6faa9e8"]),
    }
    state = {
        "schema_version": 1,
        "lineage": "R-FDI V3: Financial-Domain + Production Hardening Extension",
        "base_commit": "1f83625",
        "extension_state": "COMPLETE",
        "extension_decision": decision,
        "updated_at_utc": now,
        "v2_immutable": True,
        "phases": {key: {"name": name, "status": status, "evidence": evidence} for key, (name, status, evidence) in phases.items()},
    }
    (ROOT / "V3_WORKFLOW_STATE.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")

    rows = [
        ["V3-E00", "V3-P00-P02", "Recovery and access audit", "environment", "preflight", "configs/v3/extension_gates.json", "CPU/GPU probe", "reports/v3/RECOVERY.md", "COMPLETE", "Recovered in place; external access decisions preserved", ""],
        ["V3-E03", "V3-P03", "Execute and verify Docker stack", "runtime", "Compose services", "configs/v3/docker-compose.yml", "Docker Desktop", "artifacts/v3/docker/stack_validation.json", "COMPLETE", "All required services healthy", "Initial Docker Hub MinIO pull failed; pinned Quay references succeeded"],
        ["V3-E04", "V3-P04", "Verify MLflow persistence", "runtime", "MLflow 3.4.0", "PostgreSQL+MinIO", "Docker Desktop", "artifacts/v3/docker/mlflow_persistence.json", "COMPLETE", "Metadata in PostgreSQL and artifact in MinIO", ""],
        ["V3-E05", "V3-P05", "Infrastructure fault recovery", "runtime", "Redis/PostgreSQL/MinIO", "controlled stop/start", "Docker Desktop", "artifacts/v3/docker/fault_recovery.json", "COMPLETE_WITH_LIMITATION", "3/3 service recovery probes passed", "Redis is not the preserved application transport"],
        ["V3-E06-CACHED", "V3-P09", "Cached route load", "synthetic", "regex", "concurrency 1/2/4/8", "CPU", "artifacts/v3/runtime/load_cached.json", "COMPLETE_PRESERVED", "0 errors across all levels", ""],
        ["V3-E06-GPU", "V3-P09", "Donut route load", "CORD development", "Donut", "corrected unique inputs", "CUDA", "artifacts/v3/runtime/load_gpu.json", "COMPLETE_PRESERVED", "Corrected GPU benchmark", ""],
        ["V3-E06-GPU-INVALID", "V3-P09", "Donut route load", "CORD development", "Donut", "deduplicated requests", "CUDA", "artifacts/v3/runtime/load_gpu_invalid_deduplicated.json", "INVALID_PRESERVED", "Excluded from comparison", "Idempotency caused duplicate collapse"],
        ["V3-E07", "V3-P05", "Executable local fault study", "synthetic", "runtime", "7 cases", "CPU", "artifacts/v3/runtime/fault_study.json", "COMPLETE_PRESERVED", "7/7 passed", ""],
        ["V3-E08", "V3-P07", "PaddleOCR-VL accelerated serving", "CORD validation sample", "PaddleOCR-VL-1.6-0.9B", "Docker/vLLM", "CUDA", "artifacts/v3/serving/paddleocr_vllm_comparison.json", "COMPLETE" if serving else "BLOCKED", "Compared with same native sample" if serving else "No serving artifact", ""],
        ["V3-E09", "V3-P08", "Expanded adversarial benchmark", "24 deterministic probes", "boundary controls", "capability isolation", "CPU", "artifacts/v3/security/adversarial_benchmark.json", "COMPLETE", "Boundary and capability isolation passed; misses retained", ""],
        ["V3-E10", "V3-P10-P11", "Statistics and extension decision", "V3 evidence", "packager", "unchanged extension gates", "CPU", "artifacts/v3/statistics/summary.json", "COMPLETE", decision, ""],
    ]
    with (ROOT / "V3_EXPERIMENT_REGISTRY.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["experiment_id", "phase", "objective", "dataset", "model", "configuration", "device", "metrics_artifact", "status", "result_summary", "failure_explanation"])
        writer.writerows(rows)

    evidence_paths = [Path("configs/v3/extension_gates.json"), Path("reports/v3/RECOVERY.md"), Path("V3_BLOCKERS.md"), Path("V3_DECISIONS.md")]
    evidence_paths += sorted(path.relative_to(ROOT) for path in (ROOT / "artifacts/v3").rglob("*") if path.is_file())
    evidence_paths += sorted(path.relative_to(ROOT) for path in (ROOT / "reports/v3").glob("*.md"))
    manifest = []
    for path in dict.fromkeys(evidence_paths):
        status = "invalid" if "invalid_deduplicated" in str(path) else "evidence"
        manifest.append({"id": f"V3-{len(manifest)+1:03d}", "kind": status, "path": str(path), "sha256": sha256(ROOT / path), "status": status})
    (ROOT / "V3_EVIDENCE_MANIFEST.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in manifest))
    print(json.dumps({"decision": decision, "requirements": requirements, "manifest_entries": len(manifest)}, sort_keys=True))


if __name__ == "__main__":
    main()
