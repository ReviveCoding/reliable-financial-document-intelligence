from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from PIL import Image


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def valid_box(box: list[float]) -> bool:
    return len(box) == 4 and 0 <= box[0] <= box[2] <= 1 and 0 <= box[1] <= box[3] <= 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    split_rows = {}
    for split in ("train", "dev"):
        selected = [json.loads(line) for line in (args.root / f"{split}.jsonl").read_text().splitlines()]
        split_rows[split] = selected
        rows.extend(selected)
    bad_images = 0
    bad_boxes = 0
    pages = 0
    line_item_cells = 0
    for row in rows:
        for path_text in row["pages"]:
            pages += 1
            try:
                with Image.open(path_text) as image:
                    image.verify()
            except Exception:
                bad_images += 1
        bad_boxes += sum(not valid_box(field["bbox"]) for field in row["fields"].values())
        for item in row["line_items"]:
            line_item_cells += len(item["bboxes"])
            bad_boxes += sum(not valid_box(box) for box in item["bboxes"].values())
    train_vendors = {row["vendor_group"] for row in split_rows["train"]}
    dev_vendors = {row["vendor_group"] for row in split_rows["dev"]}
    train_layouts = {row["layout_cluster"] for row in split_rows["train"]}
    dev_layouts = {row["layout_cluster"] for row in split_rows["dev"]}
    result = {
        "experiment_id": "V2-E03",
        "dataset": "R-FDI Rendered Synthetic V2",
        "version": "2.0.0",
        "seed": 20260911,
        "audited_content_splits": ["train", "dev"],
        "documents_audited": len(rows),
        "pages_verified": pages,
        "bad_images": bad_images,
        "bad_boxes": bad_boxes,
        "line_item_cells_with_boxes": line_item_cells,
        "document_types": dict(Counter(row["document_type"] for row in rows)),
        "corruptions": dict(Counter(row["corruption"]["type"] for row in rows)),
        "vendor_overlap_train_dev": len(train_vendors & dev_vendors),
        "layout_id_overlap_train_dev": len(train_layouts & dev_layouts),
        "split_geometry_policy": "Train/dev/final use disjoint margin ranges, header offsets, table columns, and template variant IDs.",
        "jsonl_sha256": {split: sha256(args.root / f"{split}.jsonl") for split in ("train", "dev", "final")},
        "final_content_policy": "Only the final JSONL checksum was read before authorization; final record content was not parsed.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
