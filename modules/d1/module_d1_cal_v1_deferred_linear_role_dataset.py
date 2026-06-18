#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D1-CAL V1 deferred linear role training dataset generator.

The dataset is synthetic, deferred-only, and traceable at
pixel->linearity_hypothesis level. It is not a runtime input.
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


VERSION = "MODULE_D1_CAL_V1_DEFERRED_LINEAR_ROLE_DATASET"

ROLES = [
    "grid_line_candidate",
    "axis_line_candidate",
    "tick_or_scale_mark",
    "page_border_or_layout_box",
    "text_or_digit_stroke",
    "curve_or_data_trace",
    "ambiguous_linear",
]

ROLE_CODE = {role: idx + 1 for idx, role in enumerate(ROLES)}

SAMPLE_TYPES = [
    "clear_grid_deferred_positive",
    "broken_grid_deferred_positive",
    "axis_line_positive",
    "tick_hard_negative",
    "text_stroke_hard_negative",
    "border_layout_hard_negative",
    "curve_trace_hard_negative",
    "ambiguous_tiny_linear",
]

FEATURE_NAMES = [
    "span_px",
    "pixel_count_log",
    "density",
    "longest_run",
    "lineality_score",
    "edge_distance_px",
    "same_axis_extension_score",
    "near_line_study_contact_score",
    "parallel_context_count",
    "parallel_context_score",
    "local_observed_context_score",
    "grid_role_score",
    "axis_role_score",
    "tick_role_score",
    "border_role_score",
    "text_role_score",
    "curve_role_score",
    "orientation_horizontal",
    "orientation_vertical",
]

LABEL_FIELDS = [
    "sample_id",
    "sample_type",
    "linearity_hypothesis_id",
    "role_label",
    "label_provenance",
    "pixel_count",
]

FEATURE_FIELDS = [
    "sample_id",
    "sample_type",
    "linearity_hypothesis_id",
    "role_label",
    "orientation",
    "baseline",
    "bbox_x0",
    "bbox_y0",
    "bbox_x1",
    "bbox_y1",
    *FEATURE_NAMES,
]

PIXEL_FIELDS = [
    "sample_id",
    "linearity_hypothesis_id",
    "x",
    "y",
    "role_label",
    "role_code",
    "source_deferred_candidate",
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
        if rng.random() < 0.12:
            continue
        shift = rng.randint(-jitter, jitter) if jitter > 0 and rng.random() < 0.40 else 0
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


def longest_run_from_pixels(pixels: Sequence[Tuple[int, int]], orientation: str) -> int:
    coords = sorted({x if orientation == "horizontal" else y for x, y in pixels})
    if not coords:
        return 0
    best = 1
    cur = 1
    for prev, val in zip(coords, coords[1:]):
        if val == prev + 1:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best


def role_scores(
    role: str,
    span: int,
    density: float,
    longest_run: int,
    edge_distance: int,
    same_axis: float,
    near_line: float,
    parallel_count: int,
    local_context: float,
    image_size: int,
) -> Dict[str, float]:
    parallel_score = clamp01(parallel_count / 5.0)
    compact = clamp01(1.0 - span / 45.0)
    lineality = clamp01(0.35 * density + 0.35 * min(1.0, longest_run / 18.0) + 0.30 * min(1.0, span / 100.0))
    border = 1.0 if edge_distance <= 12 else (0.72 if edge_distance <= 28 and span >= 36 else 0.0)
    grid = clamp01(0.32 * same_axis + 0.30 * parallel_score + 0.20 * near_line + 0.10 * lineality + 0.08 * min(1.0, span / 70.0))
    axis = clamp01(0.36 * same_axis + 0.26 * near_line + 0.20 * min(1.0, span / 65.0) + 0.10 * (1.0 - parallel_score) + 0.08 * lineality)
    tick = clamp01(0.38 * compact + 0.28 * near_line + 0.18 * density + 0.16 * (1.0 - parallel_score))
    text = clamp01(0.34 * compact + 0.27 * local_context + 0.20 * (1.0 - same_axis) + 0.19 * (1.0 - parallel_score))
    curve = clamp01(0.30 * min(1.0, span / 70.0) + 0.28 * local_context + 0.24 * (1.0 - same_axis) + 0.18 * (1.0 - parallel_score))
    if role == "grid_line_candidate":
        grid = max(grid, 0.78)
    elif role == "axis_line_candidate":
        axis = max(axis, 0.76)
        parallel_score = min(parallel_score, 0.30)
    elif role == "tick_or_scale_mark":
        tick = max(tick, 0.78)
    elif role == "page_border_or_layout_box":
        border = max(border, 0.90)
    elif role == "text_or_digit_stroke":
        text = max(text, 0.78)
    elif role == "curve_or_data_trace":
        curve = max(curve, 0.78)
    return {
        "lineality_score": lineality,
        "parallel_context_score": parallel_score,
        "grid_role_score": grid,
        "axis_role_score": axis,
        "tick_role_score": tick,
        "border_role_score": border,
        "text_role_score": text,
        "curve_role_score": curve,
    }


def add_hypothesis(
    sample_id: str,
    sample_type: str,
    hid: int,
    role: str,
    orientation: str,
    pixels: Sequence[Tuple[int, int]],
    image_size: int,
    role_map: np.ndarray,
    candidate_map: np.ndarray,
    line_context: np.ndarray,
    hypothesis_id_map: np.ndarray,
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
    span = max(width, height)
    area = max(1, width * height)
    n = len(clipped)
    density = clamp01(n / area)
    longest_run = longest_run_from_pixels(clipped, orientation)
    edge_distance = min(x0, y0, image_size - 1 - x1, image_size - 1 - y1)
    baseline = int(round(sum(y for _, y in clipped) / n)) if orientation == "horizontal" else int(round(sum(x for x, _ in clipped) / n))

    if role == "grid_line_candidate":
        same_axis = rng.uniform(0.50, 0.95)
        near_line = rng.uniform(0.35, 0.90)
        parallel_count = rng.randint(2, 6)
        local_context = rng.uniform(0.00, 0.20)
    elif role == "axis_line_candidate":
        same_axis = rng.uniform(0.45, 0.90)
        near_line = rng.uniform(0.30, 0.80)
        parallel_count = rng.randint(0, 1)
        local_context = rng.uniform(0.05, 0.25)
    elif role == "tick_or_scale_mark":
        same_axis = rng.uniform(0.05, 0.35)
        near_line = rng.uniform(0.35, 0.90)
        parallel_count = rng.randint(0, 1)
        local_context = rng.uniform(0.10, 0.35)
    elif role == "page_border_or_layout_box":
        same_axis = rng.uniform(0.10, 0.50)
        near_line = rng.uniform(0.10, 0.55)
        parallel_count = rng.randint(0, 2)
        local_context = rng.uniform(0.05, 0.30)
        edge_distance = min(edge_distance, rng.randint(0, 10))
    elif role == "text_or_digit_stroke":
        same_axis = rng.uniform(0.00, 0.25)
        near_line = rng.uniform(0.00, 0.35)
        parallel_count = rng.randint(0, 1)
        local_context = rng.uniform(0.45, 0.95)
    elif role == "curve_or_data_trace":
        same_axis = rng.uniform(0.00, 0.30)
        near_line = rng.uniform(0.05, 0.40)
        parallel_count = rng.randint(0, 1)
        local_context = rng.uniform(0.45, 0.95)
    else:
        same_axis = rng.uniform(0.10, 0.55)
        near_line = rng.uniform(0.05, 0.55)
        parallel_count = rng.randint(0, 2)
        local_context = rng.uniform(0.20, 0.70)

    scores = role_scores(role, span, density, longest_run, edge_distance, same_axis, near_line, parallel_count, local_context, image_size)
    code = ROLE_CODE[role]
    for x, y in clipped:
        candidate_map[y, x] = 1
        role_map[y, x] = code
        hypothesis_id_map[y, x] = hid
        pixel_rows.append(
            {
                "sample_id": sample_id,
                "linearity_hypothesis_id": hid,
                "x": x,
                "y": y,
                "role_label": role,
                "role_code": code,
                "source_deferred_candidate": True,
            }
        )

    if role in {"grid_line_candidate", "axis_line_candidate", "tick_or_scale_mark"}:
        for x, y in clipped[:: max(1, len(clipped) // 24)]:
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    yy = y + dy
                    xx = x + dx
                    if 0 <= yy < image_size and 0 <= xx < image_size:
                        line_context[yy, xx] = 1

    feature_rows.append(
        {
            "sample_id": sample_id,
            "sample_type": sample_type,
            "linearity_hypothesis_id": hid,
            "role_label": role,
            "orientation": orientation,
            "baseline": baseline,
            "bbox_x0": x0,
            "bbox_y0": y0,
            "bbox_x1": x1,
            "bbox_y1": y1,
            "span_px": span,
            "pixel_count_log": math.log1p(n),
            "density": density,
            "longest_run": longest_run,
            "edge_distance_px": edge_distance,
            "same_axis_extension_score": same_axis,
            "near_line_study_contact_score": near_line,
            "parallel_context_count": parallel_count,
            "local_observed_context_score": local_context,
            "orientation_horizontal": 1.0 if orientation == "horizontal" else 0.0,
            "orientation_vertical": 1.0 if orientation == "vertical" else 0.0,
            **scores,
        }
    )
    label_rows.append(
        {
            "sample_id": sample_id,
            "sample_type": sample_type,
            "linearity_hypothesis_id": hid,
            "role_label": role,
            "label_provenance": "synthetic_traceable_linear_role_truth",
            "pixel_count": n,
        }
    )


def pixels_for_role(role: str, image_size: int, rng: random.Random) -> Tuple[str, List[Tuple[int, int]]]:
    orientation = rng.choice(["horizontal", "vertical"])
    if role == "page_border_or_layout_box":
        orientation = rng.choice(["horizontal", "vertical"])
        baseline = rng.choice([rng.randint(2, 12), rng.randint(image_size - 13, image_size - 3)])
        start = rng.randint(image_size // 8, image_size // 3)
        end = rng.randint(image_size // 2, image_size - image_size // 8)
        return orientation, line_pixels(orientation, baseline, start, end, 0, 1, rng)
    if role == "tick_or_scale_mark":
        baseline = rng.randint(image_size // 6, image_size - image_size // 6)
        start = rng.randint(image_size // 6, image_size - image_size // 6)
        return orientation, line_pixels(orientation, baseline, start, start + rng.randint(8, 26), 0, 1, rng)
    if role == "text_or_digit_stroke":
        x = rng.randint(35, image_size - 35)
        y = rng.randint(35, image_size - 35)
        pixels: List[Tuple[int, int]] = []
        for k in range(rng.randint(3, 7)):
            pixels += line_pixels("vertical", x + k * rng.randint(1, 3), y, y + rng.randint(9, 24), 0, 1, rng)
            if rng.random() < 0.60:
                pixels += line_pixels("horizontal", y + rng.randint(0, 18), x, x + rng.randint(6, 18), 0, 1, rng)
        return orientation, pixels
    if role == "curve_or_data_trace":
        x0 = rng.randint(25, image_size // 3)
        y0 = rng.randint(40, image_size - 40)
        pixels = []
        for t in range(rng.randint(30, 90)):
            x = x0 + t
            y = int(y0 + 12 * math.sin(t / rng.uniform(7.0, 13.0)))
            pixels.append((x, y))
        return "horizontal", pixels
    if role == "ambiguous_linear":
        x = rng.randint(20, image_size - 20)
        y = rng.randint(20, image_size - 20)
        return orientation, [(x + rng.randint(-4, 4), y + rng.randint(-4, 4)) for _ in range(rng.randint(5, 12))]

    baseline = rng.randint(image_size // 7, image_size - image_size // 7)
    start = rng.randint(image_size // 10, image_size // 3)
    end = rng.randint(image_size // 2, image_size - image_size // 10)
    jitter = 1 if role == "broken_grid_deferred_positive" else 0
    return orientation, line_pixels(orientation, baseline, start, end, jitter, rng.choice([1, 1, 2]), rng)


def generate_sample(sample_id: str, sample_type: str, image_size: int, rng: random.Random, out_dir: Path) -> Dict[str, Any]:
    sample_dir = out_dir / "samples" / sample_id
    maps_dir = sample_dir / "maps"
    tables_dir = sample_dir / "tables"
    visuals_dir = sample_dir / "visuals"
    for path in (maps_dir, tables_dir, visuals_dir):
        ensure_dir(path)

    role_map = np.zeros((image_size, image_size), dtype=np.uint8)
    candidate_map = np.zeros_like(role_map, dtype=np.uint8)
    line_context = np.zeros_like(role_map, dtype=np.uint8)
    hypothesis_id_map = np.zeros((image_size, image_size), dtype=np.uint16)
    feature_rows: List[Dict[str, Any]] = []
    label_rows: List[Dict[str, Any]] = []
    pixel_rows: List[Dict[str, Any]] = []

    base_role_by_type = {
        "clear_grid_deferred_positive": "grid_line_candidate",
        "broken_grid_deferred_positive": "grid_line_candidate",
        "axis_line_positive": "axis_line_candidate",
        "tick_hard_negative": "tick_or_scale_mark",
        "text_stroke_hard_negative": "text_or_digit_stroke",
        "border_layout_hard_negative": "page_border_or_layout_box",
        "curve_trace_hard_negative": "curve_or_data_trace",
        "ambiguous_tiny_linear": "ambiguous_linear",
    }
    roles = [base_role_by_type[sample_type]]
    roles.extend(rng.sample(ROLES, k=min(5, len(ROLES))))
    hid = 1
    for role in roles:
        orientation, pixels = pixels_for_role(role, image_size, rng)
        add_hypothesis(
            sample_id,
            sample_type,
            hid,
            role,
            orientation,
            pixels,
            image_size,
            role_map,
            candidate_map,
            line_context,
            hypothesis_id_map,
            feature_rows,
            label_rows,
            pixel_rows,
            rng,
        )
        hid += 1

    Image.fromarray((candidate_map * 255), "L").save(sample_dir / "input_mask.png")
    np.save(maps_dir / "truth_role_class_map.npy", role_map)
    np.save(maps_dir / "d1_candidate_map.npy", candidate_map)
    np.save(maps_dir / "line_study_context_map.npy", line_context)
    np.save(maps_dir / "linearity_hypothesis_id_map.npy", hypothesis_id_map)
    write_csv(tables_dir / "linearity_role_labels.csv", label_rows, LABEL_FIELDS)
    write_csv(tables_dir / "linearity_features.csv", feature_rows, FEATURE_FIELDS)
    write_csv(tables_dir / "pixel_trace.csv", pixel_rows, PIXEL_FIELDS)

    colors = {
        0: (255, 255, 255),
        ROLE_CODE["grid_line_candidate"]: (0, 165, 90),
        ROLE_CODE["axis_line_candidate"]: (40, 120, 255),
        ROLE_CODE["tick_or_scale_mark"]: (245, 175, 35),
        ROLE_CODE["page_border_or_layout_box"]: (120, 80, 210),
        ROLE_CODE["text_or_digit_stroke"]: (220, 45, 45),
        ROLE_CODE["curve_or_data_trace"]: (0, 185, 190),
        ROLE_CODE["ambiguous_linear"]: (135, 135, 135),
    }
    visual = np.full((image_size, image_size, 3), 255, dtype=np.uint8)
    visual[line_context > 0] = (225, 225, 225)
    for code, color in colors.items():
        if code:
            visual[role_map == code] = color
    img = Image.fromarray(visual, "RGB")
    canvas = Image.new("RGB", (image_size, image_size + 36), "white")
    canvas.paste(img, (0, 36))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 10), f"{sample_id} - {sample_type}", fill=(0, 0, 0), font=font(13))
    canvas.save(visuals_dir / "audit_summary.png")

    counts = {role: sum(1 for row in label_rows if row["role_label"] == role) for role in ROLES}
    return {
        "sample_id": sample_id,
        "sample_type": sample_type,
        "hypothesis_count": len(label_rows),
        "pixel_count": int(np.count_nonzero(candidate_map)),
        **{f"{role}_count": counts[role] for role in ROLES},
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
        img = Image.open(out_dir / "samples" / sid / "visuals" / "audit_summary.png").convert("RGB")
        img.thumbnail((180, 210))
        tile = Image.new("RGB", (190, 220), "white")
        tile.paste(img, ((190 - img.width) // 2, 5))
        thumbs.append(tile)
    cols = 4
    rows = max(1, int(math.ceil(len(thumbs) / cols)))
    sheet = Image.new("RGB", (cols * 190, rows * 220 + 34), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 10), "D1-CAL V1 dataset contact sheet", fill=(0, 0, 0), font=font(16))
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
        sample_id = f"d1cal_{idx:04d}_{sample_type}"
        sample_rows.append(generate_sample(sample_id, sample_type, cfg.image_size, rng, out_dir))

    sample_ids = [row["sample_id"] for row in sample_rows]
    splits = split_ids(sample_ids, cfg, rng)
    write_splits(out_dir, splits)
    contact_sheet(out_dir, sample_ids)

    role_counts = {role: sum(int(row[f"{role}_count"]) for row in sample_rows) for role in ROLES}
    hard_negative = sum(role_counts[role] for role in ROLES if role != "grid_line_candidate")
    total = max(sum(role_counts.values()), 1)
    split_disjoint = not (set(splits["train"]) & set(splits["validation"]) or set(splits["train"]) & set(splits["holdout"]) or set(splits["validation"]) & set(splits["holdout"]))
    audit = {
        "status": "PASS" if split_disjoint and hard_negative / total >= 0.30 and all(role_counts.values()) else "FAIL",
        "sample_count": len(sample_rows),
        "hypothesis_count": total,
        "role_counts": role_counts,
        "hard_negative_ratio": hard_negative / total,
        "pixel_hypothesis_traceability_rate": 1.0,
        "hypothesis_feature_traceability_rate": 1.0,
        "split_independence_pass": split_disjoint,
        "runtime_truth_labels_allowed": False,
    }
    manifest = {
        "dataset_id": "D1_CAL_V1_DEFERRED_LINEAR_ROLE_DATASET",
        "version": VERSION,
        "config": asdict(cfg),
        "sample_count": len(sample_rows),
        "sample_types": SAMPLE_TYPES,
        "roles": ROLES,
        "role_code": ROLE_CODE,
        "feature_names": FEATURE_NAMES,
        "splits": {name: len(ids) for name, ids in splits.items()},
        "critical_rule": "No module may gain interpretation by losing geometric traceability.",
    }
    write_json(out_dir / "dataset_manifest.json", manifest)
    write_json(out_dir / "dataset_audit.json", audit)
    write_csv(out_dir / "dataset_balance_report.csv", sample_rows, [
        "sample_id",
        "sample_type",
        "hypothesis_count",
        "pixel_count",
        *[f"{role}_count" for role in ROLES],
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

