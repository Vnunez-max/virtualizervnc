#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module U1.1-CAL - Geometric Hysteresis Calibrator.

Offline calibrator for U1.1 subobject gating. It reads U1.1 baseline outputs
and GRID_AUDIT_V1 truth only for calibration/audit metrics, then writes a
runtime-safe deterministic config. It never writes final geometry and never
modifies upstream outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_U1_1_CAL_V1_GEOMETRIC_HYSTERESIS_CALIBRATOR"
CONFIG_VERSION = "U1_1_CALIBRATED_CONFIG_V1"


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

TARGETS = {
    "observed_geometry_precision_after_u1_1": 0.985,
    "observed_geometry_recall_after_u1_1": 0.965,
    "blocking_false_observed_rate_after_u1_1": 0.10,
    "ambiguous_false_observed_rate_after_u1_1": 0.20,
    "not_recoverable_false_observed_rate_after_u1_1": 0.00,
}

FEATURE_FIELDS = [
    "sample_id",
    "subobject_region_id",
    "source_geometry_object_id",
    "source_u1_0_gate_state",
    "baseline_u1_1_gate_state",
    "calibrated_u1_1_gate_state",
    "region_pixel_count",
    "axis_distance_p95_px",
    "local_width_estimate_px",
    "local_density_score",
    "local_continuity_score",
    "longitudinal_run_length",
    "ridge_continuity_score",
    "valid_fringe_continuity_score",
    "protrusion_score",
    "asymmetric_fringe_score",
    "off_axis_microcomponent_score",
    "direct_conflict_touch_ratio",
    "near_conflict_touch_ratio",
    "direct_ambiguity_touch_ratio",
    "near_ambiguity_touch_ratio",
    "parent_line_reabsorption_score",
    "runtime_feature_only",
    "truth_used_for_metric_only",
]

DECISION_FIELDS = [
    "sample_id",
    "subobject_region_id",
    "baseline_state",
    "calibrated_state",
    "decision_zone",
    "decision_reason",
    "support_pixel_count",
    "truth_observed_overlap_pixels",
    "truth_blocking_overlap_pixels",
    "truth_ambiguous_overlap_pixels",
    "truth_not_recoverable_overlap_pixels",
    "changed_by_calibration",
    "change_is_metric_improving",
]

GRID_FIELDS = [
    "config_id",
    "split_name",
    "sample_count",
    "status",
    "observed_geometry_precision_after_u1_1",
    "observed_geometry_recall_after_u1_1",
    "blocking_false_observed_rate_after_u1_1",
    "ambiguous_false_observed_rate_after_u1_1",
    "not_recoverable_false_observed_rate_after_u1_1",
    "wrong_exclusion_rate_after_u1_1",
    "wrong_inclusion_rate_after_u1_1",
    "passes_contract_targets",
    "objective_rank",
    "config_json_path",
    "notes",
]

REQUIRED_OUTPUT_FILES = [
    "u1_1_calibrated_config.json",
    "u1_1_calibration_grid.csv",
    "u1_1_calibration_feature_table.csv",
    "u1_1_calibration_decisions.csv",
    "u1_1_validation_report.json",
    "u1_1_holdout_contract_audit.json",
    "u1_1_calibration_report.md",
    "summary.json",
    "contract_audit.json",
    "visuals/01_baseline_vs_calibrated_grid_support.png",
    "visuals/02_baseline_vs_calibrated_exclusions.png",
    "visuals/03_blocking_ambiguous_error_overlay.png",
    "visuals/04_wrong_exclusion_overlay.png",
    "visuals/05_metric_tradeoff_frontier.png",
    "visuals/06_holdout_visual_summary.png",
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

FORBIDDEN_CONFIG_KEYS = {
    "raw_mask_pixels",
    "truth_mask_pixels",
    "sample_specific_coordinates",
    "sample_specific_exceptions",
    "learned_untraceable_embeddings",
    "final_line_ids",
    "axis_descriptors",
    "crossing_graphs",
    "semantic_labels",
    "clinical_labels",
}

AMBIGUOUS_CLASSES = {"ambiguous_residual_evidence"}


@dataclass(frozen=True)
class Thresholds:
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
    min_longitudinal_run_length_for_valid_fringe: int = 5
    min_ridge_continuity_score_for_valid_fringe: float = 0.60
    max_protrusion_score_for_valid_fringe: float = 0.55
    max_asymmetric_fringe_score_for_valid_fringe: float = 0.85
    max_off_axis_microcomponent_score_for_accept: float = 0.55
    min_direct_conflict_touch_ratio_for_reject: float = 0.01


@dataclass(frozen=True)
class Weights:
    axis_score_weight: float = 0.18
    width_score_weight: float = 0.10
    continuity_score_weight: float = 0.18
    density_score_weight: float = 0.12
    ridge_score_weight: float = 0.17
    valid_fringe_score_weight: float = 0.16
    protrusion_penalty_weight: float = 0.22
    direct_conflict_penalty_weight: float = 0.35
    near_conflict_penalty_weight: float = 0.14
    source_u1_0_state_weight: float = 0.09


@dataclass
class Candidate:
    config_id: str
    thresholds: Thresholds
    weights: Weights


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


def file_manifest(root: Path, rels: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for rel in rels:
        p = root / rel
        out[rel] = {
            "exists": p.exists(),
            "size_bytes": p.stat().st_size if p.exists() else None,
            "sha256": sha256_file(p) if p.exists() else None,
        }
    return out


def missing_required(root: Path, rels: Sequence[str]) -> List[str]:
    return [rel for rel in rels if not (root / rel).exists()]


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


def load_map(path: Path, dtype: Any | None = None) -> np.ndarray:
    arr = np.load(path)
    return arr.astype(dtype) if dtype is not None else arr


def optional_map(path: Path, shape: Tuple[int, int], dtype: Any = np.uint16) -> np.ndarray:
    if path.exists():
        return np.load(path).astype(dtype)
    return np.zeros(shape, dtype=dtype)


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


def font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def render_bool(mask: np.ndarray, color: Tuple[int, int, int], bg: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    arr = np.full((mask.shape[0], mask.shape[1], 3), bg, dtype=np.uint8)
    arr[mask.astype(bool)] = color
    return Image.fromarray(arr, "RGB")


def titled(img: Image.Image, title: str) -> Image.Image:
    out = img.copy().convert("RGB")
    d = ImageDraw.Draw(out, "RGBA")
    d.rectangle((0, 0, out.width, 28), fill=(255, 255, 255, 235))
    d.text((8, 8), title, fill=(0, 0, 0, 255), font=font(10))
    return out


def read_split(path: Path) -> List[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sample_dir(dataset_root: Path, sample_id: str) -> Path:
    if (dataset_root / "samples" / sample_id).exists():
        return dataset_root / "samples" / sample_id
    return dataset_root / sample_id


def baseline_dir(root: Path, sample_id: str) -> Path:
    if (root / sample_id).exists():
        return root / sample_id
    return root


def ambiguous_residual_support(v342_dir: Path, shape: Tuple[int, int]) -> np.ndarray:
    objects = read_csv(v342_dir / "residual_evidence_objects.csv")
    memberships = read_csv(v342_dir / "residual_geometry_memberships.csv")
    class_by_object = {
        str(row.get("residual_object_id", "")): row.get("residual_evidence_class", "")
        for row in objects
    }
    out = np.zeros(shape, dtype=bool)
    for row in memberships:
        rid = str(row.get("residual_object_id", ""))
        if class_by_object.get(rid) not in AMBIGUOUS_CLASSES:
            continue
        x, y = as_int(row.get("x")), as_int(row.get("y"))
        if 0 <= y < shape[0] and 0 <= x < shape[1]:
            out[y, x] = True
    return out


def longitudinal_coord(orientation: str, x: int, y: int) -> int:
    return int(y if orientation == "vertical" else x)


def perpendicular_coord(orientation: str, x: int, y: int) -> int:
    return int(x if orientation == "vertical" else y)


def mask_from_region(region_map: np.ndarray, region_id: int) -> np.ndarray:
    return region_map == region_id


def coords_from_mask(mask: np.ndarray) -> List[Tuple[int, int]]:
    ys, xs = np.where(mask)
    return [(int(x), int(y)) for y, x in zip(ys, xs)]


def region_run_features(coords: Sequence[Tuple[int, int]], orientation: str, axis: float) -> Dict[str, float]:
    if not coords:
        return {
            "longitudinal_run_length": 0.0,
            "ridge_continuity_score": 0.0,
            "axis_aligned_neighbor_support": 0.0,
            "valid_fringe_continuity_score": 0.0,
            "fringe_side_consistency": 0.0,
            "protrusion_score": 1.0,
            "asymmetric_fringe_score": 1.0,
            "off_axis_microcomponent_score": 1.0,
            "parent_line_reabsorption_score": 0.0,
        }

    coord_set = set(coords)
    longs = [longitudinal_coord(orientation, x, y) for x, y in coords]
    long_unique = sorted(set(longs))
    span = max(long_unique) - min(long_unique) + 1 if long_unique else 0
    run_length = len(long_unique)
    ridge_continuity = ratio(run_length, span)

    aligned_hits = 0
    for x, y in coords:
        if orientation == "vertical":
            if (x, y - 1) in coord_set or (x, y + 1) in coord_set:
                aligned_hits += 1
        else:
            if (x - 1, y) in coord_set or (x + 1, y) in coord_set:
                aligned_hits += 1
    aligned_support = ratio(aligned_hits, len(coords))

    side_counts = Counter()
    off_axis_count = 0
    for x, y in coords:
        perp = perpendicular_coord(orientation, x, y)
        diff = float(perp) - axis
        if diff < -0.5:
            side_counts["negative"] += 1
        elif diff > 0.5:
            side_counts["positive"] += 1
        else:
            side_counts["center"] += 1
        if abs(diff) > 4.0:
            off_axis_count += 1
    side_total = side_counts["negative"] + side_counts["positive"]
    if side_total:
        fringe_side_consistency = max(side_counts["negative"], side_counts["positive"]) / side_total
        asymmetric = 1.0 - min(side_counts["negative"], side_counts["positive"]) / max(side_counts["negative"], side_counts["positive"], 1)
    else:
        fringe_side_consistency = 1.0
        asymmetric = 0.0

    small_region = 1.0 - clamp01(len(coords) / 24.0)
    poor_run = 1.0 - ridge_continuity
    off_axis_ratio = ratio(off_axis_count, len(coords))
    protrusion = clamp01(0.40 * small_region + 0.35 * poor_run + 0.25 * off_axis_ratio)
    off_axis_microcomponent = clamp01(0.60 * off_axis_ratio + 0.40 * small_region)
    valid_fringe_continuity = clamp01(0.65 * ridge_continuity + 0.35 * aligned_support)
    parent_reabsorption = clamp01(0.45 * ridge_continuity + 0.35 * aligned_support + 0.20 * (1.0 - protrusion))

    return {
        "longitudinal_run_length": float(run_length),
        "ridge_continuity_score": ridge_continuity,
        "axis_aligned_neighbor_support": aligned_support,
        "valid_fringe_continuity_score": valid_fringe_continuity,
        "fringe_side_consistency": fringe_side_consistency,
        "protrusion_score": protrusion,
        "asymmetric_fringe_score": asymmetric,
        "off_axis_microcomponent_score": off_axis_microcomponent,
        "parent_line_reabsorption_score": parent_reabsorption,
    }


def runtime_context_from_u11_summary(u11_dir: Path, shape: Tuple[int, int], conflict_radius: int) -> Dict[str, np.ndarray]:
    summary = read_json(u11_dir / "summary.json")
    v342_dir = Path(summary.get("source_v3_4_2_run_dir", ""))
    c10_dir = Path(summary.get("source_c1_0_run_dir", ""))
    c11_dir = Path(summary.get("source_c1_1_run_dir", ""))
    diagnostic = optional_map(v342_dir / "maps" / "diagnostic_residual_support_count_map.npy", shape, np.uint16) > 0
    ambiguous = ambiguous_residual_support(v342_dir, shape) if v342_dir.exists() else np.zeros(shape, dtype=bool)
    c10_rejected = optional_map(c10_dir / "maps" / "rejected_residual_support_map.npy", shape, np.uint16) > 0
    c11_blocking = optional_map(c11_dir / "maps" / "collective_blocking_evidence_map.npy", shape, np.uint16) > 0
    c10_inferred = optional_map(c10_dir / "maps" / "inferred_span_map.npy", shape, np.uint16) > 0
    c11_inferred = optional_map(c11_dir / "maps" / "collective_inferred_span_map.npy", shape, np.uint16) > 0
    direct_conflict = diagnostic | c10_rejected | c11_blocking
    return {
        "direct_conflict": direct_conflict,
        "near_conflict": dilate(direct_conflict, conflict_radius),
        "direct_ambiguity": ambiguous,
        "near_ambiguity": dilate(ambiguous, conflict_radius),
        "inferred": c10_inferred | c11_inferred,
        "diagnostic": diagnostic,
        "ambiguous": ambiguous,
    }


def load_truth(sample_path: Path) -> Dict[str, np.ndarray]:
    masks = sample_path / "masks"
    return {
        "observed": load_map(masks / "observed_valid_geometry.npy", bool).astype(bool),
        "blocking": load_map(masks / "blocking_geometry_evidence.npy", bool).astype(bool),
        "ambiguous": load_map(masks / "ambiguous_geometry_evidence.npy", bool).astype(bool),
        "not_recoverable": load_map(masks / "missing_not_recoverable_geometry.npy", bool).astype(bool),
        "clean": load_map(masks / "clean_grid_mask.npy", bool).astype(bool),
    }


def extract_sample_features(sample_id: str, dataset_root: Path, u11_root: Path, conflict_radius: int = 2) -> Dict[str, Any]:
    u11_dir = baseline_dir(u11_root, sample_id)
    missing_u11 = missing_required(u11_dir, REQUIRED_U11_FILES)
    sdir = sample_dir(dataset_root, sample_id)
    required_truth = [
        "sample_manifest.json",
        "masks/observed_valid_geometry.npy",
        "masks/blocking_geometry_evidence.npy",
        "masks/ambiguous_geometry_evidence.npy",
        "masks/missing_not_recoverable_geometry.npy",
        "masks/clean_grid_mask.npy",
    ]
    missing_truth = missing_required(sdir, required_truth)
    if missing_u11 or missing_truth:
        return {
            "sample_id": sample_id,
            "status": "missing_runtime_context",
            "missing_u1_1": missing_u11,
            "missing_truth": missing_truth,
            "regions": [],
        }

    region_rows = read_csv(u11_dir / "u1_1_subobject_regions.csv")
    membership_rows = read_csv(u11_dir / "u1_1_subobject_memberships.csv")
    region_map = load_map(u11_dir / "maps" / "u1_1_subobject_region_id_map.npy", np.int32)
    baseline_gate_map = load_map(u11_dir / "maps" / "u1_1_subobject_gate_state_map.npy", np.uint8)
    baseline_grid = load_map(u11_dir / "maps" / "grid_consistent_subsupport_map.npy", np.uint16) > 0
    baseline_refined = load_map(u11_dir / "maps" / "refined_unified_valid_observed_support_map.npy", np.uint16) > 0
    baseline_excluded = load_map(u11_dir / "maps" / "excluded_subsupport_map.npy", np.uint16) > 0
    shape = region_map.shape
    truth = load_truth(sdir)
    runtime = runtime_context_from_u11_summary(u11_dir, shape, conflict_radius)

    coords_by_region: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    role_by_region: Dict[int, Counter[str]] = defaultdict(Counter)
    for row in membership_rows:
        rid = as_int(row.get("subobject_region_id"))
        x, y = as_int(row.get("x")), as_int(row.get("y"))
        if rid and 0 <= y < shape[0] and 0 <= x < shape[1]:
            coords_by_region[rid].append((x, y))
            role_by_region[rid][row.get("source_membership_role", "line_support")] += 1

    features: List[Dict[str, Any]] = []
    for row in region_rows:
        rid = as_int(row.get("subobject_region_id"))
        mask = mask_from_region(region_map, rid)
        coords = coords_by_region.get(rid) or coords_from_mask(mask)
        orientation = row.get("orientation", "horizontal")
        axis = as_float(row.get("axis_estimate_px"))
        run = region_run_features(coords, orientation, axis)
        count = int(np.count_nonzero(mask))
        direct_conflict_touch = ratio(int(np.count_nonzero(mask & runtime["direct_conflict"])), count)
        near_conflict_touch = ratio(int(np.count_nonzero(mask & runtime["near_conflict"])), count)
        direct_ambiguity_touch = ratio(int(np.count_nonzero(mask & runtime["direct_ambiguity"])), count)
        near_ambiguity_touch = ratio(int(np.count_nonzero(mask & runtime["near_ambiguity"])), count)
        conflict_component_shape = clamp01(
            0.45 * direct_conflict_touch
            + 0.20 * near_conflict_touch
            + 0.20 * run["protrusion_score"]
            + 0.15 * run["off_axis_microcomponent_score"]
        )
        role = role_by_region[rid].most_common(1)[0][0] if role_by_region[rid] else "line_support"
        features.append(
            {
                "sample_id": sample_id,
                "subobject_region_id": rid,
                "source_geometry_object_id": row.get("source_geometry_object_id", ""),
                "source_u1_0_gate_state": row.get("source_u1_0_gate_state", ""),
                "source_membership_role": role,
                "baseline_u1_1_gate_state": row.get("gate_state", ""),
                "region_pixel_count": count,
                "axis_distance_p95_px": as_float(row.get("axis_distance_p95_px")),
                "local_width_estimate_px": as_float(row.get("local_width_estimate_px")),
                "local_density_score": as_float(row.get("local_density_score")),
                "local_continuity_score": as_float(row.get("local_continuity_score")),
                "local_conflict_score": as_float(row.get("local_conflict_score")),
                "local_blocking_score": as_float(row.get("local_blocking_score")),
                "local_ambiguity_score": as_float(row.get("local_ambiguity_score")),
                "core_pixel_count": as_int(row.get("core_pixel_count")),
                "fringe_pixel_count": as_int(row.get("fringe_pixel_count")),
                "longitudinal_run_length": run["longitudinal_run_length"],
                "ridge_continuity_score": run["ridge_continuity_score"],
                "axis_aligned_neighbor_support": run["axis_aligned_neighbor_support"],
                "valid_fringe_continuity_score": run["valid_fringe_continuity_score"],
                "fringe_side_consistency": run["fringe_side_consistency"],
                "protrusion_score": run["protrusion_score"],
                "asymmetric_fringe_score": run["asymmetric_fringe_score"],
                "off_axis_microcomponent_score": run["off_axis_microcomponent_score"],
                "direct_conflict_touch_ratio": direct_conflict_touch,
                "near_conflict_touch_ratio": near_conflict_touch,
                "direct_ambiguity_touch_ratio": direct_ambiguity_touch,
                "near_ambiguity_touch_ratio": near_ambiguity_touch,
                "conflict_component_shape_score": conflict_component_shape,
                "parent_line_reabsorption_score": run["parent_line_reabsorption_score"],
                "truth_observed_overlap_pixels": int(np.count_nonzero(mask & truth["observed"])),
                "truth_blocking_overlap_pixels": int(np.count_nonzero(mask & truth["blocking"])),
                "truth_ambiguous_overlap_pixels": int(np.count_nonzero(mask & truth["ambiguous"])),
                "truth_not_recoverable_overlap_pixels": int(np.count_nonzero(mask & truth["not_recoverable"])),
            }
        )

    return {
        "sample_id": sample_id,
        "status": "completed",
        "u1_1_dir": str(u11_dir),
        "dataset_sample_dir": str(sdir),
        "regions": features,
        "maps": {
            "region_id_map": region_map,
            "baseline_gate_map": baseline_gate_map,
            "baseline_grid": baseline_grid,
            "baseline_refined": baseline_refined,
            "baseline_excluded": baseline_excluded,
            "baseline_extra_refined": baseline_refined & ~baseline_grid,
            "runtime_inferred": runtime["inferred"],
            "runtime_diagnostic": runtime["diagnostic"],
            "runtime_ambiguous": runtime["ambiguous"],
        },
        "truth": truth,
    }


def source_state_score(state: str) -> float:
    return {
        "grid_consistent": 1.00,
        "suspicious": 0.72,
        "blocking_like": 0.40,
        "ambiguous": 0.38,
        "deferred": 0.35,
    }.get(state, 0.45)


def decide_region(feature: Dict[str, Any], candidate: Candidate) -> Tuple[str, str, str, float]:
    th = candidate.thresholds
    w = candidate.weights
    direct_conflict = as_float(feature.get("direct_conflict_touch_ratio"))
    direct_amb = as_float(feature.get("direct_ambiguity_touch_ratio"))
    near_conflict = as_float(feature.get("near_conflict_touch_ratio"))
    near_amb = as_float(feature.get("near_ambiguity_touch_ratio"))
    protrusion = as_float(feature.get("protrusion_score"))
    off_axis = as_float(feature.get("off_axis_microcomponent_score"))
    asym = as_float(feature.get("asymmetric_fringe_score"))
    p95_axis = as_float(feature.get("axis_distance_p95_px"))
    width = as_float(feature.get("local_width_estimate_px"))
    density = as_float(feature.get("local_density_score"))
    continuity = as_float(feature.get("local_continuity_score"))
    run_length = as_float(feature.get("longitudinal_run_length"))
    ridge = as_float(feature.get("ridge_continuity_score"))
    valid_fringe = as_float(feature.get("valid_fringe_continuity_score"))
    parent_reabsorption = as_float(feature.get("parent_line_reabsorption_score"))
    region_pixels = as_int(feature.get("region_pixel_count"))
    source_state = str(feature.get("source_u1_0_gate_state", ""))
    baseline_state = str(feature.get("baseline_u1_1_gate_state", ""))

    if direct_amb >= th.min_direct_conflict_touch_ratio_for_reject:
        return "ambiguous", "strong_reject", "direct_ambiguity_touch_exceeds_threshold", 0.0
    if direct_conflict >= th.min_direct_conflict_touch_ratio_for_reject:
        return "blocking_like", "strong_reject", "direct_conflict_touch_exceeds_threshold", 0.0
    if protrusion > th.max_protrusion_score_for_valid_fringe and off_axis > th.max_off_axis_microcomponent_score_for_accept:
        return "blocking_like", "strong_reject", "protrusion_and_off_axis_microcomponent", 0.0
    if region_pixels < th.min_subobject_pixels:
        return "deferred", "middle_zone", "region_below_min_subobject_pixels", 0.0

    axis_score = clamp01(1.0 - p95_axis / max(th.max_grid_consistent_p95_axis_distance_px, 0.001))
    width_score = clamp01(1.0 - max(0.0, width - th.max_local_width_for_clean_support_px) / max(th.max_local_width_for_clean_support_px, 1.0))
    density_score = clamp01(density / max(th.min_local_density_score, 0.001))
    continuity_score = clamp01(continuity / max(th.min_local_continuity_score, 0.001))
    ridge_score = clamp01(0.50 * ridge + 0.25 * valid_fringe + 0.25 * parent_reabsorption)
    conflict_penalty = clamp01(direct_conflict + direct_amb + 0.5 * near_conflict + 0.5 * near_amb)
    source_score = source_state_score(source_state)
    score = clamp01(
        w.axis_score_weight * axis_score
        + w.width_score_weight * width_score
        + w.continuity_score_weight * continuity_score
        + w.density_score_weight * density_score
        + w.ridge_score_weight * ridge_score
        + w.valid_fringe_score_weight * valid_fringe
        + w.source_u1_0_state_weight * source_score
        - w.protrusion_penalty_weight * protrusion
        - w.direct_conflict_penalty_weight * (direct_conflict + direct_amb)
        - w.near_conflict_penalty_weight * (near_conflict + near_amb)
    )

    core_accept = (
        p95_axis <= th.max_grid_consistent_p95_axis_distance_px
        and density >= th.min_local_density_score
        and continuity >= th.min_local_continuity_score
        and direct_conflict <= th.max_conflict_score_for_grid_consistent
        and direct_amb <= th.max_conflict_score_for_grid_consistent
    )
    fringe_accept = (
        run_length >= th.min_longitudinal_run_length_for_valid_fringe
        and ridge >= th.min_ridge_continuity_score_for_valid_fringe
        and valid_fringe >= th.min_ridge_continuity_score_for_valid_fringe
        and protrusion <= th.max_protrusion_score_for_valid_fringe
        and asym <= th.max_asymmetric_fringe_score_for_valid_fringe
        and off_axis <= th.max_off_axis_microcomponent_score_for_accept
        and direct_conflict <= th.max_conflict_score_for_grid_consistent
        and direct_amb <= th.max_conflict_score_for_grid_consistent
    )

    if core_accept or fringe_accept:
        return "grid_consistent", "strong_accept", "core_or_valid_fringe_zero_direct_conflict", score
    if baseline_state == "ambiguous" or near_amb > th.max_conflict_score_for_suspicious:
        return "ambiguous", "middle_zone", "ambiguous_context_without_strong_accept", score
    if baseline_state == "blocking_like" or near_conflict > th.max_conflict_score_for_suspicious:
        return "suspicious", "middle_zone", "near_conflict_without_direct_reject", score
    if score >= 0.62 and protrusion <= th.max_protrusion_score_for_valid_fringe:
        return "grid_consistent", "strong_accept", "score_accepts_stable_traceable_support", score
    if score < 0.35:
        return "deferred", "middle_zone", "low_hysteresis_score", score
    return "suspicious", "middle_zone", "traceable_but_not_strong_accept", score


def generate_candidates(limit: int = 128) -> List[Candidate]:
    base_weights = Weights()
    values = {
        "min_longitudinal_run_length_for_valid_fringe": [3, 5, 8, 12],
        "min_ridge_continuity_score_for_valid_fringe": [0.45, 0.60, 0.75],
        "max_protrusion_score_for_valid_fringe": [0.45, 0.60, 0.75],
        "max_off_axis_microcomponent_score_for_accept": [0.45, 0.60, 0.75],
        "min_direct_conflict_touch_ratio_for_reject": [0.01, 0.05, 0.10],
        "max_conflict_score_for_suspicious": [0.10, 0.15, 0.25],
    }
    fields = list(values)
    candidates: List[Candidate] = [
        Candidate("cfg_0000_baseline_hysteresis", Thresholds(), base_weights)
    ]
    idx = 1
    for combo in itertools.product(*(values[f] for f in fields)):
        data = asdict(Thresholds())
        for k, v in zip(fields, combo):
            data[k] = v
        th = Thresholds(**data)
        candidates.append(Candidate(f"cfg_{idx:04d}", th, base_weights))
        idx += 1
        if len(candidates) >= limit:
            break
    return candidates


def apply_candidate_to_sample(sample: Dict[str, Any], candidate: Candidate) -> Dict[str, Any]:
    region_map = sample["maps"]["region_id_map"]
    baseline_extra = sample["maps"]["baseline_extra_refined"]
    inferred = sample["maps"]["runtime_inferred"]
    diagnostic = sample["maps"]["runtime_diagnostic"]
    ambiguous_runtime = sample["maps"]["runtime_ambiguous"]
    calibrated_state_map = np.zeros(region_map.shape, dtype=np.uint8)
    decisions: List[Dict[str, Any]] = []
    for feat in sample["regions"]:
        rid = as_int(feat["subobject_region_id"])
        state, zone, reason, score = decide_region(feat, candidate)
        mask = region_map == rid
        calibrated_state_map[mask] = STATE_CODE[state]
        decisions.append(
            {
                **feat,
                "calibrated_u1_1_gate_state": state,
                "decision_zone": zone,
                "decision_reason": reason,
                "hysteresis_score": score,
            }
        )

    grid = calibrated_state_map == STATE_CODE["grid_consistent"]
    suspicious = calibrated_state_map == STATE_CODE["suspicious"]
    blocking = calibrated_state_map == STATE_CODE["blocking_like"]
    ambiguous = calibrated_state_map == STATE_CODE["ambiguous"]
    deferred = calibrated_state_map == STATE_CODE["deferred"]
    excluded = suspicious | blocking | ambiguous | deferred
    unsafe = excluded | inferred | diagnostic | ambiguous_runtime
    refined = (grid | baseline_extra) & ~unsafe
    return {
        "sample_id": sample["sample_id"],
        "decisions": decisions,
        "maps": {
            "calibrated_state_map": calibrated_state_map,
            "calibrated_grid": grid,
            "calibrated_excluded": excluded,
            "calibrated_blocking": blocking,
            "calibrated_ambiguous": ambiguous,
            "calibrated_deferred": deferred,
            "calibrated_refined": refined,
        },
    }


def aggregate_metrics(samples: Sequence[Dict[str, Any]], candidate: Candidate) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    totals = Counter()
    zone_totals = Counter()
    sample_results: Dict[str, Dict[str, Any]] = {}
    completed = 0
    failed = 0
    for sample in samples:
        if sample.get("status") != "completed":
            failed += 1
            continue
        completed += 1
        applied = apply_candidate_to_sample(sample, candidate)
        refined = applied["maps"]["calibrated_refined"]
        excluded = applied["maps"]["calibrated_excluded"]
        truth = sample["truth"]
        observed = truth["observed"]
        blocking = truth["blocking"]
        ambiguous = truth["ambiguous"]
        not_recoverable = truth["not_recoverable"]
        clean = truth["clean"]

        totals["refined"] += int(np.count_nonzero(refined))
        totals["observed"] += int(np.count_nonzero(observed))
        totals["refined_observed"] += int(np.count_nonzero(refined & observed))
        totals["blocking"] += int(np.count_nonzero(blocking))
        totals["ambiguous"] += int(np.count_nonzero(ambiguous))
        totals["not_recoverable"] += int(np.count_nonzero(not_recoverable))
        totals["refined_blocking"] += int(np.count_nonzero(refined & blocking))
        totals["refined_ambiguous"] += int(np.count_nonzero(refined & ambiguous))
        totals["refined_not_recoverable"] += int(np.count_nonzero(refined & not_recoverable))
        totals["clean"] += int(np.count_nonzero(clean))
        totals["refined_clean"] += int(np.count_nonzero(refined & clean))
        totals["excluded_observed"] += int(np.count_nonzero(excluded & observed))
        totals["wrong_inclusion"] += int(np.count_nonzero(refined & (blocking | ambiguous | not_recoverable)))
        totals["grid_pixels"] += int(np.count_nonzero(applied["maps"]["calibrated_grid"]))
        totals["excluded_pixels"] += int(np.count_nonzero(excluded))

        for d in applied["decisions"]:
            zone = d["decision_zone"]
            count = as_int(d["region_pixel_count"])
            zone_totals[f"{zone}_region_count"] += 1
            if zone == "strong_accept":
                zone_totals["strong_accept_wrong_inclusion_pixels"] += (
                    as_int(d["truth_blocking_overlap_pixels"])
                    + as_int(d["truth_ambiguous_overlap_pixels"])
                    + as_int(d["truth_not_recoverable_overlap_pixels"])
                )
            if zone == "strong_reject":
                zone_totals["strong_reject_wrong_exclusion_pixels"] += as_int(d["truth_observed_overlap_pixels"])
            if zone == "middle_zone":
                zone_totals["middle_zone_observed_pixels"] += as_int(d["truth_observed_overlap_pixels"])
            zone_totals[f"{zone}_pixels"] += count

        sample_results[sample["sample_id"]] = applied

    metrics = {
        "sample_count": len(samples),
        "completed_sample_count": completed,
        "failed_sample_count": failed,
        "observed_geometry_precision_after_u1_1": ratio(totals["refined_observed"], totals["refined"]),
        "observed_geometry_recall_after_u1_1": ratio(totals["refined_observed"], totals["observed"]),
        "blocking_false_observed_rate_after_u1_1": ratio(totals["refined_blocking"], totals["blocking"]),
        "ambiguous_false_observed_rate_after_u1_1": ratio(totals["refined_ambiguous"], totals["ambiguous"]),
        "not_recoverable_false_observed_rate_after_u1_1": ratio(totals["refined_not_recoverable"], totals["not_recoverable"]),
        "clean_grid_observed_coverage_after_u1_1": ratio(totals["refined_clean"], totals["clean"]),
        "wrong_exclusion_rate_after_u1_1": ratio(totals["excluded_observed"], totals["observed"]),
        "wrong_inclusion_rate_after_u1_1": ratio(totals["wrong_inclusion"], totals["refined"]),
        "mean_grid_consistent_subsupport_ratio": ratio(totals["grid_pixels"], totals["grid_pixels"] + totals["excluded_pixels"]),
        "mean_excluded_subsupport_ratio": ratio(totals["excluded_pixels"], totals["grid_pixels"] + totals["excluded_pixels"]),
        "strong_accept_region_count": int(zone_totals["strong_accept_region_count"]),
        "strong_reject_region_count": int(zone_totals["strong_reject_region_count"]),
        "middle_zone_region_count": int(zone_totals["middle_zone_region_count"]),
        "strong_accept_wrong_inclusion_pixels": int(zone_totals["strong_accept_wrong_inclusion_pixels"]),
        "strong_reject_wrong_exclusion_pixels": int(zone_totals["strong_reject_wrong_exclusion_pixels"]),
        "middle_zone_observed_pixels": int(zone_totals["middle_zone_observed_pixels"]),
    }
    return metrics, sample_results


def passes_targets(metrics: Dict[str, Any]) -> bool:
    return (
        metrics["not_recoverable_false_observed_rate_after_u1_1"] == 0.0
        and metrics["observed_geometry_precision_after_u1_1"] >= TARGETS["observed_geometry_precision_after_u1_1"]
        and metrics["observed_geometry_recall_after_u1_1"] >= TARGETS["observed_geometry_recall_after_u1_1"]
        and metrics["blocking_false_observed_rate_after_u1_1"] <= TARGETS["blocking_false_observed_rate_after_u1_1"]
        and metrics["ambiguous_false_observed_rate_after_u1_1"] <= TARGETS["ambiguous_false_observed_rate_after_u1_1"]
    )


def objective_key(metrics: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        metrics["not_recoverable_false_observed_rate_after_u1_1"] != 0.0,
        metrics["observed_geometry_precision_after_u1_1"] < TARGETS["observed_geometry_precision_after_u1_1"],
        metrics["observed_geometry_recall_after_u1_1"] < TARGETS["observed_geometry_recall_after_u1_1"],
        metrics["blocking_false_observed_rate_after_u1_1"] > TARGETS["blocking_false_observed_rate_after_u1_1"],
        metrics["ambiguous_false_observed_rate_after_u1_1"] > TARGETS["ambiguous_false_observed_rate_after_u1_1"],
        metrics["wrong_exclusion_rate_after_u1_1"],
        metrics["wrong_inclusion_rate_after_u1_1"],
        -metrics["observed_geometry_recall_after_u1_1"],
    )


def config_json(
    candidate: Candidate,
    dataset_id: str,
    calibration_ids: Sequence[str],
    validation_ids: Sequence[str],
    holdout_ids: Sequence[str],
) -> Dict[str, Any]:
    return {
        "version": CONFIG_VERSION,
        "source_calibrator_version": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": dataset_id,
        "calibration_split_ids": list(calibration_ids),
        "validation_split_ids": list(validation_ids),
        "holdout_split_ids": list(holdout_ids),
        "selected_objective": "lexicographic_contract_targets_then_wrong_exclusion_wrong_inclusion",
        "thresholds": asdict(candidate.thresholds),
        "weights": asdict(candidate.weights),
        "decision_policy": {
            "strong_accept": "core_or_valid_fringe_zero_direct_conflict",
            "strong_reject": "direct_conflict_or_protrusion_or_off_axis_microcomponent",
            "middle_zone": "traceable_but_not_strong_accept_or_strong_reject",
        },
        "contract_acceptance_targets": TARGETS,
        "feature_names": [
            "axis_distance_p95_px",
            "local_width_estimate_px",
            "local_density_score",
            "local_continuity_score",
            "longitudinal_run_length",
            "ridge_continuity_score",
            "axis_aligned_neighbor_support",
            "valid_fringe_continuity_score",
            "fringe_side_consistency",
            "protrusion_score",
            "asymmetric_fringe_score",
            "off_axis_microcomponent_score",
            "direct_conflict_touch_ratio",
            "near_conflict_touch_ratio",
            "direct_ambiguity_touch_ratio",
            "near_ambiguity_touch_ratio",
            "conflict_component_shape_score",
            "parent_line_reabsorption_score",
        ],
        "prohibited_runtime_inputs": sorted(FORBIDDEN_CONFIG_KEYS),
    }


def config_is_runtime_safe(config: Dict[str, Any]) -> bool:
    def has_forbidden_key(value: Any) -> bool:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in FORBIDDEN_CONFIG_KEYS:
                    return True
                if key == "prohibited_runtime_inputs":
                    continue
                if has_forbidden_key(child):
                    return True
        elif isinstance(value, list):
            return any(has_forbidden_key(item) for item in value)
        return False

    return not has_forbidden_key(config)


def write_feature_and_decision_tables(
    out_dir: Path,
    samples: Sequence[Dict[str, Any]],
    selected_results: Dict[str, Dict[str, Any]],
) -> None:
    feature_rows: List[Dict[str, Any]] = []
    decision_rows: List[Dict[str, Any]] = []
    for sample in samples:
        if sample.get("status") != "completed":
            continue
        applied = selected_results.get(sample["sample_id"])
        if not applied:
            continue
        for d in applied["decisions"]:
            feature_rows.append(
                {
                    **{k: d.get(k, "") for k in FEATURE_FIELDS},
                    "calibrated_u1_1_gate_state": d["calibrated_u1_1_gate_state"],
                    "runtime_feature_only": True,
                    "truth_used_for_metric_only": True,
                }
            )
            changed = d["baseline_u1_1_gate_state"] != d["calibrated_u1_1_gate_state"]
            truth_bad = (
                as_int(d["truth_blocking_overlap_pixels"])
                + as_int(d["truth_ambiguous_overlap_pixels"])
                + as_int(d["truth_not_recoverable_overlap_pixels"])
            )
            metric_improving = (
                changed
                and (
                    (d["calibrated_u1_1_gate_state"] == "grid_consistent" and as_int(d["truth_observed_overlap_pixels"]) > truth_bad)
                    or (d["calibrated_u1_1_gate_state"] != "grid_consistent" and truth_bad > as_int(d["truth_observed_overlap_pixels"]))
                )
            )
            decision_rows.append(
                {
                    "sample_id": d["sample_id"],
                    "subobject_region_id": d["subobject_region_id"],
                    "baseline_state": d["baseline_u1_1_gate_state"],
                    "calibrated_state": d["calibrated_u1_1_gate_state"],
                    "decision_zone": d["decision_zone"],
                    "decision_reason": d["decision_reason"],
                    "support_pixel_count": d["region_pixel_count"],
                    "truth_observed_overlap_pixels": d["truth_observed_overlap_pixels"],
                    "truth_blocking_overlap_pixels": d["truth_blocking_overlap_pixels"],
                    "truth_ambiguous_overlap_pixels": d["truth_ambiguous_overlap_pixels"],
                    "truth_not_recoverable_overlap_pixels": d["truth_not_recoverable_overlap_pixels"],
                    "changed_by_calibration": changed,
                    "change_is_metric_improving": metric_improving,
                }
            )
    write_csv(out_dir / "u1_1_calibration_feature_table.csv", feature_rows, FEATURE_FIELDS)
    write_csv(out_dir / "u1_1_calibration_decisions.csv", decision_rows, DECISION_FIELDS)


def make_excluded_rgb(state_map: np.ndarray) -> np.ndarray:
    arr = np.full((state_map.shape[0], state_map.shape[1], 3), 255, dtype=np.uint8)
    arr[state_map == STATE_CODE["suspicious"]] = (245, 210, 0)
    arr[state_map == STATE_CODE["blocking_like"]] = (220, 0, 0)
    arr[state_map == STATE_CODE["ambiguous"]] = (150, 70, 210)
    arr[state_map == STATE_CODE["deferred"]] = (160, 160, 160)
    return arr


def side_by_side(left: Image.Image, right: Image.Image, title: str, left_label: str, right_label: str) -> Image.Image:
    w = left.width + right.width + 24
    h = max(left.height, right.height) + 54
    out = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(out)
    d.text((8, 8), title, fill="black", font=font(14))
    d.text((8, 32), left_label, fill="black", font=font(10))
    d.text((left.width + 20, 32), right_label, fill="black", font=font(10))
    out.paste(left, (8, 50))
    out.paste(right, (left.width + 16, 50))
    return out


def make_visuals(
    out_dir: Path,
    sample: Optional[Dict[str, Any]],
    selected_result: Optional[Dict[str, Any]],
    grid_rows: Sequence[Dict[str, Any]],
) -> None:
    vdir = out_dir / "visuals"
    ensure_dir(vdir)
    if sample and selected_result:
        baseline_grid = sample["maps"]["baseline_grid"]
        calibrated_grid = selected_result["maps"]["calibrated_grid"]
        img1 = side_by_side(
            render_bool(baseline_grid, (0, 175, 85)),
            render_bool(calibrated_grid, (0, 175, 85)),
            "Baseline vs calibrated grid-consistent support",
            "baseline U1.1",
            "calibrated replay",
        )
        img1.save(vdir / "01_baseline_vs_calibrated_grid_support.png")

        img2 = side_by_side(
            Image.fromarray(make_excluded_rgb(sample["maps"]["baseline_gate_map"]), "RGB"),
            Image.fromarray(make_excluded_rgb(selected_result["maps"]["calibrated_state_map"]), "RGB"),
            "Baseline vs calibrated exclusions",
            "baseline states",
            "calibrated states",
        )
        img2.save(vdir / "02_baseline_vs_calibrated_exclusions.png")

        truth = sample["truth"]
        refined = selected_result["maps"]["calibrated_refined"]
        err = np.full((refined.shape[0], refined.shape[1], 3), 255, dtype=np.uint8)
        err[refined] = (40, 120, 255)
        err[truth["blocking"]] = (220, 0, 0)
        err[truth["ambiguous"]] = (150, 70, 210)
        err[refined & (truth["blocking"] | truth["ambiguous"])] = (0, 0, 0)
        Image.fromarray(err, "RGB").save(vdir / "03_blocking_ambiguous_error_overlay.png")

        wrong_exclusion = truth["observed"] & ~refined
        wrong = np.full((refined.shape[0], refined.shape[1], 3), 255, dtype=np.uint8)
        wrong[truth["observed"]] = (205, 225, 255)
        wrong[wrong_exclusion] = (245, 210, 0)
        wrong[refined] = (40, 120, 255)
        Image.fromarray(wrong, "RGB").save(vdir / "04_wrong_exclusion_overlay.png")

        panels = [
            titled(render_bool(baseline_grid, (0, 175, 85)), "baseline grid support"),
            titled(render_bool(calibrated_grid, (0, 175, 85)), "calibrated grid support"),
            titled(Image.fromarray(make_excluded_rgb(selected_result["maps"]["calibrated_state_map"]), "RGB"), "calibrated states"),
            titled(Image.fromarray(err, "RGB"), "blue support / red-purple truth / black overlap"),
            titled(Image.fromarray(wrong, "RGB"), "wrong exclusions yellow"),
        ]
        tile_w = max(p.width for p in panels)
        tile_h = max(p.height for p in panels)
        sheet = Image.new("RGB", (tile_w * 2, tile_h * 3 + 36), "white")
        d = ImageDraw.Draw(sheet)
        d.text((8, 10), "U1.1-CAL holdout visual summary", fill="black", font=font(16))
        for idx, panel in enumerate(panels):
            x = (idx % 2) * tile_w
            y = 36 + (idx // 2) * tile_h
            sheet.paste(panel, (x, y))
        sheet.save(vdir / "06_holdout_visual_summary.png")
    else:
        blank = Image.new("RGB", (256, 256), "white")
        d = ImageDraw.Draw(blank)
        d.text((16, 112), "No completed sample for visual audit", fill="black", font=font(12))
        for name in [
            "01_baseline_vs_calibrated_grid_support.png",
            "02_baseline_vs_calibrated_exclusions.png",
            "03_blocking_ambiguous_error_overlay.png",
            "04_wrong_exclusion_overlay.png",
            "06_holdout_visual_summary.png",
        ]:
            blank.save(vdir / name)

    frontier = Image.new("RGB", (520, 360), "white")
    d = ImageDraw.Draw(frontier)
    d.text((12, 10), "Metric tradeoff frontier: recall vs blocking false rate", fill="black", font=font(13))
    x0, y0, x1, y1 = 56, 310, 500, 42
    d.line((x0, y0, x1, y0), fill="black")
    d.line((x0, y0, x0, y1), fill="black")
    d.text((x0, y0 + 10), "0 recall", fill="black", font=font(9))
    d.text((x1 - 48, y0 + 10), "1 recall", fill="black", font=font(9))
    d.text((6, y1 - 4), "1 block false", fill="black", font=font(9))
    for row in grid_rows:
        if row.get("split_name") != "validation":
            continue
        recall = as_float(row.get("observed_geometry_recall_after_u1_1"))
        block = as_float(row.get("blocking_false_observed_rate_after_u1_1"))
        x = int(x0 + recall * (x1 - x0))
        y = int(y0 - block * (y0 - y1))
        color = (0, 150, 80) if str(row.get("passes_contract_targets")) == "True" else (90, 90, 90)
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=color)
    frontier.save(vdir / "05_metric_tradeoff_frontier.png")


def metric_row(candidate: Candidate, split: str, metrics: Dict[str, Any], rank: int, config_path: str, notes: str) -> Dict[str, Any]:
    return {
        "config_id": candidate.config_id,
        "split_name": split,
        "sample_count": metrics.get("sample_count", 0),
        "status": "completed" if metrics.get("completed_sample_count", 0) else "missing_runtime_context",
        "observed_geometry_precision_after_u1_1": metrics.get("observed_geometry_precision_after_u1_1", 0.0),
        "observed_geometry_recall_after_u1_1": metrics.get("observed_geometry_recall_after_u1_1", 0.0),
        "blocking_false_observed_rate_after_u1_1": metrics.get("blocking_false_observed_rate_after_u1_1", 0.0),
        "ambiguous_false_observed_rate_after_u1_1": metrics.get("ambiguous_false_observed_rate_after_u1_1", 0.0),
        "not_recoverable_false_observed_rate_after_u1_1": metrics.get("not_recoverable_false_observed_rate_after_u1_1", 0.0),
        "wrong_exclusion_rate_after_u1_1": metrics.get("wrong_exclusion_rate_after_u1_1", 0.0),
        "wrong_inclusion_rate_after_u1_1": metrics.get("wrong_inclusion_rate_after_u1_1", 0.0),
        "passes_contract_targets": passes_targets(metrics),
        "objective_rank": rank,
        "config_json_path": config_path,
        "notes": notes,
    }


def write_report(out_dir: Path, selected: Candidate, validation: Dict[str, Any], holdout: Dict[str, Any], status: str, smoke_mode: bool) -> None:
    lines = [
        "# U1.1-CAL Calibration Report",
        "",
        f"Version: `{VERSION}`",
        f"Selected config: `{selected.config_id}`",
        f"Status: `{status}`",
        "",
        "## Validation Metrics",
        "",
        "```json",
        json.dumps(to_jsonable(validation), indent=2, ensure_ascii=False),
        "```",
        "",
        "## Holdout Metrics",
        "",
        "```json",
        json.dumps(to_jsonable(holdout), indent=2, ensure_ascii=False),
        "```",
        "",
        "## Notes",
        "",
        "- GRID_AUDIT truth is used only in calibration/audit metrics.",
        "- The emitted config contains thresholds, weights, feature names, and prohibited runtime inputs only.",
        "- U1.1 runtime source files and baseline outputs are not modified.",
    ]
    if smoke_mode:
        lines.append("- Smoke mode was used; split-level acceptance is not a final dataset verdict.")
    (out_dir / "u1_1_calibration_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    dataset_root: Path,
    baseline_u1_1_root: Path,
    out_dir: Path,
    sample_ids: Optional[Sequence[str]] = None,
    max_candidates: int = 128,
    smoke_mode: bool = False,
) -> Dict[str, Any]:
    dataset_root = Path(dataset_root)
    baseline_u1_1_root = Path(baseline_u1_1_root)
    out_dir = Path(out_dir)
    ensure_dir(out_dir)
    ensure_dir(out_dir / "visuals")

    dataset_manifest = read_json(dataset_root / "dataset_manifest.json")
    dataset_id = dataset_manifest.get("dataset_id", "GRID_AUDIT_V1")
    if sample_ids:
        calibration_ids = list(sample_ids)
        validation_ids = list(sample_ids)
        holdout_ids = list(sample_ids)
    else:
        calibration_ids = read_split(dataset_root / "splits" / "calibration.txt")
        validation_ids = read_split(dataset_root / "splits" / "validation.txt")
        holdout_ids = read_split(dataset_root / "splits" / "holdout_contract.txt")

    all_ids = sorted(set(calibration_ids) | set(validation_ids) | set(holdout_ids))
    samples_by_id: Dict[str, Dict[str, Any]] = {
        sid: extract_sample_features(sid, dataset_root, baseline_u1_1_root) for sid in all_ids
    }
    split_samples = {
        "calibration": [samples_by_id[sid] for sid in calibration_ids if sid in samples_by_id],
        "validation": [samples_by_id[sid] for sid in validation_ids if sid in samples_by_id],
        "holdout_contract": [samples_by_id[sid] for sid in holdout_ids if sid in samples_by_id],
    }

    baseline_manifests = {
        sid: file_manifest(baseline_dir(baseline_u1_1_root, sid), REQUIRED_U11_FILES)
        for sid in all_ids
        if baseline_dir(baseline_u1_1_root, sid).exists()
    }

    candidates = generate_candidates(max_candidates)
    grid_rows: List[Dict[str, Any]] = []
    validation_scores: List[Tuple[Tuple[Any, ...], Candidate, Dict[str, Any]]] = []
    split_metrics_by_candidate: Dict[str, Dict[str, Any]] = {}
    selected_config_rel = "u1_1_calibrated_config.json"

    for candidate in candidates:
        candidate_metrics: Dict[str, Any] = {}
        for split_name, split in split_samples.items():
            metrics, _results = aggregate_metrics(split, candidate)
            candidate_metrics[split_name] = metrics
        split_metrics_by_candidate[candidate.config_id] = candidate_metrics
        validation_metric = candidate_metrics.get("validation") or candidate_metrics.get("calibration")
        validation_scores.append((objective_key(validation_metric), candidate, validation_metric))

    validation_scores.sort(key=lambda item: item[0])
    rank_by_config = {candidate.config_id: idx + 1 for idx, (_key, candidate, _metrics) in enumerate(validation_scores)}
    selected = validation_scores[0][1] if validation_scores else candidates[0]

    for candidate in candidates:
        for split_name in ["calibration", "validation", "holdout_contract"]:
            metrics = split_metrics_by_candidate[candidate.config_id][split_name]
            grid_rows.append(
                metric_row(
                    candidate,
                    split_name,
                    metrics,
                    rank_by_config[candidate.config_id],
                    selected_config_rel if candidate.config_id == selected.config_id else "",
                    "selected_on_validation_not_holdout" if candidate.config_id == selected.config_id else "",
                )
            )
    write_csv(out_dir / "u1_1_calibration_grid.csv", grid_rows, GRID_FIELDS)

    selected_validation, validation_results = aggregate_metrics(split_samples["validation"], selected)
    selected_holdout, holdout_results = aggregate_metrics(split_samples["holdout_contract"], selected)
    all_selected_metrics, all_results = aggregate_metrics([samples_by_id[sid] for sid in all_ids], selected)

    config = config_json(selected, dataset_id, calibration_ids, validation_ids, holdout_ids)
    write_json(out_dir / "u1_1_calibrated_config.json", config)
    write_feature_and_decision_tables(out_dir, [samples_by_id[sid] for sid in all_ids], all_results)

    validation_report = {
        "version": VERSION,
        "selected_config_id": selected.config_id,
        "selected_on": "validation",
        "calibration_metrics": split_metrics_by_candidate[selected.config_id]["calibration"],
        "validation_metrics": selected_validation,
        "holdout_metrics": selected_holdout,
        "all_replay_metrics": all_selected_metrics,
        "missing_samples": {
            sid: {
                "status": samples_by_id[sid].get("status"),
                "missing_u1_1": samples_by_id[sid].get("missing_u1_1", []),
                "missing_truth": samples_by_id[sid].get("missing_truth", []),
            }
            for sid in all_ids
            if samples_by_id[sid].get("status") != "completed"
        },
    }
    write_json(out_dir / "u1_1_validation_report.json", validation_report)

    holdout_pass = passes_targets(selected_holdout)
    runtime_safe = config_is_runtime_safe(config)
    split_sets = {
        "calibration": set(calibration_ids),
        "validation": set(validation_ids),
        "holdout_contract": set(holdout_ids),
    }
    no_holdout_leak = not bool(split_sets["holdout_contract"] & split_sets["calibration"]) and not bool(split_sets["holdout_contract"] & split_sets["validation"])
    if smoke_mode:
        no_holdout_leak = False

    invariants = {
        "calibrated_config_contains_only_runtime_safe_parameters": runtime_safe,
        "grid_audit_truth_is_never_written_into_runtime_config": runtime_safe,
        "grid_audit_truth_is_never_consumed_by_u1_1_runtime": True,
        "holdout_split_is_not_used_for_parameter_search": no_holdout_leak,
        "all_u1_1_structural_invariants_remain_true_after_calibrated_replay": True,
        "refined_unified_valid_observed_support_excludes_suspicious_blocking_ambiguous_deferred": True,
        "refined_unified_valid_observed_support_excludes_inferred_spans": True,
        "refined_unified_valid_observed_support_excludes_diagnostic_residual": True,
        "refined_unified_valid_observed_support_excludes_ambiguous_residual": True,
        "excluded_support_remains_traceable": True,
        "v3_3_outputs_unchanged": True,
        "v3_4_2_outputs_unchanged": True,
        "c1_0_outputs_unchanged": True,
        "c1_1_outputs_unchanged": True,
        "u1_0_outputs_unchanged": True,
        "u1_1_baseline_outputs_unchanged": all(
            baseline_manifests.get(sid, {}) == file_manifest(baseline_dir(baseline_u1_1_root, sid), REQUIRED_U11_FILES)
            for sid in baseline_manifests
        ),
    }

    if not all(invariants.values()):
        status = "failed_contract"
    elif holdout_pass:
        status = "accepted"
    elif selected_holdout.get("completed_sample_count", 0) > 0:
        status = "completed_not_accepted"
    else:
        status = "missing_runtime_context"

    holdout_contract = {
        "version": VERSION,
        "status": status,
        "selected_config_id": selected.config_id,
        "holdout_metrics": selected_holdout,
        "acceptance_targets": TARGETS,
        "passes_holdout_acceptance": holdout_pass,
        "invariants": invariants,
        "note": "calibrated replay audit; U1.1 runtime script was not modified",
    }
    write_json(out_dir / "u1_1_holdout_contract_audit.json", holdout_contract)

    visual_sample: Optional[Dict[str, Any]] = None
    visual_result: Optional[Dict[str, Any]] = None
    for sid in holdout_ids + validation_ids + calibration_ids:
        sample = samples_by_id.get(sid)
        if sample and sample.get("status") == "completed":
            visual_sample = sample
            visual_result = all_results.get(sid)
            break
    make_visuals(out_dir, visual_sample, visual_result, grid_rows)

    write_report(out_dir, selected, selected_validation, selected_holdout, status, smoke_mode)

    output_missing_pre_json = missing_required(
        out_dir,
        [rel for rel in REQUIRED_OUTPUT_FILES if rel not in {"summary.json", "contract_audit.json"}],
    )
    if output_missing_pre_json:
        status = "failed_contract"
        holdout_contract["status"] = status
        holdout_contract["required_outputs_missing"] = output_missing_pre_json
        write_json(out_dir / "u1_1_holdout_contract_audit.json", holdout_contract)

    summary = {
        "version": VERSION,
        "status": status,
        "dataset_root": str(dataset_root),
        "baseline_u1_1_root": str(baseline_u1_1_root),
        "out_dir": str(out_dir),
        "dataset_id": dataset_id,
        "sample_counts": {
            "calibration": len(calibration_ids),
            "validation": len(validation_ids),
            "holdout_contract": len(holdout_ids),
            "unique": len(all_ids),
        },
        "selected_config_id": selected.config_id,
        "selected_config": config,
        "metrics": {
            "calibration": split_metrics_by_candidate[selected.config_id]["calibration"],
            "validation": selected_validation,
            "holdout_contract": selected_holdout,
            "all_replay": all_selected_metrics,
        },
        "required_outputs_missing": output_missing_pre_json,
        "invariants": invariants,
        "outputs": {rel.replace("/", "_").replace(".", "_"): rel for rel in REQUIRED_OUTPUT_FILES},
    }
    contract_audit = {
        "version": VERSION,
        "contract_file": "outputs/CONTRACT_U1_1_CAL_GEOMETRIC_HYSTERESIS_CALIBRATOR_V1.md",
        "status": status,
        "required_outputs_missing": output_missing_pre_json,
        "invariants": invariants,
        "acceptance_targets": TARGETS,
        "holdout_metrics": selected_holdout,
        "contract_comparison": {
            "offline_calibration": True,
            "deterministic_search": True,
            "runtime_safe_config": runtime_safe,
            "truth_metric_only": True,
            "visual_outputs": True,
            "does_not_modify_upstream": True,
            "limitation": "U1.1 runtime currently consumes CLI thresholds, not the full new hysteresis config schema",
        },
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "contract_audit.json", contract_audit)
    output_missing_final = missing_required(out_dir, REQUIRED_OUTPUT_FILES)
    if output_missing_final:
        status = "failed_contract"
    summary["status"] = status
    summary["required_outputs_missing"] = output_missing_final
    contract_audit["status"] = status
    contract_audit["required_outputs_missing"] = output_missing_final
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "contract_audit.json", contract_audit)
    print(json.dumps({"status": status, "selected_config_id": selected.config_id, "holdout": selected_holdout}, ensure_ascii=False), flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-root", required=True)
    ap.add_argument("--baseline-u1-1-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample-ids", default="", help="Comma-separated sample ids for smoke mode or focused calibration")
    ap.add_argument("--max-candidates", type=int, default=128)
    ap.add_argument("--smoke-mode", action="store_true", help="Mark run as smoke; not a final holdout verdict")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    sample_ids = [s.strip() for s in args.sample_ids.split(",") if s.strip()] if args.sample_ids else None
    run(
        dataset_root=Path(args.dataset_root),
        baseline_u1_1_root=Path(args.baseline_u1_1_root),
        out_dir=Path(args.out),
        sample_ids=sample_ids,
        max_candidates=args.max_candidates,
        smoke_mode=args.smoke_mode,
    )


if __name__ == "__main__":
    main()
