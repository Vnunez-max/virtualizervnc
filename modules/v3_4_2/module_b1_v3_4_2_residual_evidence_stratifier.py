#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module B1 V3.4.2 — Residual Evidence Stratifier.

Contract:
    V3.3 output
    -> residual_after_geometry_mask
    -> horizontal/vertical residual support objects
    -> residual line fragments
    -> residual multipart fragments
    -> text/noise/crossing/ambiguous residual fragments
    -> residual geometry maps, memberships, segments, gaps, audit
    -> residual evidence classes and evidence-layer maps

V3.4.2 does not redetect the full image.
V3.4.2 does not modify V3.3 outputs.
V3.4.2 does not create synthetic support.
V3.4.2 separates observed support pixels from axis hypotheses.
V3.4.2 separates organized residual from candidate/strong geometry evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


@dataclass
class Config:
    version: str = "MODULE_B1_V3_4_2_RESIDUAL_EVIDENCE_STRATIFIER"
    polarity: str = "white_pixels_active"

    min_run_length_px: int = 8
    min_object_pixels: int = 4
    max_gap_join_px: int = 10
    max_axis_spread_px: float = 2.0
    min_line_like_score: float = 0.58
    min_text_like_score: float = 0.62
    noise_max_pixels: int = 3
    crossing_touch_radius_px: int = 2
    near_geometry_radius_px: float = 4.0
    draw_width_px: int = 1


OBJECT_FIELDS = [
    "residual_object_id",
    "object_type",
    "audit_state",
    "audit_reason",
    "orientation",
    "axis_hypothesis_px",
    "axis_source",
    "x1",
    "y1",
    "x2",
    "y2",
    "length_hull_px",
    "observed_support_length_px",
    "support_pixel_count",
    "support_component_count",
    "support_interval_count",
    "support_intervals",
    "gap_interval_count",
    "gap_intervals",
    "total_gap_px",
    "max_gap_px",
    "gap_burden",
    "coverage_within_intervals",
    "coverage_within_hull",
    "bbox_x_min",
    "bbox_y_min",
    "bbox_x_max",
    "bbox_y_max",
    "bbox_width_px",
    "bbox_height_px",
    "bbox_elongation",
    "local_density",
    "component_density",
    "axis_spread_px",
    "mean_axis_error_px",
    "p95_axis_error_px",
    "nearest_v3_3_object_id",
    "nearest_v3_3_object_distance_px",
    "touches_v3_3_geometry",
    "parallel_to_nearby_geometry",
    "collinear_with_nearby_geometry",
    "crosses_nearby_geometry",
    "text_like_score",
    "line_like_score",
    "confidence",
    "uncertainty",
    "residual_evidence_class",
    "residual_evidence_layer",
    "geometry_evidence_score",
    "candidate_geometry_score",
    "strong_geometry_score",
    "text_like_risk",
    "thickness_risk",
    "noise_risk",
    "ambiguity_score",
    "overpromotion_risk",
    "underpromotion_risk",
    "line_recovery_evidence_hint",
    "axis_evidence_hint",
    "crossing_context_hint",
    "thickness_repair_hint",
    "diagnostic_only_hint",
    "evidence_reason",
    "support_inside_mask",
    "support_inside_residual",
    "modifies_mask",
    "creates_synthetic_support",
]


SEGMENT_FIELDS = [
    "segment_id",
    "residual_object_id",
    "orientation",
    "axis_local_px",
    "x1",
    "y1",
    "x2",
    "y2",
    "length_px",
    "support_pixel_count",
    "local_coverage_ratio",
    "local_gap_count",
    "local_max_gap_px",
    "local_axis_error_px",
    "local_density",
    "segment_role",
]


GAP_FIELDS = [
    "gap_id",
    "residual_object_id",
    "between_segment_a",
    "between_segment_b",
    "gap_start",
    "gap_end",
    "gap_length_px",
    "gap_class",
    "gap_context",
    "support_before",
    "support_after",
    "v3_3_geometry_in_gap",
    "overextension_risk",
]


MEMBERSHIP_FIELDS = [
    "residual_object_id",
    "x",
    "y",
    "membership_role",
    "membership_weight",
    "distance_to_axis_px",
    "longitudinal_position_px",
]


AUDIT_FIELDS = [
    "residual_object_id",
    "object_type",
    "audit_state",
    "audit_reason",
    "support_pixel_count",
    "support_inside_mask",
    "support_inside_residual",
    "creates_synthetic_support",
    "line_like_score",
    "text_like_score",
    "residual_evidence_class",
    "residual_evidence_layer",
    "geometry_evidence_score",
    "candidate_geometry_score",
    "strong_geometry_score",
    "text_like_risk",
    "thickness_risk",
    "noise_risk",
    "ambiguity_score",
    "overpromotion_risk",
    "underpromotion_risk",
    "line_recovery_evidence_hint",
    "axis_evidence_hint",
    "crossing_context_hint",
    "thickness_repair_hint",
    "diagnostic_only_hint",
    "evidence_reason",
    "nearest_v3_3_object_distance_px",
]


EVIDENCE_FIELDS = [
    "residual_object_id",
    "object_type",
    "audit_state",
    "orientation",
    "x1",
    "y1",
    "x2",
    "y2",
    "support_pixel_count",
    "length_hull_px",
    "line_like_score",
    "text_like_score",
    "residual_evidence_class",
    "residual_evidence_layer",
    "geometry_evidence_score",
    "candidate_geometry_score",
    "strong_geometry_score",
    "text_like_risk",
    "thickness_risk",
    "noise_risk",
    "ambiguity_score",
    "overpromotion_risk",
    "underpromotion_risk",
    "line_recovery_evidence_hint",
    "axis_evidence_hint",
    "crossing_context_hint",
    "thickness_repair_hint",
    "diagnostic_only_hint",
    "evidence_reason",
]


TYPE_CODES = {
    "background": 0,
    "residual_line_fragment": 1,
    "residual_multipart_fragment": 2,
    "residual_crossing_fragment": 3,
    "residual_text_like_fragment": 4,
    "residual_noise_fragment": 5,
    "ambiguous_residual_fragment": 6,
    "residual_thickness_fragment": 7,
}


EVIDENCE_CODES = {
    "background": 0,
    "strong_residual_geometry": 1,
    "candidate_residual_geometry": 2,
    "thickness_or_jitter_evidence": 3,
    "crossing_context_evidence": 4,
    "diagnostic_text_like_residual": 5,
    "diagnostic_noise_residual": 6,
    "ambiguous_residual_evidence": 7,
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def font(size: int = 12):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def to_jsonable(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(to_jsonable(obj), indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
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


def load_mask(image_path: Optional[Path], run_dir: Path, cfg: Config) -> np.ndarray:
    src: Optional[Path] = image_path
    if src is None:
        candidate = run_dir / "visuals" / "01_mask_evidence.png"
        if candidate.exists():
            src = candidate
    if src is None or not src.exists():
        raise FileNotFoundError("Mask image not found. Pass --image or provide V3.3 visuals/01_mask_evidence.png.")

    last_error: Exception | None = None
    for _ in range(5):
        try:
            arr = np.asarray(Image.open(src).convert("L"))
            break
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    else:
        if last_error:
            raise last_error
        raise FileNotFoundError(src)
    if cfg.polarity == "white_pixels_active":
        return arr > 127
    if cfg.polarity == "black_pixels_active":
        return arr < 128
    raise ValueError(f"Unsupported polarity: {cfg.polarity}")


def load_map(path: Path, shape: Tuple[int, int], dtype=np.uint16) -> np.ndarray:
    if path.exists():
        return np.load(path)
    return np.zeros(shape, dtype=dtype)


def load_bool_map(path: Path, shape: Tuple[int, int]) -> np.ndarray:
    if path.exists():
        return np.load(path).astype(bool)
    return np.zeros(shape, dtype=bool)


def interval_string(intervals: List[Tuple[int, int]]) -> str:
    return ";".join(f"{a}-{b}" for a, b in intervals)


def valid_runs_1d(arr: np.ndarray, min_len: int) -> List[Tuple[int, int]]:
    runs: List[Tuple[int, int]] = []
    start: Optional[int] = None
    for idx, value in enumerate(arr.astype(bool)):
        if value and start is None:
            start = idx
        elif not value and start is not None:
            if idx - start >= min_len:
                runs.append((start, idx - 1))
            start = None
    if start is not None and len(arr) - start >= min_len:
        runs.append((start, len(arr) - 1))
    return runs


def all_components(mask: np.ndarray, min_pixels: int = 1) -> List[Dict[str, Any]]:
    h, w = mask.shape
    seen = np.zeros(mask.shape, dtype=bool)
    comps: List[Dict[str, Any]] = []
    yy, xx = np.nonzero(mask)

    for sy, sx in zip(yy, xx):
        if seen[sy, sx]:
            continue
        q: deque[Tuple[int, int]] = deque([(int(sx), int(sy))])
        seen[sy, sx] = True
        coords: List[Tuple[int, int]] = []
        while q:
            x, y = q.popleft()
            coords.append((x, y))
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((nx, ny))
        if len(coords) >= min_pixels:
            xs = [p[0] for p in coords]
            ys = [p[1] for p in coords]
            comps.append({
                "coords": coords,
                "x0": min(xs),
                "x1": max(xs),
                "y0": min(ys),
                "y1": max(ys),
                "pixel_count": len(coords),
            })
    return comps


def component_count_for_coords(coords: set[Tuple[int, int]]) -> int:
    if not coords:
        return 0
    remaining = set(coords)
    count = 0
    while remaining:
        start = next(iter(remaining))
        remaining.remove(start)
        q = deque([start])
        count += 1
        while q:
            x, y = q.popleft()
            for nb in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if nb in remaining:
                    remaining.remove(nb)
                    q.append(nb)
    return count


def point_segment_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    vx = x2 - x1
    vy = y2 - y1
    wx = px - x1
    wy = py - y1
    denom = vx * vx + vy * vy
    if denom <= 1e-9:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / denom))
    cx = x1 + t * vx
    cy = y1 + t * vy
    return math.hypot(px - cx, py - cy)


def nearest_geometry_relation(
    coords: set[Tuple[int, int]],
    orientation: str,
    axis: float,
    v3_objects: List[Dict[str, str]],
    cfg: Config,
) -> Dict[str, Any]:
    if not coords or not v3_objects:
        return {
            "nearest_v3_3_object_id": 0,
            "nearest_v3_3_object_distance_px": 999999.0,
            "touches_v3_3_geometry": False,
            "parallel_to_nearby_geometry": False,
            "collinear_with_nearby_geometry": False,
            "crosses_nearby_geometry": False,
        }

    xs = [x for x, _ in coords]
    ys = [y for _, y in coords]
    cx = float(np.mean(xs))
    cy = float(np.mean(ys))
    best_id = 0
    best_dist = 999999.0
    best_obj: Optional[Dict[str, str]] = None
    any_parallel_near = False
    any_collinear_near = False
    any_perpendicular_near = False
    for obj in v3_objects:
        x1 = as_float(obj.get("x1"))
        y1 = as_float(obj.get("y1"))
        x2 = as_float(obj.get("x2"))
        y2 = as_float(obj.get("y2"))
        dist = point_segment_distance(cx, cy, x1, y1, x2, y2)
        obj_orientation = str(obj.get("orientation", ""))
        if dist <= cfg.near_geometry_radius_px and obj_orientation in {"horizontal", "vertical"}:
            if obj_orientation == orientation:
                any_parallel_near = True
                obj_axis = as_float(obj.get("axis_center_px"), 999999.0)
                if abs(obj_axis - axis) <= max(cfg.max_axis_spread_px, cfg.near_geometry_radius_px):
                    any_collinear_near = True
            else:
                any_perpendicular_near = True
        if dist < best_dist:
            best_dist = dist
            best_id = as_int(obj.get("geometry_object_id"))
            best_obj = obj

    nearby = best_dist <= cfg.near_geometry_radius_px
    parallel = False
    collinear = False
    crosses = False
    if best_obj:
        obj_orientation = str(best_obj.get("orientation", ""))
        parallel = any_parallel_near or (nearby and obj_orientation == orientation)
        if parallel:
            obj_axis = as_float(best_obj.get("axis_center_px"), 999999.0)
            collinear = any_collinear_near or abs(obj_axis - axis) <= max(cfg.max_axis_spread_px, cfg.near_geometry_radius_px)
        crosses = any_perpendicular_near or (nearby and obj_orientation in {"horizontal", "vertical"} and obj_orientation != orientation)
    return {
        "nearest_v3_3_object_id": best_id,
        "nearest_v3_3_object_distance_px": float(best_dist),
        "touches_v3_3_geometry": nearby,
        "parallel_to_nearby_geometry": parallel,
        "collinear_with_nearby_geometry": collinear,
        "crosses_nearby_geometry": crosses,
    }


def generate_run_candidates(residual: np.ndarray, cfg: Config) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    h, w = residual.shape
    cid = 1
    for y in range(h):
        for x0, x1 in valid_runs_1d(residual[y, :], cfg.min_run_length_px):
            coords = {(x, y) for x in range(x0, x1 + 1) if residual[y, x]}
            candidates.append({
                "candidate_id": cid,
                "orientation": "horizontal",
                "axis": float(y),
                "intervals": [(int(x0), int(x1))],
                "coords": coords,
            })
            cid += 1
    for x in range(w):
        for y0, y1 in valid_runs_1d(residual[:, x], cfg.min_run_length_px):
            coords = {(x, y) for y in range(y0, y1 + 1) if residual[y, x]}
            candidates.append({
                "candidate_id": cid,
                "orientation": "vertical",
                "axis": float(x),
                "intervals": [(int(y0), int(y1))],
                "coords": coords,
            })
            cid += 1
    return candidates


def merge_candidates_into_groups(candidates: List[Dict[str, Any]], cfg: Config) -> List[Dict[str, Any]]:
    groups: List[Dict[str, Any]] = []
    for orientation in ("horizontal", "vertical"):
        items = sorted(
            [c for c in candidates if c["orientation"] == orientation],
            key=lambda c: (c["axis"], c["intervals"][0][0], c["intervals"][0][1]),
        )
        open_groups: List[Dict[str, Any]] = []
        for cand in items:
            c_axis = float(cand["axis"])
            c0, c1 = cand["intervals"][0]
            best_idx = -1
            best_cost = 999999.0
            for idx, group in enumerate(open_groups):
                axes = group["axes"] + [c_axis]
                axis_spread = max(axes) - min(axes)
                g0 = min(a for a, _ in group["intervals"])
                g1 = max(b for _, b in group["intervals"])
                gap = 0
                if c0 > g1:
                    gap = c0 - g1 - 1
                elif g0 > c1:
                    gap = g0 - c1 - 1
                if axis_spread <= cfg.max_axis_spread_px and gap <= cfg.max_gap_join_px:
                    cost = axis_spread + 0.05 * max(0, gap)
                    if cost < best_cost:
                        best_cost = cost
                        best_idx = idx
            if best_idx >= 0:
                group = open_groups[best_idx]
                group["candidate_ids"].append(cand["candidate_id"])
                group["axes"].append(c_axis)
                group["intervals"].extend(cand["intervals"])
                group["coords"] |= cand["coords"]
            else:
                open_groups.append({
                    "orientation": orientation,
                    "candidate_ids": [cand["candidate_id"]],
                    "axes": [c_axis],
                    "intervals": list(cand["intervals"]),
                    "coords": set(cand["coords"]),
                })
        groups.extend(open_groups)
    return groups


def score_text_and_line(
    coords: set[Tuple[int, int]],
    intervals: List[Tuple[int, int]],
    axis_spread: float,
    gap_burden: float,
    bbox_elongation: float,
    component_count: int,
    local_density: float,
    coverage_hull: float,
) -> Tuple[float, float]:
    support = max(1, len(coords))
    component_density = float(component_count / support)
    shortness = 1.0 if support < 18 else max(0.0, 1.0 - support / 80.0)
    fragmentation = min(1.0, max(0, len(intervals) - 1) / 5.0)

    line_like = (
        0.30 * min(1.0, bbox_elongation / 8.0)
        + 0.25 * max(0.0, 1.0 - axis_spread / 4.0)
        + 0.20 * max(0.0, 1.0 - gap_burden)
        + 0.15 * min(1.0, coverage_hull * 2.0)
        + 0.10 * max(0.0, 1.0 - component_density * 4.0)
    )
    text_like = (
        0.30 * shortness
        + 0.25 * min(1.0, component_density * 8.0)
        + 0.20 * max(0.0, 1.0 - min(1.0, bbox_elongation / 4.0))
        + 0.15 * min(1.0, local_density * 3.0)
        + 0.10 * fragmentation
    )
    return float(min(1.0, line_like)), float(min(1.0, text_like))


def make_object_from_group(
    object_id: int,
    group: Dict[str, Any],
    residual: np.ndarray,
    mask: np.ndarray,
    combined_v3: np.ndarray,
    v3_objects: List[Dict[str, str]],
    cfg: Config,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    orientation = str(group["orientation"])
    coords: set[Tuple[int, int]] = set(group["coords"])
    axes = [float(x) for x in group["axes"]]
    axis = float(np.median(axes)) if axes else 0.0
    intervals = sorted([(int(a), int(b)) for a, b in group["intervals"]])
    merged_intervals: List[Tuple[int, int]] = []
    for a, b in intervals:
        if not merged_intervals or a > merged_intervals[-1][1] + 1:
            merged_intervals.append((a, b))
        else:
            merged_intervals[-1] = (merged_intervals[-1][0], max(merged_intervals[-1][1], b))

    xs = [x for x, _ in coords]
    ys = [y for _, y in coords]
    bbox_x0, bbox_x1 = min(xs), max(xs)
    bbox_y0, bbox_y1 = min(ys), max(ys)
    bbox_w = bbox_x1 - bbox_x0 + 1
    bbox_h = bbox_y1 - bbox_y0 + 1
    bbox_elongation = float(max(bbox_w, bbox_h) / max(1, min(bbox_w, bbox_h)))
    bbox_area = max(1, bbox_w * bbox_h)
    local_density = float(len(coords) / bbox_area)
    axis_errors = [abs((y if orientation == "horizontal" else x) - axis) for x, y in coords]
    mean_axis_error = float(np.mean(axis_errors)) if axis_errors else 0.0
    p95_axis_error = float(np.percentile(axis_errors, 95)) if axis_errors else 0.0
    axis_spread = float(max(axes) - min(axes)) if axes else 0.0
    hull_start = int(min(a for a, _ in merged_intervals))
    hull_end = int(max(b for _, b in merged_intervals))
    hull_len = int(hull_end - hull_start + 1)
    observed_len = int(sum(b - a + 1 for a, b in merged_intervals))

    gaps: List[Tuple[int, int, int, int]] = []
    for idx in range(len(merged_intervals) - 1):
        gs = merged_intervals[idx][1] + 1
        ge = merged_intervals[idx + 1][0] - 1
        if ge >= gs:
            gaps.append((idx, idx + 1, gs, ge))
    total_gap = int(sum(ge - gs + 1 for _, _, gs, ge in gaps))
    max_gap = int(max([ge - gs + 1 for _, _, gs, ge in gaps], default=0))
    gap_burden = float(total_gap / max(1, hull_len))
    coverage_intervals = float(len(coords) / max(1, observed_len))
    coverage_hull = float(len(coords) / max(1, hull_len))
    component_count = component_count_for_coords(coords)
    component_density = float(component_count / max(1, len(coords)))
    line_like, text_like = score_text_and_line(
        coords,
        merged_intervals,
        axis_spread,
        gap_burden,
        bbox_elongation,
        component_count,
        local_density,
        coverage_hull,
    )
    relation = nearest_geometry_relation(coords, orientation, axis, v3_objects, cfg)

    if relation["crosses_nearby_geometry"] and len(coords) <= 80:
        object_type = "residual_crossing_fragment"
        audit_state = "crossing_residual"
        audit_reason = "near_perpendicular_v3_3_geometry"
    elif (
        relation["parallel_to_nearby_geometry"]
        and relation["nearest_v3_3_object_distance_px"] <= cfg.near_geometry_radius_px
        and text_like < max(0.82, line_like + 0.10)
        and len(coords) >= cfg.min_object_pixels
    ):
        object_type = "residual_thickness_fragment"
        audit_state = "faithful_residual_geometry" if line_like >= 0.50 else "weak_residual_geometry"
        audit_reason = "near_parallel_v3_3_geometry_thickness_or_jitter_residual"
    elif (
        relation["nearest_v3_3_object_distance_px"] <= max(6.0, cfg.near_geometry_radius_px * 1.5)
        and line_like >= 0.62
        and text_like < 0.90
        and len(coords) >= cfg.min_object_pixels
    ):
        object_type = "residual_thickness_fragment"
        audit_state = "weak_residual_geometry"
        audit_reason = "near_v3_3_geometry_compact_thickness_or_jitter_residual"
    elif len(coords) <= cfg.noise_max_pixels:
        object_type = "residual_noise_fragment"
        audit_state = "noise_residual"
        audit_reason = "very_small_residual_support"
    elif text_like >= cfg.min_text_like_score and text_like > line_like:
        object_type = "residual_text_like_fragment"
        audit_state = "text_like_residual"
        audit_reason = "text_like_score_dominates"
    elif line_like >= cfg.min_line_like_score and len(merged_intervals) > 1:
        object_type = "residual_multipart_fragment"
        audit_state = "faithful_residual_geometry" if line_like >= 0.72 else "weak_residual_geometry"
        audit_reason = "aligned_residual_segments_with_explicit_gaps"
    elif line_like >= cfg.min_line_like_score:
        object_type = "residual_line_fragment"
        audit_state = "faithful_residual_geometry" if line_like >= 0.72 else "weak_residual_geometry"
        audit_reason = "line_like_residual_support"
    else:
        object_type = "ambiguous_residual_fragment"
        audit_state = "ambiguous_residual"
        audit_reason = "insufficient_separation_between_line_text_noise_scores"

    if orientation == "horizontal":
        x1, y1, x2, y2 = float(hull_start), axis, float(hull_end), axis
    else:
        x1, y1, x2, y2 = axis, float(hull_start), axis, float(hull_end)

    support_inside_mask = all(mask[y, x] for x, y in coords)
    support_inside_residual = all(residual[y, x] for x, y in coords)
    confidence = max(line_like, text_like)
    if object_type in {"residual_noise_fragment", "ambiguous_residual_fragment"}:
        confidence = 0.5 * confidence

    obj = {
        "residual_object_id": object_id,
        "object_type": object_type,
        "audit_state": audit_state,
        "audit_reason": audit_reason,
        "orientation": orientation,
        "axis_hypothesis_px": axis,
        "axis_source": "median_residual_support_axis",
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "length_hull_px": hull_len,
        "observed_support_length_px": observed_len,
        "support_pixel_count": len(coords),
        "support_component_count": component_count,
        "support_interval_count": len(merged_intervals),
        "support_intervals": interval_string(merged_intervals),
        "gap_interval_count": len(gaps),
        "gap_intervals": interval_string([(gs, ge) for _, _, gs, ge in gaps]),
        "total_gap_px": total_gap,
        "max_gap_px": max_gap,
        "gap_burden": gap_burden,
        "coverage_within_intervals": coverage_intervals,
        "coverage_within_hull": coverage_hull,
        "bbox_x_min": bbox_x0,
        "bbox_y_min": bbox_y0,
        "bbox_x_max": bbox_x1,
        "bbox_y_max": bbox_y1,
        "bbox_width_px": bbox_w,
        "bbox_height_px": bbox_h,
        "bbox_elongation": bbox_elongation,
        "local_density": local_density,
        "component_density": component_density,
        "axis_spread_px": axis_spread,
        "mean_axis_error_px": mean_axis_error,
        "p95_axis_error_px": p95_axis_error,
        **relation,
        "text_like_score": text_like,
        "line_like_score": line_like,
        "confidence": float(confidence),
        "uncertainty": float(1.0 - confidence),
        "support_inside_mask": bool(support_inside_mask),
        "support_inside_residual": bool(support_inside_residual),
        "modifies_mask": False,
        "creates_synthetic_support": False,
    }

    segments: List[Dict[str, Any]] = []
    memberships: List[Dict[str, Any]] = []
    segment_ids: List[int] = []
    segment_base = object_id * 100000
    for idx, (s0, s1) in enumerate(merged_intervals, start=1):
        sid = segment_base + idx
        segment_ids.append(sid)
        if orientation == "horizontal":
            seg_coords = {(x, y) for x, y in coords if s0 <= x <= s1}
            sx1, sy1, sx2, sy2 = float(s0), axis, float(s1), axis
        else:
            seg_coords = {(x, y) for x, y in coords if s0 <= y <= s1}
            sx1, sy1, sx2, sy2 = axis, float(s0), axis, float(s1)
        seg_len = int(s1 - s0 + 1)
        segments.append({
            "segment_id": sid,
            "residual_object_id": object_id,
            "orientation": orientation,
            "axis_local_px": axis,
            "x1": sx1,
            "y1": sy1,
            "x2": sx2,
            "y2": sy2,
            "length_px": seg_len,
            "support_pixel_count": len(seg_coords),
            "local_coverage_ratio": float(len(seg_coords) / max(1, seg_len)),
            "local_gap_count": 0,
            "local_max_gap_px": 0,
            "local_axis_error_px": p95_axis_error,
            "local_density": float(len(seg_coords) / max(1, seg_len)),
            "segment_role": "support_segment" if object_type not in {"residual_text_like_fragment", "ambiguous_residual_fragment"} else object_type.replace("residual_", "").replace("_fragment", "_segment"),
        })

    gaps_rows: List[Dict[str, Any]] = []
    for idx, (a_idx, b_idx, gs, ge) in enumerate(gaps, start=1):
        gap_len = int(ge - gs + 1)
        if orientation == "horizontal":
            g_axis = int(round(axis))
            gap_slice = combined_v3[max(0, g_axis - 1):min(combined_v3.shape[0], g_axis + 2), max(0, gs):min(combined_v3.shape[1], ge + 1)]
        else:
            g_axis = int(round(axis))
            gap_slice = combined_v3[max(0, gs):min(combined_v3.shape[0], ge + 1), max(0, g_axis - 1):min(combined_v3.shape[1], g_axis + 2)]
        v3_in_gap = bool(np.any(gap_slice > 0))
        if v3_in_gap:
            gap_class = "geometry_occupied_gap"
        elif gap_len <= cfg.max_gap_join_px:
            gap_class = "small_internal_gap"
        elif gap_len >= max(12, cfg.max_gap_join_px):
            gap_class = "overextension_gap"
        else:
            gap_class = "true_break_gap"
        gaps_rows.append({
            "gap_id": object_id * 100000 + idx,
            "residual_object_id": object_id,
            "between_segment_a": segment_ids[a_idx],
            "between_segment_b": segment_ids[b_idx],
            "gap_start": gs,
            "gap_end": ge,
            "gap_length_px": gap_len,
            "gap_class": gap_class,
            "gap_context": "axis_hypothesis_gap_not_support",
            "support_before": True,
            "support_after": True,
            "v3_3_geometry_in_gap": v3_in_gap,
            "overextension_risk": bool(gap_class == "overextension_gap"),
        })

    role = {
        "residual_line_fragment": "residual_support",
        "residual_multipart_fragment": "residual_support",
        "residual_crossing_fragment": "crossing_residual_support",
        "residual_thickness_fragment": "residual_support",
        "residual_text_like_fragment": "text_like_support",
        "residual_noise_fragment": "noise_support",
        "ambiguous_residual_fragment": "shared_residual_support",
    }.get(object_type, "residual_support")
    for x, y in sorted(coords):
        memberships.append({
            "residual_object_id": object_id,
            "x": int(x),
            "y": int(y),
            "membership_role": role,
            "membership_weight": 1.0,
            "distance_to_axis_px": float(abs((y if orientation == "horizontal" else x) - axis)),
            "longitudinal_position_px": float(x if orientation == "horizontal" else y),
        })
    return obj, segments, gaps_rows, memberships


def organize_residual_geometry(
    mask: np.ndarray,
    residual: np.ndarray,
    combined_v3: np.ndarray,
    v3_objects: List[Dict[str, str]],
    cfg: Config,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], np.ndarray, np.ndarray]:
    candidates = generate_run_candidates(residual, cfg)
    groups = merge_candidates_into_groups(candidates, cfg)
    groups.sort(key=lambda g: len(g["coords"]), reverse=True)

    used: set[Tuple[int, int]] = set()
    objects: List[Dict[str, Any]] = []
    segments: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    memberships: List[Dict[str, Any]] = []
    residual_support = np.zeros(mask.shape, dtype=np.uint16)
    residual_type_map = np.zeros(mask.shape, dtype=np.uint8)
    object_id = 1

    for group in groups:
        coords = set(group["coords"]) - used
        if len(coords) < cfg.min_object_pixels:
            continue
        group = dict(group)
        group["coords"] = coords
        obj, segs, gap_rows, mems = make_object_from_group(
            object_id, group, residual, mask, combined_v3, v3_objects, cfg
        )
        if obj["audit_state"] in {"noise_residual"} and len(coords) > cfg.noise_max_pixels:
            obj["audit_state"] = "ambiguous_residual"
            obj["object_type"] = "ambiguous_residual_fragment"
        objects.append(obj)
        segments.extend(segs)
        gaps.extend(gap_rows)
        memberships.extend(mems)
        for x, y in coords:
            residual_support[y, x] += 1
            residual_type_map[y, x] = TYPE_CODES[obj["object_type"]]
        used |= coords
        object_id += 1

    remaining = residual.copy()
    for x, y in used:
        remaining[y, x] = False
    for comp in all_components(remaining, min_pixels=1):
        coords = set(comp["coords"])
        orientation = "horizontal" if comp["x1"] - comp["x0"] >= comp["y1"] - comp["y0"] else "vertical"
        intervals = [(comp["x0"], comp["x1"])] if orientation == "horizontal" else [(comp["y0"], comp["y1"])]
        axis_vals = [y for _, y in coords] if orientation == "horizontal" else [x for x, _ in coords]
        group = {
            "orientation": orientation,
            "candidate_ids": [],
            "axes": [float(np.median(axis_vals))],
            "intervals": intervals,
            "coords": coords,
        }
        obj, segs, gap_rows, mems = make_object_from_group(
            object_id, group, residual, mask, combined_v3, v3_objects, cfg
        )
        if len(coords) <= cfg.noise_max_pixels:
            obj["object_type"] = "residual_noise_fragment"
            obj["audit_state"] = "noise_residual"
            obj["audit_reason"] = "remaining_small_component"
        elif (
            obj["parallel_to_nearby_geometry"]
            and obj["nearest_v3_3_object_distance_px"] <= cfg.near_geometry_radius_px
            and obj["text_like_score"] < 0.85
        ):
            obj["object_type"] = "residual_thickness_fragment"
            obj["audit_state"] = "weak_residual_geometry"
            obj["audit_reason"] = "remaining_component_near_parallel_v3_3_geometry"
        elif (
            obj["nearest_v3_3_object_distance_px"] <= max(6.0, cfg.near_geometry_radius_px * 1.5)
            and obj["line_like_score"] >= 0.62
            and obj["text_like_score"] < 0.90
        ):
            obj["object_type"] = "residual_thickness_fragment"
            obj["audit_state"] = "weak_residual_geometry"
            obj["audit_reason"] = "remaining_component_near_v3_3_geometry_thickness_or_jitter"
        elif obj["text_like_score"] >= cfg.min_text_like_score:
            obj["object_type"] = "residual_text_like_fragment"
            obj["audit_state"] = "text_like_residual"
            obj["audit_reason"] = "remaining_component_text_like"
        else:
            obj["object_type"] = "ambiguous_residual_fragment"
            obj["audit_state"] = "ambiguous_residual"
            obj["audit_reason"] = "remaining_unclaimed_component"
        objects.append(obj)
        segments.extend(segs)
        gaps.extend(gap_rows)
        memberships.extend(mems)
        for x, y in coords:
            residual_support[y, x] += 1
            residual_type_map[y, x] = TYPE_CODES[obj["object_type"]]
        object_id += 1

    return objects, segments, gaps, memberships, residual_support, residual_type_map


def longest_true_run_1d(arr: np.ndarray) -> int:
    best = 0
    cur = 0
    for value in arr.astype(bool):
        if value:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def line_like_residual_metrics(residual: np.ndarray, min_run: int) -> Dict[str, int]:
    row_runs = [longest_true_run_1d(residual[y, :]) for y in range(residual.shape[0])]
    col_runs = [longest_true_run_1d(residual[:, x]) for x in range(residual.shape[1])]
    return {
        "max_horizontal_residual_run_px": int(max(row_runs, default=0)),
        "max_vertical_residual_run_px": int(max(col_runs, default=0)),
        "line_like_residual_remaining_rows": int(sum(x >= min_run for x in row_runs)),
        "line_like_residual_remaining_cols": int(sum(x >= min_run for x in col_runs)),
    }


def clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def residual_evidence_annotation(obj: Dict[str, Any], cfg: Config) -> Dict[str, Any]:
    """
    Adds an evidence language on top of the V3.4.1 residual object type.

    This function does not create lines, axes, crossings, families, or support.
    It only describes how a residual object may be used by later modules.
    """
    object_type = str(obj.get("object_type", ""))
    audit_state = str(obj.get("audit_state", ""))
    support = float(as_int(obj.get("support_pixel_count", 0)))
    length = float(as_int(obj.get("length_hull_px", 0)))
    line_like = float(obj.get("line_like_score", 0.0))
    text_like = float(obj.get("text_like_score", 0.0))
    gap_burden = float(obj.get("gap_burden", 1.0))
    coverage_hull = float(obj.get("coverage_within_hull", 0.0))
    axis_spread = float(obj.get("axis_spread_px", 999.0))
    nearest_distance = float(obj.get("nearest_v3_3_object_distance_px", 999.0))
    parallel = bool(obj.get("parallel_to_nearby_geometry", False))
    crossing = bool(obj.get("crosses_nearby_geometry", False))

    length_score = clamp01(length / 48.0)
    support_score = clamp01(support / 48.0)
    compact_axis_score = clamp01(1.0 - axis_spread / max(1.0, cfg.max_axis_spread_px * 2.0))
    continuity_score = clamp01(1.0 - gap_burden)
    coverage_score = clamp01(coverage_hull * 2.0)
    near_geometry_score = clamp01(1.0 - nearest_distance / max(1.0, cfg.near_geometry_radius_px * 2.5))

    text_like_risk = clamp01(text_like)
    noise_risk = clamp01(1.0 - support_score)
    if object_type == "residual_noise_fragment":
        noise_risk = 1.0
    thickness_risk = 1.0 if object_type == "residual_thickness_fragment" else 0.0
    if parallel and nearest_distance <= cfg.near_geometry_radius_px:
        thickness_risk = max(thickness_risk, 0.75)
    ambiguity_score = clamp01(1.0 - abs(line_like - text_like))
    if object_type == "ambiguous_residual_fragment":
        ambiguity_score = max(ambiguity_score, 0.80)

    geometry_evidence_score = clamp01(
        0.30 * line_like
        + 0.20 * length_score
        + 0.15 * compact_axis_score
        + 0.15 * continuity_score
        + 0.10 * coverage_score
        + 0.10 * near_geometry_score
        - 0.18 * max(0.0, text_like_risk - line_like)
        - 0.12 * (1.0 if object_type == "residual_noise_fragment" else 0.0)
    )
    candidate_geometry_score = clamp01(
        0.55 * geometry_evidence_score
        + 0.25 * line_like
        + 0.10 * length_score
        + 0.10 * continuity_score
    )
    strong_geometry_score = clamp01(
        0.50 * geometry_evidence_score
        + 0.25 * line_like
        + 0.15 * compact_axis_score
        + 0.10 * coverage_score
        - 0.25 * max(0.0, text_like_risk - 0.65)
        - 0.20 * (1.0 if object_type in {"residual_noise_fragment", "ambiguous_residual_fragment"} else 0.0)
    )

    if object_type == "residual_noise_fragment":
        evidence_class = "diagnostic_noise_residual"
        evidence_layer = "diagnostic_residual"
        reason = "noise_object_type"
    elif object_type == "residual_text_like_fragment":
        evidence_class = "diagnostic_text_like_residual"
        evidence_layer = "diagnostic_residual"
        reason = "text_like_object_type"
    elif object_type == "ambiguous_residual_fragment":
        evidence_class = "ambiguous_residual_evidence"
        evidence_layer = "ambiguous_residual"
        reason = "ambiguous_object_type"
    elif object_type == "residual_crossing_fragment":
        evidence_class = "crossing_context_evidence"
        evidence_layer = "candidate_geometry_residual"
        reason = "crossing_context_not_final_crossing"
    elif object_type == "residual_thickness_fragment":
        evidence_class = "thickness_or_jitter_evidence"
        evidence_layer = "candidate_geometry_residual"
        reason = "near_existing_geometry_thickness_or_jitter"
    elif (
        object_type in {"residual_line_fragment", "residual_multipart_fragment"}
        and audit_state == "faithful_residual_geometry"
        and strong_geometry_score >= 0.68
        and text_like_risk <= 0.74
    ):
        evidence_class = "strong_residual_geometry"
        evidence_layer = "strong_geometry_residual"
        reason = "faithful_line_like_residual_with_low_text_risk"
    elif (
        object_type in {"residual_line_fragment", "residual_multipart_fragment"}
        and candidate_geometry_score >= 0.50
        and text_like_risk <= 0.86
    ):
        evidence_class = "candidate_residual_geometry"
        evidence_layer = "candidate_geometry_residual"
        reason = "line_like_residual_candidate_but_not_strong"
    else:
        evidence_class = "ambiguous_residual_evidence"
        evidence_layer = "ambiguous_residual"
        reason = "evidence_scores_do_not_support_geometry_layer"

    diagnostic_only = evidence_layer in {"diagnostic_residual", "ambiguous_residual"}
    line_hint = evidence_class in {"strong_residual_geometry", "candidate_residual_geometry"}
    axis_hint = bool(line_hint and length >= cfg.min_run_length_px and compact_axis_score >= 0.45)
    crossing_hint = evidence_class == "crossing_context_evidence" or bool(crossing)
    thickness_hint = evidence_class == "thickness_or_jitter_evidence"

    overpromotion_risk = clamp01(max(text_like_risk, noise_risk, ambiguity_score) * (1.0 - geometry_evidence_score))
    underpromotion_risk = clamp01(max(0.0, line_like - text_like_risk) * (1.0 - candidate_geometry_score))

    return {
        "residual_evidence_class": evidence_class,
        "residual_evidence_layer": evidence_layer,
        "geometry_evidence_score": geometry_evidence_score,
        "candidate_geometry_score": candidate_geometry_score,
        "strong_geometry_score": strong_geometry_score,
        "text_like_risk": text_like_risk,
        "thickness_risk": thickness_risk,
        "noise_risk": noise_risk,
        "ambiguity_score": ambiguity_score,
        "overpromotion_risk": overpromotion_risk,
        "underpromotion_risk": underpromotion_risk,
        "line_recovery_evidence_hint": bool(line_hint),
        "axis_evidence_hint": bool(axis_hint),
        "crossing_context_hint": bool(crossing_hint),
        "thickness_repair_hint": bool(thickness_hint),
        "diagnostic_only_hint": bool(diagnostic_only),
        "evidence_reason": reason,
    }


def annotate_residual_evidence(objects: List[Dict[str, Any]], cfg: Config) -> None:
    for obj in objects:
        obj.update(residual_evidence_annotation(obj, cfg))


def evidence_layer_counts(objects: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    return {
        "residual_evidence_class_counts": dict(Counter(str(obj.get("residual_evidence_class", "")) for obj in objects)),
        "residual_evidence_layer_counts": dict(Counter(str(obj.get("residual_evidence_layer", "")) for obj in objects)),
    }


def render_mask(mask: np.ndarray, active=(0, 0, 0), bg=(255, 255, 255)) -> Image.Image:
    pix = np.zeros((*mask.shape, 3), dtype=np.uint8)
    pix[:, :] = np.array(bg, dtype=np.uint8)
    pix[mask] = np.array(active, dtype=np.uint8)
    return Image.fromarray(pix, mode="RGB")


def render_type_map(mask: np.ndarray, type_map: np.ndarray) -> Image.Image:
    pix = np.zeros((*mask.shape, 3), dtype=np.uint8)
    pix[:, :] = np.array([255, 255, 255], dtype=np.uint8)
    pix[mask] = np.array([225, 225, 225], dtype=np.uint8)
    colors = {
        TYPE_CODES["residual_line_fragment"]: np.array([0, 170, 0], dtype=np.uint8),
        TYPE_CODES["residual_multipart_fragment"]: np.array([0, 120, 255], dtype=np.uint8),
        TYPE_CODES["residual_crossing_fragment"]: np.array([240, 190, 0], dtype=np.uint8),
        TYPE_CODES["residual_text_like_fragment"]: np.array([220, 0, 0], dtype=np.uint8),
        TYPE_CODES["residual_noise_fragment"]: np.array([120, 120, 120], dtype=np.uint8),
        TYPE_CODES["ambiguous_residual_fragment"]: np.array([160, 0, 180], dtype=np.uint8),
        TYPE_CODES["residual_thickness_fragment"]: np.array([0, 200, 180], dtype=np.uint8),
    }
    for code, color in colors.items():
        pix[type_map == code] = color
    return Image.fromarray(pix, mode="RGB")


def render_evidence_map(mask: np.ndarray, evidence_map: np.ndarray) -> Image.Image:
    pix = np.zeros((*mask.shape, 3), dtype=np.uint8)
    pix[:, :] = np.array([255, 255, 255], dtype=np.uint8)
    pix[mask] = np.array([232, 232, 232], dtype=np.uint8)
    colors = {
        EVIDENCE_CODES["strong_residual_geometry"]: np.array([0, 150, 0], dtype=np.uint8),
        EVIDENCE_CODES["candidate_residual_geometry"]: np.array([80, 170, 255], dtype=np.uint8),
        EVIDENCE_CODES["thickness_or_jitter_evidence"]: np.array([0, 200, 180], dtype=np.uint8),
        EVIDENCE_CODES["crossing_context_evidence"]: np.array([245, 190, 0], dtype=np.uint8),
        EVIDENCE_CODES["diagnostic_text_like_residual"]: np.array([220, 0, 0], dtype=np.uint8),
        EVIDENCE_CODES["diagnostic_noise_residual"]: np.array([110, 110, 110], dtype=np.uint8),
        EVIDENCE_CODES["ambiguous_residual_evidence"]: np.array([160, 0, 180], dtype=np.uint8),
    }
    for code, color in colors.items():
        pix[evidence_map == code] = color
    return Image.fromarray(pix, mode="RGB")


def draw_objects(base: Image.Image, objects: List[Dict[str, Any]], title: str, cfg: Config) -> Image.Image:
    img = base.copy().convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    colors = {
        "residual_line_fragment": (0, 170, 0, 230),
        "residual_multipart_fragment": (0, 120, 255, 230),
        "residual_crossing_fragment": (240, 190, 0, 230),
        "residual_thickness_fragment": (0, 200, 180, 230),
        "residual_text_like_fragment": (220, 0, 0, 210),
        "residual_noise_fragment": (120, 120, 120, 200),
        "ambiguous_residual_fragment": (160, 0, 180, 210),
    }
    for obj in objects:
        color = colors.get(str(obj["object_type"]), (0, 0, 0, 200))
        d.line((obj["x1"], obj["y1"], obj["x2"], obj["y2"]), fill=color, width=max(1, cfg.draw_width_px))
    return titled(img, title)


def titled(img: Image.Image, title: str) -> Image.Image:
    out = img.copy().convert("RGB")
    d = ImageDraw.Draw(out, "RGBA")
    d.rectangle((0, 0, out.width, 32), fill=(255, 255, 255, 235))
    d.text((8, 9), title, fill=(0, 0, 0, 255), font=font(11))
    return out


def make_visuals(
    out_dir: Path,
    mask: np.ndarray,
    residual_in: np.ndarray,
    residual_type_map: np.ndarray,
    residual_evidence_class_map: np.ndarray,
    residual_support: np.ndarray,
    candidate_residual_support: np.ndarray,
    evidence_strong_residual_support: np.ndarray,
    diagnostic_residual_support: np.ndarray,
    residual_after: np.ndarray,
    residual_after_candidate: np.ndarray,
    residual_after_evidence_strong: np.ndarray,
    objects: List[Dict[str, Any]],
    cfg: Config,
) -> None:
    vdir = out_dir / "visuals"
    ensure_dir(vdir)
    base = render_mask(mask, active=(0, 0, 0), bg=(255, 255, 255))
    residual_img = render_mask(residual_in, active=(0, 0, 0), bg=(255, 255, 255))
    support_img = render_mask(residual_support > 0, active=(0, 120, 255), bg=(255, 255, 255))
    type_img = render_type_map(residual_in, residual_type_map)
    evidence_img = render_evidence_map(residual_in, residual_evidence_class_map)
    candidate_img = render_mask(candidate_residual_support > 0, active=(80, 170, 255), bg=(255, 255, 255))
    evidence_strong_img = render_mask(evidence_strong_residual_support > 0, active=(0, 150, 0), bg=(255, 255, 255))
    diagnostic_img = render_mask(diagnostic_residual_support > 0, active=(220, 0, 0), bg=(255, 255, 255))
    after_img = render_mask(residual_after, active=(0, 0, 0), bg=(255, 255, 255))
    after_candidate_img = render_mask(residual_after_candidate, active=(0, 0, 0), bg=(255, 255, 255))
    after_evidence_strong_img = render_mask(residual_after_evidence_strong, active=(0, 0, 0), bg=(255, 255, 255))
    comparison = Image.new("RGB", (mask.shape[1] * 2, mask.shape[0]), "white")
    comparison.paste(titled(residual_img, "V3.3 residual input"), (0, 0))
    comparison.paste(titled(after_evidence_strong_img, "residual after V3.4.2 strong evidence"), (mask.shape[1], 0))

    panels = [
        ("01_residual_input.png", "residual input R3", residual_img),
        ("02_residual_object_type_map.png", "object type map", type_img),
        ("03_residual_evidence_class_map.png", "evidence class map", evidence_img),
        ("04_candidate_geometry_residual.png", "candidate geometry residual", candidate_img),
        ("05_strong_geometry_residual.png", "strong geometry residual evidence", evidence_strong_img),
        ("06_diagnostic_residual.png", "diagnostic residual", diagnostic_img),
        ("07_residual_after_any_organization.png", "residual after any organization", after_img),
        ("08_residual_after_candidate_geometry.png", "residual after candidate geometry", after_candidate_img),
        ("09_residual_after_strong_geometry.png", "residual after strong geometry", after_evidence_strong_img),
        ("10_v3_3_vs_v3_4_2_strong_residual.png", "R3 vs residual after V3.4.2 strong", comparison),
        ("11_residual_object_hypotheses.png", "residual object hypotheses", draw_objects(base, objects, "residual object hypotheses", cfg)),
    ]
    tiles: List[Image.Image] = []
    for filename, title, image in panels:
        image.save(vdir / filename)
        im = titled(image, title)
        im.thumbnail((430, 320))
        tile = Image.new("RGB", (460, 370), "white")
        tile.paste(im, ((460 - im.width) // 2, 34))
        tiles.append(tile)

    cols = 2
    rows = int(math.ceil(len(tiles) / cols))
    sheet = Image.new("RGB", (cols * 460, rows * 370 + 46), "white")
    d = ImageDraw.Draw(sheet)
    d.text((10, 12), "V3.4.2 Residual Evidence Stratifier", fill="black", font=font(18))
    for idx, tile in enumerate(tiles):
        sheet.paste(tile, ((idx % cols) * 460, 46 + (idx // cols) * 370))
    sheet.save(vdir / "12_audit_summary.png")


def run(run_dir: Path, image_path: Optional[Path], out_dir: Path, cfg: Optional[Config] = None) -> Dict[str, Any]:
    cfg = cfg or Config()
    run_dir = Path(run_dir)
    out_dir = Path(out_dir)
    ensure_dir(out_dir)
    ensure_dir(out_dir / "tables")
    ensure_dir(out_dir / "maps")

    mask = load_mask(image_path, run_dir, cfg)
    shape = mask.shape
    v3_summary = read_json(run_dir / "summary.json")
    v3_objects = read_csv(run_dir / "geometry_objects.csv")
    combined_v3 = load_map(run_dir / "maps" / "combined_geometry_support_count_map.npy", shape)
    residual_in = load_bool_map(run_dir / "maps" / "residual_after_geometry_mask.npy", shape)
    if not np.any(residual_in):
        residual_in = mask & (combined_v3 == 0)

    objects, segments, gaps, memberships, residual_support, residual_type_map = organize_residual_geometry(
        mask, residual_in, combined_v3, v3_objects, cfg
    )
    annotate_residual_evidence(objects, cfg)
    combined_v3_4 = combined_v3 + residual_support
    residual_after = mask & (combined_v3_4 == 0)
    residual_object_id_map = np.zeros(shape, dtype=np.int32)
    residual_evidence_class_map = np.zeros(shape, dtype=np.uint8)
    strong_types = {
        "residual_line_fragment",
        "residual_multipart_fragment",
        "residual_crossing_fragment",
        "residual_thickness_fragment",
    }
    object_type_by_id = {int(obj["residual_object_id"]): str(obj["object_type"]) for obj in objects}
    evidence_class_by_id = {int(obj["residual_object_id"]): str(obj["residual_evidence_class"]) for obj in objects}
    evidence_layer_by_id = {int(obj["residual_object_id"]): str(obj["residual_evidence_layer"]) for obj in objects}
    strong_residual_support = np.zeros(shape, dtype=np.uint16)
    candidate_residual_support = np.zeros(shape, dtype=np.uint16)
    evidence_strong_residual_support = np.zeros(shape, dtype=np.uint16)
    diagnostic_residual_support = np.zeros(shape, dtype=np.uint16)
    for mem in memberships:
        y = as_int(mem["y"])
        x = as_int(mem["x"])
        oid = as_int(mem["residual_object_id"])
        residual_object_id_map[y, x] = oid
        evidence_class = evidence_class_by_id.get(oid, "")
        evidence_layer = evidence_layer_by_id.get(oid, "")
        residual_evidence_class_map[y, x] = EVIDENCE_CODES.get(evidence_class, 0)
        if object_type_by_id.get(oid) in strong_types:
            strong_residual_support[y, x] += 1
        if evidence_layer in {"candidate_geometry_residual", "strong_geometry_residual"}:
            candidate_residual_support[y, x] += 1
        if evidence_layer == "strong_geometry_residual":
            evidence_strong_residual_support[y, x] += 1
        if evidence_layer in {"diagnostic_residual", "ambiguous_residual"}:
            diagnostic_residual_support[y, x] += 1
    strong_combined_v3_4 = combined_v3 + strong_residual_support
    residual_after_strong = mask & (strong_combined_v3_4 == 0)
    candidate_combined_v3_4_2 = combined_v3 + candidate_residual_support
    evidence_strong_combined_v3_4_2 = combined_v3 + evidence_strong_residual_support
    residual_after_candidate = mask & (candidate_combined_v3_4_2 == 0)
    residual_after_evidence_strong = mask & (evidence_strong_combined_v3_4_2 == 0)

    audit_rows = [
        {
            "residual_object_id": obj["residual_object_id"],
            "object_type": obj["object_type"],
            "audit_state": obj["audit_state"],
            "audit_reason": obj["audit_reason"],
            "support_pixel_count": obj["support_pixel_count"],
            "support_inside_mask": obj["support_inside_mask"],
            "support_inside_residual": obj["support_inside_residual"],
            "creates_synthetic_support": obj["creates_synthetic_support"],
            "line_like_score": obj["line_like_score"],
            "text_like_score": obj["text_like_score"],
            "residual_evidence_class": obj["residual_evidence_class"],
            "residual_evidence_layer": obj["residual_evidence_layer"],
            "geometry_evidence_score": obj["geometry_evidence_score"],
            "candidate_geometry_score": obj["candidate_geometry_score"],
            "strong_geometry_score": obj["strong_geometry_score"],
            "text_like_risk": obj["text_like_risk"],
            "thickness_risk": obj["thickness_risk"],
            "noise_risk": obj["noise_risk"],
            "ambiguity_score": obj["ambiguity_score"],
            "overpromotion_risk": obj["overpromotion_risk"],
            "underpromotion_risk": obj["underpromotion_risk"],
            "line_recovery_evidence_hint": obj["line_recovery_evidence_hint"],
            "axis_evidence_hint": obj["axis_evidence_hint"],
            "crossing_context_hint": obj["crossing_context_hint"],
            "thickness_repair_hint": obj["thickness_repair_hint"],
            "diagnostic_only_hint": obj["diagnostic_only_hint"],
            "evidence_reason": obj["evidence_reason"],
            "nearest_v3_3_object_distance_px": obj["nearest_v3_3_object_distance_px"],
        }
        for obj in objects
    ]

    evidence_rows = [{key: obj.get(key, "") for key in EVIDENCE_FIELDS} for obj in objects]
    candidate_rows = [
        row for row, obj in zip(evidence_rows, objects)
        if obj.get("residual_evidence_layer") in {"candidate_geometry_residual", "strong_geometry_residual"}
    ]
    strong_evidence_rows = [
        row for row, obj in zip(evidence_rows, objects)
        if obj.get("residual_evidence_layer") == "strong_geometry_residual"
    ]
    diagnostic_rows = [
        row for row, obj in zip(evidence_rows, objects)
        if obj.get("residual_evidence_layer") in {"diagnostic_residual", "ambiguous_residual"}
    ]

    active_pixels = int(np.sum(mask))
    v3_support_pixels = int(np.sum(combined_v3 > 0))
    v3_residual_pixels = int(np.sum(residual_in))
    v3_4_residual_geometry_pixels = int(np.sum(residual_support > 0))
    strong_residual_geometry_pixels = int(np.sum(strong_residual_support > 0))
    v3_4_combined_pixels = int(np.sum(combined_v3_4 > 0))
    strong_combined_pixels = int(np.sum(strong_combined_v3_4 > 0))
    candidate_residual_geometry_pixels = int(np.sum(candidate_residual_support > 0))
    evidence_strong_residual_geometry_pixels = int(np.sum(evidence_strong_residual_support > 0))
    diagnostic_residual_pixels = int(np.sum(diagnostic_residual_support > 0))
    candidate_combined_pixels = int(np.sum(candidate_combined_v3_4_2 > 0))
    evidence_strong_combined_pixels = int(np.sum(evidence_strong_combined_v3_4_2 > 0))
    residual_after_pixels = int(np.sum(residual_after))
    residual_after_strong_pixels = int(np.sum(residual_after_strong))
    residual_after_candidate_pixels = int(np.sum(residual_after_candidate))
    residual_after_evidence_strong_pixels = int(np.sum(residual_after_evidence_strong))
    support_outside_mask = int(np.sum((residual_support > 0) & ~mask))
    support_outside_residual = int(np.sum((residual_support > 0) & ~residual_in))
    candidate_outside_residual = int(np.sum((candidate_residual_support > 0) & ~residual_in))
    evidence_strong_outside_candidate = int(np.sum((evidence_strong_residual_support > 0) & ~(candidate_residual_support > 0)))
    diagnostic_outside_residual = int(np.sum((diagnostic_residual_support > 0) & ~residual_in))
    object_type_counts = dict(Counter(str(obj["object_type"]) for obj in objects))
    audit_state_counts = dict(Counter(str(obj["audit_state"]) for obj in objects))
    evidence_counts = evidence_layer_counts(objects)
    residual_metrics = line_like_residual_metrics(residual_after, cfg.min_run_length_px)
    residual_after_candidate_metrics = line_like_residual_metrics(residual_after_candidate, cfg.min_run_length_px)
    residual_after_evidence_strong_metrics = line_like_residual_metrics(residual_after_evidence_strong, cfg.min_run_length_px)

    summary = {
        "version": cfg.version,
        "status": "completed",
        "run_dir": str(run_dir),
        "image_path": str(image_path) if image_path else "",
        "source_v3_3_version": v3_summary.get("version", ""),
        "config": to_jsonable(asdict(cfg)),
        "counts": {
            "input_active_pixels": active_pixels,
            "v3_3_geometry_support_pixels": v3_support_pixels,
            "v3_3_residual_pixels": v3_residual_pixels,
            "v3_4_residual_geometry_pixels": v3_4_residual_geometry_pixels,
            "v3_4_strong_residual_geometry_pixels": strong_residual_geometry_pixels,
            "organized_residual_pixels": v3_4_residual_geometry_pixels,
            "candidate_residual_geometry_pixels": candidate_residual_geometry_pixels,
            "evidence_strong_residual_geometry_pixels": evidence_strong_residual_geometry_pixels,
            "diagnostic_residual_pixels": diagnostic_residual_pixels,
            "v3_4_combined_support_pixels": v3_4_combined_pixels,
            "v3_4_strong_combined_support_pixels": strong_combined_pixels,
            "candidate_combined_v3_4_2_support_pixels": candidate_combined_pixels,
            "evidence_strong_combined_v3_4_2_support_pixels": evidence_strong_combined_pixels,
            "residual_after_v3_4_pixels": residual_after_pixels,
            "residual_after_strong_v3_4_pixels": residual_after_strong_pixels,
            "residual_after_candidate_geometry_pixels": residual_after_candidate_pixels,
            "residual_after_evidence_strong_geometry_pixels": residual_after_evidence_strong_pixels,
            "residual_reduction_pixels": int(v3_residual_pixels - residual_after_pixels),
            "strong_residual_reduction_pixels": int(v3_residual_pixels - residual_after_strong_pixels),
            "candidate_residual_reduction_pixels": int(v3_residual_pixels - residual_after_candidate_pixels),
            "evidence_strong_residual_reduction_pixels": int(v3_residual_pixels - residual_after_evidence_strong_pixels),
            "residual_object_count": len(objects),
            "residual_segment_count": len(segments),
            "residual_gap_count": len(gaps),
            "support_outside_mask_pixels": support_outside_mask,
            "support_outside_residual_pixels": support_outside_residual,
            "candidate_support_outside_residual_pixels": candidate_outside_residual,
            "evidence_strong_support_outside_candidate_pixels": evidence_strong_outside_candidate,
            "diagnostic_support_outside_residual_pixels": diagnostic_outside_residual,
            "object_type_counts": object_type_counts,
            "audit_state_counts": audit_state_counts,
            **evidence_counts,
        },
        "metrics": {
            "residual_reduction_ratio": float((v3_residual_pixels - residual_after_pixels) / max(1, v3_residual_pixels)),
            "strong_residual_reduction_ratio": float((v3_residual_pixels - residual_after_strong_pixels) / max(1, v3_residual_pixels)),
            "candidate_residual_reduction_ratio": float((v3_residual_pixels - residual_after_candidate_pixels) / max(1, v3_residual_pixels)),
            "evidence_strong_residual_reduction_ratio": float((v3_residual_pixels - residual_after_evidence_strong_pixels) / max(1, v3_residual_pixels)),
            "v3_4_combined_coverage_ratio": float(v3_4_combined_pixels / max(1, active_pixels)),
            "v3_4_strong_combined_coverage_ratio": float(strong_combined_pixels / max(1, active_pixels)),
            "candidate_combined_v3_4_2_coverage_ratio": float(candidate_combined_pixels / max(1, active_pixels)),
            "evidence_strong_combined_v3_4_2_coverage_ratio": float(evidence_strong_combined_pixels / max(1, active_pixels)),
            "mean_line_like_score": float(np.mean([obj["line_like_score"] for obj in objects])) if objects else 0.0,
            "mean_text_like_score": float(np.mean([obj["text_like_score"] for obj in objects])) if objects else 0.0,
            "mean_geometry_evidence_score": float(np.mean([obj["geometry_evidence_score"] for obj in objects])) if objects else 0.0,
            "mean_candidate_geometry_score": float(np.mean([obj["candidate_geometry_score"] for obj in objects])) if objects else 0.0,
            "mean_strong_geometry_score": float(np.mean([obj["strong_geometry_score"] for obj in objects])) if objects else 0.0,
            "mean_overpromotion_risk": float(np.mean([obj["overpromotion_risk"] for obj in objects])) if objects else 0.0,
            "mean_underpromotion_risk": float(np.mean([obj["underpromotion_risk"] for obj in objects])) if objects else 0.0,
            "max_gap_px": int(max([obj["max_gap_px"] for obj in objects], default=0)),
            "mean_gap_burden": float(np.mean([obj["gap_burden"] for obj in objects])) if objects else 0.0,
            **residual_metrics,
            "candidate_max_horizontal_residual_run_px": residual_after_candidate_metrics["max_horizontal_residual_run_px"],
            "candidate_max_vertical_residual_run_px": residual_after_candidate_metrics["max_vertical_residual_run_px"],
            "strong_evidence_max_horizontal_residual_run_px": residual_after_evidence_strong_metrics["max_horizontal_residual_run_px"],
            "strong_evidence_max_vertical_residual_run_px": residual_after_evidence_strong_metrics["max_vertical_residual_run_px"],
        },
        "contract": {
            "v3_3_outputs_unchanged": True,
            "support_inside_mask": bool(support_outside_mask == 0),
            "support_inside_residual": bool(support_outside_residual == 0),
            "creates_synthetic_support": False,
            "modifies_mask": False,
            "separates_support_from_axis_hypothesis": True,
            "separates_organized_residual_from_geometry_evidence": True,
            "creates_line_objects": False,
            "creates_axis_descriptors": False,
            "creates_crossings": False,
            "creates_families": False,
            "detects_high_level_semantics": False,
            "detects_only_horizontal_vertical_residual_geometry": True,
        },
        "invariants": {
            "residual_after_v3_4_subset_of_residual_input": bool(np.all(~residual_after | residual_in)),
            "combined_v3_4_contains_combined_v3": bool(np.all(combined_v3_4 >= combined_v3)),
            "presence_identity_preserved": bool(active_pixels == int(np.sum(combined_v3_4 > 0)) + residual_after_pixels),
            "all_objects_inside_mask": all(bool(obj["support_inside_mask"]) for obj in objects),
            "all_objects_inside_residual": all(bool(obj["support_inside_residual"]) for obj in objects),
            "candidate_support_subset_of_organized_residual": bool(np.all(~(candidate_residual_support > 0) | (residual_support > 0))),
            "evidence_strong_support_subset_of_candidate_support": bool(np.all(~(evidence_strong_residual_support > 0) | (candidate_residual_support > 0))),
            "diagnostic_support_subset_of_organized_residual": bool(np.all(~(diagnostic_residual_support > 0) | (residual_support > 0))),
            "candidate_support_inside_residual": bool(candidate_outside_residual == 0),
            "evidence_strong_support_inside_candidate": bool(evidence_strong_outside_candidate == 0),
            "diagnostic_support_inside_residual": bool(diagnostic_outside_residual == 0),
        },
        "outputs": {
            "residual_geometry_objects_csv": "residual_geometry_objects.csv",
            "residual_geometry_segments_csv": "residual_geometry_segments.csv",
            "residual_geometry_gaps_csv": "residual_geometry_gaps.csv",
            "residual_geometry_memberships_csv": "residual_geometry_memberships.csv",
            "residual_geometry_audit_csv": "residual_geometry_audit.csv",
            "residual_evidence_objects_csv": "residual_evidence_objects.csv",
            "residual_geometry_candidates_csv": "residual_geometry_candidates.csv",
            "strong_residual_geometry_objects_csv": "strong_residual_geometry_objects.csv",
            "diagnostic_residual_objects_csv": "diagnostic_residual_objects.csv",
            "residual_layer_audit_json": "residual_layer_audit.json",
            "residual_geometry_support_count_map": "maps/residual_geometry_support_count_map.npy",
            "strong_residual_geometry_support_count_map": "maps/strong_residual_geometry_support_count_map.npy",
            "candidate_residual_geometry_support_count_map": "maps/candidate_residual_geometry_support_count_map.npy",
            "evidence_strong_residual_geometry_support_count_map": "maps/evidence_strong_residual_geometry_support_count_map.npy",
            "diagnostic_residual_support_count_map": "maps/diagnostic_residual_support_count_map.npy",
            "combined_v3_4_support_count_map": "maps/combined_v3_4_support_count_map.npy",
            "strong_combined_v3_4_support_count_map": "maps/strong_combined_v3_4_support_count_map.npy",
            "candidate_combined_v3_4_2_support_count_map": "maps/candidate_combined_v3_4_2_support_count_map.npy",
            "evidence_strong_combined_v3_4_2_support_count_map": "maps/evidence_strong_combined_v3_4_2_support_count_map.npy",
            "residual_after_v3_4_mask": "maps/residual_after_v3_4_mask.npy",
            "residual_after_strong_v3_4_mask": "maps/residual_after_strong_v3_4_mask.npy",
            "residual_after_candidate_geometry_mask": "maps/residual_after_candidate_geometry_mask.npy",
            "residual_after_evidence_strong_geometry_mask": "maps/residual_after_evidence_strong_geometry_mask.npy",
            "residual_object_type_map": "maps/residual_object_type_map.npy",
            "residual_object_id_map": "maps/residual_object_id_map.npy",
            "residual_evidence_class_map": "maps/residual_evidence_class_map.npy",
            "audit_visual": "visuals/12_audit_summary.png",
        },
    }

    residual_layer_audit = {
        "version": cfg.version,
        "semantic_rule": "organized_residual_pixels_are_not_identical_to_geometry_evidence_pixels",
        "counts": {
            "organized_residual_pixels": v3_4_residual_geometry_pixels,
            "candidate_residual_geometry_pixels": candidate_residual_geometry_pixels,
            "evidence_strong_residual_geometry_pixels": evidence_strong_residual_geometry_pixels,
            "diagnostic_residual_pixels": diagnostic_residual_pixels,
            **evidence_counts,
        },
        "invariants": summary["invariants"],
        "contract": summary["contract"],
        "layers": {
            "organized_residual": "all residual pixels assigned to a residual object",
            "candidate_geometry_residual": "residual evidence that may be consumed by later geometry modules",
            "strong_geometry_residual": "residual evidence with stronger local line-like support",
            "diagnostic_residual": "text/noise/ambiguous residual retained for traceability",
        },
    }

    write_csv(out_dir / "residual_geometry_objects.csv", objects, OBJECT_FIELDS)
    write_csv(out_dir / "tables" / "residual_geometry_objects.csv", objects, OBJECT_FIELDS)
    write_csv(out_dir / "residual_geometry_segments.csv", segments, SEGMENT_FIELDS)
    write_csv(out_dir / "tables" / "residual_geometry_segments.csv", segments, SEGMENT_FIELDS)
    write_csv(out_dir / "residual_geometry_gaps.csv", gaps, GAP_FIELDS)
    write_csv(out_dir / "tables" / "residual_geometry_gaps.csv", gaps, GAP_FIELDS)
    write_csv(out_dir / "residual_geometry_memberships.csv", memberships, MEMBERSHIP_FIELDS)
    write_csv(out_dir / "tables" / "residual_geometry_memberships.csv", memberships, MEMBERSHIP_FIELDS)
    write_csv(out_dir / "residual_geometry_audit.csv", audit_rows, AUDIT_FIELDS)
    write_csv(out_dir / "tables" / "residual_geometry_audit.csv", audit_rows, AUDIT_FIELDS)
    write_csv(out_dir / "residual_evidence_objects.csv", evidence_rows, EVIDENCE_FIELDS)
    write_csv(out_dir / "tables" / "residual_evidence_objects.csv", evidence_rows, EVIDENCE_FIELDS)
    write_csv(out_dir / "residual_geometry_candidates.csv", candidate_rows, EVIDENCE_FIELDS)
    write_csv(out_dir / "tables" / "residual_geometry_candidates.csv", candidate_rows, EVIDENCE_FIELDS)
    write_csv(out_dir / "strong_residual_geometry_objects.csv", strong_evidence_rows, EVIDENCE_FIELDS)
    write_csv(out_dir / "tables" / "strong_residual_geometry_objects.csv", strong_evidence_rows, EVIDENCE_FIELDS)
    write_csv(out_dir / "diagnostic_residual_objects.csv", diagnostic_rows, EVIDENCE_FIELDS)
    write_csv(out_dir / "tables" / "diagnostic_residual_objects.csv", diagnostic_rows, EVIDENCE_FIELDS)

    np.save(out_dir / "maps" / "residual_geometry_support_count_map.npy", residual_support)
    np.save(out_dir / "maps" / "strong_residual_geometry_support_count_map.npy", strong_residual_support)
    np.save(out_dir / "maps" / "candidate_residual_geometry_support_count_map.npy", candidate_residual_support)
    np.save(out_dir / "maps" / "evidence_strong_residual_geometry_support_count_map.npy", evidence_strong_residual_support)
    np.save(out_dir / "maps" / "diagnostic_residual_support_count_map.npy", diagnostic_residual_support)
    np.save(out_dir / "maps" / "combined_v3_4_support_count_map.npy", combined_v3_4)
    np.save(out_dir / "maps" / "strong_combined_v3_4_support_count_map.npy", strong_combined_v3_4)
    np.save(out_dir / "maps" / "candidate_combined_v3_4_2_support_count_map.npy", candidate_combined_v3_4_2)
    np.save(out_dir / "maps" / "evidence_strong_combined_v3_4_2_support_count_map.npy", evidence_strong_combined_v3_4_2)
    np.save(out_dir / "maps" / "residual_after_v3_4_mask.npy", residual_after)
    np.save(out_dir / "maps" / "residual_after_strong_v3_4_mask.npy", residual_after_strong)
    np.save(out_dir / "maps" / "residual_after_candidate_geometry_mask.npy", residual_after_candidate)
    np.save(out_dir / "maps" / "residual_after_evidence_strong_geometry_mask.npy", residual_after_evidence_strong)
    np.save(out_dir / "maps" / "residual_object_type_map.npy", residual_type_map)
    np.save(out_dir / "maps" / "residual_object_id_map.npy", residual_object_id_map)
    np.save(out_dir / "maps" / "residual_evidence_class_map.npy", residual_evidence_class_map)
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "residual_layer_audit.json", residual_layer_audit)
    make_visuals(
        out_dir,
        mask,
        residual_in,
        residual_type_map,
        residual_evidence_class_map,
        residual_support,
        candidate_residual_support,
        evidence_strong_residual_support,
        diagnostic_residual_support,
        residual_after,
        residual_after_candidate,
        residual_after_evidence_strong,
        objects,
        cfg,
    )
    print(json.dumps({"status": summary["status"], **summary["counts"], **summary["metrics"]}, ensure_ascii=False), flush=True)
    return summary


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--image", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--polarity", choices=["white_pixels_active", "black_pixels_active"], default="white_pixels_active")
    ap.add_argument("--min-run-length", type=int, default=8)
    ap.add_argument("--min-object-pixels", type=int, default=4)
    ap.add_argument("--max-gap-join", type=int, default=10)
    ap.add_argument("--max-axis-spread", type=float, default=2.0)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config(
        polarity=args.polarity,
        min_run_length_px=args.min_run_length,
        min_object_pixels=args.min_object_pixels,
        max_gap_join_px=args.max_gap_join,
        max_axis_spread_px=args.max_axis_spread,
    )
    run(
        run_dir=Path(args.run_dir),
        image_path=Path(args.image) if args.image else None,
        out_dir=Path(args.out),
        cfg=cfg,
    )


if __name__ == "__main__":
    main()
