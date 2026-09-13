from __future__ import annotations

import argparse
import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def request(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json"} if body else {})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()
            value = json.loads(raw) if response.headers.get_content_type() == "application/json" else raw.decode()
            return response.status, value
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--reviewer", default="http://127.0.0.1:8080/review.html")
    args = parser.parse_args()

    content = b"Invoice: DOCKER-V3-001\nSubtotal: 10.00\nTax: 2.00\nTotal: 12.00\nCurrency: USD\n"
    payload = {"idempotency_key": f"docker-probe-{time.time_ns()}",
               "content_b64": base64.b64encode(content).decode(),
               "media_type": "text/plain", "route": "cheap"}
    create_status, created = request(f"{args.api}/documents", "POST", payload)
    document_id = created["document_id"]
    duplicate_status, duplicate = request(f"{args.api}/documents", "POST", payload)
    result_status, result = 0, None
    for _ in range(200):
        result_status, result = request(f"{args.api}/documents/{document_id}/result")
        if result_status == 200:
            break
        time.sleep(0.05)
    review_status, review = request(f"{args.api}/documents/{document_id}/review", "POST", {
        "action": "EDIT", "corrections": {"total": "12.00"},
        "reason": "V3 Docker reviewer verification", "reviewer": "v3-automated-probe"})
    _, document = request(f"{args.api}/documents/{document_id}")
    _, health = request(f"{args.api}/health")
    _, metrics = request(f"{args.api}/metrics")
    _, reviewer_html = request(args.reviewer)
    _, api_reviewer_html = request(f"{args.api}/review")
    checks = {
        "create_accepted": create_status == 202 and created.get("created") is True,
        "duplicate_deduplicated": duplicate_status == 202 and not duplicate.get("created")
        and duplicate.get("document_id") == document_id,
        "worker_completed": result_status == 200 and result.get("normalized", {}).get("total") == "12.00",
        "review_committed": review_status == 200 and review.get("state") == "REVIEWED"
        and document.get("state") == "REVIEWED",
        "reviewer_service_html": isinstance(reviewer_html, str) and "R-FDI Reviewer" in reviewer_html
        and "localhost:8000" in reviewer_html,
        "api_reviewer_html": isinstance(api_reviewer_html, str) and "R-FDI Reviewer" in api_reviewer_html,
        "metrics_exposed": isinstance(metrics, str) and "rfdi_finalization_commits_total" in metrics,
    }
    output = {"experiment_id": "V3-E03-API-REVIEWER", "backend_reported": health.get("backend"),
              "document_id": document_id, "checks": checks, "all_checks_passed": all(checks.values()),
              "result": result, "health": health, "review": review}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"all_checks_passed": output["all_checks_passed"], "checks": checks}, sort_keys=True))
    if not output["all_checks_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
