from __future__ import annotations

import argparse
import asyncio
import base64
import json
import statistics
import time
from pathlib import Path
from typing import Any

import httpx


def quantile(values: list[float], q: float) -> float:
    values = sorted(values)
    position = (len(values) - 1) * q
    lower = int(position); upper = min(lower + 1, len(values)); weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


async def wait_result(client: httpx.AsyncClient, document_id: str, timeout: float = 90) -> dict[str, Any]:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        response = await client.get(f"/documents/{document_id}/result")
        if response.status_code == 200:
            return response.json()
        await asyncio.sleep(0.01)
    raise TimeoutError(document_id)


async def run_one(client: httpx.AsyncClient, semaphore: asyncio.Semaphore, payload: dict[str, Any]) -> dict[str, Any]:
    async with semaphore:
        started = time.perf_counter()
        response = await client.post("/documents", json=payload)
        response.raise_for_status()
        result = await wait_result(client, response.json()["document_id"])
        return {"e2e_ms": (time.perf_counter() - started) * 1000, "queue_wait_ms": result["queue_wait_ms"], "inference_ms": result["inference_ms"], "db_ms": result["db_ms"]}


def summarize(records: list[dict[str, float]], wall: float, errors: int) -> dict[str, Any]:
    output: dict[str, Any] = {"completed": len(records), "errors": errors, "error_rate": errors / (len(records) + errors), "throughput_docs_second": len(records) / wall, "wall_seconds": wall}
    for metric in ("e2e_ms", "queue_wait_ms", "inference_ms", "db_ms"):
        values = [record[metric] for record in records]
        output[metric] = {"p50": quantile(values, .5), "p95": quantile(values, .95), "p99": quantile(values, .99), "mean": statistics.mean(values)}
    return output


async def main_async(args: argparse.Namespace) -> dict[str, Any]:
    image_rows = [json.loads(line) for line in args.input_jsonl.read_text().splitlines()] if args.input_jsonl else []
    results = []
    async with httpx.AsyncClient(base_url=args.base_url, timeout=120) as client:
        for concurrency in args.concurrency:
            payloads = []
            for index in range(args.documents):
                if image_rows:
                    row = image_rows[index % len(image_rows)]
                    # PNG decoders ignore bytes after IEND; this unique audit suffix preserves pixels
                    # while preventing content-addressed idempotency from collapsing load requests.
                    content = Path(row["pages"][0]["image_path"]).read_bytes() + f"\nRFDI-V3-LOAD-{concurrency}-{index}-{time.time_ns()}".encode(); media_type = "image/png"
                else:
                    content = f"Invoice: V3-{concurrency}-{index}\nSubtotal: 10.00\nTax: 2.00\nTotal: 12.00\nCurrency: USD\nMemo: load-{time.time_ns()}".encode(); media_type = "text/plain"
                payloads.append({"idempotency_key": f"load-{args.route}-{concurrency}-{index}-{time.time_ns()}", "content_b64": base64.b64encode(content).decode(), "media_type": media_type, "route": args.route})
            semaphore = asyncio.Semaphore(concurrency)
            started = time.perf_counter(); responses = await asyncio.gather(*(run_one(client, semaphore, payload) for payload in payloads), return_exceptions=True); wall = time.perf_counter() - started
            records = [response for response in responses if isinstance(response, dict)]
            results.append({"concurrency": concurrency, **summarize(records, wall, len(responses) - len(records))})
    return {"experiment_id": "V3-E06-GPU" if args.route == "donut" else "V3-E06-CACHED", "route": args.route, "documents_per_level": args.documents, "concurrency_results": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8130")
    parser.add_argument("--route", choices=["cheap", "donut"], default="cheap")
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 2, 4, 8])
    parser.add_argument("--documents", type=int, default=40)
    parser.add_argument("--input-jsonl", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); result = asyncio.run(main_async(args)); args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n"); print(json.dumps(result, sort_keys=True))


if __name__ == "__main__": main()
