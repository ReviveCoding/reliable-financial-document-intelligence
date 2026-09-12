from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dhash(path: Path) -> int:
    with Image.open(path) as image:
        gray = image.convert("L").resize((9, 8))
        pixels = np.asarray(gray)
    bits = pixels[:, 1:] > pixels[:, :-1]
    value = 0
    for bit in bits.ravel():
        value = (value << 1) | int(bit)
    return value


def compare_images(left: list[Path], right: list[Path]) -> dict[str, int]:
    left_sha = {sha256(path) for path in left}
    right_sha = {sha256(path) for path in right}
    left_hash = [dhash(path) for path in left]
    right_hash = [dhash(path) for path in right]
    near = sum(min((value ^ candidate).bit_count() for candidate in left_hash) <= 2 for value in right_hash)
    return {
        "left_images": len(left),
        "right_images": len(right),
        "exact_sha256_overlaps": len(left_sha & right_sha),
        "dhash_hamming_le_2_right_images": near,
    }


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def cord_text(row: dict) -> str:
    return " ".join(word.get("text", "") for line in row["ground_truth"].get("valid_line", []) for word in line.get("words", []))


def funsd_text(row: dict) -> str:
    return " ".join(word.get("text", "") for item in row["ground_truth"].get("form", []) for word in item.get("words", []))


def compare_text(left: list[str], right: list[str]) -> dict[str, int]:
    normalize = lambda value: " ".join(value.casefold().split())
    left_normalized = [normalize(value) for value in left]
    right_normalized = [normalize(value) for value in right]
    exact = len(set(left_normalized) & set(right_normalized))
    left_tokens = [set(value.split()) for value in left_normalized]
    near = 0
    for tokens in (set(value.split()) for value in right_normalized):
        similarity = max((len(tokens & candidate) / max(1, len(tokens | candidate)) for candidate in left_tokens), default=0)
        near += similarity >= 0.95
    return {"exact_normalized_text_overlaps": exact, "jaccard_ge_0_95_right_documents": near}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cord", type=Path, required=True)
    parser.add_argument("--funsd", type=Path, required=True)
    parser.add_argument("--synthetic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cord_train = jsonl(args.cord / "train.jsonl")
    cord_dev = jsonl(args.cord / "validation.jsonl")
    cord_test = jsonl(args.cord / "test.jsonl")
    funsd_train = jsonl(args.funsd / "train.jsonl")
    funsd_test = jsonl(args.funsd / "test.jsonl")
    synth_train = jsonl(args.synthetic / "train.jsonl")
    synth_dev = jsonl(args.synthetic / "dev.jsonl")

    cord_tokens = []
    cord_fields = Counter()
    for row in cord_train + cord_dev:
        truth = row["ground_truth"]
        cord_tokens.append(sum(len(line.get("words", [])) for line in truth.get("valid_line", [])))
        for group, values in truth.get("gt_parse", {}).items():
            if isinstance(values, dict):
                cord_fields.update(f"{group}.{key}" for key in values)
            elif isinstance(values, list):
                for item in values:
                    if isinstance(item, dict):
                        cord_fields.update(f"{group}.{key}" for key in item)
    funsd_labels = Counter()
    funsd_words = []
    for row in funsd_train:
        forms = row["ground_truth"]["form"]
        funsd_labels.update(item["label"] for item in forms)
        funsd_words.append(sum(len(item.get("words", [])) for item in forms))

    cord_images = args.cord / "images"
    funsd_raw = Path("/home/bjw-0/.local/share/rfdi-runtime/data/raw/funsd/dataset")
    result = {
        "experiment_id": "V2-E17",
        "eda_scope": "Development content only; locked content is reduced inside this audit to aggregate leakage counts and is never emitted or used for selection.",
        "eda": {
            "cord": {
                "development_documents": len(cord_train) + len(cord_dev),
                "ocr_tokens_mean": float(np.mean(cord_tokens)),
                "ocr_tokens_p95": float(np.quantile(cord_tokens, 0.95)),
                "field_frequency": dict(cord_fields.most_common()),
            },
            "funsd": {
                "training_documents": len(funsd_train),
                "words_mean": float(np.mean(funsd_words)),
                "words_p95": float(np.quantile(funsd_words, 0.95)),
                "entity_frequency": dict(funsd_labels),
            },
            "synthetic": {
                "development_documents": len(synth_train) + len(synth_dev),
                "document_types": dict(Counter(row["document_type"] for row in synth_train + synth_dev)),
                "corruptions": dict(Counter(row["corruption"]["type"] for row in synth_train + synth_dev)),
                "line_items_mean": float(np.mean([len(row["line_items"]) for row in synth_train + synth_dev])),
                "multi_page_documents": sum(len(row["pages"]) > 1 for row in synth_train + synth_dev),
            },
        },
        "leakage": {
            "cord_train_vs_validation": compare_images(sorted((cord_images / "train").glob("*.png")), sorted((cord_images / "validation").glob("*.png"))),
            "cord_train_vs_test": compare_images(sorted((cord_images / "train").glob("*.png")), sorted((cord_images / "test").glob("*.png"))),
            "funsd_train_vs_test": compare_images(sorted((funsd_raw / "training_data/images").glob("*")), sorted((funsd_raw / "testing_data/images").glob("*"))),
            "synthetic_train_vs_dev": compare_images(sorted((args.synthetic / "train").glob("*.png")), sorted((args.synthetic / "dev").glob("*.png"))),
            "synthetic_train_vs_final": compare_images(sorted((args.synthetic / "train").glob("*.png")), sorted((args.synthetic / "final").glob("*.png"))),
            "cord_text_train_vs_validation": compare_text([cord_text(row) for row in cord_train], [cord_text(row) for row in cord_dev]),
            "cord_text_train_vs_test": compare_text([cord_text(row) for row in cord_train], [cord_text(row) for row in cord_test]),
            "funsd_text_train_vs_test": compare_text([funsd_text(row) for row in funsd_train], [funsd_text(row) for row in funsd_test]),
            "synthetic_vendor_overlap_train_dev": len({row["vendor_group"] for row in synth_train} & {row["vendor_group"] for row in synth_dev}),
            "synthetic_layout_overlap_train_dev": len({row["layout_cluster"] for row in synth_train} & {row["layout_cluster"] for row in synth_dev}),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
