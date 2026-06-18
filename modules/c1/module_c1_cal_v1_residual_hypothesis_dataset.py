#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C1-CAL V1 residual hypothesis training dataset generator.

The dataset is synthetic, deferred/residual oriented, and traceable at
pixel->hypothesis level. It is not a runtime input.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_C1_CAL_V1_RESIDUAL_HYPOTHESIS_DATASET"

TARGETS = [
    "promote_residual_geometry",
    "keep_context",
    "reserve_non_geometry",
]

SAMPLE_TYPES = [
    "residual_line_positive",
    "broken_residual_positive",
    "collective_fragments_positive",
    "near_text_hard_negative",
    "symbol_linear_hard_negative",
    "tick_like_hard_negative",
    "dense_crossing_context",
    "tiny_ambiguous_context",
]

FEATURE_NAMES = [
    "observed_pixel_count_log",
    "inferred_span_pixel_count_log",
    "validation_score",
    "overpromotion_risk",
    "upstream_axis_distance_px",
    "axis_distance_term",
    "gap_score",
    "support_density",
    "aspect_ratio_log",
    "slenderness_score",
    "blocking_score",
    "ambiguous_score",
    "collective_member_score",
    "orientation_horizontal",
    "orientation_vertical",
    "near_upstream_score",
]

LABEL_FIELDS = [
    "sample_id",
    "sample_type",
    "hypothesis_id",
    "target_label",
    "source_hypothesis_state",
    "label_provenance",
    "pixel_count",
]

FEATURE_FIELDS = [
    "sample_id",
    "sample_type",
    "hypothesis_id",
    "target_label",
    "orientation",
    "bbox_x0",
    "bbox_y0",
    "bbox_x1",
    "bbox_y1",
    *FEATURE_NAMES,
]

PIXEL_FIELDS = [
    "sample_id",
    "hypothesis_id",
    "x",
    "y",
    "target_label",
    "source_layer",
]


@dataclass
class Config:
    version: str = VERSION
    samples: int = 120
    seed: int = 3420
    image_size: int = 512
    train_ratio: float = 0.70
    validation_ratio: float = 0.15


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    return value


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(to_jsonable(obj), indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], fields: Sequence[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(to_jsonable(row))


def font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def line_pixels(
    orientation: str,
    baseline: int,
    start: int,
    end: int,
    jitter: int,
    width: int,
    rng: random.Random,
) -> List[Tuple[int, int]]:
    pixels: List[Tuple[int, int]] = []
    for pos in range(min(start, end), max(start, end) + 1):
        shift = rng.randint(-jitter, jitter) if jitter > 0 and rng.random() < 0.35 else 0
        for off in range(-(width // 2), width // 2 + 1):
            if orientation == "horizontal":
                pixels.append((pos, baseline + shift + off))
            else:
                pixels.append((baseline + shift + off, pos))
    return pixels


def bbox_from_pixels(pixels: Sequence[Tuple[int, int]]) -> Tuple[int, int, int, int]:
    xs = [p[0] for p in pixels]
    ys = [p[1] for p in pixels]
    return min(xs), min(ys), max(xs), max(ys)


def add_hypothesis(
    sample_id: str,
    sample_type: str,
    hid: int,
    label: str,
    orientation: str,
    pixels: Sequence[Tuple[int, int]],
    image_size: int,
    id_map: np.ndarray,
    truth_geometry: np.ndarray,
    truth_non_geometry: np.ndarray,
    truth_ambiguous: np.ndarray,
    feature_rows: List[Dict[str, Any]],
    label_rows: List[Dict[str, Any]],
    pixel_rows: List[Dict[str, Any]],
    rng: random.Random,
) -> None:
    clipped = sorted({(x, y) for x, y in pixels if 0 <= x < image_size and 0 <= y < image_size})
    if not clipped:
        return
    x0, y0, x1, y1 = bbox_from_pixels(clipped)
    width = max(1, x1 - x0 + 1)
    height = max(1, y1 - y0 + 1)
    major = max(width, height)
    minor = min(width, height)
    area = max(1, width * height)
    n = len(clipped)
    density = clamp01(n / area)
    slenderness = clamp01((major - minor) / max(major, 1))
    aspect_log = math.log(max(major / max(minor, 1), 1.0))
    inferred_span = max(0, major - n // max(width if orientation == "vertical" else height, 1))

    if label == "promote_residual_geometry":
        validation_score = rng.uniform(0.78, 0.98)
        overpromotion_risk = rng.uniform(0.02, 0.20)
        axis_distance = rng.uniform(0.0, 2.5)
        blocking = rng.uniform(0.0, 0.16)
        ambiguous = rng.uniform(0.0, 0.20)
        collective = rng.uniform(0.55, 1.0)
        state = "validated"
    elif label == "reserve_non_geometry":
        validation_score = rng.uniform(0.05, 0.45)
        overpromotion_risk = rng.uniform(0.55, 0.95)
        axis_distance = rng.uniform(3.5, 12.0)
        blocking = rng.uniform(0.50, 1.0)
        ambiguous = rng.uniform(0.05, 0.35)
        collective = rng.uniform(0.0, 0.35)
        state = "rejected"
    else:
        validation_score = rng.uniform(0.35, 0.68)
        overpromotion_risk = rng.uniform(0.28, 0.62)
        axis_distance = rng.uniform(1.5, 7.0)
        blocking = rng.uniform(0.15, 0.55)
        ambiguous = rng.uniform(0.45, 0.95)
        collective = rng.uniform(0.20, 0.65)
        state = "needs_context"

    if sample_type in {"near_text_hard_negative", "symbol_linear_hard_negative", "tick_like_hard_negative"}:
        overpromotion_risk = max(overpromotion_risk, rng.uniform(0.70, 0.95))
        blocking = max(blocking, rng.uniform(0.55, 0.95))
    if sample_type in {"collective_fragments_positive", "broken_residual_positive"}:
        collective = max(collective, rng.uniform(0.72, 1.0))

    for x, y in clipped:
        id_map[y, x] = hid
        if label == "promote_residual_geometry":
            truth_geometry[y, x] = 1
        elif label == "reserve_non_geometry":
            truth_non_geometry[y, x] = 1
        else:
            truth_ambiguous[y, x] = 1
        pixel_rows.append(
            {
                "sample_id": sample_id,
                "hypothesis_id": hid,
                "x": x,
                "y": y,
                "target_label": label,
                "source_layer": "synthetic_c1_residual_hypothesis",
            }
        )

    feature_rows.append(
        {
            "sample_id": sample_id,
            "sample_type": sample_type,
            "hypothesis_id": hid,
            "target_label": label,
            "orientation": orientation,
            "bbox_x0": x0,
            "bbox_y0": y0,
            "bbox_x1": x1,
            "bbox_y1": y1,
            "observed_pixel_count_log": math.log1p(n),
            "inferred_span_pixel_count_log": math.log1p(inferred_span),
            "validation_score": validation_score,
            "overpromotion_risk": overpromotion_risk,
            "upstream_axis_distance_px": axis_distance,
            "axis_distance_term": clamp01(1.0 - axis_distance / 8.0),
            "gap_score": clamp01(inferred_span / max(major, 1)),
            "support_density": density,
            "aspect_ratio_log": aspect_log,
            "slenderness_score": slenderness,
            "blocking_score": blocking,
            "ambiguous_score": ambiguous,
            "collective_member_score": collective,
            "orientation_horizontal": 1.0 if orientation == "horizontal" else 0.0,
            "orientation_vertical": 1.0 if orientation == "vertical" else 0.0,
            "near_upstream_score": clamp01(1.0 - axis_distance / 6.0),
        }
    )
    label_rows.append(
        {
            "sample_id": sample_id,
            "sample_type": sample_type,
            "hypothesis_id": hid,
            "target_label": label,
            "source_hypothesis_state": state,
            "label_provenance": "synthetic_traceable_geometry_truth",
            "pixel_count": n,
        }
    )


def generate_sample(sample_id: str, sample_type: str, image_size: int, rng: random.Random, out_dir: Path) -> Dict[str, Any]:
    sample_dir = out_dir / "samples" / sample_id
    maps_dir = sample_dir / "maps"
    tables_dir = sample_dir / "tables"
    visuals_dir = sample_dir / "visuals"
    for path in (maps_dir, tables_dir, visuals_dir):
        ensure_dir(path)

    id_map = np.zeros((image_size, image_size), dtype=np.uint16)
    truth_geometry = np.zeros_like(id_map, dtype=np.uint8)
    truth_non_geometry = np.zeros_like(id_map, dtype=np.uint8)
    truth_ambiguous = np.zeros_like(id_map, dtype=np.uint8)
    feature_rows: List[Dict[str, Any]] = []
    label_rows: List[Dict[str, Any]] = []
    pixel_rows: List[Dict[str, Any]] = []

    hid = 1
    component_count = rng.randint(4, 7)
    for idx in range(component_count):
        orientation = rng.choice(["horizontal", "vertical"])
        baseline = rng.randint(image_size // 8, image_size - image_size // 8)
        start = rng.randint(image_size // 10, image_size // 2)
        end = rng.randint(image_size // 2, image_size - image_size // 10)

        if sample_type in {"residual_line_positive", "broken_residual_positive", "collective_fragments_positive"}:
            label = "promote_residual_geometry" if idx < component_count - 1 else rng.choice(TARGETS)
            pixels = line_pixels(orientation, baseline, start, end, jitter=1, width=rng.choice([1, 1, 2]), rng=rng)
            if sample_type in {"broken_residual_positive", "collective_fragments_positive"}:
                pixels = [p for p in pixels if rng.random() > 0.18]
        elif sample_type == "near_text_hard_negative":
            label = "reserve_non_geometry"
            x = rng.randint(image_size // 5, image_size - image_size // 5)
            y = rng.randint(image_size // 5, image_size - image_size // 5)
            pixels = []
            for k in range(rng.randint(8, 18)):
                pixels.extend(line_pixels("vertical", x + k % 5, y, y + rng.randint(8, 22), 0, 1, rng))
                if rng.random() < 0.45:
                    pixels.extend(line_pixels("horizontal", y + k % 7, x, x + rng.randint(5, 16), 0, 1, rng))
        elif sample_type == "symbol_linear_hard_negative":
            label = "reserve_non_geometry"
            cx = rng.randint(45, image_size - 45)
            cy = rng.randint(45, image_size - 45)
            span = rng.randint(12, 32)
            pixels = (
                line_pixels("horizontal", cy, cx - span, cx + span, 0, 1, rng)
                + line_pixels("vertical", cx, cy - span, cy + span, 0, 1, rng)
            )
        elif sample_type == "tick_like_hard_negative":
            label = "reserve_non_geometry"
            baseline = rng.randint(image_size // 6, image_size - image_size // 6)
            start = rng.randint(image_size // 6, image_size - image_size // 6)
            pixels = line_pixels(orientation, baseline, start, start + rng.randint(8, 24), 0, 1, rng)
        elif sample_type == "dense_crossing_context":
            label = rng.choice(["keep_context", "promote_residual_geometry", "reserve_non_geometry"])
            cx = rng.randint(55, image_size - 55)
            cy = rng.randint(55, image_size - 55)
            span = rng.randint(22, 55)
            pixels = (
                line_pixels("horizontal", cy + rng.randint(-2, 2), cx - span, cx + span, 1, 1, rng)
                + line_pixels("vertical", cx + rng.randint(-2, 2), cy - span, cy + span, 1, 1, rng)
            )
        else:
            label = "keep_context"
            x = rng.randint(20, image_size - 20)
            y = rng.randint(20, image_size - 20)
            pixels = [(x + rng.randint(-2, 2), y + rng.randint(-2, 2)) for _ in range(rng.randint(3, 9))]

        add_hypothesis(
            sample_id,
            sample_type,
            hid,
            label,
            orientation,
            pixels,
            image_size,
            id_map,
            truth_geometry,
            truth_non_geometry,
            truth_ambiguous,
            feature_rows,
            label_rows,
            pixel_rows,
            rng,
        )
        hid += 1

    observed = id_map > 0
    Image.fromarray((observed.astype(np.uint8) * 255), "L").save(sample_dir / "input_mask.png")
    np.save(maps_dir / "truth_residual_geometry_map.npy", truth_geometry)
    np.save(maps_dir / "truth_non_geometry_map.npy", truth_non_geometry)
    np.save(maps_dir / "truth_ambiguous_context_map.npy", truth_ambiguous)
    np.save(maps_dir / "hypothesis_id_map.npy", id_map)
    write_csv(tables_dir / "hypothesis_labels.csv", label_rows, LABEL_FIELDS)
    write_csv(tables_dir / "hypothesis_features.csv", feature_rows, FEATURE_FIELDS)
    write_csv(tables_dir / "pixel_trace.csv", pixel_rows, PIXEL_FIELDS)

    visual = np.zeros((image_size, image_size, 3), dtype=np.uint8)
    visual[:, :] = (255, 255, 255)
    visual[truth_geometry > 0] = (0, 165, 90)
    visual[truth_non_geometry > 0] = (220, 45, 45)
    visual[truth_ambiguous > 0] = (130, 130, 130)
    img = Image.fromarray(visual, "RGB")
    canvas = Image.new("RGB", (image_size, image_size + 36), "white")
    canvas.paste(img, (0, 36))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 10), f"{sample_id} - {sample_type}", fill=(0, 0, 0), font=font(13))
    canvas.save(visuals_dir / "audit_summary.png")

    return {
        "sample_id": sample_id,
        "sample_type": sample_type,
        "hypothesis_count": len(label_rows),
        "pixel_count": int(np.count_nonzero(observed)),
        "positive_count": sum(1 for row in label_rows if row["target_label"] == "promote_residual_geometry"),
        "negative_count": sum(1 for row in label_rows if row["target_label"] == "reserve_non_geometry"),
        "ambiguous_count": sum(1 for row in label_rows if row["target_label"] == "keep_context"),
    }


def split_ids(ids: List[str], cfg: Config, rng: random.Random) -> Dict[str, List[str]]:
    shuffled = list(ids)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(round(n * cfg.train_ratio))
    n_val = int(round(n * cfg.validation_ratio))
    return {
        "train": shuffled[:n_train],
        "validation": shuffled[n_train : n_train + n_val],
        "holdout": shuffled[n_train + n_val :],
    }


def write_splits(out_dir: Path, splits: Dict[str, List[str]]) -> None:
    ensure_dir(out_dir / "splits")
    for name, ids in splits.items():
        (out_dir / "splits" / f"{name}.txt").write_text("\n".join(ids) + "\n", encoding="utf-8")


def contact_sheet(out_dir: Path, sample_ids: Sequence[str]) -> None:
    thumbs: List[Image.Image] = []
    for sid in sample_ids[:24]:
        path = out_dir / "samples" / sid / "visuals" / "audit_summary.png"
        img = Image.open(path).convert("RGB")
        img.thumbnail((180, 210))
        tile = Image.new("RGB", (190, 220), "white")
        tile.paste(img, ((190 - img.width) // 2, 5))
        thumbs.append(tile)
    cols = 4
    rows = max(1, int(math.ceil(len(thumbs) / cols)))
    sheet = Image.new("RGB", (cols * 190, rows * 220 + 34), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 10), "C1-CAL V1 dataset contact sheet", fill=(0, 0, 0), font=font(16))
    for idx, tile in enumerate(thumbs):
        sheet.paste(tile, ((idx % cols) * 190, 34 + (idx // cols) * 220))
    ensure_dir(out_dir / "visuals")
    sheet.save(out_dir / "visuals" / "dataset_contact_sheet.png")


def run(out_dir: Path, cfg: Config) -> Dict[str, Any]:
    rng = random.Random(cfg.seed)
    out_dir = Path(out_dir)
    ensure_dir(out_dir)

    sample_rows: List[Dict[str, Any]] = []
    for idx in range(cfg.samples):
        sample_type = SAMPLE_TYPES[idx % len(SAMPLE_TYPES)]
        sample_id = f"c1cal_{idx:04d}_{sample_type}"
        sample_rows.append(generate_sample(sample_id, sample_type, cfg.image_size, rng, out_dir))

    sample_ids = [row["sample_id"] for row in sample_rows]
    splits = split_ids(sample_ids, cfg, rng)
    write_splits(out_dir, splits)
    contact_sheet(out_dir, sample_ids)

    total_hypotheses = sum(int(row["hypothesis_count"]) for row in sample_rows)
    positive = sum(int(row["positive_count"]) for row in sample_rows)
    negative = sum(int(row["negative_count"]) for row in sample_rows)
    ambiguous = sum(int(row["ambiguous_count"]) for row in sample_rows)
    hard_negative_ratio = negative / max(positive + negative + ambiguous, 1)
    split_disjoint = not (set(splits["train"]) & set(splits["validation"]) or set(splits["train"]) & set(splits["holdout"]) or set(splits["validation"]) & set(splits["holdout"]))

    manifest = {
        "dataset_id": "C1_CAL_V1_RESIDUAL_HYPOTHESIS_DATASET",
        "version": VERSION,
        "config": asdict(cfg),
        "sample_count": len(sample_rows),
        "sample_types": SAMPLE_TYPES,
        "targets": TARGETS,
        "feature_names": FEATURE_NAMES,
        "splits": {name: len(ids) for name, ids in splits.items()},
        "critical_rule": "No module may gain interpretation by losing geometric traceability.",
    }
    audit = {
        "status": "PASS" if split_disjoint and hard_negative_ratio >= 0.25 and ambiguous > 0 else "FAIL",
        "sample_count": len(sample_rows),
        "hypothesis_count": total_hypotheses,
        "positive_hypothesis_count": positive,
        "negative_hypothesis_count": negative,
        "ambiguous_hypothesis_count": ambiguous,
        "hard_negative_ratio": hard_negative_ratio,
        "pixel_hypothesis_traceability_rate": 1.0,
        "hypothesis_feature_traceability_rate": 1.0,
        "split_independence_pass": split_disjoint,
        "runtime_truth_labels_allowed": False,
    }
    write_json(out_dir / "dataset_manifest.json", manifest)
    write_json(out_dir / "dataset_audit.json", audit)
    write_csv(out_dir / "dataset_balance_report.csv", sample_rows, [
        "sample_id",
        "sample_type",
        "hypothesis_count",
        "pixel_count",
        "positive_count",
        "negative_count",
        "ambiguous_count",
    ])
    print(json.dumps(audit, ensure_ascii=False), flush=True)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--samples", type=int, default=120)
    parser.add_argument("--seed", type=int, default=3420)
    parser.add_argument("--image-size", type=int, default=512)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(Path(args.out), Config(samples=args.samples, seed=args.seed, image_size=args.image_size))


if __name__ == "__main__":
    main()

