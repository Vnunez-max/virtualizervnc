#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module U1.1 - Subobject Clean Grid Geometry Purity Gate.

U1.1 refines U1.0 object-level clean-grid gating inside each traceable V3.3
observed geometry object. It separates clean core support from suspicious,
blocking-like, ambiguous, or deferred subsupport without creating geometry,
repairing gaps, moving coordinates, or modifying upstream outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_U1_1_V1_SUBOBJECT_CLEAN_GRID_GEOMETRY_PURITY_GATE"


@dataclass
class Config:
    version: str = VERSION
    max_core_axis_distance_px: float = 3.0
    max_grid_consistent_p95_axis_distance_px: float = 5.0
    max_local_width_for_clean_support_px: float = 9.0
    min_local_density_score: float = 0.35
    min_local_continuity_score: float = 0.40
    max_conflict_score_for_grid_consistent: float = 0.0
    max_conflict_score_for_suspicious: float = 0.15
    min_subobject_pixels: int = 2
    conflict_neighborhood_px: int = 2
    local_window_radius_px: int = 4
    max_bridge_gap_px: int = 1
    allow_zero_conflict_core_promotion_from_u1_0_blocking: bool = True


GATE_STATES = [
    "grid_consistent",
    "suspicious",
    "blocking_like",
    "ambiguous",
    "deferred",
]

STATE_CODE = {
    "grid_consistent": 1,
    "suspicious": 2,
    "blocking_like": 3,
    "ambiguous": 4,
    "deferred": 5,
}

STATE_PRIORITY = {
    "blocking_like": 5,
    "ambiguous": 4,
    "suspicious": 3,
    "deferred": 2,
    "grid_consistent": 1,
}

REGION_FIELDS = [
    "subobject_region_id",
    "source_geometry_object_id",
    "source_u1_0_gate_state",
    "orientation",
    "axis_estimate_px",
    "region_longitudinal_start",
    "region_longitudinal_end",
    "region_pixel_count",
    "core_pixel_count",
    "fringe_pixel_count",
    "gate_state",
    "subobject_score",
    "axis_distance_median_px",
    "axis_distance_p95_px",
    "local_width_estimate_px",
    "local_continuity_score",
    "local_density_score",
    "local_conflict_score",
    "local_blocking_score",
    "local_ambiguity_score",
    "gate_reason",
]

MEMBERSHIP_FIELDS = [
    "subobject_region_id",
    "source_geometry_object_id",
    "x",
    "y",
    "source_layer",
    "source_membership_role",
    "source_u1_0_gate_state",
    "u1_1_gate_state",
    "membership_source",
    "membership_weight",
]

VALIDATION_FIELDS = [
    "subobject_region_id",
    "source_geometry_object_id",
    "u1_1_gate_state",
    "support_subset_of_v3_3_observed",
    "excluded_support_not_counted_as_refined_unified",
    "blocking_not_counted_as_clean_grid_support",
    "ambiguous_not_counted_as_clean_grid_support",
    "inferred_span_not_counted_as_observed_support",
    "does_not_modify_upstream_geometry",
    "does_not_create_geometry",
    "validation_reason",
    "rejection_or_deferral_reason",
]

REQUIRED_V33_FILES = [
    "summary.json",
    "geometry_objects.csv",
    "maps/combined_geometry_support_count_map.npy",
    "maps/residual_after_geometry_mask.npy",
]

OPTIONAL_V33_MEMBERSHIP_FILES = [
    "pixel_geometry_memberships.csv",
    "geometry_memberships.csv",
]

REQUIRED_V342_FILES = [
    "summary.json",
    "residual_evidence_objects.csv",
    "residual_geometry_memberships.csv",
    "residual_layer_audit.json",
    "maps/diagnostic_residual_support_count_map.npy",
    "maps/residual_evidence_class_map.npy",
    "maps/residual_object_id_map.npy",
]

OPTIONAL_V342_FILES = [
    "maps/evidence_strong_residual_geometry_support_count_map.npy",
    "maps/candidate_residual_geometry_support_count_map.npy",
]

REQUIRED_C10_FILES = [
    "summary.json",
    "contract_audit.json",
    "maps/validated_hypothesis_observed_support_map.npy",
    "maps/inferred_span_map.npy",
    "maps/rejected_residual_support_map.npy",
]

REQUIRED_C11_FILES = [
    "summary.json",
    "contract_audit.json",
    "maps/collective_validated_observed_support_map.npy",
    "maps/collective_inferred_span_map.npy",
    "maps/collective_blocking_evidence_map.npy",
]

REQUIRED_U10_FILES = [
    "summary.json",
    "contract_audit.json",
    "u1_0_geometry_gate_objects.csv",
    "u1_0_geometry_gate_memberships.csv",
    "u1_0_geometry_gate_validation.csv",
    "maps/grid_consistent_observed_geometry_map.npy",
    "maps/suspicious_observed_geometry_map.npy",
    "maps/blocking_like_observed_geometry_map.npy",
    "maps/ambiguous_observed_geometry_map.npy",
    "maps/deferred_observed_geometry_map.npy",
    "maps/excluded_from_unified_observed_support_map.npy",
    "maps/u1_0_gate_state_map.npy",
    "maps/unified_valid_observed_support_map.npy",
]

REQUIRED_OUTPUT_FILES = [
    "u1_1_subobject_regions.csv",
    "u1_1_subobject_memberships.csv",
    "u1_1_subobject_validation.csv",
    "u1_1_excluded_subsupport.csv",
    "u1_1_blocking_like_subsupport.csv",
    "u1_1_ambiguous_subsupport.csv",
    "summary.json",
    "contract_audit.json",
    "maps/grid_consistent_subsupport_map.npy",
    "maps/suspicious_subsupport_map.npy",
    "maps/blocking_like_subsupport_map.npy",
    "maps/ambiguous_subsupport_map.npy",
    "maps/deferred_subsupport_map.npy",
    "maps/excluded_subsupport_map.npy",
    "maps/u1_1_subobject_region_id_map.npy",
    "maps/u1_1_subobject_gate_state_map.npy",
    "maps/refined_unified_valid_observed_support_map.npy",
    "visuals/01_u1_0_input_gate_state.png",
    "visuals/02_subobject_grid_consistent_support.png",
    "visuals/03_subobject_excluded_support.png",
    "visuals/04_blocking_and_ambiguous_subsupport.png",
    "visuals/05_refined_unified_valid_observed_support.png",
    "visuals/06_u1_1_gate_summary.png",
]

AMBIGUOUS_CLASSES = {"ambiguous_residual_evidence"}


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
    path.write_text(
        json.dumps(to_jsonable(obj), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


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


def assert_required_inputs(
    v33_dir: Path,
    v342_dir: Path,
    c10_dir: Path,
    c11_dir: Path,
    u10_dir: Path,
) -> Dict[str, List[str]]:
    v33_required = list(REQUIRED_V33_FILES)
    if not any((v33_dir / rel).exists() for rel in OPTIONAL_V33_MEMBERSHIP_FILES):
        if not (u10_dir / "u1_0_geometry_gate_memberships.csv").exists():
            v33_required.append("pixel_geometry_memberships.csv")
    missing = {
        "v3_3": missing_required(v33_dir, v33_required),
        "v3_4_2": missing_required(v342_dir, REQUIRED_V342_FILES),
        "c1_0": missing_required(c10_dir, REQUIRED_C10_FILES),
        "c1_1": missing_required(c11_dir, REQUIRED_C11_FILES),
        "u1_0": missing_required(u10_dir, REQUIRED_U10_FILES),
    }
    absent = [f"{group}:{rel}" for group, rels in missing.items() for rel in rels]
    if absent:
        raise FileNotFoundError("Missing required U1.1 input files: " + ", ".join(absent))
    return missing


def load_map(path: Path, dtype: Any | None = None) -> np.ndarray:
    arr = np.load(path)
    return arr.astype(dtype) if dtype is not None else arr


def optional_map(path: Path, shape: Tuple[int, int], dtype: Any = np.uint16) -> np.ndarray:
    if path.exists():
        return np.load(path).astype(dtype)
    return np.zeros(shape, dtype=dtype)


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except Exception:
        return default


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def ratio(num: int, den: int) -> float:
    return float(num / den) if den else 0.0


def mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=float), q))


def font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def render_bool(
    mask: np.ndarray,
    active: Tuple[int, int, int],
    bg: Tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
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


def object_longitudinal_range(row: Dict[str, str]) -> Tuple[float, float]:
    orientation = row.get("orientation", "")
    if orientation == "vertical":
        a = as_float(row.get("y1"))
        b = as_float(row.get("y2"))
    else:
        a = as_float(row.get("x1"))
        b = as_float(row.get("x2"))
    return min(a, b), max(a, b)


def choose_v33_membership_file(v33_dir: Path) -> Tuple[Optional[Path], str]:
    if (v33_dir / "pixel_geometry_memberships.csv").exists():
        return v33_dir / "pixel_geometry_memberships.csv", "pixel_geometry_memberships.csv"
    if (v33_dir / "geometry_memberships.csv").exists():
        return v33_dir / "geometry_memberships.csv", "geometry_memberships.csv"
    return None, ""


def load_v33_points(
    v33_dir: Path,
    u10_dir: Path,
    geometry_objects: Sequence[Dict[str, str]],
    combined_v3: np.ndarray,
) -> Tuple[
    Dict[str, Set[Tuple[int, int]]],
    Dict[Tuple[str, int, int], str],
    Dict[Tuple[str, int, int], float],
    str,
]:
    points: Dict[str, Set[Tuple[int, int]]] = defaultdict(set)
    role_by_pixel: Dict[Tuple[str, int, int], str] = {}
    weight_by_pixel: Dict[Tuple[str, int, int], float] = {}
    membership_file, source_name = choose_v33_membership_file(v33_dir)

    if membership_file is not None:
        for row in read_csv(membership_file):
            gid = str(row.get("geometry_object_id", row.get("object_id", "")))
            x = as_int(row.get("x"))
            y = as_int(row.get("y"))
            if gid and 0 <= y < combined_v3.shape[0] and 0 <= x < combined_v3.shape[1]:
                points[gid].add((x, y))
                key = (gid, x, y)
                role_by_pixel[key] = row.get("membership_role", row.get("source_membership_role", "line_support")) or "line_support"
                weight_by_pixel[key] = as_float(row.get("membership_weight"), 1.0)
        return points, role_by_pixel, weight_by_pixel, source_name

    u10_memberships = read_csv(u10_dir / "u1_0_geometry_gate_memberships.csv")
    if u10_memberships:
        for row in u10_memberships:
            gid = str(row.get("source_geometry_object_id", ""))
            x = as_int(row.get("x"))
            y = as_int(row.get("y"))
            if gid and 0 <= y < combined_v3.shape[0] and 0 <= x < combined_v3.shape[1]:
                points[gid].add((x, y))
                key = (gid, x, y)
                role_by_pixel[key] = row.get("source_membership_role", "u1_0_preserved_support") or "u1_0_preserved_support"
                weight_by_pixel[key] = as_float(row.get("membership_weight"), 1.0)
        return points, role_by_pixel, weight_by_pixel, "u1_0_geometry_gate_memberships.csv"

    # Last-resort reconstruction is traceable to V3.3 object declarations and
    # the combined observed support map. It is reported in membership_source.
    for row in geometry_objects:
        gid = str(row.get("geometry_object_id", ""))
        if not gid:
            continue
        orientation = row.get("orientation", "")
        axis = int(round(as_float(row.get("axis_center_px"))))
        start, end = object_longitudinal_range(row)
        start_i = int(math.floor(start))
        end_i = int(math.ceil(end))
        if orientation == "vertical":
            x0, x1 = max(0, axis - 3), min(combined_v3.shape[1] - 1, axis + 3)
            y0, y1 = max(0, start_i), min(combined_v3.shape[0] - 1, end_i)
            ys, xs = np.where(combined_v3[y0 : y1 + 1, x0 : x1 + 1] > 0)
            for yy, xx in zip(ys, xs):
                x, y = x0 + int(xx), y0 + int(yy)
                points[gid].add((x, y))
                role_by_pixel[(gid, x, y)] = "reconstructed_support"
                weight_by_pixel[(gid, x, y)] = 1.0
        else:
            y0, y1 = max(0, axis - 3), min(combined_v3.shape[0] - 1, axis + 3)
            x0, x1 = max(0, start_i), min(combined_v3.shape[1] - 1, end_i)
            ys, xs = np.where(combined_v3[y0 : y1 + 1, x0 : x1 + 1] > 0)
            for yy, xx in zip(ys, xs):
                x, y = x0 + int(xx), y0 + int(yy)
                points[gid].add((x, y))
                role_by_pixel[(gid, x, y)] = "reconstructed_support"
                weight_by_pixel[(gid, x, y)] = 1.0
    return points, role_by_pixel, weight_by_pixel, "reconstructed_from_v3_3_maps"


def load_u10_state_by_object(u10_dir: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for row in read_csv(u10_dir / "u1_0_geometry_gate_objects.csv"):
        gid = str(row.get("source_geometry_object_id", ""))
        state = row.get("gate_state", "")
        if gid and state:
            out[gid] = state
    return out


def load_u10_state_by_pixel(u10_dir: Path, shape: Tuple[int, int]) -> Dict[Tuple[str, int, int], str]:
    out: Dict[Tuple[str, int, int], str] = {}
    for row in read_csv(u10_dir / "u1_0_geometry_gate_memberships.csv"):
        gid = str(row.get("source_geometry_object_id", ""))
        x = as_int(row.get("x"))
        y = as_int(row.get("y"))
        state = row.get("gate_state", "")
        if gid and state and 0 <= y < shape[0] and 0 <= x < shape[1]:
            out[(gid, x, y)] = state
    return out


def ambiguous_residual_support(
    v342_objects: Sequence[Dict[str, str]],
    v342_memberships: Sequence[Dict[str, str]],
    shape: Tuple[int, int],
) -> np.ndarray:
    class_by_object = {
        str(row.get("residual_object_id", "")): row.get("residual_evidence_class", "")
        for row in v342_objects
    }
    out = np.zeros(shape, dtype=bool)
    for row in v342_memberships:
        rid = str(row.get("residual_object_id", ""))
        if class_by_object.get(rid) not in AMBIGUOUS_CLASSES:
            continue
        x, y = as_int(row.get("x")), as_int(row.get("y"))
        if 0 <= y < shape[0] and 0 <= x < shape[1]:
            out[y, x] = True
    return out


def axis_distance(orientation: str, axis: float, x: int, y: int) -> float:
    if orientation == "vertical":
        return abs(float(x) - axis)
    return abs(float(y) - axis)


def longitudinal_coord(orientation: str, x: int, y: int) -> int:
    return int(y if orientation == "vertical" else x)


def perpendicular_coord(orientation: str, x: int, y: int) -> int:
    return int(x if orientation == "vertical" else y)


def local_profile(points: Set[Tuple[int, int]], orientation: str) -> Tuple[Dict[int, int], Dict[int, List[int]], Set[int]]:
    by_long: Dict[int, Set[int]] = defaultdict(set)
    occupied_longs: Set[int] = set()
    for x, y in points:
        long_coord = longitudinal_coord(orientation, x, y)
        perp = perpendicular_coord(orientation, x, y)
        by_long[long_coord].add(perp)
        occupied_longs.add(long_coord)
    width_by_long = {k: len(v) for k, v in by_long.items()}
    perps_by_long = {k: sorted(v) for k, v in by_long.items()}
    return width_by_long, perps_by_long, occupied_longs


def local_continuity(occupied_longs: Set[int], coord: int, radius: int) -> float:
    if radius <= 0:
        return 1.0 if coord in occupied_longs else 0.0
    total = 2 * radius + 1
    hit = sum(1 for c in range(coord - radius, coord + radius + 1) if c in occupied_longs)
    return ratio(hit, total)


def local_density_score(
    points: Set[Tuple[int, int]],
    orientation: str,
    x: int,
    y: int,
    radius: int,
) -> float:
    if radius <= 0:
        return 1.0 if (x, y) in points else 0.0
    long0 = longitudinal_coord(orientation, x, y)
    perp0 = perpendicular_coord(orientation, x, y)
    count = 0
    total = (2 * radius + 1) * (2 * radius + 1)
    for px, py in points:
        if abs(longitudinal_coord(orientation, px, py) - long0) <= radius and abs(perpendicular_coord(orientation, px, py) - perp0) <= radius:
            count += 1
    return clamp01(count / max(total, 1))


def point_seed_state(
    *,
    x: int,
    y: int,
    gid: str,
    orientation: str,
    axis: float,
    points: Set[Tuple[int, int]],
    width_by_long: Dict[int, int],
    occupied_longs: Set[int],
    source_u10_state: str,
    diagnostic_direct: np.ndarray,
    diagnostic_near: np.ndarray,
    ambiguous_direct: np.ndarray,
    ambiguous_near: np.ndarray,
    blocking_direct: np.ndarray,
    blocking_near: np.ndarray,
    inferred: np.ndarray,
    cfg: Config,
) -> Tuple[str, Dict[str, float], str]:
    del gid
    long_coord = longitudinal_coord(orientation, x, y)
    dist = axis_distance(orientation, axis, x, y)
    width = float(width_by_long.get(long_coord, 1))
    continuity = local_continuity(occupied_longs, long_coord, cfg.local_window_radius_px)
    density = local_density_score(points, orientation, x, y, max(1, cfg.local_window_radius_px // 2))
    core = dist <= cfg.max_core_axis_distance_px
    near_conflict = bool(diagnostic_near[y, x] or blocking_near[y, x])
    direct_conflict = bool(diagnostic_direct[y, x] or blocking_direct[y, x])
    near_ambiguity = bool(ambiguous_near[y, x])
    direct_ambiguity = bool(ambiguous_direct[y, x])
    width_too_high = width > cfg.max_local_width_for_clean_support_px
    axis_too_far = dist > cfg.max_grid_consistent_p95_axis_distance_px
    weak_density = density < cfg.min_local_density_score
    weak_continuity = continuity < cfg.min_local_continuity_score
    reasons: List[str] = []

    if inferred[y, x]:
        reasons.append("overlaps_inferred_span_audit_context")
        state = "deferred"
    elif direct_conflict:
        reasons.append("direct_diagnostic_or_blocking_conflict")
        state = "blocking_like"
    elif direct_ambiguity:
        reasons.append("direct_ambiguous_residual_conflict")
        state = "ambiguous"
    elif near_conflict and (not core or width_too_high or source_u10_state != "grid_consistent"):
        reasons.append("near_conflict_on_fringe_or_nonclean_source")
        state = "blocking_like"
    elif near_ambiguity and (not core or width_too_high or source_u10_state != "grid_consistent"):
        reasons.append("near_ambiguity_on_fringe_or_nonclean_source")
        state = "ambiguous"
    elif axis_too_far and width_too_high:
        reasons.append("far_from_axis_inside_wide_support")
        state = "blocking_like" if source_u10_state in {"blocking_like", "suspicious"} else "suspicious"
    elif axis_too_far:
        reasons.append("far_from_source_axis")
        state = "suspicious"
    elif width_too_high and not core:
        reasons.append("fringe_inside_locally_wide_support")
        state = "suspicious"
    elif weak_density and weak_continuity:
        reasons.append("low_local_density_and_continuity")
        state = "deferred"
    elif source_u10_state == "blocking_like" and not cfg.allow_zero_conflict_core_promotion_from_u1_0_blocking:
        reasons.append("source_u1_0_blocking_like")
        state = "blocking_like"
    elif source_u10_state == "blocking_like" and not (core and not near_conflict and not near_ambiguity and not width_too_high):
        reasons.append("source_u1_0_blocking_like_without_clean_core_evidence")
        state = "blocking_like"
    elif source_u10_state == "ambiguous" and not (core and not near_conflict and not near_ambiguity and not width_too_high):
        reasons.append("source_u1_0_ambiguous_without_clean_core_evidence")
        state = "ambiguous"
    elif source_u10_state == "deferred" and not (core and not near_conflict and not near_ambiguity and not width_too_high):
        reasons.append("source_u1_0_deferred_without_clean_core_evidence")
        state = "deferred"
    elif source_u10_state == "suspicious" and not core and (weak_density or weak_continuity):
        reasons.append("source_u1_0_suspicious_noncore_weak_support")
        state = "suspicious"
    else:
        reasons.append("traceable_core_or_profile_consistent_support")
        state = "grid_consistent"

    features = {
        "axis_distance_px": dist,
        "local_width_px": width,
        "local_continuity_score": continuity,
        "local_density_score": density,
        "local_conflict": 1.0 if (near_conflict or direct_conflict) else 0.0,
        "local_blocking": 1.0 if (diagnostic_near[y, x] or blocking_near[y, x] or direct_conflict) else 0.0,
        "local_ambiguity": 1.0 if (near_ambiguity or direct_ambiguity) else 0.0,
        "is_core": 1.0 if core else 0.0,
    }
    return state, features, ";".join(reasons)


def conservative_state(states: Sequence[str]) -> str:
    if not states:
        return "deferred"
    return max(states, key=lambda s: STATE_PRIORITY.get(s, 0))


def connected_components(points: Set[Tuple[int, int]], max_bridge_gap: int = 1) -> List[Set[Tuple[int, int]]]:
    if not points:
        return []
    remaining = set(points)
    comps: List[Set[Tuple[int, int]]] = []
    offsets = [
        (dx, dy)
        for dy in range(-max_bridge_gap, max_bridge_gap + 1)
        for dx in range(-max_bridge_gap, max_bridge_gap + 1)
        if not (dx == 0 and dy == 0)
    ]
    while remaining:
        start = remaining.pop()
        comp = {start}
        q: deque[Tuple[int, int]] = deque([start])
        while q:
            x, y = q.popleft()
            for dx, dy in offsets:
                nb = (x + dx, y + dy)
                if nb in remaining:
                    remaining.remove(nb)
                    comp.add(nb)
                    q.append(nb)
        comps.append(comp)
    return comps


def score_region(
    state_hint: str,
    source_u10_state: str,
    axis_distances: Sequence[float],
    widths: Sequence[float],
    continuities: Sequence[float],
    densities: Sequence[float],
    blocking_flags: Sequence[float],
    ambiguity_flags: Sequence[float],
    cfg: Config,
) -> Tuple[str, float, str]:
    p95_axis = percentile(axis_distances, 95)
    med_axis = percentile(axis_distances, 50)
    width_est = percentile(widths, 95)
    continuity = mean(continuities)
    density = mean(densities)
    blocking_score = mean(blocking_flags)
    ambiguity_score = mean(ambiguity_flags)
    conflict_score = max(blocking_score, ambiguity_score)

    axis_score = clamp01(1.0 - p95_axis / max(cfg.max_grid_consistent_p95_axis_distance_px, 0.001))
    width_score = clamp01(1.0 - max(0.0, width_est - cfg.max_core_axis_distance_px) / max(cfg.max_local_width_for_clean_support_px, 0.001))
    u10_bonus = {
        "grid_consistent": 1.0,
        "suspicious": 0.78,
        "blocking_like": 0.52,
        "ambiguous": 0.45,
        "deferred": 0.42,
    }.get(source_u10_state, 0.45)
    score = clamp01(
        0.28 * axis_score
        + 0.22 * width_score
        + 0.20 * continuity
        + 0.18 * density
        + 0.12 * u10_bonus
        - 0.35 * conflict_score
    )

    reasons: List[str] = []
    if blocking_score > cfg.max_conflict_score_for_grid_consistent:
        reasons.append("region_has_blocking_or_diagnostic_conflict")
        return "blocking_like", score, ";".join(reasons)
    if ambiguity_score > cfg.max_conflict_score_for_grid_consistent:
        reasons.append("region_has_ambiguous_residual_conflict")
        return "ambiguous", score, ";".join(reasons)
    if p95_axis > cfg.max_grid_consistent_p95_axis_distance_px and width_est > cfg.max_local_width_for_clean_support_px:
        reasons.append("region_far_from_axis_and_wide")
        return "blocking_like" if source_u10_state in {"blocking_like", "suspicious"} else "suspicious", score, ";".join(reasons)
    if p95_axis > cfg.max_grid_consistent_p95_axis_distance_px:
        reasons.append("region_far_from_axis")
        return "suspicious", score, ";".join(reasons)
    if width_est > cfg.max_local_width_for_clean_support_px and p95_axis > cfg.max_core_axis_distance_px + 2.0:
        reasons.append("region_locally_too_wide_and_not_axis_core")
        return "suspicious", score, ";".join(reasons)
    if density < cfg.min_local_density_score and continuity < cfg.min_local_continuity_score:
        reasons.append("region_low_density_and_low_continuity")
        return "deferred", score, ";".join(reasons)
    if source_u10_state == "blocking_like" and score < 0.55:
        reasons.append("source_u1_0_blocking_like_low_subobject_score")
        return "blocking_like", score, ";".join(reasons)
    if source_u10_state == "ambiguous" and score < 0.58:
        reasons.append("source_u1_0_ambiguous_low_subobject_score")
        return "ambiguous", score, ";".join(reasons)
    if source_u10_state == "deferred" and score < 0.58:
        reasons.append("source_u1_0_deferred_low_subobject_score")
        return "deferred", score, ";".join(reasons)
    if state_hint in {"blocking_like", "ambiguous"} and score < 0.65:
        reasons.append(f"conservative_seed_state_{state_hint}")
        return state_hint, score, ";".join(reasons)
    if state_hint == "suspicious" and score < 0.62:
        reasons.append("suspicious_seed_low_score")
        return "suspicious", score, ";".join(reasons)

    reasons.append("region_traceable_zero_conflict_profile_consistent")
    return "grid_consistent", score, ";".join(reasons)


def segment_source_object(
    source: Dict[str, str],
    points: Set[Tuple[int, int]],
    source_u10_state: str,
    u10_state_by_pixel: Dict[Tuple[str, int, int], str],
    role_by_pixel: Dict[Tuple[str, int, int], str],
    weight_by_pixel: Dict[Tuple[str, int, int], float],
    membership_source: str,
    diagnostic_direct: np.ndarray,
    diagnostic_near: np.ndarray,
    ambiguous_direct: np.ndarray,
    ambiguous_near: np.ndarray,
    blocking_direct: np.ndarray,
    blocking_near: np.ndarray,
    inferred: np.ndarray,
    cfg: Config,
) -> List[Dict[str, Any]]:
    gid = str(source.get("geometry_object_id", ""))
    orientation = source.get("orientation", "")
    axis = as_float(source.get("axis_center_px"))
    if orientation not in {"horizontal", "vertical"}:
        orientation = "horizontal"
    width_by_long, _perps_by_long, occupied_longs = local_profile(points, orientation)

    pixels: Dict[Tuple[int, int], Dict[str, Any]] = {}
    grouped_points: Dict[str, Set[Tuple[int, int]]] = defaultdict(set)
    for x, y in points:
        pixel_u10_state = u10_state_by_pixel.get((gid, x, y), source_u10_state)
        state, features, reason = point_seed_state(
            x=x,
            y=y,
            gid=gid,
            orientation=orientation,
            axis=axis,
            points=points,
            width_by_long=width_by_long,
            occupied_longs=occupied_longs,
            source_u10_state=pixel_u10_state,
            diagnostic_direct=diagnostic_direct,
            diagnostic_near=diagnostic_near,
            ambiguous_direct=ambiguous_direct,
            ambiguous_near=ambiguous_near,
            blocking_direct=blocking_direct,
            blocking_near=blocking_near,
            inferred=inferred,
            cfg=cfg,
        )
        pixels[(x, y)] = {
            "seed_state": state,
            "features": features,
            "seed_reason": reason,
            "source_u10_state": pixel_u10_state,
            "role": role_by_pixel.get((gid, x, y), "line_support"),
            "weight": weight_by_pixel.get((gid, x, y), 1.0),
            "membership_source": membership_source,
        }
        grouped_points[state].add((x, y))

    segments: List[Dict[str, Any]] = []
    for state_hint in GATE_STATES:
        for comp in connected_components(grouped_points.get(state_hint, set()), cfg.max_bridge_gap_px):
            if len(comp) < cfg.min_subobject_pixels and state_hint == "grid_consistent":
                # A tiny clean island is still traceable, but not enough to
                # serve as clean-grid support.
                state_hint_for_score = "deferred"
            else:
                state_hint_for_score = state_hint

            axis_distances = [pixels[p]["features"]["axis_distance_px"] for p in comp]
            widths = [pixels[p]["features"]["local_width_px"] for p in comp]
            continuities = [pixels[p]["features"]["local_continuity_score"] for p in comp]
            densities = [pixels[p]["features"]["local_density_score"] for p in comp]
            blocking_flags = [pixels[p]["features"]["local_blocking"] for p in comp]
            ambiguity_flags = [pixels[p]["features"]["local_ambiguity"] for p in comp]
            pixel_source_states = [pixels[p]["source_u10_state"] for p in comp]
            region_source_state = conservative_state(pixel_source_states) if pixel_source_states else source_u10_state
            final_state, score, score_reason = score_region(
                state_hint_for_score,
                region_source_state,
                axis_distances,
                widths,
                continuities,
                densities,
                blocking_flags,
                ambiguity_flags,
                cfg,
            )
            longs = [longitudinal_coord(orientation, x, y) for x, y in comp]
            core_count = sum(1 for d in axis_distances if d <= cfg.max_core_axis_distance_px)
            fringe_count = len(comp) - core_count
            seed_reason_counts = Counter(pixels[p]["seed_reason"] for p in comp)
            common_seed_reasons = [reason for reason, _count in seed_reason_counts.most_common(3)]
            gate_reason = score_reason
            if common_seed_reasons:
                gate_reason = gate_reason + "|" + "|".join(common_seed_reasons)
            segments.append(
                {
                    "source_geometry_object_id": gid,
                    "source_u1_0_gate_state": region_source_state,
                    "orientation": orientation,
                    "axis_estimate_px": axis,
                    "region_longitudinal_start": min(longs) if longs else 0,
                    "region_longitudinal_end": max(longs) if longs else 0,
                    "region_pixel_count": len(comp),
                    "core_pixel_count": core_count,
                    "fringe_pixel_count": fringe_count,
                    "gate_state": final_state,
                    "subobject_score": score,
                    "axis_distance_median_px": percentile(axis_distances, 50),
                    "axis_distance_p95_px": percentile(axis_distances, 95),
                    "local_width_estimate_px": percentile(widths, 95),
                    "local_continuity_score": mean(continuities),
                    "local_density_score": mean(densities),
                    "local_conflict_score": max(mean(blocking_flags), mean(ambiguity_flags)),
                    "local_blocking_score": mean(blocking_flags),
                    "local_ambiguity_score": mean(ambiguity_flags),
                    "gate_reason": gate_reason,
                    "_pixels": comp,
                    "_pixel_meta": pixels,
                }
            )
    return segments


def make_visuals(
    out_dir: Path,
    u10_state_map: np.ndarray,
    grid: np.ndarray,
    suspicious: np.ndarray,
    blocking: np.ndarray,
    ambiguous: np.ndarray,
    deferred: np.ndarray,
    excluded: np.ndarray,
    refined_unified: np.ndarray,
    inferred: np.ndarray,
) -> None:
    vdir = out_dir / "visuals"
    ensure_dir(vdir)

    u10_arr = np.full((u10_state_map.shape[0], u10_state_map.shape[1], 3), 255, dtype=np.uint8)
    u10_arr[u10_state_map == STATE_CODE["grid_consistent"]] = (0, 175, 85)
    u10_arr[u10_state_map == STATE_CODE["suspicious"]] = (245, 210, 0)
    u10_arr[u10_state_map == STATE_CODE["blocking_like"]] = (220, 0, 0)
    u10_arr[u10_state_map == STATE_CODE["ambiguous"]] = (150, 70, 210)
    u10_arr[u10_state_map == STATE_CODE["deferred"]] = (160, 160, 160)
    Image.fromarray(u10_arr, "RGB").save(vdir / "01_u1_0_input_gate_state.png")

    render_bool(grid, (0, 175, 85)).save(vdir / "02_subobject_grid_consistent_support.png")

    excluded_arr = np.full((grid.shape[0], grid.shape[1], 3), 255, dtype=np.uint8)
    excluded_arr[suspicious] = (245, 210, 0)
    excluded_arr[blocking] = (220, 0, 0)
    excluded_arr[ambiguous] = (150, 70, 210)
    excluded_arr[deferred] = (160, 160, 160)
    excluded_arr[excluded & ~(suspicious | blocking | ambiguous | deferred)] = (0, 0, 0)
    Image.fromarray(excluded_arr, "RGB").save(vdir / "03_subobject_excluded_support.png")

    block_amb = np.full((grid.shape[0], grid.shape[1], 3), 255, dtype=np.uint8)
    block_amb[blocking] = (220, 0, 0)
    block_amb[ambiguous] = (150, 70, 210)
    Image.fromarray(block_amb, "RGB").save(vdir / "04_blocking_and_ambiguous_subsupport.png")

    refined_arr = np.full((grid.shape[0], grid.shape[1], 3), 255, dtype=np.uint8)
    refined_arr[refined_unified] = (40, 120, 255)
    refined_arr[inferred] = (255, 160, 0)
    Image.fromarray(refined_arr, "RGB").save(vdir / "05_refined_unified_valid_observed_support.png")

    panels = [
        titled(Image.fromarray(u10_arr, "RGB"), "U1.0 input gate state"),
        titled(render_bool(grid, (0, 175, 85)), "U1.1 grid-consistent subsupport"),
        titled(Image.fromarray(excluded_arr, "RGB"), "excluded: yellow/red/purple/gray"),
        titled(Image.fromarray(block_amb, "RGB"), "blocking red / ambiguous purple"),
        titled(Image.fromarray(refined_arr, "RGB"), "refined unified blue / inferred orange"),
    ]
    tile_w = max(p.width for p in panels)
    tile_h = max(p.height for p in panels)
    sheet = Image.new("RGB", (tile_w * 2, tile_h * 3 + 36), "white")
    d = ImageDraw.Draw(sheet)
    d.text((8, 10), "U1.1 Subobject Clean Grid Geometry Purity Gate", fill="black", font=font(16))
    for idx, panel in enumerate(panels):
        x = (idx % 2) * tile_w
        y = 36 + (idx // 2) * tile_h
        sheet.paste(panel, (x, y))
    sheet.save(vdir / "06_u1_1_gate_summary.png")


def audit_with_grid_truth(sample_dir: Optional[Path], refined_unified: np.ndarray, excluded: np.ndarray) -> Dict[str, Any]:
    if sample_dir is None:
        return {}
    masks = sample_dir / "masks"
    required = [
        "observed_valid_geometry.npy",
        "blocking_geometry_evidence.npy",
        "ambiguous_geometry_evidence.npy",
        "missing_not_recoverable_geometry.npy",
    ]
    if any(not (masks / rel).exists() for rel in required):
        return {"grid_audit_truth_available": False}

    observed = load_map(masks / "observed_valid_geometry.npy", bool).astype(bool)
    blocking = load_map(masks / "blocking_geometry_evidence.npy", bool).astype(bool)
    ambiguous = load_map(masks / "ambiguous_geometry_evidence.npy", bool).astype(bool)
    not_recoverable = load_map(masks / "missing_not_recoverable_geometry.npy", bool).astype(bool)
    clean = load_map(masks / "clean_grid_mask.npy", bool).astype(bool) if (masks / "clean_grid_mask.npy").exists() else observed

    return {
        "grid_audit_truth_available": True,
        "observed_geometry_precision_after_u1_1": ratio(int(np.count_nonzero(refined_unified & observed)), int(np.count_nonzero(refined_unified))),
        "observed_geometry_recall_after_u1_1": ratio(int(np.count_nonzero(refined_unified & observed)), int(np.count_nonzero(observed))),
        "blocking_false_observed_rate_after_u1_1": ratio(int(np.count_nonzero(refined_unified & blocking)), int(np.count_nonzero(blocking))),
        "ambiguous_false_observed_rate_after_u1_1": ratio(int(np.count_nonzero(refined_unified & ambiguous)), int(np.count_nonzero(ambiguous))),
        "not_recoverable_false_observed_rate_after_u1_1": ratio(int(np.count_nonzero(refined_unified & not_recoverable)), int(np.count_nonzero(not_recoverable))),
        "clean_grid_observed_coverage_after_u1_1": ratio(int(np.count_nonzero(refined_unified & clean)), int(np.count_nonzero(clean))),
        "wrong_exclusion_rate_after_u1_1": ratio(int(np.count_nonzero(excluded & observed)), int(np.count_nonzero(observed))),
        "wrong_inclusion_rate_after_u1_1": ratio(int(np.count_nonzero(refined_unified & (blocking | ambiguous | not_recoverable))), int(np.count_nonzero(refined_unified))),
    }


def run(
    v33_dir: Path,
    v342_dir: Path,
    c10_dir: Path,
    c11_dir: Path,
    u10_dir: Path,
    out_dir: Path,
    image_path: Optional[Path] = None,
    grid_audit_sample_dir: Optional[Path] = None,
    cfg: Optional[Config] = None,
) -> Dict[str, Any]:
    del image_path
    cfg = cfg or Config()
    v33_dir = Path(v33_dir)
    v342_dir = Path(v342_dir)
    c10_dir = Path(c10_dir)
    c11_dir = Path(c11_dir)
    u10_dir = Path(u10_dir)
    out_dir = Path(out_dir)

    missing_inputs = assert_required_inputs(v33_dir, v342_dir, c10_dir, c11_dir, u10_dir)
    v33_manifest_files = REQUIRED_V33_FILES + [p for p in OPTIONAL_V33_MEMBERSHIP_FILES if (v33_dir / p).exists()]
    v342_manifest_files = REQUIRED_V342_FILES + [p for p in OPTIONAL_V342_FILES if (v342_dir / p).exists()]
    source_manifest_before = {
        "v3_3": file_manifest(v33_dir, v33_manifest_files),
        "v3_4_2": file_manifest(v342_dir, v342_manifest_files),
        "c1_0": file_manifest(c10_dir, REQUIRED_C10_FILES),
        "c1_1": file_manifest(c11_dir, REQUIRED_C11_FILES),
        "u1_0": file_manifest(u10_dir, REQUIRED_U10_FILES),
    }

    ensure_dir(out_dir)
    ensure_dir(out_dir / "maps")
    ensure_dir(out_dir / "visuals")

    v33_summary = read_json(v33_dir / "summary.json")
    v342_summary = read_json(v342_dir / "summary.json")
    c10_summary = read_json(c10_dir / "summary.json")
    c11_summary = read_json(c11_dir / "summary.json")
    u10_summary = read_json(u10_dir / "summary.json")
    geometry_objects = read_csv(v33_dir / "geometry_objects.csv")
    v342_objects = read_csv(v342_dir / "residual_evidence_objects.csv")
    v342_memberships = read_csv(v342_dir / "residual_geometry_memberships.csv")

    combined_v3 = load_map(v33_dir / "maps" / "combined_geometry_support_count_map.npy")
    shape = combined_v3.shape
    v3_observed = combined_v3 > 0

    strong_residual = optional_map(v342_dir / "maps" / "evidence_strong_residual_geometry_support_count_map.npy", shape, np.uint16) > 0
    diagnostic = load_map(v342_dir / "maps" / "diagnostic_residual_support_count_map.npy", np.uint16) > 0
    ambiguous_residual = ambiguous_residual_support(v342_objects, v342_memberships, shape)
    c10_valid = load_map(c10_dir / "maps" / "validated_hypothesis_observed_support_map.npy", np.uint16) > 0
    c10_inferred = load_map(c10_dir / "maps" / "inferred_span_map.npy", np.uint16) > 0
    c10_rejected = load_map(c10_dir / "maps" / "rejected_residual_support_map.npy", np.uint16) > 0
    c11_valid = load_map(c11_dir / "maps" / "collective_validated_observed_support_map.npy", np.uint16) > 0
    c11_inferred = load_map(c11_dir / "maps" / "collective_inferred_span_map.npy", np.uint16) > 0
    c11_blocking = load_map(c11_dir / "maps" / "collective_blocking_evidence_map.npy", np.uint16) > 0
    inferred = c10_inferred | c11_inferred

    u10_state_map = load_map(u10_dir / "maps" / "u1_0_gate_state_map.npy", np.uint8)

    diagnostic_near = dilate(diagnostic, cfg.conflict_neighborhood_px)
    ambiguous_near = dilate(ambiguous_residual, cfg.conflict_neighborhood_px)
    blocking_direct = c10_rejected | c11_blocking
    blocking_near = dilate(blocking_direct, cfg.conflict_neighborhood_px)

    points_by_object, role_by_pixel, weight_by_pixel, membership_source = load_v33_points(
        v33_dir,
        u10_dir,
        geometry_objects,
        combined_v3,
    )
    u10_state_by_object = load_u10_state_by_object(u10_dir)
    u10_state_by_pixel = load_u10_state_by_pixel(u10_dir, shape)

    raw_segments: List[Dict[str, Any]] = []
    for source in geometry_objects:
        gid = str(source.get("geometry_object_id", ""))
        points = points_by_object.get(gid, set())
        if not points:
            continue
        source_u10_state = u10_state_by_object.get(gid, "deferred")
        raw_segments.extend(
            segment_source_object(
                source=source,
                points=points,
                source_u10_state=source_u10_state,
                u10_state_by_pixel=u10_state_by_pixel,
                role_by_pixel=role_by_pixel,
                weight_by_pixel=weight_by_pixel,
                membership_source=membership_source,
                diagnostic_direct=diagnostic,
                diagnostic_near=diagnostic_near,
                ambiguous_direct=ambiguous_residual,
                ambiguous_near=ambiguous_near,
                blocking_direct=blocking_direct,
                blocking_near=blocking_near,
                inferred=inferred,
                cfg=cfg,
            )
        )

    region_rows: List[Dict[str, Any]] = []
    membership_rows: List[Dict[str, Any]] = []
    validation_rows: List[Dict[str, Any]] = []
    excluded_rows: List[Dict[str, Any]] = []
    blocking_rows: List[Dict[str, Any]] = []
    ambiguous_rows: List[Dict[str, Any]] = []

    state_map = np.zeros(shape, dtype=np.uint8)
    region_id_map = np.zeros(shape, dtype=np.int32)

    for region_id, segment in enumerate(raw_segments, start=1):
        pixels = segment.pop("_pixels")
        pixel_meta = segment.pop("_pixel_meta")
        row = {
            "subobject_region_id": region_id,
            **segment,
        }
        region_rows.append(row)
        state = row["gate_state"]
        if state != "grid_consistent":
            excluded_rows.append(row)
        if state == "blocking_like":
            blocking_rows.append(row)
        if state == "ambiguous":
            ambiguous_rows.append(row)

        for x, y in sorted(pixels, key=lambda p: (p[1], p[0])):
            meta = pixel_meta[(x, y)]
            membership_rows.append(
                {
                    "subobject_region_id": region_id,
                    "source_geometry_object_id": row["source_geometry_object_id"],
                    "x": x,
                    "y": y,
                    "source_layer": "v3_3_observed_geometry",
                    "source_membership_role": meta["role"],
                    "source_u1_0_gate_state": meta["source_u10_state"],
                    "u1_1_gate_state": state,
                    "membership_source": meta["membership_source"],
                    "membership_weight": meta["weight"],
                }
            )
            old_code = int(state_map[y, x])
            old_state = next((name for name, code in STATE_CODE.items() if code == old_code), "")
            if not old_state or STATE_PRIORITY[state] > STATE_PRIORITY[old_state]:
                state_map[y, x] = STATE_CODE[state]
                region_id_map[y, x] = region_id

        validation_rows.append(
            {
                "subobject_region_id": region_id,
                "source_geometry_object_id": row["source_geometry_object_id"],
                "u1_1_gate_state": state,
                "support_subset_of_v3_3_observed": True,
                "excluded_support_not_counted_as_refined_unified": state != "grid_consistent",
                "blocking_not_counted_as_clean_grid_support": True,
                "ambiguous_not_counted_as_clean_grid_support": True,
                "inferred_span_not_counted_as_observed_support": True,
                "does_not_modify_upstream_geometry": True,
                "does_not_create_geometry": True,
                "validation_reason": "passed_subobject_gate_as_grid_consistent" if state == "grid_consistent" else "",
                "rejection_or_deferral_reason": "" if state == "grid_consistent" else row["gate_reason"],
            }
        )

    grid_map = state_map == STATE_CODE["grid_consistent"]
    suspicious_map = state_map == STATE_CODE["suspicious"]
    blocking_map = state_map == STATE_CODE["blocking_like"]
    ambiguous_map = state_map == STATE_CODE["ambiguous"]
    deferred_map = state_map == STATE_CODE["deferred"]
    excluded_map = suspicious_map | blocking_map | ambiguous_map | deferred_map

    unsafe = excluded_map | diagnostic | ambiguous_residual | inferred
    refined_unified = (grid_map | strong_residual | c10_valid | c11_valid) & ~unsafe

    source_manifest_after = {
        "v3_3": file_manifest(v33_dir, v33_manifest_files),
        "v3_4_2": file_manifest(v342_dir, v342_manifest_files),
        "c1_0": file_manifest(c10_dir, REQUIRED_C10_FILES),
        "c1_1": file_manifest(c11_dir, REQUIRED_C11_FILES),
        "u1_0": file_manifest(u10_dir, REQUIRED_U10_FILES),
    }

    state_maps = [grid_map, suspicious_map, blocking_map, ambiguous_map, deferred_map]
    overlap_count = np.zeros(shape, dtype=np.uint8)
    for m in state_maps:
        overlap_count += m.astype(np.uint8)

    membership_pixel_count = len({(as_int(r["x"]), as_int(r["y"])) for r in membership_rows})
    state_pixel_count = int(np.count_nonzero(overlap_count))
    region_pixels_traceable = bool(
        all(
            0 <= as_int(r["y"]) < shape[0]
            and 0 <= as_int(r["x"]) < shape[1]
            and v3_observed[as_int(r["y"]), as_int(r["x"])]
            for r in membership_rows
        )
    )

    invariants = {
        "grid_consistent_subsupport_subset_of_v3_3_observed_support": bool(np.all(~grid_map | v3_observed)),
        "suspicious_subsupport_subset_of_v3_3_observed_support": bool(np.all(~suspicious_map | v3_observed)),
        "blocking_like_subsupport_subset_of_v3_3_observed_support": bool(np.all(~blocking_map | v3_observed)),
        "ambiguous_subsupport_subset_of_v3_3_observed_support": bool(np.all(~ambiguous_map | v3_observed)),
        "deferred_subsupport_subset_of_v3_3_observed_support": bool(np.all(~deferred_map | v3_observed)),
        "all_u1_1_gate_state_maps_are_mutually_exclusive": bool(np.all(overlap_count <= 1)),
        "refined_unified_valid_observed_support_excludes_suspicious_blocking_ambiguous_deferred": not bool(np.any(refined_unified & excluded_map)),
        "refined_unified_valid_observed_support_excludes_inferred_spans": not bool(np.any(refined_unified & inferred)),
        "refined_unified_valid_observed_support_excludes_diagnostic_residual": not bool(np.any(refined_unified & diagnostic)),
        "refined_unified_valid_observed_support_excludes_ambiguous_residual": not bool(np.any(refined_unified & ambiguous_residual)),
        "no_synthetic_observed_support": bool(np.all(~refined_unified | (v3_observed | strong_residual | c10_valid | c11_valid))),
        "excluded_support_remains_traceable": bool(region_pixels_traceable and membership_pixel_count == state_pixel_count),
        "v3_3_outputs_unchanged": source_manifest_before["v3_3"] == source_manifest_after["v3_3"],
        "v3_4_2_outputs_unchanged": source_manifest_before["v3_4_2"] == source_manifest_after["v3_4_2"],
        "c1_0_outputs_unchanged": source_manifest_before["c1_0"] == source_manifest_after["c1_0"],
        "c1_1_outputs_unchanged": source_manifest_before["c1_1"] == source_manifest_after["c1_1"],
        "u1_0_outputs_unchanged": source_manifest_before["u1_0"] == source_manifest_after["u1_0"],
    }

    scores = [as_float(r["subobject_score"]) for r in region_rows]
    axis_p95s = [as_float(r["axis_distance_p95_px"]) for r in region_rows]
    widths = [as_float(r["local_width_estimate_px"]) for r in region_rows]
    conflicts = [as_float(r["local_conflict_score"]) for r in region_rows]

    counts = {
        "source_v3_3_observed_pixels": int(np.count_nonzero(v3_observed)),
        "u1_1_classified_observed_pixels": int(np.count_nonzero(overlap_count)),
        "grid_consistent_subsupport_pixels": int(np.count_nonzero(grid_map)),
        "suspicious_subsupport_pixels": int(np.count_nonzero(suspicious_map)),
        "blocking_like_subsupport_pixels": int(np.count_nonzero(blocking_map)),
        "ambiguous_subsupport_pixels": int(np.count_nonzero(ambiguous_map)),
        "deferred_subsupport_pixels": int(np.count_nonzero(deferred_map)),
        "excluded_subsupport_pixels": int(np.count_nonzero(excluded_map)),
        "refined_unified_valid_observed_support_pixels": int(np.count_nonzero(refined_unified)),
        "subobject_region_count": len(region_rows),
        "subobject_region_gate_state_counts": dict(Counter(r["gate_state"] for r in region_rows)),
        "diagnostic_pixels_used_as_clean_grid_support": int(np.count_nonzero(refined_unified & diagnostic)),
        "ambiguous_pixels_used_as_validated_support": int(np.count_nonzero(refined_unified & ambiguous_residual)),
        "inferred_span_pixels_used_as_observed_support": int(np.count_nonzero(refined_unified & inferred)),
    }
    metrics = {
        "classified_v3_3_observed_ratio": ratio(counts["u1_1_classified_observed_pixels"], counts["source_v3_3_observed_pixels"]),
        "grid_consistent_subsupport_ratio": ratio(counts["grid_consistent_subsupport_pixels"], counts["source_v3_3_observed_pixels"]),
        "excluded_subsupport_ratio": ratio(counts["excluded_subsupport_pixels"], counts["source_v3_3_observed_pixels"]),
        "mean_subobject_score": mean(scores),
        "mean_axis_distance_p95_px": mean(axis_p95s),
        "mean_local_width_estimate_px": mean(widths),
        "mean_local_conflict_score": mean(conflicts),
    }
    grid_audit_metrics = audit_with_grid_truth(grid_audit_sample_dir, refined_unified, excluded_map)
    if grid_audit_metrics:
        metrics["grid_audit_v1"] = grid_audit_metrics

    contract = {
        "creates_final_geometry": False,
        "creates_line_objects": False,
        "creates_axis_descriptors": False,
        "creates_crossings": False,
        "modifies_v3_3_outputs": False,
        "modifies_v3_4_2_outputs": False,
        "modifies_c1_0_outputs": False,
        "modifies_c1_1_outputs": False,
        "modifies_u1_0_outputs": False,
        "uses_grid_audit_truth_as_runtime_input": False,
        "separates_observed_support_from_inferred_span": True,
        "excluded_support_remains_traceable": True,
    }

    np.save(out_dir / "maps" / "grid_consistent_subsupport_map.npy", grid_map.astype(np.uint16))
    np.save(out_dir / "maps" / "suspicious_subsupport_map.npy", suspicious_map.astype(np.uint16))
    np.save(out_dir / "maps" / "blocking_like_subsupport_map.npy", blocking_map.astype(np.uint16))
    np.save(out_dir / "maps" / "ambiguous_subsupport_map.npy", ambiguous_map.astype(np.uint16))
    np.save(out_dir / "maps" / "deferred_subsupport_map.npy", deferred_map.astype(np.uint16))
    np.save(out_dir / "maps" / "excluded_subsupport_map.npy", excluded_map.astype(np.uint16))
    np.save(out_dir / "maps" / "u1_1_subobject_region_id_map.npy", region_id_map)
    np.save(out_dir / "maps" / "u1_1_subobject_gate_state_map.npy", state_map)
    np.save(out_dir / "maps" / "refined_unified_valid_observed_support_map.npy", refined_unified.astype(np.uint16))

    write_csv(out_dir / "u1_1_subobject_regions.csv", region_rows, REGION_FIELDS)
    write_csv(out_dir / "u1_1_subobject_memberships.csv", membership_rows, MEMBERSHIP_FIELDS)
    write_csv(out_dir / "u1_1_subobject_validation.csv", validation_rows, VALIDATION_FIELDS)
    write_csv(out_dir / "u1_1_excluded_subsupport.csv", excluded_rows, REGION_FIELDS)
    write_csv(out_dir / "u1_1_blocking_like_subsupport.csv", blocking_rows, REGION_FIELDS)
    write_csv(out_dir / "u1_1_ambiguous_subsupport.csv", ambiguous_rows, REGION_FIELDS)

    make_visuals(
        out_dir,
        u10_state_map,
        grid_map,
        suspicious_map,
        blocking_map,
        ambiguous_map,
        deferred_map,
        excluded_map,
        refined_unified,
        inferred,
    )

    output_missing_before_json = missing_required(out_dir, [rel for rel in REQUIRED_OUTPUT_FILES if rel not in {"summary.json", "contract_audit.json"}])
    status = "completed" if all(invariants.values()) and not output_missing_before_json else "failed_contract"
    outputs = {
        "u1_1_subobject_regions_csv": "u1_1_subobject_regions.csv",
        "u1_1_subobject_memberships_csv": "u1_1_subobject_memberships.csv",
        "u1_1_subobject_validation_csv": "u1_1_subobject_validation.csv",
        "u1_1_excluded_subsupport_csv": "u1_1_excluded_subsupport.csv",
        "u1_1_blocking_like_subsupport_csv": "u1_1_blocking_like_subsupport.csv",
        "u1_1_ambiguous_subsupport_csv": "u1_1_ambiguous_subsupport.csv",
        "summary_json": "summary.json",
        "contract_audit_json": "contract_audit.json",
        "grid_consistent_subsupport_map": "maps/grid_consistent_subsupport_map.npy",
        "suspicious_subsupport_map": "maps/suspicious_subsupport_map.npy",
        "blocking_like_subsupport_map": "maps/blocking_like_subsupport_map.npy",
        "ambiguous_subsupport_map": "maps/ambiguous_subsupport_map.npy",
        "deferred_subsupport_map": "maps/deferred_subsupport_map.npy",
        "excluded_subsupport_map": "maps/excluded_subsupport_map.npy",
        "u1_1_subobject_region_id_map": "maps/u1_1_subobject_region_id_map.npy",
        "u1_1_subobject_gate_state_map": "maps/u1_1_subobject_gate_state_map.npy",
        "refined_unified_valid_observed_support_map": "maps/refined_unified_valid_observed_support_map.npy",
        "visual_summary": "visuals/06_u1_1_gate_summary.png",
    }

    summary = {
        "version": VERSION,
        "status": status,
        "source_v3_3_run_dir": str(v33_dir),
        "source_v3_4_2_run_dir": str(v342_dir),
        "source_c1_0_run_dir": str(c10_dir),
        "source_c1_1_run_dir": str(c11_dir),
        "source_u1_0_run_dir": str(u10_dir),
        "source_v3_3_version": v33_summary.get("version", ""),
        "source_v3_4_2_version": v342_summary.get("version", ""),
        "source_c1_0_version": c10_summary.get("version", ""),
        "source_c1_1_version": c11_summary.get("version", ""),
        "source_u1_0_version": u10_summary.get("version", ""),
        "config": asdict(cfg),
        "required_inputs_missing": missing_inputs,
        "required_outputs_missing": output_missing_before_json,
        "counts": counts,
        "metrics": metrics,
        "invariants": invariants,
        "contract": contract,
        "outputs": outputs,
        "source_manifest_before": source_manifest_before,
        "source_manifest_after": source_manifest_after,
    }
    contract_audit = {
        "version": VERSION,
        "contract_file": "outputs/CONTRACT_U1_1_SUBOBJECT_CLEAN_GRID_GEOMETRY_PURITY_GATE_V1.md",
        "status": status,
        "semantic_rule": "u1_1_is_a_subobject_purity_gate_not_geometry_creator",
        "traceability_rule": "all_subsupport_states_remain_pixel_traceable_to_v3_3_observed_support",
        "required_inputs_missing": missing_inputs,
        "required_outputs_missing": output_missing_before_json,
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
    ap.add_argument("--v3-run-dir", required=True)
    ap.add_argument("--v3-4-2-dir", required=True)
    ap.add_argument("--c1-dir", required=True)
    ap.add_argument("--c1-1-dir", required=True)
    ap.add_argument("--u1-0-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--image", default=None, help="Optional audit image; not used as geometry source")
    ap.add_argument("--grid-audit-sample-dir", default=None, help="Optional GRID_AUDIT_V1 sample dir for benchmark metrics only")
    ap.add_argument("--max-core-axis-distance", type=float, default=3.0)
    ap.add_argument("--max-grid-consistent-p95-axis-distance", type=float, default=5.0)
    ap.add_argument("--max-local-width-for-clean-support", type=float, default=9.0)
    ap.add_argument("--min-local-density-score", type=float, default=0.35)
    ap.add_argument("--min-local-continuity-score", type=float, default=0.40)
    ap.add_argument("--max-conflict-score-for-grid-consistent", type=float, default=0.0)
    ap.add_argument("--max-conflict-score-for-suspicious", type=float, default=0.15)
    ap.add_argument("--min-subobject-pixels", type=int, default=2)
    ap.add_argument("--conflict-neighborhood", type=int, default=2)
    ap.add_argument("--local-window-radius", type=int, default=4)
    ap.add_argument("--max-bridge-gap", type=int, default=1)
    ap.add_argument(
        "--disallow-blocking-source-core-promotion",
        action="store_true",
        help="Keep U1.0 blocking_like sources blocking unless conflicts are absent and this flag is not set",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config(
        max_core_axis_distance_px=args.max_core_axis_distance,
        max_grid_consistent_p95_axis_distance_px=args.max_grid_consistent_p95_axis_distance,
        max_local_width_for_clean_support_px=args.max_local_width_for_clean_support,
        min_local_density_score=args.min_local_density_score,
        min_local_continuity_score=args.min_local_continuity_score,
        max_conflict_score_for_grid_consistent=args.max_conflict_score_for_grid_consistent,
        max_conflict_score_for_suspicious=args.max_conflict_score_for_suspicious,
        min_subobject_pixels=args.min_subobject_pixels,
        conflict_neighborhood_px=args.conflict_neighborhood,
        local_window_radius_px=args.local_window_radius,
        max_bridge_gap_px=args.max_bridge_gap,
        allow_zero_conflict_core_promotion_from_u1_0_blocking=not args.disallow_blocking_source_core_promotion,
    )
    run(
        v33_dir=Path(args.v3_run_dir),
        v342_dir=Path(args.v3_4_2_dir),
        c10_dir=Path(args.c1_dir),
        c11_dir=Path(args.c1_1_dir),
        u10_dir=Path(args.u1_0_dir),
        out_dir=Path(args.out),
        image_path=Path(args.image) if args.image else None,
        grid_audit_sample_dir=Path(args.grid_audit_sample_dir) if args.grid_audit_sample_dir else None,
        cfg=cfg,
    )


if __name__ == "__main__":
    main()
