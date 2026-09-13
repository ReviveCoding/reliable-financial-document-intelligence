from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import mlflow

ROOT = Path("/tmp/rfdi-v3-2")
protocol = ROOT / "configs/v3_2/risk_protocol.json"
mlflow.set_tracking_uri("http://127.0.0.1:5000")
experiment = mlflow.set_experiment("rfdi-v3-2-critical-risk-control")
run_id = os.environ.get("RFDI_MLFLOW_RUN_ID")
with mlflow.start_run(run_id=run_id, run_name=None if run_id else "v3.2-frozen-critical-risk-analysis") as run:
    mlflow.log_param("analysis_version", "3.2.0")
    mlflow.log_param("protocol_sha256", hashlib.sha256(protocol.read_bytes()).hexdigest())
    mlflow.log_param("extractor_weights_changed", False)
    mlflow.log_param("cord_test_designation", "RETROSPECTIVE_LOCKED_BENCHMARK")
    mlflow.log_param("promotion_decision", "V3_2_RISK_MODEL_NO_PROMOTION")
    for directory in (ROOT / "artifacts/v3_2", ROOT / "docs/assets/v3_2"):
        mlflow.log_artifacts(str(directory), artifact_path=str(directory.relative_to(ROOT)))
    print(json.dumps({"experiment_id": experiment.experiment_id, "run_id": run.info.run_id, "status": "LOGGED", "artifact_uri": run.info.artifact_uri}, sort_keys=True))
