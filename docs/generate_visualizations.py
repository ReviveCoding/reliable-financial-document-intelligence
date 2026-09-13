from __future__ import annotations

import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"


def svg_document(width: int, height: int, body: str, title: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">Generated from committed R-FDI evidence by docs/generate_visualizations.py.</desc>
  <style>
    .bg {{ fill: #f8fafc; }} .panel {{ fill: #ffffff; stroke: #cbd5e1; }}
    .title {{ fill: #0f172a; font: 700 24px system-ui, sans-serif; }}
    .label {{ fill: #334155; font: 600 16px system-ui, sans-serif; }}
    .value {{ fill: #0f172a; font: 700 16px system-ui, sans-serif; }}
    .note {{ fill: #64748b; font: 13px system-ui, sans-serif; }}
    .native {{ fill: #64748b; }} .served {{ fill: #0f766e; }}
    .pass {{ fill: #0f766e; }} .track {{ fill: #e2e8f0; }}
    @media (prefers-color-scheme: dark) {{
      .bg {{ fill: #0f172a; }} .panel {{ fill: #111827; stroke: #475569; }}
      .title, .value {{ fill: #f8fafc; }} .label {{ fill: #e2e8f0; }}
      .note {{ fill: #94a3b8; }} .native {{ fill: #94a3b8; }}
      .served, .pass {{ fill: #2dd4bf; }} .track {{ fill: #334155; }}
    }}
  </style>
  <rect class="bg" width="100%" height="100%" rx="16"/>
{body}
</svg>
'''


def latency_chart() -> str:
    evidence = json.loads(
        (ROOT / "artifacts/v3/serving/paddleocr_vllm_comparison.json").read_text()
    )
    native = float(evidence["native_comparison"]["mean_latency_seconds"])
    served = float(evidence["mean_latency_seconds"])
    speedup = float(evidence["speedup_mean"])
    maximum = max(native, served)
    usable = 500
    native_width = usable * native / maximum
    served_width = usable * served / maximum
    body = f'''
  <rect class="panel" x="24" y="24" width="852" height="332" rx="12"/>
  <text class="title" x="52" y="68">PaddleOCR-VL mean latency</text>
  <text class="note" x="52" y="94">Paired CORD development sample · {evidence["documents"]} documents · lower is better</text>
  <text class="label" x="52" y="145">Native</text>
  <rect class="track" x="230" y="122" width="500" height="34" rx="7"/>
  <rect class="native" x="230" y="122" width="{native_width:.2f}" height="34" rx="7"/>
  <text class="value" x="750" y="145">{native:.6f} s</text>
  <text class="label" x="52" y="211">Docker / vLLM</text>
  <rect class="track" x="230" y="188" width="500" height="34" rx="7"/>
  <rect class="served" x="230" y="188" width="{served_width:.2f}" height="34" rx="7"/>
  <text class="value" x="750" y="211">{served:.6f} s</text>
  <text class="value" x="52" y="276">{speedup:.6f}× mean speedup</text>
  <text class="note" x="52" y="310">Source: artifacts/v3/serving/paddleocr_vllm_comparison.json</text>
  <text class="note" x="52" y="332">Development evidence; content-presence quality metric is not official structured CORD F1.</text>'''
    return svg_document(900, 380, body, "PaddleOCR-VL native and Docker vLLM mean latency")


def gate_chart() -> str:
    evidence = json.loads((ROOT / "artifacts/v3/statistics/summary.json").read_text())
    gates = evidence["requirements"]
    labels = {
        "production_docker_stack": "Production Docker stack",
        "mlflow_postgresql_minio_persistence": "MLflow PostgreSQL + MinIO",
        "api_load": "API and load evidence",
        "fault_recovery": "Fault recovery",
        "expanded_security": "Expanded security",
        "reviewer_application": "Reviewer application",
        "docker_gpu": "Docker GPU",
        "accelerated_serving": "Accelerated serving",
    }
    rows = []
    for index, (key, label) in enumerate(labels.items()):
        passed = bool(gates[key])
        y = 126 + index * 38
        rows.append(
            f'<circle class="{"pass" if passed else "native"}" cx="66" cy="{y - 6}" r="9"/>'
            f'<text class="label" x="88" y="{y}">{escape(label)}</text>'
            f'<text class="value" x="790" y="{y}" text-anchor="end">{"PASS" if passed else "OPEN"}</text>'
        )
    passed_count = sum(bool(value) for value in gates.values())
    body = f'''
  <rect class="panel" x="24" y="24" width="852" height="414" rx="12"/>
  <text class="title" x="52" y="68">V3 frozen extension requirements</text>
  <text class="note" x="52" y="94">{passed_count}/{len(gates)} passed · decision: {escape(evidence["extension_decision"])}</text>
  {''.join(rows)}
  <text class="note" x="52" y="418">Source: artifacts/v3/statistics/summary.json</text>'''
    return svg_document(900, 462, body, "V3 extension requirement status")


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    outputs = {
        ASSETS / "paddle_latency_comparison.svg": latency_chart(),
        ASSETS / "v3_evidence_summary.svg": gate_chart(),
    }
    for path, content in outputs.items():
        path.write_text(content)
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
