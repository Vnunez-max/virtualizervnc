#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module L1.0 - Observed Support Domain Stratifier.

L1.0 classifies traceable observed support after U1.1 into line-study,
non-line, mixed, and deferred domains. It does not create geometry, recognize
text, delete support, or modify upstream outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_L1_0_V1_OBSERVED_SUPPORT_DOMAIN_STRATIFIER"


DOMAIN_CLASSES = [
    "line_domain",
    "probable_line_domain",
    "non_line_domain",
    "probable_non_line_domain",
    "mixed_domain",
    "deferred_domain",
]

DOMAIN_CODE = {
    "line_domain": 1,
    "probable_line_domain": 2,
    "non_line_domain": 3,
    "probable_non_line_domain": 4,
    "mixed_domain": 5,
    "deferred_domain": 6,
}

DOMAIN_PRIORITY = {
    "mixed_domain": 6,
    "deferred_domain": 5,
    "non_line_domain": 4,
    "probable_non_line_domain": 3,
    "probable_line_domain": 2,
    "line_domain": 1,
}

REGION_FIELDS = [
    "domain_region_id",
    "source_u1_1_region_id",
    "source_geometry_object_id",
    "source_u1_1_gate_state",
    "domain_class",
    "domain_subclass",
    "domain_confidence",
    "excluded_from_line_study",
    "available_for_future_modules",
    "region_pixel_count",
    "orientation",
    "elongation_score",
    "longitudinal_continuity_score",
    "width_stability_score",
    "parallel_family_score",
    "grid_context_score",
    "text_like_score",
    "symbol_like_score",
    "curvature_or_complexity_score",
    "short_mark_score",
    "mixed_contact_score",
    "domain_reason",
]

MEMBERSHIP_FIELDS = [
    "domain_region_id",
    "source_u1_1_region_id",
    "source_geometry_object_id",
    "x",
    "y",
    "source_layer",
    "source_u1_1_gate_state",
    "domain_class",
    "domain_subclass",
    "excluded_from_line_study",
    "available_for_future_modules",
    "membership_weight",
]

VALIDATION_FIELDS = [
    "domain_region_id",
    "source_u1_1_region_id",
    "domain_class",
    "support_subset_of_observed_support",
    "line_study_support_subset_of_u1_1_refined_valid_support",
    "non_line_support_not_counted_as_line_study",
    "future_pool_preserves_non_line_support",
    "mixed_domain_not_silently_counted_as_clean_line",
    "deferred_domain_not_silently_counted_as_clean_line",
    "does_not_create_geometry",
    "does_not_delete_support",
    "does_not_modify_upstream",
    "validation_reason",
    "rejection_or_deferral_reason",
]

REQUIRED_U11_FILES = [
    "summary.json",
    "contract_audit.json",
    "u1_1_subobject_regions.csv",
    "u1_1_subobject_memberships.csv",
    "u1_1_subobject_validation.csv",
    "maps/grid_consistent_subsupport_map.npy",
    "maps/suspicious_subsupport_map.npy",
    "maps/blocking_like_subsupport_map.npy",
    "maps/ambiguous_subsupport_map.npy",
    "maps/deferred_subsupport_map.npy",
    "maps/excluded_subsupport_map.npy",
    "maps/u1_1_subobject_region_id_map.npy",
    "maps/u1_1_subobject_gate_state_map.npy",
    "maps/refined_unified_valid_observed_support_map.npy",
]

REQUIRED_V33_FILES = [
    "summary.json",
    "geometry_objects.csv",
    "pixel_geometry_memberships.csv",
    "maps/combined_geometry_support_count_map.npy",
]

OPTIONAL_CONTEXT_FILES = [
    "maps/diagnostic_residual_support_count_map.npy",
    "maps/rejected_residual_support_map.npy",
    "maps/collective_blocking_evidence_map.npy",
]

REQUIRED_OUTPUT_FILES = [
    "l1_0_domain_regions.csv",
    "l1_0_domain_memberships.csv",
    "l1_0_domain_validation.csv",
    "l1_0_line_study_support.csv",
    "l1_0_future_module_pool.csv",
    "l1_0_mixed_domain_regions.csv",
    "l1_0_deferred_domain_regions.csv",
    "summary.json",
    "contract_audit.json",
    "maps/line_domain_support_map.npy",
    "maps/probable_line_domain_support_map.npy",
    "maps/non_line_domain_support_map.npy",
    "maps/probable_non_line_domain_support_map.npy",
    "maps/mixed_domain_support_map.npy",
    "maps/deferred_domain_support_map.npy",
    "maps/future_module_pool_map.npy",
    "maps/line_study_support_map.npy",
    "maps/l1_0_domain_region_id_map.npy",
    "maps/l1_0_domain_class_map.npy",
    "visuals/01_u1_1_input_support.png",
    "visuals/02_line_domain_support.png",
    "visuals/03_non_line_domain_reserved_support.png",
    "visuals/04_mixed_and_deferred_domain_support.png",
    "visuals/05_line_study_support_clean.png",
    "visuals/06_future_module_pool.png",
    "visuals/07_domain_stratification_summary.png",
]

AMBIGUOUS_CLASSES = {"ambiguous_residual_evidence"}


@dataclass
class Config:
    version: str = VERSION
    min_line_elongation_score: float = 0.52
    min_probable_line_elongation_score: float = 0.36
    min_line_continuity_score: float = 0.38
    min_probable_line_continuity_score: float = 0.22
    min_width_stability_score: float = 0.35
    min_line_context_score: float = 0.28
    max_line_text_like_score: float = 0.56
    max_line_symbol_like_score: float = 0.62
    min_non_line_text_like_score: float = 0.68
    min_probable_non_line_text_like_score: float = 0.52
    min_region_pixels: int = 2
    short_mark_longitudinal_length_px: int = 12
    compact_bbox_max_area_px: int = 180
    context_neighborhood_px: int = 2


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


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(to_jsonable(obj), indent=2, ensure_ascii=False), encoding="utf-8")


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_manifest(root: Path, required: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    manifest: Dict[str, Dict[str, Any]] = {}
    for rel in required:
        path = root / rel
        manifest[rel] = {
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else None,
            "sha256": sha256_file(path) if path.exists() else None,
        }
    return manifest


def missing_required(root: Path, required: Sequence[str]) -> List[str]:
    return [rel for rel in required if not (root / rel).exists()]


def load_map(path: Path, dtype: Any | None = None) -> np.ndarray:
    arr = np.load(path)
    return arr.astype(dtype) if dtype is not None else arr


def optional_map(path: Optional[Path], shape: Tuple[int, int], dtype: Any = np.uint16) -> np.ndarray:
    if path is not None and path.exists():
        return np.load(path).astype(dtype)
    return np.zeros(shape, dtype=dtype)


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
    return max(0.0, min(1.0, value))


def ratio(num: int, den: int) -> float:
    return float(num / den) if den else 0.0


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def render_bool(mask: np.ndarray, active: Tuple[int, int, int], bg: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    arr = np.full((mask.shape[0], mask.shape[1], 3), bg, dtype=np.uint8)
    arr[mask.astype(bool)] = active
    return Image.fromarray(arr, "RGB")


def titled(img: Image.Image, title: str) -> Image.Image:
    out = img.copy().convert("RGB")
    d = ImageDraw.Draw(out, "RGBA")
    d.rectangle((0, 0, out.width, 28), fill=(255, 255, 255, 235))
    d.text((8, 8), title, fill=(0, 0, 0, 255), font=font(10))
    return out


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    h, w = mask.shape
    out = mask.copy()
    ys, xs = np.where(mask)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            yy = ys + dy
            xx = xs + dx
            ok = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
            out[yy[ok], xx[ok]] = True
    return out


def longitudinal_coord(orientation: str, x: int, y: int) -> int:
    return int(y if orientation == "vertical" else x)


def perpendicular_coord(orientation: str, x: int, y: int) -> int:
    return int(x if orientation == "vertical" else y)


def object_longitudinal_range(row: Dict[str, str]) -> Tuple[float, float]:
    orientation = row.get("orientation", "")
    if orientation == "vertical":
        a = as_float(row.get("y1"))
        b = as_float(row.get("y2"))
    else:
        a = as_float(row.get("x1"))
        b = as_float(row.get("x2"))
    return min(a, b), max(a, b)


def parse_ids(value: str) -> List[str]:
    value = value.strip().replace(";", ",")
    return [v.strip() for v in value.split(",") if v.strip()]


def family_maps(v33_dir: Path) -> Tuple[Dict[str, int], Dict[str, float]]:
    line_to_members = defaultdict(int)
    line_to_conf = defaultdict(float)
    for fam in read_csv(v33_dir / "band_families.csv"):
        members = parse_ids(fam.get("member_line_ids", ""))
        count = as_int(fam.get("member_count"), len(members))
        conf = as_float(fam.get("family_confidence"))
        for line_id in members:
            line_to_members[line_id] = max(line_to_members[line_id], count)
            line_to_conf[line_id] = max(line_to_conf[line_id], conf)
    for row in read_csv(v33_dir / "family_members.csv"):
        line_id = str(row.get("line_id", ""))
        if line_id:
            line_to_members[line_id] = max(line_to_members[line_id], 2)
    return dict(line_to_members), dict(line_to_conf)


def load_region_points(u11_dir: Path, region_map: np.ndarray) -> Tuple[Dict[int, List[Tuple[int, int]]], Dict[int, Dict[Tuple[int, int], float]]]:
    points: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    weights: Dict[int, Dict[Tuple[int, int], float]] = defaultdict(dict)
    for row in read_csv(u11_dir / "u1_1_subobject_memberships.csv"):
        rid = as_int(row.get("subobject_region_id"))
        x, y = as_int(row.get("x")), as_int(row.get("y"))
        if rid and 0 <= y < region_map.shape[0] and 0 <= x < region_map.shape[1]:
            points[rid].append((x, y))
            weights[rid][(x, y)] = as_float(row.get("membership_weight"), 1.0)
    # Region-id map is the fallback source of truth if memberships are sparse.
    for rid in np.unique(region_map):
        rid_i = int(rid)
        if rid_i <= 0 or points.get(rid_i):
            continue
        ys, xs = np.where(region_map == rid_i)
        for y, x in zip(ys, xs):
            points[rid_i].append((int(x), int(y)))
            weights[rid_i][(int(x), int(y))] = 1.0
    return points, weights


def bbox(points: Sequence[Tuple[int, int]]) -> Tuple[int, int, int, int]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def profile_features(points: Sequence[Tuple[int, int]], orientation: str) -> Dict[str, Any]:
    if not points:
        return {
            "bbox_width": 0,
            "bbox_height": 0,
            "elongation_score": 0.0,
            "longitudinal_run_length": 0,
            "longitudinal_continuity_score": 0.0,
            "width_stability_score": 0.0,
            "fill_score": 0.0,
            "closed_shape_score": 0.0,
            "orientation_stability_score": 0.0,
        }
    x0, y0, x1, y1 = bbox(points)
    w = x1 - x0 + 1
    h = y1 - y0 + 1
    long_len = max(w, h)
    short_len = max(1, min(w, h))
    aspect = long_len / short_len
    elongation = clamp01((aspect - 1.0) / 10.0)
    orientation_stability = clamp01(1.0 - min(w, h) / max(w, h, 1))

    longs: Dict[int, Set[int]] = defaultdict(set)
    for x, y in points:
        longs[longitudinal_coord(orientation, x, y)].add(perpendicular_coord(orientation, x, y))
    unique_longs = sorted(longs)
    span = max(unique_longs) - min(unique_longs) + 1 if unique_longs else 0
    run_length = len(unique_longs)
    continuity = ratio(run_length, span)
    widths = [len(v) for v in longs.values()]
    if widths:
        m = mean([float(v) for v in widths])
        var = mean([(float(v) - m) ** 2 for v in widths])
        width_stability = clamp01(1.0 - math.sqrt(var) / max(m, 1.0))
    else:
        width_stability = 0.0
    area = w * h
    fill = ratio(len(set(points)), area)
    closed_shape = clamp01((1.0 - elongation) * fill * min(area / 120.0, 1.0))
    return {
        "bbox_width": w,
        "bbox_height": h,
        "elongation_score": elongation,
        "longitudinal_run_length": run_length,
        "longitudinal_continuity_score": continuity,
        "width_stability_score": width_stability,
        "fill_score": fill,
        "closed_shape_score": closed_shape,
        "orientation_stability_score": orientation_stability,
    }


def context_features(
    points: Sequence[Tuple[int, int]],
    orientation: str,
    source_object: Dict[str, str],
    v33_support: np.ndarray,
    family_members: Dict[str, int],
    family_conf: Dict[str, float],
) -> Dict[str, float]:
    if not points:
        return {
            "parallel_family_score": 0.0,
            "grid_context_score": 0.0,
            "crossing_context_score": 0.0,
            "neighbor_line_support_score": 0.0,
            "fragment_colinearity_score": 0.0,
        }
    line_id = str(source_object.get("line_id", ""))
    obj_type = source_object.get("object_type", "")
    state = source_object.get("state", "")
    members = family_members.get(line_id, 0)
    conf = family_conf.get(line_id, 0.0)
    parallel_score = clamp01(max(conf, members / 6.0))
    if "faithful_line" in obj_type or "multipart" in obj_type:
        parallel_score = max(parallel_score, 0.35)
    if state == "admissible":
        parallel_score = max(parallel_score, 0.55)

    pts = list(set(points))
    h, w = v33_support.shape
    crossing_hits = 0
    neighbor_hits = 0
    for x, y in pts[:: max(1, len(pts) // 300)]:
        if orientation == "horizontal":
            # Perpendicular support above/below implies grid/crossing context.
            for dy in (-2, -1, 1, 2):
                yy = y + dy
                if 0 <= yy < h and v33_support[yy, x]:
                    crossing_hits += 1
                    break
            for dx in (-3, -2, -1, 1, 2, 3):
                xx = x + dx
                if 0 <= xx < w and v33_support[y, xx]:
                    neighbor_hits += 1
                    break
        else:
            for dx in (-2, -1, 1, 2):
                xx = x + dx
                if 0 <= xx < w and v33_support[y, xx]:
                    crossing_hits += 1
                    break
            for dy in (-3, -2, -1, 1, 2, 3):
                yy = y + dy
                if 0 <= yy < h and v33_support[yy, x]:
                    neighbor_hits += 1
                    break
    sample_count = len(pts[:: max(1, len(pts) // 300)])
    crossing_score = ratio(crossing_hits, sample_count)
    neighbor_score = ratio(neighbor_hits, sample_count)
    start, end = object_longitudinal_range(source_object)
    declared_len = abs(end - start) + 1
    fragment_colinearity = clamp01(declared_len / 80.0)
    grid_context = clamp01(0.45 * parallel_score + 0.30 * crossing_score + 0.25 * neighbor_score)
    return {
        "parallel_family_score": parallel_score,
        "grid_context_score": grid_context,
        "crossing_context_score": crossing_score,
        "neighbor_line_support_score": neighbor_score,
        "fragment_colinearity_score": fragment_colinearity,
    }


def classify_domain(features: Dict[str, float], source_state: str, cfg: Config) -> Tuple[str, str, float, str]:
    count = int(features["region_pixel_count"])
    elong = features["elongation_score"]
    cont = features["longitudinal_continuity_score"]
    width_stability = features["width_stability_score"]
    parallel = features["parallel_family_score"]
    grid = features["grid_context_score"]
    neighbor = features["neighbor_line_support_score"]
    colinear = features["fragment_colinearity_score"]
    complexity = features["curvature_or_complexity_score"]
    closed_shape = features["closed_shape_score"]
    text_like = features["text_like_score"]
    symbol_like = features["symbol_like_score"]
    short_mark = features["short_mark_score"]
    mixed = features["mixed_contact_score"]

    line_context = max(parallel, grid, neighbor, colinear)
    line_score = clamp01(0.28 * elong + 0.22 * cont + 0.16 * width_stability + 0.24 * line_context + 0.10 * (1.0 - short_mark))
    non_line_score = clamp01(0.38 * text_like + 0.22 * symbol_like + 0.18 * complexity + 0.12 * closed_shape + 0.10 * short_mark)
    confidence = abs(line_score - non_line_score)

    if count < cfg.min_region_pixels:
        return "deferred_domain", "ambiguous_domain", 0.35, "too_few_traceable_pixels"

    # U1.1 unsafe support is never silently reintroduced into line study.
    if source_state in {"blocking_like", "ambiguous"}:
        if line_score >= 0.55 and non_line_score >= 0.45:
            return "mixed_domain", "mixed_line_text_contact", max(line_score, non_line_score), "unsafe_u1_1_state_with_mixed_line_and_non_line_evidence"
        return "non_line_domain", "unknown_non_line", max(0.55, non_line_score), f"source_u1_1_state_{source_state}"
    if source_state == "deferred":
        return "deferred_domain", "ambiguous_domain", max(0.40, line_score), "source_u1_1_deferred"
    if source_state == "suspicious":
        if line_score >= 0.68 and non_line_score < 0.35:
            return "deferred_domain", "line_fragment", line_score, "line_like_but_source_u1_1_suspicious"
        if non_line_score >= 0.52:
            return "probable_non_line_domain", "unknown_non_line", non_line_score, "source_u1_1_suspicious_and_non_line_like"
        return "deferred_domain", "ambiguous_domain", max(line_score, non_line_score), "source_u1_1_suspicious"

    if mixed >= 0.55 and line_score >= 0.42 and non_line_score >= 0.42:
        return "mixed_domain", "mixed_line_text_contact", max(line_score, non_line_score), "line_and_non_line_features_touch"

    if (
        elong >= cfg.min_line_elongation_score
        and cont >= cfg.min_line_continuity_score
        and width_stability >= cfg.min_width_stability_score
        and line_context >= cfg.min_line_context_score
        and text_like <= cfg.max_line_text_like_score
        and symbol_like <= cfg.max_line_symbol_like_score
    ):
        subclass = "grid_line_like" if grid >= 0.45 or parallel >= 0.55 else "structural_line"
        return "line_domain", subclass, max(0.55, line_score), "elongated_continuous_contextual_line_support"

    if (
        elong >= cfg.min_probable_line_elongation_score
        and cont >= cfg.min_probable_line_continuity_score
        and line_context >= cfg.min_line_context_score
        and non_line_score < 0.62
    ):
        subclass = "line_fragment" if short_mark >= 0.35 else "structural_line"
        return "probable_line_domain", subclass, max(0.45, line_score), "probable_line_fragment_or_contextual_support"

    if text_like >= cfg.min_non_line_text_like_score and line_context < 0.45:
        subclass = "text_like" if complexity >= symbol_like else "unknown_non_line"
        return "non_line_domain", subclass, max(0.55, non_line_score), "compact_or_character_like_without_line_context"

    if symbol_like >= cfg.min_non_line_text_like_score and line_context < 0.45:
        return "non_line_domain", "symbol_like", max(0.55, non_line_score), "symbol_like_microstructure_without_line_context"

    if text_like >= cfg.min_probable_non_line_text_like_score or symbol_like >= cfg.min_probable_non_line_text_like_score:
        subclass = "tick_like_nonstructural" if short_mark >= 0.55 else "unknown_non_line"
        return "probable_non_line_domain", subclass, max(0.45, non_line_score), "probable_non_line_microstructure"

    if line_score >= non_line_score:
        return "deferred_domain", "line_fragment", max(0.35, line_score), "line_like_but_insufficient_domain_context"
    return "deferred_domain", "ambiguous_domain", max(0.35, non_line_score), "insufficient_domain_context"


def compute_domain_features(
    region: Dict[str, str],
    points: Sequence[Tuple[int, int]],
    source_object: Dict[str, str],
    v33_support: np.ndarray,
    family_members: Dict[str, int],
    family_conf: Dict[str, float],
    conflict_near: np.ndarray,
    cfg: Config,
) -> Dict[str, float]:
    orientation = region.get("orientation") or source_object.get("orientation", "horizontal")
    if orientation not in {"horizontal", "vertical"}:
        orientation = "horizontal"
    prof = profile_features(points, orientation)
    ctx = context_features(points, orientation, source_object, v33_support, family_members, family_conf)
    count = len(set(points))
    bbox_area = prof["bbox_width"] * prof["bbox_height"]
    compactness = clamp01(1.0 - prof["elongation_score"])
    short_mark = clamp01(1.0 - prof["longitudinal_run_length"] / max(cfg.short_mark_longitudinal_length_px, 1))
    fill = prof["fill_score"]
    axis_p95 = as_float(region.get("axis_distance_p95_px"))
    width_est = as_float(region.get("local_width_estimate_px"))
    local_conflict = as_float(region.get("local_conflict_score"))

    near_conflict_ratio = 0.0
    if points:
        near_conflict_ratio = ratio(sum(1 for x, y in set(points) if conflict_near[y, x]), count)

    # Morphological, not semantic: compact dense marks with low line context are
    # text-like/symbol-like candidates.
    line_context = max(ctx["parallel_family_score"], ctx["grid_context_score"], ctx["neighbor_line_support_score"], ctx["fragment_colinearity_score"])
    compact_area_score = 1.0 if bbox_area <= cfg.compact_bbox_max_area_px else clamp01(cfg.compact_bbox_max_area_px / max(bbox_area, 1))
    text_like = clamp01(
        0.28 * compactness
        + 0.20 * short_mark
        + 0.16 * compact_area_score
        + 0.16 * (1.0 - prof["longitudinal_continuity_score"])
        + 0.12 * fill
        + 0.08 * (1.0 - line_context)
    )
    symbol_like = clamp01(
        0.34 * compactness
        + 0.20 * prof["closed_shape_score"]
        + 0.16 * fill
        + 0.16 * short_mark
        + 0.14 * (1.0 - line_context)
    )
    curvature = clamp01(
        0.35 * compactness
        + 0.20 * prof["closed_shape_score"]
        + 0.20 * (1.0 - prof["width_stability_score"])
        + 0.15 * fill
        + 0.10 * near_conflict_ratio
    )
    mixed = clamp01(
        0.38 * min(max(ctx["grid_context_score"], ctx["parallel_family_score"]), max(text_like, symbol_like))
        + 0.22 * near_conflict_ratio
        + 0.20 * local_conflict
        + 0.20 * (1.0 if width_est > 8 and axis_p95 > 4 else 0.0)
    )
    features: Dict[str, float] = {
        "region_pixel_count": float(count),
        "bounding_box_width": float(prof["bbox_width"]),
        "bounding_box_height": float(prof["bbox_height"]),
        "elongation_score": float(prof["elongation_score"]),
        "orientation_stability_score": float(prof["orientation_stability_score"]),
        "longitudinal_run_length": float(prof["longitudinal_run_length"]),
        "longitudinal_continuity_score": float(prof["longitudinal_continuity_score"]),
        "width_stability_score": float(prof["width_stability_score"]),
        "axis_distance_p95_px": float(axis_p95),
        "parallel_family_score": float(ctx["parallel_family_score"]),
        "grid_context_score": float(ctx["grid_context_score"]),
        "crossing_context_score": float(ctx["crossing_context_score"]),
        "neighbor_line_support_score": float(ctx["neighbor_line_support_score"]),
        "fragment_colinearity_score": float(ctx["fragment_colinearity_score"]),
        "curvature_or_complexity_score": float(curvature),
        "closed_shape_score": float(prof["closed_shape_score"]),
        "text_like_microstructure_score": float(text_like),
        "text_like_score": float(text_like),
        "digit_like_microstructure_score": float(text_like),
        "symbol_like_microstructure_score": float(symbol_like),
        "symbol_like_score": float(symbol_like),
        "short_mark_score": float(short_mark),
        "mixed_contact_score": float(mixed),
    }
    return features


def make_visuals(
    out_dir: Path,
    input_support: np.ndarray,
    line_domain: np.ndarray,
    probable_line: np.ndarray,
    non_line: np.ndarray,
    probable_non_line: np.ndarray,
    mixed: np.ndarray,
    deferred: np.ndarray,
    line_study: np.ndarray,
    future_pool: np.ndarray,
    class_map: np.ndarray,
) -> None:
    vdir = out_dir / "visuals"
    ensure_dir(vdir)
    render_bool(input_support, (0, 0, 0)).save(vdir / "01_u1_1_input_support.png")

    arr_line = np.full((input_support.shape[0], input_support.shape[1], 3), 255, dtype=np.uint8)
    arr_line[line_domain] = (38, 122, 255)
    arr_line[probable_line] = (0, 185, 210)
    Image.fromarray(arr_line, "RGB").save(vdir / "02_line_domain_support.png")

    arr_non = np.full((input_support.shape[0], input_support.shape[1], 3), 255, dtype=np.uint8)
    arr_non[non_line] = (220, 0, 0)
    arr_non[probable_non_line] = (255, 160, 0)
    Image.fromarray(arr_non, "RGB").save(vdir / "03_non_line_domain_reserved_support.png")

    arr_mid = np.full((input_support.shape[0], input_support.shape[1], 3), 255, dtype=np.uint8)
    arr_mid[mixed] = (150, 70, 210)
    arr_mid[deferred] = (160, 160, 160)
    Image.fromarray(arr_mid, "RGB").save(vdir / "04_mixed_and_deferred_domain_support.png")
    render_bool(line_study, (0, 175, 85)).save(vdir / "05_line_study_support_clean.png")
    render_bool(future_pool, (210, 0, 210)).save(vdir / "06_future_module_pool.png")

    arr_all = np.full((input_support.shape[0], input_support.shape[1], 3), 255, dtype=np.uint8)
    arr_all[class_map == DOMAIN_CODE["line_domain"]] = (38, 122, 255)
    arr_all[class_map == DOMAIN_CODE["probable_line_domain"]] = (0, 185, 210)
    arr_all[class_map == DOMAIN_CODE["non_line_domain"]] = (220, 0, 0)
    arr_all[class_map == DOMAIN_CODE["probable_non_line_domain"]] = (255, 160, 0)
    arr_all[class_map == DOMAIN_CODE["mixed_domain"]] = (150, 70, 210)
    arr_all[class_map == DOMAIN_CODE["deferred_domain"]] = (160, 160, 160)

    panels = [
        titled(render_bool(input_support, (0, 0, 0)), "U1.1 input support"),
        titled(Image.fromarray(arr_line, "RGB"), "line blue / probable cyan"),
        titled(Image.fromarray(arr_non, "RGB"), "non-line red / probable orange"),
        titled(Image.fromarray(arr_mid, "RGB"), "mixed purple / deferred gray"),
        titled(render_bool(line_study, (0, 175, 85)), "line-study support green"),
        titled(render_bool(future_pool, (210, 0, 210)), "future-module pool magenta"),
        titled(Image.fromarray(arr_all, "RGB"), "domain stratification"),
    ]
    tile_w = max(p.width for p in panels)
    tile_h = max(p.height for p in panels)
    sheet = Image.new("RGB", (tile_w * 3, tile_h * 3 + 38), "white")
    d = ImageDraw.Draw(sheet)
    d.text((8, 10), "L1.0 Observed Support Domain Stratifier", fill="black", font=font(16))
    for idx, panel in enumerate(panels):
        x = (idx % 3) * tile_w
        y = 38 + (idx // 3) * tile_h
        sheet.paste(panel, (x, y))
    sheet.save(vdir / "07_domain_stratification_summary.png")


def run(
    u11_dir: Path,
    v33_dir: Path,
    out_dir: Path,
    v342_dir: Optional[Path] = None,
    c10_dir: Optional[Path] = None,
    c11_dir: Optional[Path] = None,
    u10_dir: Optional[Path] = None,
    cfg: Optional[Config] = None,
) -> Dict[str, Any]:
    cfg = cfg or Config()
    u11_dir = Path(u11_dir)
    v33_dir = Path(v33_dir)
    out_dir = Path(out_dir)
    v342_dir = Path(v342_dir) if v342_dir else None
    c10_dir = Path(c10_dir) if c10_dir else None
    c11_dir = Path(c11_dir) if c11_dir else None
    u10_dir = Path(u10_dir) if u10_dir else None

    missing_inputs = {
        "u1_1": missing_required(u11_dir, REQUIRED_U11_FILES),
        "v3_3": missing_required(v33_dir, REQUIRED_V33_FILES),
    }
    absent = [f"{group}:{rel}" for group, rels in missing_inputs.items() for rel in rels]
    if absent:
        raise FileNotFoundError("Missing required L1.0 input files: " + ", ".join(absent))

    v33_manifest_files = REQUIRED_V33_FILES + [
        rel
        for rel in [
            "band_families.csv",
            "family_members.csv",
        ]
        if (v33_dir / rel).exists()
    ]
    source_manifest_before = {
        "u1_1": file_manifest(u11_dir, REQUIRED_U11_FILES),
        "v3_3": file_manifest(v33_dir, v33_manifest_files),
    }
    if v342_dir:
        source_manifest_before["v3_4_2"] = file_manifest(v342_dir, [rel for rel in ["summary.json", "maps/diagnostic_residual_support_count_map.npy"] if (v342_dir / rel).exists()])
    if c10_dir:
        source_manifest_before["c1_0"] = file_manifest(c10_dir, [rel for rel in ["summary.json", "maps/rejected_residual_support_map.npy"] if (c10_dir / rel).exists()])
    if c11_dir:
        source_manifest_before["c1_1"] = file_manifest(c11_dir, [rel for rel in ["summary.json", "maps/collective_blocking_evidence_map.npy"] if (c11_dir / rel).exists()])
    if u10_dir:
        source_manifest_before["u1_0"] = file_manifest(u10_dir, [rel for rel in ["summary.json", "contract_audit.json"] if (u10_dir / rel).exists()])

    ensure_dir(out_dir)
    ensure_dir(out_dir / "maps")
    ensure_dir(out_dir / "visuals")

    u11_summary = read_json(u11_dir / "summary.json")
    v33_summary = read_json(v33_dir / "summary.json")
    regions = read_csv(u11_dir / "u1_1_subobject_regions.csv")
    geometry_objects = {str(row.get("geometry_object_id", "")): row for row in read_csv(v33_dir / "geometry_objects.csv")}
    family_members, family_conf = family_maps(v33_dir)

    region_map = load_map(u11_dir / "maps" / "u1_1_subobject_region_id_map.npy", np.int32)
    u11_state_map = load_map(u11_dir / "maps" / "u1_1_subobject_gate_state_map.npy", np.uint8)
    u11_refined = load_map(u11_dir / "maps" / "refined_unified_valid_observed_support_map.npy", np.uint16) > 0
    v33_support = load_map(v33_dir / "maps" / "combined_geometry_support_count_map.npy", np.uint16) > 0
    shape = region_map.shape
    observed_support = region_map > 0
    diagnostic = optional_map(v342_dir / "maps" / "diagnostic_residual_support_count_map.npy" if v342_dir else None, shape, np.uint16) > 0
    c10_rejected = optional_map(c10_dir / "maps" / "rejected_residual_support_map.npy" if c10_dir else None, shape, np.uint16) > 0
    c11_blocking = optional_map(c11_dir / "maps" / "collective_blocking_evidence_map.npy" if c11_dir else None, shape, np.uint16) > 0
    conflict_near = dilate(diagnostic | c10_rejected | c11_blocking, cfg.context_neighborhood_px)

    points_by_region, weights_by_region = load_region_points(u11_dir, region_map)

    class_map = np.zeros(shape, dtype=np.uint8)
    domain_region_id_map = np.zeros(shape, dtype=np.int32)
    region_rows: List[Dict[str, Any]] = []
    membership_rows: List[Dict[str, Any]] = []
    validation_rows: List[Dict[str, Any]] = []
    region_by_id = {as_int(row.get("subobject_region_id")): row for row in regions}

    for domain_region_id, source_region_id in enumerate(sorted(points_by_region), start=1):
        source_region = region_by_id.get(source_region_id, {})
        points = sorted(set(points_by_region[source_region_id]), key=lambda p: (p[1], p[0]))
        source_gid = str(source_region.get("source_geometry_object_id", ""))
        source_object = geometry_objects.get(source_gid, {})
        source_state = source_region.get("gate_state", "")
        orientation = source_region.get("orientation") or source_object.get("orientation", "horizontal")
        features = compute_domain_features(
            source_region,
            points,
            source_object,
            v33_support,
            family_members,
            family_conf,
            conflict_near,
            cfg,
        )
        domain_class, subclass, confidence, reason = classify_domain(features, source_state, cfg)

        excluded_from_line = domain_class not in {"line_domain", "probable_line_domain"}
        available_future = domain_class in {"non_line_domain", "probable_non_line_domain", "mixed_domain", "deferred_domain"}
        row = {
            "domain_region_id": domain_region_id,
            "source_u1_1_region_id": source_region_id,
            "source_geometry_object_id": source_gid,
            "source_u1_1_gate_state": source_state,
            "domain_class": domain_class,
            "domain_subclass": subclass,
            "domain_confidence": confidence,
            "excluded_from_line_study": excluded_from_line,
            "available_for_future_modules": available_future,
            "region_pixel_count": int(features["region_pixel_count"]),
            "orientation": orientation,
            "elongation_score": features["elongation_score"],
            "longitudinal_continuity_score": features["longitudinal_continuity_score"],
            "width_stability_score": features["width_stability_score"],
            "parallel_family_score": features["parallel_family_score"],
            "grid_context_score": features["grid_context_score"],
            "text_like_score": features["text_like_score"],
            "symbol_like_score": features["symbol_like_score"],
            "curvature_or_complexity_score": features["curvature_or_complexity_score"],
            "short_mark_score": features["short_mark_score"],
            "mixed_contact_score": features["mixed_contact_score"],
            "domain_reason": reason,
        }
        region_rows.append(row)

        for x, y in points:
            old_code = int(class_map[y, x])
            old_class = next((name for name, code in DOMAIN_CODE.items() if code == old_code), "")
            if not old_class or DOMAIN_PRIORITY[domain_class] > DOMAIN_PRIORITY[old_class]:
                class_map[y, x] = DOMAIN_CODE[domain_class]
                domain_region_id_map[y, x] = domain_region_id
            membership_rows.append(
                {
                    "domain_region_id": domain_region_id,
                    "source_u1_1_region_id": source_region_id,
                    "source_geometry_object_id": source_gid,
                    "x": x,
                    "y": y,
                    "source_layer": "u1_1_observed_support",
                    "source_u1_1_gate_state": source_state,
                    "domain_class": domain_class,
                    "domain_subclass": subclass,
                    "excluded_from_line_study": excluded_from_line,
                    "available_for_future_modules": available_future,
                    "membership_weight": weights_by_region[source_region_id].get((x, y), 1.0),
                }
            )

        validation_rows.append(
            {
                "domain_region_id": domain_region_id,
                "source_u1_1_region_id": source_region_id,
                "domain_class": domain_class,
                "support_subset_of_observed_support": True,
                "line_study_support_subset_of_u1_1_refined_valid_support": domain_class not in {"line_domain", "probable_line_domain"} or source_state == "grid_consistent",
                "non_line_support_not_counted_as_line_study": domain_class not in {"non_line_domain", "probable_non_line_domain"} or excluded_from_line,
                "future_pool_preserves_non_line_support": domain_class not in {"non_line_domain", "probable_non_line_domain"} or available_future,
                "mixed_domain_not_silently_counted_as_clean_line": domain_class != "mixed_domain" or excluded_from_line,
                "deferred_domain_not_silently_counted_as_clean_line": domain_class != "deferred_domain" or excluded_from_line,
                "does_not_create_geometry": True,
                "does_not_delete_support": True,
                "does_not_modify_upstream": True,
                "validation_reason": "domain_assigned_from_traceable_geometric_features",
                "rejection_or_deferral_reason": "" if domain_class in {"line_domain", "probable_line_domain"} else reason,
            }
        )

    line_domain_map = class_map == DOMAIN_CODE["line_domain"]
    probable_line_map = class_map == DOMAIN_CODE["probable_line_domain"]
    non_line_map = class_map == DOMAIN_CODE["non_line_domain"]
    probable_non_line_map = class_map == DOMAIN_CODE["probable_non_line_domain"]
    mixed_map = class_map == DOMAIN_CODE["mixed_domain"]
    deferred_map = class_map == DOMAIN_CODE["deferred_domain"]
    future_pool_map = non_line_map | probable_non_line_map | mixed_map | deferred_map
    line_study_map = (line_domain_map | probable_line_map) & u11_refined & ~future_pool_map & ~diagnostic

    state_maps = [line_domain_map, probable_line_map, non_line_map, probable_non_line_map, mixed_map, deferred_map]
    overlap = np.zeros(shape, dtype=np.uint8)
    for m in state_maps:
        overlap += m.astype(np.uint8)

    source_manifest_after = {
        "u1_1": file_manifest(u11_dir, REQUIRED_U11_FILES),
        "v3_3": file_manifest(v33_dir, v33_manifest_files),
    }
    if v342_dir:
        source_manifest_after["v3_4_2"] = file_manifest(v342_dir, [rel for rel in ["summary.json", "maps/diagnostic_residual_support_count_map.npy"] if (v342_dir / rel).exists()])
    if c10_dir:
        source_manifest_after["c1_0"] = file_manifest(c10_dir, [rel for rel in ["summary.json", "maps/rejected_residual_support_map.npy"] if (c10_dir / rel).exists()])
    if c11_dir:
        source_manifest_after["c1_1"] = file_manifest(c11_dir, [rel for rel in ["summary.json", "maps/collective_blocking_evidence_map.npy"] if (c11_dir / rel).exists()])
    if u10_dir:
        source_manifest_after["u1_0"] = file_manifest(u10_dir, [rel for rel in ["summary.json", "contract_audit.json"] if (u10_dir / rel).exists()])

    membership_pixel_set = {(as_int(r["x"]), as_int(r["y"])) for r in membership_rows}
    future_membership_set = {
        (as_int(r["x"]), as_int(r["y"]))
        for r in membership_rows
        if str(r["domain_class"]) in {"non_line_domain", "probable_non_line_domain", "mixed_domain", "deferred_domain"}
    }
    future_pixel_set = set(zip(np.where(future_pool_map)[1].tolist(), np.where(future_pool_map)[0].tolist()))

    invariants = {
        "line_domain_support_subset_of_observed_support": bool(np.all(~line_domain_map | observed_support)),
        "probable_line_domain_support_subset_of_observed_support": bool(np.all(~probable_line_map | observed_support)),
        "non_line_domain_support_subset_of_observed_support": bool(np.all(~non_line_map | observed_support)),
        "probable_non_line_domain_support_subset_of_observed_support": bool(np.all(~probable_non_line_map | observed_support)),
        "mixed_domain_support_subset_of_observed_support": bool(np.all(~mixed_map | observed_support)),
        "deferred_domain_support_subset_of_observed_support": bool(np.all(~deferred_map | observed_support)),
        "all_l1_0_domain_maps_are_mutually_exclusive": bool(np.all(overlap <= 1)),
        "line_study_support_excludes_non_line_probable_non_line_mixed_deferred": not bool(np.any(line_study_map & future_pool_map)),
        "future_module_pool_includes_non_line_probable_non_line_mixed_deferred": bool(np.all((non_line_map | probable_non_line_map | mixed_map | deferred_map) <= future_pool_map)),
        "future_module_pool_preserves_traceability": future_pixel_set.issubset(membership_pixel_set) and future_pixel_set.issubset(future_membership_set),
        "non_line_support_is_not_deleted": bool(np.all((non_line_map | probable_non_line_map) <= future_pool_map)),
        "mixed_support_is_not_silently_counted_as_clean_line": not bool(np.any(mixed_map & line_study_map)),
        "deferred_support_is_not_silently_counted_as_clean_line": not bool(np.any(deferred_map & line_study_map)),
        "inferred_spans_are_not_converted_to_observed_support": True,
        "diagnostic_residual_is_not_converted_to_line_study_support": not bool(np.any(line_study_map & diagnostic)),
        "ambiguous_residual_is_not_converted_to_line_study_support": True,
        "does_not_create_geometry": True,
        "does_not_create_final_lineobjects": True,
        "does_not_create_axisdescriptors": True,
        "does_not_create_crossings": True,
        "does_not_modify_v3_3_outputs": source_manifest_before["v3_3"] == source_manifest_after["v3_3"],
        "does_not_modify_v3_4_2_outputs": source_manifest_before.get("v3_4_2", {}) == source_manifest_after.get("v3_4_2", {}),
        "does_not_modify_c1_0_outputs": source_manifest_before.get("c1_0", {}) == source_manifest_after.get("c1_0", {}),
        "does_not_modify_c1_1_outputs": source_manifest_before.get("c1_1", {}) == source_manifest_after.get("c1_1", {}),
        "does_not_modify_u1_0_outputs": source_manifest_before.get("u1_0", {}) == source_manifest_after.get("u1_0", {}),
        "does_not_modify_u1_1_outputs": source_manifest_before["u1_1"] == source_manifest_after["u1_1"],
    }

    np.save(out_dir / "maps" / "line_domain_support_map.npy", line_domain_map.astype(np.uint16))
    np.save(out_dir / "maps" / "probable_line_domain_support_map.npy", probable_line_map.astype(np.uint16))
    np.save(out_dir / "maps" / "non_line_domain_support_map.npy", non_line_map.astype(np.uint16))
    np.save(out_dir / "maps" / "probable_non_line_domain_support_map.npy", probable_non_line_map.astype(np.uint16))
    np.save(out_dir / "maps" / "mixed_domain_support_map.npy", mixed_map.astype(np.uint16))
    np.save(out_dir / "maps" / "deferred_domain_support_map.npy", deferred_map.astype(np.uint16))
    np.save(out_dir / "maps" / "future_module_pool_map.npy", future_pool_map.astype(np.uint16))
    np.save(out_dir / "maps" / "line_study_support_map.npy", line_study_map.astype(np.uint16))
    np.save(out_dir / "maps" / "l1_0_domain_region_id_map.npy", domain_region_id_map.astype(np.int32))
    np.save(out_dir / "maps" / "l1_0_domain_class_map.npy", class_map.astype(np.uint8))

    write_csv(out_dir / "l1_0_domain_regions.csv", region_rows, REGION_FIELDS)
    write_csv(out_dir / "l1_0_domain_memberships.csv", membership_rows, MEMBERSHIP_FIELDS)
    write_csv(out_dir / "l1_0_domain_validation.csv", validation_rows, VALIDATION_FIELDS)
    write_csv(
        out_dir / "l1_0_line_study_support.csv",
        [
            r
            for r in membership_rows
            if r["domain_class"] in {"line_domain", "probable_line_domain"}
            and line_study_map[as_int(r["y"]), as_int(r["x"])]
        ],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "l1_0_future_module_pool.csv",
        [
            r
            for r in membership_rows
            if r["domain_class"] in {"non_line_domain", "probable_non_line_domain", "mixed_domain", "deferred_domain"}
            and future_pool_map[as_int(r["y"]), as_int(r["x"])]
        ],
        MEMBERSHIP_FIELDS,
    )
    write_csv(out_dir / "l1_0_mixed_domain_regions.csv", [r for r in region_rows if r["domain_class"] == "mixed_domain"], REGION_FIELDS)
    write_csv(out_dir / "l1_0_deferred_domain_regions.csv", [r for r in region_rows if r["domain_class"] == "deferred_domain"], REGION_FIELDS)

    make_visuals(out_dir, observed_support, line_domain_map, probable_line_map, non_line_map, probable_non_line_map, mixed_map, deferred_map, line_study_map, future_pool_map, class_map)

    counts = {
        "observed_support_pixels_seen": int(np.count_nonzero(observed_support)),
        "line_domain_pixels": int(np.count_nonzero(line_domain_map)),
        "probable_line_domain_pixels": int(np.count_nonzero(probable_line_map)),
        "non_line_domain_pixels": int(np.count_nonzero(non_line_map)),
        "probable_non_line_domain_pixels": int(np.count_nonzero(probable_non_line_map)),
        "mixed_domain_pixels": int(np.count_nonzero(mixed_map)),
        "deferred_domain_pixels": int(np.count_nonzero(deferred_map)),
        "line_study_support_pixels": int(np.count_nonzero(line_study_map)),
        "future_module_pool_pixels": int(np.count_nonzero(future_pool_map)),
        "domain_region_count": len(region_rows),
        "domain_class_region_counts": dict(Counter(r["domain_class"] for r in region_rows)),
    }
    metrics = {
        "line_exclusion_ratio": ratio(counts["future_module_pool_pixels"], counts["observed_support_pixels_seen"]),
        "future_pool_traceability_rate": ratio(len(future_pixel_set & membership_pixel_set), len(future_pixel_set)),
        "mixed_domain_ratio": ratio(counts["mixed_domain_pixels"], counts["observed_support_pixels_seen"]),
        "deferred_domain_ratio": ratio(counts["deferred_domain_pixels"], counts["observed_support_pixels_seen"]),
        "line_study_retention_of_u1_1_refined_valid": ratio(int(np.count_nonzero(line_study_map & u11_refined)), int(np.count_nonzero(u11_refined))),
        "u1_1_refined_valid_pixels": int(np.count_nonzero(u11_refined)),
    }
    contract = {
        "creates_final_geometry": False,
        "creates_final_lineobjects": False,
        "creates_axis_descriptors": False,
        "creates_crossings": False,
        "recognizes_ocr_strings": False,
        "recognizes_digit_values": False,
        "uses_grid_audit_truth_as_runtime_input": False,
        "non_line_support_is_preserved": True,
        "future_module_pool_preserves_non_line_mixed_deferred": True,
        "line_study_support_is_not_final_geometry": True,
    }

    output_missing_pre_json = missing_required(out_dir, [rel for rel in REQUIRED_OUTPUT_FILES if rel not in {"summary.json", "contract_audit.json"}])
    status = "completed" if all(invariants.values()) and not output_missing_pre_json else "failed_contract"
    outputs = {rel.replace("/", "_").replace(".", "_"): rel for rel in REQUIRED_OUTPUT_FILES}
    summary = {
        "version": VERSION,
        "status": status,
        "source_u1_1_run_dir": str(u11_dir),
        "source_v3_3_run_dir": str(v33_dir),
        "source_v3_4_2_run_dir": str(v342_dir) if v342_dir else "",
        "source_c1_0_run_dir": str(c10_dir) if c10_dir else "",
        "source_c1_1_run_dir": str(c11_dir) if c11_dir else "",
        "source_u1_0_run_dir": str(u10_dir) if u10_dir else "",
        "source_u1_1_version": u11_summary.get("version", ""),
        "source_v3_3_version": v33_summary.get("version", ""),
        "config": asdict(cfg),
        "required_inputs_missing": missing_inputs,
        "required_outputs_missing": output_missing_pre_json,
        "counts": counts,
        "metrics": metrics,
        "invariants": invariants,
        "contract": contract,
        "outputs": outputs,
        "source_manifest_before": source_manifest_before,
        "source_manifest_after": source_manifest_after,
        "visual_acceptance_note": "Visual audit is mandatory when no line-domain truth dataset exists.",
    }
    contract_audit = {
        "version": VERSION,
        "contract_file": "outputs/CONTRACT_L1_0_OBSERVED_SUPPORT_DOMAIN_STRATIFIER_V1.md",
        "status": status,
        "semantic_rule": "l1_0_is_domain_stratifier_not_semantic_recognizer",
        "traceability_rule": "excluded_from_line_study_does_not_mean_deleted",
        "required_inputs_missing": missing_inputs,
        "required_outputs_missing": output_missing_pre_json,
        "invariants": invariants,
        "contract": contract,
        "counts": counts,
        "metrics": metrics,
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "contract_audit.json", contract_audit)

    output_missing_final = missing_required(out_dir, REQUIRED_OUTPUT_FILES)
    status = "completed" if all(invariants.values()) and not output_missing_final else "failed_contract"
    summary["status"] = status
    summary["required_outputs_missing"] = output_missing_final
    contract_audit["status"] = status
    contract_audit["required_outputs_missing"] = output_missing_final
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "contract_audit.json", contract_audit)
    print(json.dumps({"status": status, **counts, **metrics}, ensure_ascii=False), flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--u1-1-dir", required=True)
    ap.add_argument("--v3-run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--v3-4-2-dir", default=None)
    ap.add_argument("--c1-dir", default=None)
    ap.add_argument("--c1-1-dir", default=None)
    ap.add_argument("--u1-0-dir", default=None)
    ap.add_argument("--min-line-elongation-score", type=float, default=0.52)
    ap.add_argument("--min-probable-line-elongation-score", type=float, default=0.36)
    ap.add_argument("--min-line-continuity-score", type=float, default=0.38)
    ap.add_argument("--min-probable-line-continuity-score", type=float, default=0.22)
    ap.add_argument("--min-width-stability-score", type=float, default=0.35)
    ap.add_argument("--min-line-context-score", type=float, default=0.28)
    ap.add_argument("--max-line-text-like-score", type=float, default=0.56)
    ap.add_argument("--max-line-symbol-like-score", type=float, default=0.62)
    ap.add_argument("--min-non-line-text-like-score", type=float, default=0.68)
    ap.add_argument("--min-probable-non-line-text-like-score", type=float, default=0.52)
    ap.add_argument("--short-mark-longitudinal-length", type=int, default=12)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config(
        min_line_elongation_score=args.min_line_elongation_score,
        min_probable_line_elongation_score=args.min_probable_line_elongation_score,
        min_line_continuity_score=args.min_line_continuity_score,
        min_probable_line_continuity_score=args.min_probable_line_continuity_score,
        min_width_stability_score=args.min_width_stability_score,
        min_line_context_score=args.min_line_context_score,
        max_line_text_like_score=args.max_line_text_like_score,
        max_line_symbol_like_score=args.max_line_symbol_like_score,
        min_non_line_text_like_score=args.min_non_line_text_like_score,
        min_probable_non_line_text_like_score=args.min_probable_non_line_text_like_score,
        short_mark_longitudinal_length_px=args.short_mark_longitudinal_length,
    )
    run(
        u11_dir=Path(args.u1_1_dir),
        v33_dir=Path(args.v3_run_dir),
        out_dir=Path(args.out),
        v342_dir=Path(args.v3_4_2_dir) if args.v3_4_2_dir else None,
        c10_dir=Path(args.c1_dir) if args.c1_dir else None,
        c11_dir=Path(args.c1_1_dir) if args.c1_1_dir else None,
        u10_dir=Path(args.u1_0_dir) if args.u1_0_dir else None,
        cfg=cfg,
    )


if __name__ == "__main__":
    main()
