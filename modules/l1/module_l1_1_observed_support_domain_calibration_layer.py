#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module L1.1 - Observed Support Domain Calibration Layer.

L1.1 calibrates L1.0 domain labels over traceable observed support. It does
not create geometry, repair gaps, recognize text, or modify upstream outputs.
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


VERSION = "MODULE_L1_1_V1_OBSERVED_SUPPORT_DOMAIN_CALIBRATION_LAYER"

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

TRANSITION_KIND_CODE = {
    "unchanged": 0,
    "promoted_to_line_study": 1,
    "demoted_from_line_study": 2,
    "reserved_for_future_module": 3,
    "resolved_from_deferred": 4,
    "resolved_from_mixed": 5,
    "kept_deferred": 6,
    "kept_mixed": 7,
}

LINE_CLASSES = {"line_domain", "probable_line_domain"}
FUTURE_CLASSES = {"non_line_domain", "probable_non_line_domain", "mixed_domain", "deferred_domain"}

REGION_FIELDS = [
    "calibrated_domain_region_id",
    "source_l1_0_domain_region_id",
    "source_u1_1_region_id",
    "source_geometry_object_id",
    "source_l1_0_domain_class",
    "calibrated_l1_1_domain_class",
    "calibrated_domain_subclass",
    "transition_kind",
    "transition_confidence",
    "excluded_from_calibrated_line_study",
    "available_for_future_modules",
    "region_pixel_count",
    "orientation",
    "elongation_score",
    "longitudinal_continuity_score",
    "width_stability_score",
    "parallel_family_score",
    "grid_context_score",
    "colinearity_score",
    "microstructure_score",
    "line_context_score",
    "non_line_context_score",
    "mixed_contact_score",
    "transition_reason",
]

MEMBERSHIP_FIELDS = [
    "calibrated_domain_region_id",
    "source_l1_0_domain_region_id",
    "source_u1_1_region_id",
    "source_geometry_object_id",
    "x",
    "y",
    "source_l1_0_domain_class",
    "calibrated_l1_1_domain_class",
    "calibrated_domain_subclass",
    "transition_kind",
    "transition_confidence",
    "excluded_from_calibrated_line_study",
    "available_for_future_modules",
    "membership_weight",
]

TRANSITION_FIELDS = [
    "transition_id",
    "calibrated_domain_region_id",
    "source_l1_0_domain_region_id",
    "source_l1_0_domain_class",
    "calibrated_l1_1_domain_class",
    "transition_kind",
    "transition_confidence",
    "pixel_count",
    "support_subset_of_l1_0_observed_support",
    "line_study_transition_allowed",
    "future_pool_transition_allowed",
    "transition_reason",
]

VALIDATION_FIELDS = [
    "calibrated_domain_region_id",
    "source_l1_0_domain_region_id",
    "source_l1_0_domain_class",
    "calibrated_l1_1_domain_class",
    "support_subset_of_l1_0_observed_support",
    "calibrated_line_study_excludes_non_line_mixed_deferred",
    "calibrated_future_pool_preserves_non_line_mixed_deferred",
    "transition_preserves_source_traceability",
    "no_semantic_recognition_used",
    "does_not_create_geometry",
    "does_not_delete_support",
    "does_not_modify_upstream",
    "validation_reason",
    "rejection_or_deferral_reason",
]

REQUIRED_L10_FILES = [
    "summary.json",
    "contract_audit.json",
    "l1_0_domain_regions.csv",
    "l1_0_domain_memberships.csv",
    "l1_0_domain_validation.csv",
    "l1_0_line_study_support.csv",
    "l1_0_future_module_pool.csv",
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
]

REQUIRED_U11_FILES = [
    "summary.json",
    "contract_audit.json",
    "u1_1_subobject_regions.csv",
    "u1_1_subobject_memberships.csv",
    "maps/u1_1_subobject_region_id_map.npy",
    "maps/refined_unified_valid_observed_support_map.npy",
]

REQUIRED_V33_FILES = [
    "summary.json",
    "geometry_objects.csv",
    "pixel_geometry_memberships.csv",
    "maps/combined_geometry_support_count_map.npy",
]

REQUIRED_OUTPUT_FILES = [
    "l1_1_calibrated_domain_regions.csv",
    "l1_1_calibrated_domain_memberships.csv",
    "l1_1_domain_transitions.csv",
    "l1_1_domain_validation.csv",
    "l1_1_calibrated_line_study_support.csv",
    "l1_1_calibrated_future_module_pool.csv",
    "l1_1_promoted_to_line_study.csv",
    "l1_1_demoted_from_line_study.csv",
    "l1_1_kept_deferred_or_mixed.csv",
    "summary.json",
    "contract_audit.json",
    "maps/calibrated_line_domain_support_map.npy",
    "maps/calibrated_probable_line_domain_support_map.npy",
    "maps/calibrated_non_line_domain_support_map.npy",
    "maps/calibrated_probable_non_line_domain_support_map.npy",
    "maps/calibrated_mixed_domain_support_map.npy",
    "maps/calibrated_deferred_domain_support_map.npy",
    "maps/calibrated_line_study_support_map.npy",
    "maps/calibrated_future_module_pool_map.npy",
    "maps/l1_1_calibrated_domain_region_id_map.npy",
    "maps/l1_1_calibrated_domain_class_map.npy",
    "maps/l1_1_transition_kind_map.npy",
    "maps/l1_1_transition_confidence_map.npy",
    "visuals/01_l1_0_input_domain_summary.png",
    "visuals/02_l1_1_calibrated_domains.png",
    "visuals/03_promoted_to_line_study.png",
    "visuals/04_demoted_from_line_study.png",
    "visuals/05_calibrated_line_study_support.png",
    "visuals/06_calibrated_future_module_pool.png",
    "visuals/07_l1_0_vs_l1_1_comparison.png",
    "visuals/08_l1_1_audit_summary.png",
]


@dataclass
class Config:
    version: str = VERSION
    neighborhood_px: int = 2
    min_promotion_line_score: float = 0.67
    min_promotion_line_context: float = 0.48
    max_promotion_microstructure: float = 0.52
    max_promotion_conflict_contact: float = 0.30
    min_promotion_continuity: float = 0.24
    min_promotion_width_stability: float = 0.32
    min_demotion_non_line_score: float = 0.70
    max_demotion_line_context: float = 0.46
    min_demotion_microstructure: float = 0.64
    min_resolve_non_line_score: float = 0.67
    min_region_pixels: int = 2


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


def load_map(path: Path, dtype: Optional[Any] = None) -> np.ndarray:
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


def bbox(points: Sequence[Tuple[int, int]]) -> Tuple[int, int, int, int]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def profile_features(points: Sequence[Tuple[int, int]], orientation: str) -> Dict[str, float]:
    if not points:
        return {
            "bounding_box_width": 0.0,
            "bounding_box_height": 0.0,
            "orientation_stability_score": 0.0,
            "longitudinal_run_length": 0.0,
            "local_fill_score": 0.0,
            "compact_mark_score": 0.0,
        }
    x0, y0, x1, y1 = bbox(points)
    w = x1 - x0 + 1
    h = y1 - y0 + 1
    long_len = max(w, h)
    short_len = max(1, min(w, h))
    orientation_stability = clamp01(1.0 - short_len / max(long_len, 1))
    if orientation == "vertical":
        longs = {y for _, y in points}
    else:
        longs = {x for x, _ in points}
    area = max(1, w * h)
    fill = ratio(len(set(points)), area)
    compact_mark = clamp01((1.0 - orientation_stability) * 0.55 + fill * 0.45)
    return {
        "bounding_box_width": float(w),
        "bounding_box_height": float(h),
        "orientation_stability_score": float(orientation_stability),
        "longitudinal_run_length": float(len(longs)),
        "local_fill_score": float(fill),
        "compact_mark_score": float(compact_mark),
    }


def class_map_to_rgb(class_map: np.ndarray) -> Image.Image:
    arr = np.full((class_map.shape[0], class_map.shape[1], 3), 255, dtype=np.uint8)
    arr[class_map == DOMAIN_CODE["line_domain"]] = (38, 122, 255)
    arr[class_map == DOMAIN_CODE["probable_line_domain"]] = (0, 185, 210)
    arr[class_map == DOMAIN_CODE["non_line_domain"]] = (220, 0, 0)
    arr[class_map == DOMAIN_CODE["probable_non_line_domain"]] = (255, 160, 0)
    arr[class_map == DOMAIN_CODE["mixed_domain"]] = (150, 70, 210)
    arr[class_map == DOMAIN_CODE["deferred_domain"]] = (160, 160, 160)
    return Image.fromarray(arr, "RGB")


def load_region_points(l10_dir: Path, l10_region_map: np.ndarray) -> Tuple[Dict[int, List[Tuple[int, int]]], Dict[int, Dict[Tuple[int, int], float]], Dict[int, List[Dict[str, str]]]]:
    points: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    weights: Dict[int, Dict[Tuple[int, int], float]] = defaultdict(dict)
    source_rows: Dict[int, List[Dict[str, str]]] = defaultdict(list)
    for row in read_csv(l10_dir / "l1_0_domain_memberships.csv"):
        rid = as_int(row.get("domain_region_id"))
        x, y = as_int(row.get("x")), as_int(row.get("y"))
        if rid and 0 <= y < l10_region_map.shape[0] and 0 <= x < l10_region_map.shape[1]:
            points[rid].append((x, y))
            weights[rid][(x, y)] = as_float(row.get("membership_weight"), 1.0)
            source_rows[rid].append(row)
    for rid in np.unique(l10_region_map):
        rid_i = int(rid)
        if rid_i <= 0 or points.get(rid_i):
            continue
        ys, xs = np.where(l10_region_map == rid_i)
        for y, x in zip(ys, xs):
            points[rid_i].append((int(x), int(y)))
            weights[rid_i][(int(x), int(y))] = 1.0
    return points, weights, source_rows


def compute_features(
    l10_region: Dict[str, str],
    points: Sequence[Tuple[int, int]],
    l10_line_near: np.ndarray,
    l10_future_near: np.ndarray,
    v33_support_near: np.ndarray,
    diagnostic_near: np.ndarray,
    blocking_near: np.ndarray,
) -> Dict[str, float]:
    orientation = l10_region.get("orientation", "horizontal")
    if orientation not in {"horizontal", "vertical"}:
        orientation = "horizontal"
    prof = profile_features(points, orientation)
    count = len(set(points))
    line_neighbor = ratio(sum(1 for x, y in set(points) if l10_line_near[y, x]), count)
    future_neighbor = ratio(sum(1 for x, y in set(points) if l10_future_near[y, x]), count)
    v33_neighbor = ratio(sum(1 for x, y in set(points) if v33_support_near[y, x]), count)
    diagnostic_contact = ratio(sum(1 for x, y in set(points) if diagnostic_near[y, x]), count)
    blocking_contact = ratio(sum(1 for x, y in set(points) if blocking_near[y, x]), count)

    elongation = as_float(l10_region.get("elongation_score"))
    continuity = as_float(l10_region.get("longitudinal_continuity_score"))
    width_stability = as_float(l10_region.get("width_stability_score"))
    parallel = as_float(l10_region.get("parallel_family_score"))
    grid = as_float(l10_region.get("grid_context_score"))
    text_like = as_float(l10_region.get("text_like_score"))
    symbol_like = as_float(l10_region.get("symbol_like_score"))
    complexity = as_float(l10_region.get("curvature_or_complexity_score"))
    short_mark = as_float(l10_region.get("short_mark_score"))
    mixed = as_float(l10_region.get("mixed_contact_score"))
    colinearity = clamp01(max(line_neighbor, v33_neighbor * 0.55, parallel, grid))
    microstructure = clamp01(max(text_like, symbol_like, 0.72 * complexity + 0.28 * prof["compact_mark_score"], short_mark * 0.85))
    line_context = clamp01(max(parallel, grid, colinearity, line_neighbor))
    non_line_context = clamp01(max(microstructure, future_neighbor * 0.70, diagnostic_contact * 0.70, mixed * 0.65))
    conflict_contact = clamp01(max(diagnostic_contact, blocking_contact))
    line_score = clamp01(
        0.22 * elongation
        + 0.18 * continuity
        + 0.13 * width_stability
        + 0.27 * line_context
        + 0.12 * prof["orientation_stability_score"]
        + 0.08 * (1.0 - microstructure)
    )
    non_line_score = clamp01(
        0.36 * microstructure
        + 0.18 * future_neighbor
        + 0.16 * conflict_contact
        + 0.12 * mixed
        + 0.10 * (1.0 - line_context)
        + 0.08 * prof["compact_mark_score"]
    )
    return {
        "region_pixel_count": float(count),
        "orientation": orientation,
        "bounding_box_width": prof["bounding_box_width"],
        "bounding_box_height": prof["bounding_box_height"],
        "orientation_stability_score": prof["orientation_stability_score"],
        "longitudinal_run_length": prof["longitudinal_run_length"],
        "elongation_score": elongation,
        "longitudinal_continuity_score": continuity,
        "width_stability_score": width_stability,
        "parallel_family_score": parallel,
        "grid_context_score": grid,
        "colinearity_score": colinearity,
        "microstructure_score": microstructure,
        "compact_mark_score": prof["compact_mark_score"],
        "curvature_or_complexity_score": complexity,
        "mixed_contact_score": mixed,
        "local_line_study_neighbor_ratio": line_neighbor,
        "local_future_pool_neighbor_ratio": future_neighbor,
        "diagnostic_residual_contact_score": diagnostic_contact,
        "blocking_residual_contact_score": blocking_contact,
        "line_context_score": line_context,
        "non_line_context_score": non_line_context,
        "line_score": line_score,
        "non_line_score": non_line_score,
    }


def calibrate_domain(source_class: str, source_subclass: str, features: Dict[str, float], cfg: Config) -> Tuple[str, str, str, float, str]:
    count = int(features["region_pixel_count"])
    line_score = features["line_score"]
    non_line_score = features["non_line_score"]
    line_context = features["line_context_score"]
    micro = features["microstructure_score"]
    conflict = max(features["diagnostic_residual_contact_score"], features["blocking_residual_contact_score"])
    continuity = features["longitudinal_continuity_score"]
    width_stability = features["width_stability_score"]
    mixed = features["mixed_contact_score"]
    confidence = clamp01(abs(line_score - non_line_score) + 0.35 * max(line_context, micro))

    if count < cfg.min_region_pixels:
        return "deferred_domain", "ambiguous_domain", "kept_deferred", max(0.35, confidence), "too_few_traceable_pixels"

    if source_class in LINE_CLASSES:
        demotion_evidence = (
            non_line_score >= cfg.min_demotion_non_line_score
            and micro >= cfg.min_demotion_microstructure
            and line_context <= cfg.max_demotion_line_context
        )
        conflict_evidence = conflict >= 0.42 and line_context <= 0.56
        mixed_evidence = mixed >= 0.62 and micro >= 0.58 and line_context >= 0.36
        if mixed_evidence:
            return "mixed_domain", "mixed_line_microstructure_contact", "demoted_from_line_study", max(0.55, confidence), "line_domain_contacts_mixed_microstructure"
        if demotion_evidence or conflict_evidence:
            return "probable_non_line_domain", "character_like_microstructure", "demoted_from_line_study", max(0.55, confidence), "line_study_support_has_strong_non_line_microstructure"
        return source_class, source_subclass or "structural_line", "unchanged", max(0.45, line_score), "line_study_domain_retained_by_geometric_context"

    promotion_allowed_source = source_class in {"probable_non_line_domain", "deferred_domain"}
    promotion_evidence = (
        promotion_allowed_source
        and line_score >= cfg.min_promotion_line_score
        and line_context >= cfg.min_promotion_line_context
        and micro <= cfg.max_promotion_microstructure
        and conflict <= cfg.max_promotion_conflict_contact
        and continuity >= cfg.min_promotion_continuity
        and width_stability >= cfg.min_promotion_width_stability
    )
    if promotion_evidence:
        if source_class == "deferred_domain":
            transition_kind = "resolved_from_deferred"
        else:
            transition_kind = "promoted_to_line_study"
        return "probable_line_domain", "line_fragment", transition_kind, max(0.55, confidence), "traceable_colinear_context_supports_line_study_promotion"

    if source_class == "mixed_domain" and line_score >= cfg.min_promotion_line_score and line_context >= cfg.min_promotion_line_context:
        return "mixed_domain", "mixed_line_microstructure_contact", "kept_mixed", max(0.45, confidence), "mixed_line_like_support_not_promoted_without_safe_subsupport_separation"

    resolve_non_line = (
        source_class in {"mixed_domain", "deferred_domain", "probable_non_line_domain"}
        and non_line_score >= cfg.min_resolve_non_line_score
        and (line_context < 0.54 or micro >= 0.70)
    )
    if resolve_non_line:
        if source_class == "mixed_domain":
            return "probable_non_line_domain", "unknown_non_line", "resolved_from_mixed", max(0.52, confidence), "mixed_support_resolved_to_future_pool_by_microstructure"
        if source_class == "deferred_domain":
            return "probable_non_line_domain", "unknown_non_line", "resolved_from_deferred", max(0.52, confidence), "deferred_support_resolved_to_future_pool_by_microstructure"
        return source_class, source_subclass or "unknown_non_line", "reserved_for_future_module", max(0.45, non_line_score), "future_pool_domain_retained"

    if source_class == "mixed_domain":
        return "mixed_domain", "mixed_line_microstructure_contact", "kept_mixed", max(0.40, confidence), "mixed_domain_not_safely_resolved"
    if source_class == "deferred_domain":
        return "deferred_domain", "ambiguous_domain", "kept_deferred", max(0.40, confidence), "deferred_domain_insufficient_context"
    if source_class in FUTURE_CLASSES:
        return source_class, source_subclass or "unknown_non_line", "reserved_for_future_module", max(0.40, non_line_score), "future_pool_domain_retained"
    return "deferred_domain", "ambiguous_domain", "kept_deferred", max(0.35, confidence), "unknown_source_domain_deferred"


def make_visuals(
    out_dir: Path,
    l10_class_map: np.ndarray,
    cal_class_map: np.ndarray,
    promoted_map: np.ndarray,
    demoted_map: np.ndarray,
    line_study_map: np.ndarray,
    future_pool_map: np.ndarray,
    l10_line_study_map: np.ndarray,
    l10_future_pool_map: np.ndarray,
) -> None:
    vdir = out_dir / "visuals"
    ensure_dir(vdir)

    l10_img = class_map_to_rgb(l10_class_map)
    cal_img = class_map_to_rgb(cal_class_map)
    l10_img.save(vdir / "01_l1_0_input_domain_summary.png")
    cal_img.save(vdir / "02_l1_1_calibrated_domains.png")
    render_bool(promoted_map, (255, 220, 0)).save(vdir / "03_promoted_to_line_study.png")
    render_bool(demoted_map, (130, 0, 0)).save(vdir / "04_demoted_from_line_study.png")
    render_bool(line_study_map, (0, 175, 85)).save(vdir / "05_calibrated_line_study_support.png")
    render_bool(future_pool_map, (210, 0, 210)).save(vdir / "06_calibrated_future_module_pool.png")

    panels = [
        titled(l10_img, "L1.0 input domains"),
        titled(cal_img, "L1.1 calibrated domains"),
        titled(render_bool(l10_line_study_map, (0, 140, 80)), "L1.0 line-study"),
        titled(render_bool(line_study_map, (0, 175, 85)), "L1.1 line-study"),
        titled(render_bool(l10_future_pool_map, (180, 0, 180)), "L1.0 future pool"),
        titled(render_bool(future_pool_map, (210, 0, 210)), "L1.1 future pool"),
        titled(render_bool(promoted_map, (255, 220, 0)), "promoted to line-study"),
        titled(render_bool(demoted_map, (130, 0, 0)), "demoted from line-study"),
    ]
    tile_w = max(p.width for p in panels)
    tile_h = max(p.height for p in panels)
    sheet = Image.new("RGB", (tile_w * 4, tile_h * 2 + 38), "white")
    d = ImageDraw.Draw(sheet)
    d.text((8, 10), "L1.1 observed support domain calibration", fill="black", font=font(16))
    for idx, panel in enumerate(panels):
        x = (idx % 4) * tile_w
        y = 38 + (idx // 4) * tile_h
        sheet.paste(panel, (x, y))
    sheet.save(vdir / "07_l1_0_vs_l1_1_comparison.png")

    audit_panels = [
        titled(l10_img, "source L1.0"),
        titled(cal_img, "calibrated L1.1"),
        titled(render_bool(promoted_map, (255, 220, 0)), "yellow promotions"),
        titled(render_bool(demoted_map, (130, 0, 0)), "dark red demotions"),
        titled(render_bool(line_study_map, (0, 175, 85)), "calibrated line-study"),
        titled(render_bool(future_pool_map, (210, 0, 210)), "calibrated future pool"),
    ]
    audit = Image.new("RGB", (tile_w * 3, tile_h * 2 + 38), "white")
    d = ImageDraw.Draw(audit)
    d.text((8, 10), "L1.1 audit summary: calibration, not final geometry", fill="black", font=font(16))
    for idx, panel in enumerate(audit_panels):
        x = (idx % 3) * tile_w
        y = 38 + (idx // 3) * tile_h
        audit.paste(panel, (x, y))
    audit.save(vdir / "08_l1_1_audit_summary.png")


def run(
    l10_dir: Path,
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
    l10_dir = Path(l10_dir)
    u11_dir = Path(u11_dir)
    v33_dir = Path(v33_dir)
    out_dir = Path(out_dir)
    v342_dir = Path(v342_dir) if v342_dir else None
    c10_dir = Path(c10_dir) if c10_dir else None
    c11_dir = Path(c11_dir) if c11_dir else None
    u10_dir = Path(u10_dir) if u10_dir else None

    missing_inputs = {
        "l1_0": missing_required(l10_dir, REQUIRED_L10_FILES),
        "u1_1": missing_required(u11_dir, REQUIRED_U11_FILES),
        "v3_3": missing_required(v33_dir, REQUIRED_V33_FILES),
    }
    absent = [f"{group}:{rel}" for group, rels in missing_inputs.items() for rel in rels]
    if absent:
        raise FileNotFoundError("Missing required L1.1 input files: " + ", ".join(absent))

    source_manifest_before = {
        "l1_0": file_manifest(l10_dir, REQUIRED_L10_FILES),
        "u1_1": file_manifest(u11_dir, REQUIRED_U11_FILES),
        "v3_3": file_manifest(v33_dir, REQUIRED_V33_FILES),
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

    l10_summary = read_json(l10_dir / "summary.json")
    u11_summary = read_json(u11_dir / "summary.json")
    v33_summary = read_json(v33_dir / "summary.json")
    l10_regions = {as_int(row.get("domain_region_id")): row for row in read_csv(l10_dir / "l1_0_domain_regions.csv")}

    l10_region_map = load_map(l10_dir / "maps" / "l1_0_domain_region_id_map.npy", np.int32)
    l10_class_map = load_map(l10_dir / "maps" / "l1_0_domain_class_map.npy", np.uint8)
    l10_line_study_map = load_map(l10_dir / "maps" / "line_study_support_map.npy", np.uint16) > 0
    l10_future_pool_map = load_map(l10_dir / "maps" / "future_module_pool_map.npy", np.uint16) > 0
    u11_refined = load_map(u11_dir / "maps" / "refined_unified_valid_observed_support_map.npy", np.uint16) > 0
    v33_support = load_map(v33_dir / "maps" / "combined_geometry_support_count_map.npy", np.uint16) > 0
    shape = l10_class_map.shape
    l10_observed_support = l10_class_map > 0

    diagnostic = optional_map(v342_dir / "maps" / "diagnostic_residual_support_count_map.npy" if v342_dir else None, shape, np.uint16) > 0
    c10_rejected = optional_map(c10_dir / "maps" / "rejected_residual_support_map.npy" if c10_dir else None, shape, np.uint16) > 0
    c11_blocking = optional_map(c11_dir / "maps" / "collective_blocking_evidence_map.npy" if c11_dir else None, shape, np.uint16) > 0
    u11_ambiguous = optional_map(u11_dir / "maps" / "ambiguous_subsupport_map.npy", shape, np.uint16) > 0

    l10_line_near = dilate(l10_line_study_map, cfg.neighborhood_px)
    l10_future_near = dilate(l10_future_pool_map, cfg.neighborhood_px)
    v33_support_near = dilate(v33_support, cfg.neighborhood_px)
    diagnostic_near = dilate(diagnostic, cfg.neighborhood_px)
    blocking_near = dilate(c10_rejected | c11_blocking, cfg.neighborhood_px)

    points_by_region, weights_by_region, _source_rows = load_region_points(l10_dir, l10_region_map)

    cal_class_map = np.zeros(shape, dtype=np.uint8)
    cal_region_id_map = np.zeros(shape, dtype=np.int32)
    transition_kind_map = np.zeros(shape, dtype=np.uint8)
    transition_confidence_map = np.zeros(shape, dtype=np.float32)
    promoted_map = np.zeros(shape, dtype=bool)
    demoted_map = np.zeros(shape, dtype=bool)
    kept_deferred_map = np.zeros(shape, dtype=bool)
    kept_mixed_map = np.zeros(shape, dtype=bool)

    region_rows: List[Dict[str, Any]] = []
    membership_rows: List[Dict[str, Any]] = []
    transition_rows: List[Dict[str, Any]] = []
    validation_rows: List[Dict[str, Any]] = []

    for idx, source_region_id in enumerate(sorted(points_by_region), start=1):
        source_region = l10_regions.get(source_region_id, {})
        points = sorted(set(points_by_region[source_region_id]), key=lambda p: (p[1], p[0]))
        source_class = source_region.get("domain_class", "deferred_domain")
        source_subclass = source_region.get("domain_subclass", "")
        source_u11_id = as_int(source_region.get("source_u1_1_region_id"))
        source_gid = str(source_region.get("source_geometry_object_id", ""))
        features = compute_features(
            source_region,
            points,
            l10_line_near,
            l10_future_near,
            v33_support_near,
            diagnostic_near,
            blocking_near,
        )
        calibrated_class, subclass, transition_kind, confidence, reason = calibrate_domain(source_class, source_subclass, features, cfg)
        excluded_from_line = calibrated_class not in LINE_CLASSES
        available_future = calibrated_class in FUTURE_CLASSES
        is_promoted = source_class not in LINE_CLASSES and calibrated_class in LINE_CLASSES
        is_demoted = source_class in LINE_CLASSES and calibrated_class in FUTURE_CLASSES
        is_kept_deferred = source_class == "deferred_domain" and calibrated_class == "deferred_domain"
        is_kept_mixed = source_class == "mixed_domain" and calibrated_class == "mixed_domain"

        region_row = {
            "calibrated_domain_region_id": idx,
            "source_l1_0_domain_region_id": source_region_id,
            "source_u1_1_region_id": source_u11_id,
            "source_geometry_object_id": source_gid,
            "source_l1_0_domain_class": source_class,
            "calibrated_l1_1_domain_class": calibrated_class,
            "calibrated_domain_subclass": subclass,
            "transition_kind": transition_kind,
            "transition_confidence": confidence,
            "excluded_from_calibrated_line_study": excluded_from_line,
            "available_for_future_modules": available_future,
            "region_pixel_count": int(features["region_pixel_count"]),
            "orientation": features["orientation"],
            "elongation_score": features["elongation_score"],
            "longitudinal_continuity_score": features["longitudinal_continuity_score"],
            "width_stability_score": features["width_stability_score"],
            "parallel_family_score": features["parallel_family_score"],
            "grid_context_score": features["grid_context_score"],
            "colinearity_score": features["colinearity_score"],
            "microstructure_score": features["microstructure_score"],
            "line_context_score": features["line_context_score"],
            "non_line_context_score": features["non_line_context_score"],
            "mixed_contact_score": features["mixed_contact_score"],
            "transition_reason": reason,
        }
        region_rows.append(region_row)

        support_subset = all(0 <= y < shape[0] and 0 <= x < shape[1] and l10_observed_support[y, x] for x, y in points)
        transition_rows.append(
            {
                "transition_id": idx,
                "calibrated_domain_region_id": idx,
                "source_l1_0_domain_region_id": source_region_id,
                "source_l1_0_domain_class": source_class,
                "calibrated_l1_1_domain_class": calibrated_class,
                "transition_kind": transition_kind,
                "transition_confidence": confidence,
                "pixel_count": len(points),
                "support_subset_of_l1_0_observed_support": support_subset,
                "line_study_transition_allowed": calibrated_class in LINE_CLASSES,
                "future_pool_transition_allowed": calibrated_class in FUTURE_CLASSES,
                "transition_reason": reason,
            }
        )
        validation_rows.append(
            {
                "calibrated_domain_region_id": idx,
                "source_l1_0_domain_region_id": source_region_id,
                "source_l1_0_domain_class": source_class,
                "calibrated_l1_1_domain_class": calibrated_class,
                "support_subset_of_l1_0_observed_support": support_subset,
                "calibrated_line_study_excludes_non_line_mixed_deferred": calibrated_class in LINE_CLASSES or excluded_from_line,
                "calibrated_future_pool_preserves_non_line_mixed_deferred": calibrated_class in LINE_CLASSES or available_future,
                "transition_preserves_source_traceability": bool(source_region_id and source_class and "source_u1_1_region_id" in source_region and "source_geometry_object_id" in source_region),
                "no_semantic_recognition_used": True,
                "does_not_create_geometry": True,
                "does_not_delete_support": True,
                "does_not_modify_upstream": True,
                "validation_reason": "calibration_from_traceable_geometric_domain_features",
                "rejection_or_deferral_reason": "" if calibrated_class in LINE_CLASSES else reason,
            }
        )

        for x, y in points:
            old_code = int(cal_class_map[y, x])
            old_class = next((name for name, code in DOMAIN_CODE.items() if code == old_code), "")
            if not old_class or DOMAIN_PRIORITY[calibrated_class] > DOMAIN_PRIORITY[old_class]:
                cal_class_map[y, x] = DOMAIN_CODE[calibrated_class]
                cal_region_id_map[y, x] = idx
                transition_kind_map[y, x] = TRANSITION_KIND_CODE[transition_kind]
                transition_confidence_map[y, x] = float(confidence)
            if is_promoted:
                promoted_map[y, x] = True
            if is_demoted:
                demoted_map[y, x] = True
            if is_kept_deferred:
                kept_deferred_map[y, x] = True
            if is_kept_mixed:
                kept_mixed_map[y, x] = True

            membership_rows.append(
                {
                    "calibrated_domain_region_id": idx,
                    "source_l1_0_domain_region_id": source_region_id,
                    "source_u1_1_region_id": source_u11_id,
                    "source_geometry_object_id": source_gid,
                    "x": x,
                    "y": y,
                    "source_l1_0_domain_class": source_class,
                    "calibrated_l1_1_domain_class": calibrated_class,
                    "calibrated_domain_subclass": subclass,
                    "transition_kind": transition_kind,
                    "transition_confidence": confidence,
                    "excluded_from_calibrated_line_study": excluded_from_line,
                    "available_for_future_modules": available_future,
                    "membership_weight": weights_by_region[source_region_id].get((x, y), 1.0),
                }
            )

    cal_line_domain = cal_class_map == DOMAIN_CODE["line_domain"]
    cal_prob_line = cal_class_map == DOMAIN_CODE["probable_line_domain"]
    cal_non_line = cal_class_map == DOMAIN_CODE["non_line_domain"]
    cal_prob_non_line = cal_class_map == DOMAIN_CODE["probable_non_line_domain"]
    cal_mixed = cal_class_map == DOMAIN_CODE["mixed_domain"]
    cal_deferred = cal_class_map == DOMAIN_CODE["deferred_domain"]
    cal_future_pool = cal_non_line | cal_prob_non_line | cal_mixed | cal_deferred
    cal_line_study = (cal_line_domain | cal_prob_line) & u11_refined & ~diagnostic & ~u11_ambiguous

    state_maps = [cal_line_domain, cal_prob_line, cal_non_line, cal_prob_non_line, cal_mixed, cal_deferred]
    overlap = np.zeros(shape, dtype=np.uint8)
    for m in state_maps:
        overlap += m.astype(np.uint8)

    source_manifest_after = {
        "l1_0": file_manifest(l10_dir, REQUIRED_L10_FILES),
        "u1_1": file_manifest(u11_dir, REQUIRED_U11_FILES),
        "v3_3": file_manifest(v33_dir, REQUIRED_V33_FILES),
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
        if str(r["calibrated_l1_1_domain_class"]) in FUTURE_CLASSES
    }
    future_pixel_set = set(zip(np.where(cal_future_pool)[1].tolist(), np.where(cal_future_pool)[0].tolist()))
    promoted_pixel_set = set(zip(np.where(promoted_map)[1].tolist(), np.where(promoted_map)[0].tolist()))
    demoted_pixel_set = set(zip(np.where(demoted_map)[1].tolist(), np.where(demoted_map)[0].tolist()))

    invariants = {
        "calibrated_line_domain_support_subset_of_l1_0_observed_support": bool(np.all(~cal_line_domain | l10_observed_support)),
        "calibrated_probable_line_domain_support_subset_of_l1_0_observed_support": bool(np.all(~cal_prob_line | l10_observed_support)),
        "calibrated_non_line_domain_support_subset_of_l1_0_observed_support": bool(np.all(~cal_non_line | l10_observed_support)),
        "calibrated_probable_non_line_domain_support_subset_of_l1_0_observed_support": bool(np.all(~cal_prob_non_line | l10_observed_support)),
        "calibrated_mixed_domain_support_subset_of_l1_0_observed_support": bool(np.all(~cal_mixed | l10_observed_support)),
        "calibrated_deferred_domain_support_subset_of_l1_0_observed_support": bool(np.all(~cal_deferred | l10_observed_support)),
        "all_l1_1_calibrated_domain_maps_are_mutually_exclusive": bool(np.all(overlap <= 1)),
        "calibrated_line_study_support_excludes_non_line_probable_non_line_mixed_deferred": not bool(np.any(cal_line_study & cal_future_pool)),
        "calibrated_future_module_pool_includes_non_line_probable_non_line_mixed_deferred": bool(np.all((cal_non_line | cal_prob_non_line | cal_mixed | cal_deferred) <= cal_future_pool)),
        "calibrated_future_module_pool_preserves_traceability": future_pixel_set.issubset(membership_pixel_set) and future_pixel_set.issubset(future_membership_set),
        "all_transitions_preserve_source_l1_0_class": all(str(r.get("source_l1_0_domain_class", "")) in DOMAIN_CLASSES for r in region_rows),
        "all_transitions_preserve_source_u1_1_region_id_when_available": all("source_u1_1_region_id" in r for r in region_rows),
        "all_transitions_preserve_source_geometry_object_id_when_available": all("source_geometry_object_id" in r for r in region_rows),
        "demoted_support_is_not_deleted": demoted_pixel_set.issubset(future_pixel_set),
        "promoted_support_remains_traceable_to_l1_0_observed_support": promoted_pixel_set.issubset(membership_pixel_set) and all(l10_observed_support[y, x] for x, y in promoted_pixel_set),
        "mixed_support_is_not_silently_counted_as_clean_line": not bool(np.any(cal_mixed & cal_line_study)),
        "deferred_support_is_not_silently_counted_as_clean_line": not bool(np.any(cal_deferred & cal_line_study)),
        "inferred_spans_are_not_converted_to_observed_support": True,
        "diagnostic_residual_is_not_converted_to_line_study_support": not bool(np.any(cal_line_study & diagnostic)),
        "ambiguous_residual_is_not_converted_to_line_study_support": not bool(np.any(cal_line_study & u11_ambiguous)),
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
        "does_not_modify_l1_0_outputs": source_manifest_before["l1_0"] == source_manifest_after["l1_0"],
    }

    np.save(out_dir / "maps" / "calibrated_line_domain_support_map.npy", cal_line_domain.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_probable_line_domain_support_map.npy", cal_prob_line.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_non_line_domain_support_map.npy", cal_non_line.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_probable_non_line_domain_support_map.npy", cal_prob_non_line.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_mixed_domain_support_map.npy", cal_mixed.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_deferred_domain_support_map.npy", cal_deferred.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_line_study_support_map.npy", cal_line_study.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_future_module_pool_map.npy", cal_future_pool.astype(np.uint16))
    np.save(out_dir / "maps" / "l1_1_calibrated_domain_region_id_map.npy", cal_region_id_map.astype(np.int32))
    np.save(out_dir / "maps" / "l1_1_calibrated_domain_class_map.npy", cal_class_map.astype(np.uint8))
    np.save(out_dir / "maps" / "l1_1_transition_kind_map.npy", transition_kind_map.astype(np.uint8))
    np.save(out_dir / "maps" / "l1_1_transition_confidence_map.npy", transition_confidence_map.astype(np.float32))

    write_csv(out_dir / "l1_1_calibrated_domain_regions.csv", region_rows, REGION_FIELDS)
    write_csv(out_dir / "l1_1_calibrated_domain_memberships.csv", membership_rows, MEMBERSHIP_FIELDS)
    write_csv(out_dir / "l1_1_domain_transitions.csv", transition_rows, TRANSITION_FIELDS)
    write_csv(out_dir / "l1_1_domain_validation.csv", validation_rows, VALIDATION_FIELDS)
    write_csv(
        out_dir / "l1_1_calibrated_line_study_support.csv",
        [
            r
            for r in membership_rows
            if r["calibrated_l1_1_domain_class"] in LINE_CLASSES and cal_line_study[as_int(r["y"]), as_int(r["x"])]
        ],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "l1_1_calibrated_future_module_pool.csv",
        [
            r
            for r in membership_rows
            if r["calibrated_l1_1_domain_class"] in FUTURE_CLASSES and cal_future_pool[as_int(r["y"]), as_int(r["x"])]
        ],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "l1_1_promoted_to_line_study.csv",
        [r for r in membership_rows if r["source_l1_0_domain_class"] not in LINE_CLASSES and r["calibrated_l1_1_domain_class"] in LINE_CLASSES],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "l1_1_demoted_from_line_study.csv",
        [r for r in membership_rows if r["source_l1_0_domain_class"] in LINE_CLASSES and r["calibrated_l1_1_domain_class"] in FUTURE_CLASSES],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "l1_1_kept_deferred_or_mixed.csv",
        [r for r in membership_rows if r["transition_kind"] in {"kept_deferred", "kept_mixed"}],
        MEMBERSHIP_FIELDS,
    )

    make_visuals(out_dir, l10_class_map, cal_class_map, promoted_map, demoted_map, cal_line_study, cal_future_pool, l10_line_study_map, l10_future_pool_map)

    l10_deferred = load_map(l10_dir / "maps" / "deferred_domain_support_map.npy", np.uint16) > 0
    l10_mixed = load_map(l10_dir / "maps" / "mixed_domain_support_map.npy", np.uint16) > 0
    l10_line_study_px = int(np.count_nonzero(l10_line_study_map))
    counts = {
        "l1_0_observed_support_pixels_seen": int(np.count_nonzero(l10_observed_support)),
        "calibrated_line_domain_pixels": int(np.count_nonzero(cal_line_domain)),
        "calibrated_probable_line_domain_pixels": int(np.count_nonzero(cal_prob_line)),
        "calibrated_non_line_domain_pixels": int(np.count_nonzero(cal_non_line)),
        "calibrated_probable_non_line_domain_pixels": int(np.count_nonzero(cal_prob_non_line)),
        "calibrated_mixed_domain_pixels": int(np.count_nonzero(cal_mixed)),
        "calibrated_deferred_domain_pixels": int(np.count_nonzero(cal_deferred)),
        "calibrated_line_study_support_pixels": int(np.count_nonzero(cal_line_study)),
        "calibrated_future_module_pool_pixels": int(np.count_nonzero(cal_future_pool)),
        "promoted_to_line_study_pixels": int(np.count_nonzero(promoted_map & cal_line_study)),
        "demoted_from_line_study_pixels": int(np.count_nonzero(demoted_map)),
        "kept_deferred_pixels": int(np.count_nonzero(kept_deferred_map & cal_deferred)),
        "kept_mixed_pixels": int(np.count_nonzero(kept_mixed_map & cal_mixed)),
        "calibrated_domain_region_count": len(region_rows),
        "transition_kind_region_counts": dict(Counter(r["transition_kind"] for r in region_rows)),
        "calibrated_domain_class_region_counts": dict(Counter(r["calibrated_l1_1_domain_class"] for r in region_rows)),
        "l1_0_line_study_support_pixels": l10_line_study_px,
        "l1_0_future_module_pool_pixels": int(np.count_nonzero(l10_future_pool_map)),
        "l1_0_deferred_domain_pixels": int(np.count_nonzero(l10_deferred)),
        "l1_0_mixed_domain_pixels": int(np.count_nonzero(l10_mixed)),
    }
    metrics = {
        "calibrated_line_exclusion_ratio": ratio(counts["calibrated_future_module_pool_pixels"], counts["l1_0_observed_support_pixels_seen"]),
        "calibrated_future_pool_traceability_rate": ratio(len(future_pixel_set & membership_pixel_set), len(future_pixel_set)),
        "deferred_reduction_ratio": ratio(counts["l1_0_deferred_domain_pixels"] - counts["calibrated_deferred_domain_pixels"], counts["l1_0_deferred_domain_pixels"]),
        "mixed_reduction_ratio": ratio(counts["l1_0_mixed_domain_pixels"] - counts["calibrated_mixed_domain_pixels"], counts["l1_0_mixed_domain_pixels"]),
        "line_study_delta_ratio_vs_l1_0": ratio(counts["calibrated_line_study_support_pixels"] - counts["l1_0_line_study_support_pixels"], counts["l1_0_line_study_support_pixels"]),
        "promoted_pixel_traceability_rate": 1.0 if not promoted_pixel_set else ratio(len(promoted_pixel_set & membership_pixel_set), len(promoted_pixel_set)),
        "demoted_pixel_future_pool_rate": 1.0 if not demoted_pixel_set else ratio(len(demoted_pixel_set & future_pixel_set), len(demoted_pixel_set)),
    }
    contract = {
        "is_calibration_layer_not_recovery_module": True,
        "creates_final_geometry": False,
        "creates_final_lineobjects": False,
        "creates_axis_descriptors": False,
        "creates_crossings": False,
        "recognizes_ocr_strings": False,
        "recognizes_digit_values": False,
        "uses_grid_audit_truth_as_runtime_input": False,
        "non_line_support_is_preserved": True,
        "future_module_pool_preserves_non_line_mixed_deferred": True,
        "calibrated_line_study_support_is_not_final_geometry": True,
    }

    output_missing_pre_json = missing_required(out_dir, [rel for rel in REQUIRED_OUTPUT_FILES if rel not in {"summary.json", "contract_audit.json"}])
    status = "completed" if all(invariants.values()) and not output_missing_pre_json else "failed_contract"
    outputs = {rel.replace("/", "_").replace(".", "_"): rel for rel in REQUIRED_OUTPUT_FILES}
    summary = {
        "version": VERSION,
        "status": status,
        "source_l1_0_run_dir": str(l10_dir),
        "source_u1_1_run_dir": str(u11_dir),
        "source_v3_3_run_dir": str(v33_dir),
        "source_v3_4_2_run_dir": str(v342_dir) if v342_dir else "",
        "source_c1_0_run_dir": str(c10_dir) if c10_dir else "",
        "source_c1_1_run_dir": str(c11_dir) if c11_dir else "",
        "source_u1_0_run_dir": str(u10_dir) if u10_dir else "",
        "source_l1_0_version": l10_summary.get("version", ""),
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
        "visual_acceptance_note": "Visual audit remains mandatory because L1.1 has no line-domain ground-truth dataset.",
    }
    contract_audit = {
        "version": VERSION,
        "contract_file": "outputs/CONTRACT_L1_1_OBSERVED_SUPPORT_DOMAIN_CALIBRATION_LAYER_V1.md",
        "status": status,
        "semantic_rule": "l1_1_is_calibration_layer_not_recovery_or_semantic_recognition",
        "traceability_rule": "all_transitions_preserve_l1_0_and_u1_1_traceability",
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
    ap.add_argument("--l1-0-dir", required=True)
    ap.add_argument("--u1-1-dir", required=True)
    ap.add_argument("--v3-run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--v3-4-2-dir", default=None)
    ap.add_argument("--c1-dir", default=None)
    ap.add_argument("--c1-1-dir", default=None)
    ap.add_argument("--u1-0-dir", default=None)
    ap.add_argument("--min-promotion-line-score", type=float, default=0.67)
    ap.add_argument("--min-promotion-line-context", type=float, default=0.48)
    ap.add_argument("--max-promotion-microstructure", type=float, default=0.52)
    ap.add_argument("--min-demotion-non-line-score", type=float, default=0.70)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config(
        min_promotion_line_score=args.min_promotion_line_score,
        min_promotion_line_context=args.min_promotion_line_context,
        max_promotion_microstructure=args.max_promotion_microstructure,
        min_demotion_non_line_score=args.min_demotion_non_line_score,
    )
    run(
        l10_dir=Path(args.l1_0_dir),
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
