"""Acquire public V2 datasets into external runtime storage and canonicalize them."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

import requests
from datasets import load_dataset
from huggingface_hub import HfApi, snapshot_download
from PIL import Image

CORD_ID = "naver-clova-ix/cord-v2"
CORD_REVISION = "7f0115a4b758a71d6473b8d085751692da2fef98"
FUNSD_URL = "https://guillaumejaume.github.io/FUNSD/dataset.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def acquire_cord(root: Path) -> dict[str, Any]:
    raw = root / "raw" / "cord_v2"
    raw.mkdir(parents=True, exist_ok=True)
    snapshot_download(CORD_ID, repo_type="dataset", revision=CORD_REVISION, local_dir=raw,
                      allow_patterns=["data/*.parquet", "README.md"])
    data_files: dict[str, list[str]] = {}
    for split in ("train", "validation", "test"):
        matches = sorted(str(path) for path in (raw / "data").glob(f"{split}-*.parquet"))
        if not matches:
            raise RuntimeError(f"CORD split missing: {split}")
        data_files[split] = matches
    dataset = load_dataset("parquet", data_files=data_files)
    processed = root / "processed" / "cord_v2" / CORD_REVISION
    image_root = processed / "images"
    counts: dict[str, int] = {}
    output_hashes: dict[str, str] = {}
    for split, frame in dataset.items():
        split_images = image_root / split
        split_images.mkdir(parents=True, exist_ok=True)
        canonical = processed / f"{split}.jsonl"
        with canonical.open("w", encoding="utf-8") as handle:
            for index, row in enumerate(frame):
                image_path = split_images / f"{index:05d}.png"
                image_value = row["image"]
                if isinstance(image_value, dict) and image_value.get("bytes"):
                    raw_bytes = image_value["bytes"]
                    # Official CORD parquet stores lossless PNG bytes. Preserve them exactly;
                    # do not spend minutes recompressing or alter pixel evidence.
                    if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                        image_path.write_bytes(raw_bytes)
                        image = None
                    else:
                        image = Image.open(io.BytesIO(raw_bytes))
                elif isinstance(image_value, dict) and image_value.get("path"):
                    image = Image.open(image_value["path"])
                else:
                    image = image_value
                if image is not None:
                    image.convert("RGB").save(image_path)
                truth = json.loads(row["ground_truth"])
                record = {"document_id": f"cord-v2-{split}-{index:05d}", "source_dataset": "CORD v2",
                          "source_revision": CORD_REVISION, "split": split, "document_type": "receipt",
                          "pages": [{"page": 0, "image_path": str(image_path)}],
                          "ground_truth": truth, "provenance": {"row_index": index, "official_id": CORD_ID}}
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        counts[split] = len(frame)
        output_hashes[split] = sha256(canonical)
    parquet_hashes = {str(path.relative_to(raw)): sha256(path) for path in sorted((raw / "data").glob("*.parquet"))}
    result = {"dataset": "CORD v2", "official_id": CORD_ID, "revision": CORD_REVISION,
              "license": "cc-by-4.0", "counts": counts, "parquet_sha256": parquet_hashes,
              "canonical_sha256": output_hashes, "raw_root": str(raw), "processed_root": str(processed)}
    dump_json(processed / "manifest.json", result)
    return result


def acquire_funsd(root: Path) -> dict[str, Any]:
    raw = root / "raw" / "funsd"
    raw.mkdir(parents=True, exist_ok=True)
    archive = raw / "dataset.zip"
    if not archive.exists():
        with requests.get(FUNSD_URL, stream=True, timeout=120) as response:
            response.raise_for_status()
            with archive.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    handle.write(chunk)
    extracted = raw / "dataset"
    if not extracted.exists():
        with zipfile.ZipFile(archive) as source:
            source.extractall(raw)
    # Official archive root is dataset/{training_data,testing_data}.
    processed = root / "processed" / "funsd" / "official-2019"
    counts: dict[str, int] = {}
    output_hashes: dict[str, str] = {}
    for source_name, split in (("training_data", "train"), ("testing_data", "test")):
        annotations = extracted / source_name / "annotations"
        images = extracted / source_name / "images"
        paths = sorted(annotations.glob("*.json"))
        canonical = processed / f"{split}.jsonl"
        canonical.parent.mkdir(parents=True, exist_ok=True)
        with canonical.open("w", encoding="utf-8") as handle:
            for annotation in paths:
                truth = json.loads(annotation.read_text(encoding="utf-8"))
                candidates = list(images.glob(annotation.stem + ".*"))
                if len(candidates) != 1:
                    raise RuntimeError(f"FUNSD image mismatch for {annotation.stem}: {candidates}")
                record = {"document_id": f"funsd-{split}-{annotation.stem}", "source_dataset": "FUNSD",
                          "source_revision": "official-2019-07-05", "split": split, "document_type": "form",
                          "pages": [{"page": 0, "image_path": str(candidates[0])}], "ground_truth": truth,
                          "provenance": {"annotation_sha256": sha256(annotation), "source_url": FUNSD_URL}}
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        counts[split] = len(paths)
        output_hashes[split] = sha256(canonical)
    result = {"dataset": "FUNSD", "revision": "official-2019-07-05", "source_url": FUNSD_URL,
              "archive_sha256": sha256(archive), "archive_bytes": archive.stat().st_size,
              "counts": counts, "canonical_sha256": output_hashes, "raw_root": str(raw),
              "processed_root": str(processed), "usage_terms": "Official public project archive; attribution/citation required."}
    dump_json(processed / "manifest.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", choices=("cord", "funsd", "all"))
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("RFDI_DATA_ROOT", "/home/bjw-0/.local/share/rfdi-runtime/data")))
    args = parser.parse_args()
    results = {}
    if args.dataset in {"cord", "all"}: results["cord"] = acquire_cord(args.data_root)
    if args.dataset in {"funsd", "all"}: results["funsd"] = acquire_funsd(args.data_root)
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
