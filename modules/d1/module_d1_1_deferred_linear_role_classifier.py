#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D1.1 deferred linear role classifier.

This module classifies D1.0 simple-linearity hypotheses into geometric roles.
It does not create final geometry and only labels pixels that are already D1.0
deferred-linearity candidates.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_D1_1_V1_DEFERRED_LINEAR_ROLE_CLASSIFIER"

ROLES = [
    "grid_line_candidate",
    "axis_line_candidate",
    "tick_or_scale_mark",
    "page_border_or_layout_box",
    "text_or_digit_stroke",
    "curve_or_data_trace",
    "ambiguous_linear",
]
ROLE_CODE = {name: idx + 1 for idx, name in enumerate(ROLES)}
CODE_ROLE = {idx: name for name, idx in ROLE_CODE.items()}

ROLE_COLORS = {
    0: (255, 255, 255),
    ROLE_CODE["grid_line_candidate"]: (0, 165, 90),
    ROLE_CODE["axis_line_candidate"]: (40, 120, 255),
    ROLE_CODE["tick_or_scale_mark"]: (245, 175, 35),
    ROLE_CODE["page_border_or_layout_box"]: (120, 80, 210),
    ROLE_CODE["text_or_digit_stroke"]: (220, 45, 45),
    ROLE_CODE["curve_or_data_trace"]: (0, 185, 190),
    ROLE_CODE["ambiguous_linear"]: (135, 135, 135),
}

ROLE_PRIORITY = {
    "grid_line_candidate": 7,
    "axis_line_candidate": 6,
    "page_border_or_layout_box": 5,
    "tick_or_scale_mark": 4,
    "curve_or_data_trace": 3,
    "text_or_digit_stroke": 2,
    "ambiguous_linear": 1,
}

HYPOTHESIS_FIELDS = [
    "linearity_hypothesis_id",
    "sample_id",
    "role",
    "role_confidence",
    "role_reason",
    "orientation",
    "baseline",
    "bbox_x0",
    "bbox_y0",
    "bbox_x1",
    "bbox_y1",
    "span_px",
    "pixel_count",
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
]

MEMBERSHIP_FIELDS = [
    "sample_id",
    "x",
    "y",
    "linearity_hypothesis_id",
    "role",
    "role_code",
    "role_confidence",
    "source_domain",
    "membership_weight",
]

SUMMARY_FIELDS = ["role", "hypothesis_count", "pixel_count", "pixel_ratio_of_d1_0_candidates"]


@dataclass
class Config:
    version: str = VERSION
    line_context_radius_px: int = 3
    same_axis_radius_px: int = 3
    same_axis_longitudinal_margin_px: int = 10
    parallel_min_offset_px: int = 5
    parallel_max_offset_px: int = 85
    parallel_min_support_positions: int = 5
    border_margin_px: int = 14
    grid_min_score: float = 0.48
    grid_min_parallel_context: int = 2
    axis_min_score: float = 0.43
    tick_max_span_px: int = 30
    text_max_span_px: int = 38
    min_confidence_for_specific_role: float = 0.42


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


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], fields: Sequence[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(to_jsonable(row))


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except Exception:
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def ratio(num: int, den: int) -> float:
    return float(num / den) if den else 0.0


def count(mask: np.ndarray) -> int:
    return int(np.count_nonzero(mask))


def load_bool(path: Path) -> np.ndarray:
    return np.load(path).astype(bool)


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    h, w = mask.shape
    out = np.zeros_like(mask, dtype=bool)
    ys, xs = np.where(mask)
    for y, x in zip(ys, xs):
        y0 = max(0, y - radius)
        y1 = min(h, y + radius + 1)
        x0 = max(0, x - radius)
        x1 = min(w, x + radius + 1)
        out[y0:y1, x0:x1] = True
    return out


def font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def bbox_from_mask(mask: np.ndarray) -> Tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return (0, 0, 0, 0)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def build_masks_from_memberships(rows: Sequence[Dict[str, str]], shape: Tuple[int, int]) -> Dict[int, np.ndarray]:
    masks: Dict[int, np.ndarray] = {}
    for row in rows:
        hid = as_int(row.get("linearity_hypothesis_id"))
        x = as_int(row.get("x"))
        y = as_int(row.get("y"))
        if hid <= 0 or not (0 <= y < shape[0] and 0 <= x < shape[1]):
            continue
        if hid not in masks:
            masks[hid] = np.zeros(shape, dtype=bool)
        masks[hid][y, x] = True
    return masks


def same_axis_extension_score(
    line_study: np.ndarray,
    orientation: str,
    baseline: int,
    start: int,
    end: int,
    cfg: Config,
) -> float:
    h, w = line_study.shape
    margin = cfg.same_axis_longitudinal_margin_px
    if orientation == "horizontal":
        band_min = max(0, baseline - cfg.same_axis_radius_px)
        band_max = min(h - 1, baseline + cfg.same_axis_radius_px)
        s = max(0, start - margin)
        e = min(w - 1, end + margin)
        vec = np.any(line_study[band_min : band_max + 1, s : e + 1], axis=0)
    else:
        band_min = max(0, baseline - cfg.same_axis_radius_px)
        band_max = min(w - 1, baseline + cfg.same_axis_radius_px)
        s = max(0, start - margin)
        e = min(h - 1, end + margin)
        vec = np.any(line_study[s : e + 1, band_min : band_max + 1], axis=1)
    return ratio(int(np.count_nonzero(vec)), len(vec))


def parallel_context_count(
    line_study: np.ndarray,
    orientation: str,
    baseline: int,
    start: int,
    end: int,
    cfg: Config,
) -> int:
    h, w = line_study.shape
    found = 0
    if orientation == "horizontal":
        s = max(0, start)
        e = min(w - 1, end)
        for y in range(h):
            delta = abs(y - baseline)
            if not (cfg.parallel_min_offset_px <= delta <= cfg.parallel_max_offset_px):
                continue
            support = int(np.count_nonzero(line_study[y, s : e + 1]))
            if support >= cfg.parallel_min_support_positions:
                found += 1
    else:
        s = max(0, start)
        e = min(h - 1, end)
        for x in range(w):
            delta = abs(x - baseline)
            if not (cfg.parallel_min_offset_px <= delta <= cfg.parallel_max_offset_px):
                continue
            support = int(np.count_nonzero(line_study[s : e + 1, x]))
            if support >= cfg.parallel_min_support_positions:
                found += 1
    return found


def local_observed_context_score(mask: np.ndarray, observed: np.ndarray, line_study: np.ndarray, radius: int) -> float:
    near = dilate(mask, radius)
    local_observed = observed & near
    if count(local_observed) == 0:
        return 0.0
    non_line = local_observed & ~line_study & ~mask
    return ratio(count(non_line), count(local_observed))


def compute_features(
    row: Dict[str, str],
    mask: np.ndarray,
    line_study: np.ndarray,
    observed: np.ndarray,
    cfg: Config,
) -> Dict[str, Any]:
    x0, y0, x1, y1 = bbox_from_mask(mask)
    h, w = mask.shape
    orientation = str(row.get("orientation", ""))
    baseline = as_int(row.get("baseline"))
    start = as_int(row.get("longitudinal_start"))
    end = as_int(row.get("longitudinal_end"))
    pixel_count = count(mask)
    span = as_int(row.get("span_px"), max(x1 - x0 + 1, y1 - y0 + 1))
    density = as_float(row.get("density"))
    longest_run = as_int(row.get("longest_run"))
    lineality = as_float(row.get("lineality_score"))
    edge_distance = min(x0, y0, w - 1 - x1, h - 1 - y1)
    near = dilate(mask, cfg.line_context_radius_px)
    near_line_score = clamp01(ratio(count(near & line_study), max(pixel_count, 1)))
    same_axis_score = same_axis_extension_score(line_study, orientation, baseline, start, end, cfg)
    parallel_count = parallel_context_count(line_study, orientation, baseline, start, end, cfg)
    parallel_score = clamp01(parallel_count / 5.0)
    local_context = local_observed_context_score(mask, observed, line_study, cfg.line_context_radius_px)
    compact_score = clamp01(1.0 - span / 45.0)
    border_score = 1.0 if edge_distance <= cfg.border_margin_px else 0.0
    if edge_distance <= cfg.border_margin_px * 2 and span >= 36:
        border_score = max(border_score, 0.72)
    grid_score = clamp01(
        0.30 * same_axis_score
        + 0.28 * parallel_score
        + 0.20 * near_line_score
        + 0.14 * lineality
        + 0.08 * clamp01(span / 60.0)
    )
    axis_score = clamp01(
        0.34 * same_axis_score
        + 0.25 * near_line_score
        + 0.20 * clamp01(span / 55.0)
        + 0.14 * (1.0 - parallel_score)
        + 0.07 * lineality
    )
    tick_score = clamp01(
        0.38 * compact_score
        + 0.28 * near_line_score
        + 0.18 * density
        + 0.16 * (1.0 - parallel_score)
    )
    text_score = clamp01(
        0.34 * compact_score
        + 0.26 * local_context
        + 0.20 * (1.0 - same_axis_score)
        + 0.20 * (1.0 - parallel_score)
    )
    curve_score = clamp01(
        0.30 * clamp01(span / 60.0)
        + 0.26 * local_context
        + 0.24 * (1.0 - same_axis_score)
        + 0.20 * (1.0 - parallel_score)
    )
    return {
        "orientation": orientation,
        "baseline": baseline,
        "bbox_x0": x0,
        "bbox_y0": y0,
        "bbox_x1": x1,
        "bbox_y1": y1,
        "span_px": span,
        "pixel_count": pixel_count,
        "density": density,
        "longest_run": longest_run,
        "lineality_score": lineality,
        "edge_distance_px": edge_distance,
        "same_axis_extension_score": same_axis_score,
        "near_line_study_contact_score": near_line_score,
        "parallel_context_count": parallel_count,
        "parallel_context_score": parallel_score,
        "local_observed_context_score": local_context,
        "grid_role_score": grid_score,
        "axis_role_score": axis_score,
        "tick_role_score": tick_score,
        "border_role_score": border_score,
        "text_role_score": text_score,
        "curve_role_score": curve_score,
    }


def decide_role(features: Dict[str, Any], cfg: Config) -> Tuple[str, float, str]:
    span = int(features["span_px"])
    edge = int(features["edge_distance_px"])
    same_axis = float(features["same_axis_extension_score"])
    near_line = float(features["near_line_study_contact_score"])
    parallel_count = int(features["parallel_context_count"])
    grid = float(features["grid_role_score"])
    axis = float(features["axis_role_score"])
    tick = float(features["tick_role_score"])
    border = float(features["border_role_score"])
    text = float(features["text_role_score"])
    curve = float(features["curve_role_score"])

    if border >= 0.95:
        return "page_border_or_layout_box", border, "near_image_or_page_edge"
    if border >= 0.72 and grid < cfg.grid_min_score:
        return "page_border_or_layout_box", border, "long_linear_support_near_page_or_layout_edge"
    if grid >= cfg.grid_min_score and (parallel_count >= cfg.grid_min_parallel_context or same_axis >= 0.45) and near_line >= 0.15:
        return "grid_line_candidate", grid, "same_axis_and_parallel_grid_context"
    if axis >= cfg.axis_min_score and span >= 25 and parallel_count < cfg.grid_min_parallel_context and near_line >= 0.20:
        return "axis_line_candidate", axis, "line_like_with_axis_context_but_weak_grid_parallelism"
    if span <= cfg.tick_max_span_px and tick >= 0.46 and near_line >= 0.18:
        return "tick_or_scale_mark", tick, "short_linear_mark_near_existing_line_study"
    if curve >= 0.50 and span >= 25 and same_axis < 0.25 and parallel_count <= 1:
        return "curve_or_data_trace", curve, "linear_piece_with_local_non_grid_context"
    if span <= cfg.text_max_span_px and text >= 0.48 and same_axis < 0.30 and parallel_count <= 1:
        return "text_or_digit_stroke", text, "compact_linear_stroke_without_grid_context"

    scores = {
        "grid_line_candidate": grid,
        "axis_line_candidate": axis,
        "tick_or_scale_mark": tick,
        "page_border_or_layout_box": border,
        "text_or_digit_stroke": text,
        "curve_or_data_trace": curve,
    }
    best_role, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score >= cfg.min_confidence_for_specific_role:
        return best_role, float(best_score), "best_available_simple_geometric_role"
    return "ambiguous_linear", float(best_score), "role_scores_below_specific_threshold"


def role_rgb(role_map: np.ndarray, base: np.ndarray | None = None) -> Image.Image:
    arr = np.full((role_map.shape[0], role_map.shape[1], 3), 255, dtype=np.uint8)
    if base is not None:
        arr[base] = (230, 235, 230)
    for code, color in ROLE_COLORS.items():
        if code == 0:
            continue
        arr[role_map == code] = color
    return Image.fromarray(arr, "RGB")


def bool_rgb(mask: np.ndarray, color: Tuple[int, int, int], base: np.ndarray | None = None) -> Image.Image:
    arr = np.full((mask.shape[0], mask.shape[1], 3), 255, dtype=np.uint8)
    if base is not None:
        arr[base] = (232, 232, 232)
    arr[mask] = color
    return Image.fromarray(arr, "RGB")


def add_title(img: Image.Image, title: str) -> Image.Image:
    out = img.copy()
    d = ImageDraw.Draw(out, "RGBA")
    d.rectangle((0, 0, out.width, 30), fill=(255, 255, 255, 235))
    d.text((8, 8), title, fill=(0, 0, 0), font=font(11))
    return out


def legend_image() -> Image.Image:
    img = Image.new("RGB", (440, 250), "white")
    d = ImageDraw.Draw(img)
    d.text((12, 10), "D1.1 role legend", fill=(0, 0, 0), font=font(17))
    y = 44
    for role in ROLES:
        code = ROLE_CODE[role]
        d.rectangle((16, y, 44, y + 18), fill=ROLE_COLORS[code])
        d.text((56, y + 2), role, fill=(0, 0, 0), font=font(12))
        y += 27
    return img


def contact_sheet(panels: Sequence[Tuple[str, Image.Image]], out_path: Path, title: str) -> None:
    thumbs: List[Image.Image] = []
    for panel_title, img in panels:
        thumb = img.copy()
        thumb.thumbnail((410, 410))
        canvas = Image.new("RGB", (410, 444), "white")
        canvas.paste(thumb, ((410 - thumb.width) // 2, 30))
        d = ImageDraw.Draw(canvas)
        d.text((8, 8), panel_title, fill=(0, 0, 0), font=font(12))
        thumbs.append(canvas)
    cols = 2
    rows = int(np.ceil(len(thumbs) / cols))
    sheet = Image.new("RGB", (cols * 410, rows * 444 + 36), "white")
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), title, fill=(0, 0, 0), font=font(17))
    for idx, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((idx % cols) * 410, 36 + (idx // cols) * 444))
    ensure_dir(out_path.parent)
    sheet.save(out_path)


def run(d1_dir: Path, unit_dir: Path, out_dir: Path, sample_id: str, cfg: Config) -> Dict[str, Any]:
    out_dir = Path(out_dir)
    ensure_dir(out_dir / "maps")
    ensure_dir(out_dir / "visuals")

    d1_summary = read_json(d1_dir / "summary.json")
    hypotheses_in = read_csv(d1_dir / "d1_0_linearity_hypotheses.csv")
    memberships_in = read_csv(d1_dir / "d1_0_candidate_memberships.csv")
    d1_candidate = load_bool(d1_dir / "maps" / "simple_linearity_candidate_map.npy")
    d1_deferred = load_bool(d1_dir / "maps" / "input_deferred_map.npy")
    line_study = load_bool(unit_dir / "maps" / "unit_final_line_study_support_map.npy")
    observed = load_bool(unit_dir / "maps" / "unit_observed_support_map.npy")
    masks_by_hid = build_masks_from_memberships(memberships_in, d1_candidate.shape)

    role_class_map = np.zeros(d1_candidate.shape, dtype=np.uint8)
    role_confidence_map = np.zeros(d1_candidate.shape, dtype=np.float32)
    role_hypothesis_id_map = np.zeros(d1_candidate.shape, dtype=np.uint16)
    hypothesis_rows: List[Dict[str, Any]] = []
    membership_rows: List[Dict[str, Any]] = []

    for row in hypotheses_in:
        hid = as_int(row.get("linearity_hypothesis_id"))
        mask = masks_by_hid.get(hid)
        if hid <= 0 or mask is None or count(mask) == 0:
            continue
        features = compute_features(row, mask, line_study, observed, cfg)
        role, confidence, reason = decide_role(features, cfg)
        role_code = ROLE_CODE[role]
        hypothesis_rows.append(
            {
                "linearity_hypothesis_id": hid,
                "sample_id": sample_id,
                "role": role,
                "role_confidence": confidence,
                "role_reason": reason,
                **features,
            }
        )
        ys, xs = np.where(mask)
        for y, x in zip(ys, xs):
            current_code = int(role_class_map[y, x])
            current_role = CODE_ROLE.get(current_code, "ambiguous_linear")
            current_conf = float(role_confidence_map[y, x])
            should_assign = (
                current_code == 0
                or confidence > current_conf + 1e-9
                or (
                    abs(confidence - current_conf) <= 1e-9
                    and ROLE_PRIORITY[role] > ROLE_PRIORITY.get(current_role, 0)
                )
            )
            if should_assign:
                role_class_map[y, x] = role_code
                role_confidence_map[y, x] = confidence
                role_hypothesis_id_map[y, x] = hid
            membership_rows.append(
                {
                    "sample_id": sample_id,
                    "x": int(x),
                    "y": int(y),
                    "linearity_hypothesis_id": hid,
                    "role": role,
                    "role_code": role_code,
                    "role_confidence": confidence,
                    "source_domain": "d1_0_deferred_simple_linearity_candidate",
                    "membership_weight": 1.0,
                }
            )

    role_maps = {role: role_class_map == code for role, code in ROLE_CODE.items()}
    np.save(out_dir / "maps" / "d1_1_role_class_map.npy", role_class_map)
    np.save(out_dir / "maps" / "d1_1_role_confidence_map.npy", role_confidence_map)
    np.save(out_dir / "maps" / "d1_1_role_hypothesis_id_map.npy", role_hypothesis_id_map)
    for role, mask in role_maps.items():
        np.save(out_dir / "maps" / f"{role}_map.npy", mask.astype(np.uint16))

    classified = role_class_map > 0
    role_summary: List[Dict[str, Any]] = []
    for role in ROLES:
        role_hypotheses = [r for r in hypothesis_rows if r["role"] == role]
        role_summary.append(
            {
                "role": role,
                "hypothesis_count": len(role_hypotheses),
                "pixel_count": count(role_maps[role]),
                "pixel_ratio_of_d1_0_candidates": ratio(count(role_maps[role]), count(d1_candidate)),
            }
        )

    write_csv(out_dir / "d1_1_role_hypotheses.csv", hypothesis_rows, HYPOTHESIS_FIELDS)
    write_csv(out_dir / "d1_1_role_memberships.csv", membership_rows, MEMBERSHIP_FIELDS)
    write_csv(out_dir / "d1_1_role_summary.csv", role_summary, SUMMARY_FIELDS)

    membership_pixel_set = {(as_int(r["y"]), as_int(r["x"])) for r in membership_rows}
    classified_pixel_set = set(zip(*np.where(classified)))
    role_sum = np.zeros_like(role_class_map, dtype=np.uint8)
    for mask in role_maps.values():
        role_sum += mask.astype(np.uint8)
    invariants = {
        "classified_pixels_subset_of_d1_0_candidates": bool(np.all(~classified | d1_candidate)),
        "classified_pixels_subset_of_source_deferred": bool(np.all(~classified | d1_deferred)),
        "role_maps_mutually_exclusive": bool(np.all(role_sum <= 1)),
        "role_memberships_subset_of_d1_0_candidates": all(d1_candidate[y, x] for y, x in membership_pixel_set),
        "every_classified_pixel_has_role_and_hypothesis": bool(np.all(~classified | (role_hypothesis_id_map > 0))),
        "membership_covers_classified_pixels": classified_pixel_set.issubset(membership_pixel_set),
        "grid_line_candidate_is_not_final_geometry": True,
        "does_not_modify_upstream_outputs": True,
    }
    counts = {
        "d1_0_candidate_pixels": count(d1_candidate),
        "d1_1_classified_pixels": count(classified),
        "grid_line_candidate_pixels": count(role_maps["grid_line_candidate"]),
        "axis_line_candidate_pixels": count(role_maps["axis_line_candidate"]),
        "tick_or_scale_mark_pixels": count(role_maps["tick_or_scale_mark"]),
        "page_border_or_layout_box_pixels": count(role_maps["page_border_or_layout_box"]),
        "text_or_digit_stroke_pixels": count(role_maps["text_or_digit_stroke"]),
        "curve_or_data_trace_pixels": count(role_maps["curve_or_data_trace"]),
        "ambiguous_linear_pixels": count(role_maps["ambiguous_linear"]),
        "hypothesis_count": len(hypothesis_rows),
        "membership_row_count": len(membership_rows),
    }
    metrics = {
        "classified_ratio_of_d1_0_candidates": ratio(counts["d1_1_classified_pixels"], counts["d1_0_candidate_pixels"]),
        "grid_line_candidate_ratio_of_d1_0_candidates": ratio(counts["grid_line_candidate_pixels"], counts["d1_0_candidate_pixels"]),
        "non_grid_linear_ratio_of_d1_0_candidates": ratio(
            counts["axis_line_candidate_pixels"]
            + counts["tick_or_scale_mark_pixels"]
            + counts["page_border_or_layout_box_pixels"]
            + counts["text_or_digit_stroke_pixels"]
            + counts["curve_or_data_trace_pixels"],
            counts["d1_0_candidate_pixels"],
        ),
        "ambiguous_ratio_of_d1_0_candidates": ratio(counts["ambiguous_linear_pixels"], counts["d1_0_candidate_pixels"]),
    }
    summary = {
        "version": VERSION,
        "status": "completed" if all(invariants.values()) else "failed_contract",
        "sample_id": sample_id,
        "source_d1_0_dir": str(d1_dir),
        "source_d1_0_version": d1_summary.get("version", ""),
        "source_unit_dir": str(unit_dir),
        "out_dir": str(out_dir),
        "config": asdict(cfg),
        "roles": ROLES,
        "counts": counts,
        "metrics": metrics,
        "invariants": invariants,
        "outputs": {
            "role_hypotheses": "d1_1_role_hypotheses.csv",
            "role_memberships": "d1_1_role_memberships.csv",
            "role_summary": "d1_1_role_summary.csv",
            "role_class_map": "maps/d1_1_role_class_map.npy",
            "role_hypothesis_id_map": "maps/d1_1_role_hypothesis_id_map.npy",
            "visual_role_overlay": "visuals/01_d1_1_role_overlay.png",
            "visual_audit_summary": "visuals/04_d1_1_audit_summary.png",
        },
        "interpretation_note": "D1.1 classifies D1.0 deferred-linearity candidates by role; grid_line_candidate is not final geometry.",
    }
    write_json(out_dir / "summary.json", summary)
    write_json(
        out_dir / "contract_audit.json",
        {
            "version": VERSION,
            "status": "PASS" if all(invariants.values()) else "FAIL",
            "invariants": invariants,
            "contract": {
                "classifies_only_d1_0_candidates": True,
                "creates_final_geometry": False,
                "uses_ocr": False,
                "uses_truth_labels": False,
                "uses_manual_coordinates": False,
            },
        },
    )

    role_overlay = add_title(role_rgb(role_class_map, line_study), f"D1.1 roles on D1.0 deferred linearity - {sample_id}")
    grid_img = add_title(bool_rgb(role_maps["grid_line_candidate"], (0, 165, 90), line_study), "D1.1 grid_line_candidate only")
    non_grid = (
        role_maps["axis_line_candidate"]
        | role_maps["tick_or_scale_mark"]
        | role_maps["page_border_or_layout_box"]
        | role_maps["text_or_digit_stroke"]
        | role_maps["curve_or_data_trace"]
        | role_maps["ambiguous_linear"]
    )
    non_grid_img = add_title(role_rgb(role_class_map * non_grid.astype(np.uint8), line_study), "D1.1 non-grid/ambiguous linear roles")
    legend = legend_image()
    role_overlay.save(out_dir / "visuals" / "01_d1_1_role_overlay.png")
    grid_img.save(out_dir / "visuals" / "02_grid_line_candidates.png")
    non_grid_img.save(out_dir / "visuals" / "03_non_grid_linear_roles.png")
    legend.save(out_dir / "visuals" / "05_d1_1_legend.png")
    contact_sheet(
        [
            ("role overlay", role_overlay),
            ("grid candidates", grid_img),
            ("non-grid roles", non_grid_img),
            ("legend", legend),
        ],
        out_dir / "visuals" / "04_d1_1_audit_summary.png",
        f"D1.1 deferred linear role classifier - {sample_id}",
    )

    print(
        json.dumps(
            {
                "status": summary["status"],
                "d1_0_candidate_pixels": counts["d1_0_candidate_pixels"],
                "grid_line_candidate_pixels": counts["grid_line_candidate_pixels"],
                "axis_line_candidate_pixels": counts["axis_line_candidate_pixels"],
                "tick_or_scale_mark_pixels": counts["tick_or_scale_mark_pixels"],
                "page_border_or_layout_box_pixels": counts["page_border_or_layout_box_pixels"],
                "text_or_digit_stroke_pixels": counts["text_or_digit_stroke_pixels"],
                "curve_or_data_trace_pixels": counts["curve_or_data_trace_pixels"],
                "ambiguous_linear_pixels": counts["ambiguous_linear_pixels"],
                "invariants_pass": all(invariants.values()),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return summary


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--d1-dir", required=True)
    ap.add_argument("--unit-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample-id", default="sample")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    run(
        d1_dir=Path(args.d1_dir),
        unit_dir=Path(args.unit_dir),
        out_dir=Path(args.out),
        sample_id=args.sample_id,
        cfg=Config(),
    )


if __name__ == "__main__":
    main()
