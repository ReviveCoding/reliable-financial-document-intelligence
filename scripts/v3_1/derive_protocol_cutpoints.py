from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import cv2
import numpy as np


def flatten(value: object) -> list[str]:
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in flatten(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in flatten(item)]
    return [] if value is None else [str(value)]


def hierarchy_depth(value: object) -> int:
    if isinstance(value, dict):
        return 1 + max((hierarchy_depth(item) for item in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((hierarchy_depth(item) for item in value), default=0)
    return 0


def image_features(path: str) -> dict[str, float]:
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError(f"unreadable image: {path}")
    _, foreground = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(foreground > 0))
    skew = 0.0
    if len(coords) > 10:
        skew = float(cv2.minAreaRect(coords[:, ::-1].astype(np.float32))[-1])
        skew = skew - 90 if skew > 45 else skew
    return {
        "blur": float(cv2.Laplacian(image, cv2.CV_64F).var()),
        "luminance": float(image.mean()),
        "contrast": float(image.std()),
        "abs_skew": abs(skew),
        "edge_density": float((cv2.Canny(image, 100, 200) > 0).mean()),
        "foreground_density": float((foreground > 0).mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    values: dict[str, list[float]] = {}
    for line in args.input.read_text().splitlines():
        row = json.loads(line)
        ground_truth = row["ground_truth"]
        parsed = ground_truth["gt_parse"]
        leaves = flatten(parsed)
        words = [
            word
            for item in ground_truth.get("valid_line", [])
            for word in item.get("words", [])
        ]
        tokens = [str(word["text"]) for word in words]
        size = ground_truth["meta"]["image_size"]
        width, height = int(size["width"]), int(size["height"])
        megapixels = width * height / 1_000_000
        categories = [
            str(item.get("category", "")).casefold()
            for item in ground_truth.get("valid_line", [])
        ]
        total_text = str(parsed.get("total", {}).get("total_price", ""))
        digits = "".join(re.findall(r"\d", total_text))
        features = {
            "ground_truth_leaf_count": len(leaves),
            "line_item_count": len(parsed.get("menu", [])),
            "ocr_token_count": len(tokens),
            "document_text_length": sum(len(token) for token in tokens),
            "hierarchy_depth": hierarchy_depth(parsed),
            "image_aspect_ratio": width / height,
            "image_megapixels": megapixels,
            "text_density_tokens_per_megapixel": len(tokens) / megapixels,
            "numeric_token_density": sum(bool(re.search(r"\d", token)) for token in tokens)
            / max(1, len(tokens)),
            "monetary_field_density": sum(
                any(
                    term in category
                    for term in ("price", "total", "tax", "subtotal", "change", "cash")
                )
                for category in categories
            )
            / max(1, len(categories)),
            "total_amount": float(digits or 0),
            **image_features(row["pages"][0]["image_path"]),
        }
        for name, value in features.items():
            values.setdefault(name, []).append(float(value))
    result = {
        name: {
            "q33": float(np.quantile(series, 0.33)),
            "q50": float(np.quantile(series, 0.50)),
            "q67": float(np.quantile(series, 0.67)),
        }
        for name, series in sorted(values.items())
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
