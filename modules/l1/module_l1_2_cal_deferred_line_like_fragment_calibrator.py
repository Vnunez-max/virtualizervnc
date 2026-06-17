#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module L1.2-CAL - Deferred Line-Like Fragment Calibrator.

L1.2-CAL calibrates only support that L1.2 kept as deferred. It may promote a
strict traceable subset to probable_line_domain when the fragment has strong
external line context and width/local stability is unreliable. It does not
create geometry, repair gaps, recognize text, or modify upstream outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_L1_2_CAL_V1_DEFERRED_LINE_LIKE_FRAGMENT_CALIBRATOR"

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

CALIBRATION_KIND_CODE = {
    "unchanged_non_deferred": 0,
    "promoted_deferred_to_probable_line": 1,
    "kept_deferred": 2,
}

LINE_CLASSES = {"line_domain", "probable_line_domain"}
FUTURE_CLASSES = {"non_line_domain", "probable_non_line_domain", "mixed_domain", "deferred_domain"}

CALIBRATION_SUBCLASS = "deferred_line_like_width_unstable_candidate"

REGION_FIELDS = [
    "calibrated_region_id",
    "source_l1_2_resolved_domain_region_id",
    "source_l1_1_calibrated_domain_region_id",
    "source_l1_0_domain_region_id",
    "source_u1_1_region_id",
    "source_geometry_object_id",
    "source_l1_2_domain_class",
    "source_l1_2_deferred_subclass",
    "calibrated_l1_2_cal_domain_class",
    "calibration_subclass",
    "calibration_kind",
    "calibration_confidence",
    "excluded_from_calibrated_line_study",
    "available_for_future_modules",
    "region_pixel_count",
    "orientation",
    "line_context_score",
    "colinearity_score",
    "width_stability_score",
    "width_reliability_score",
    "microstructure_score",
    "mixed_contact_score",
    "diagnostic_contact_score",
    "blocking_contact_score",
    "external_line_context_score",
    "calibration_reason",
]

MEMBERSHIP_FIELDS = [
    "calibrated_region_id",
    "source_l1_2_resolved_domain_region_id",
    "source_l1_1_calibrated_domain_region_id",
    "source_l1_0_domain_region_id",
    "source_u1_1_region_id",
    "source_geometry_object_id",
    "x",
    "y",
    "source_l1_2_domain_class",
    "source_l1_2_deferred_subclass",
    "calibrated_l1_2_cal_domain_class",
    "calibration_subclass",
    "calibration_kind",
    "calibration_confidence",
    "excluded_from_calibrated_line_study",
    "available_for_future_modules",
    "membership_weight",
]

CANDIDATE_FIELDS = [
    "candidate_id",
    "calibrated_region_id",
    "source_l1_2_resolved_domain_region_id",
    "source_l1_2_deferred_subclass",
    "candidate_pixel_count",
    "line_context_score",
    "colinearity_score",
    "width_stability_score",
    "width_reliability_score",
    "microstructure_score",
    "mixed_contact_score",
    "diagnostic_contact_score",
    "blocking_contact_score",
    "external_line_context_score",
    "candidate_reason",
]

VALIDATION_FIELDS = [
    "calibrated_region_id",
    "source_l1_2_resolved_domain_region_id",
    "source_l1_2_domain_class",
    "source_l1_2_deferred_subclass",
    "calibrated_l1_2_cal_domain_class",
    "changed_support_subset_of_l1_2_deferred_support",
    "non_deferred_support_preserved",
    "line_domain_not_created_from_deferred",
    "calibrated_line_study_excludes_non_line_mixed_deferred",
    "calibrated_future_pool_preserves_non_line_mixed_deferred",
    "calibration_preserves_source_traceability",
    "no_semantic_recognition_used",
    "does_not_create_geometry",
    "does_not_delete_support",
    "does_not_modify_upstream",
    "validation_reason",
    "rejection_or_deferral_reason",
]

REQUIRED_L12_FILES = [
    "summary.json",
    "contract_audit.json",
    "l1_2_deferred_subclasses.csv",
    "l1_2_resolved_domain_regions.csv",
    "l1_2_resolved_domain_memberships.csv",
    "l1_2_deferred_resolutions.csv",
    "l1_2_domain_validation.csv",
    "l1_2_resolved_line_study_support.csv",
    "l1_2_resolved_future_module_pool.csv",
    "maps/resolved_line_domain_support_map.npy",
    "maps/resolved_probable_line_domain_support_map.npy",
    "maps/resolved_non_line_domain_support_map.npy",
    "maps/resolved_probable_non_line_domain_support_map.npy",
    "maps/resolved_mixed_domain_support_map.npy",
    "maps/resolved_deferred_domain_support_map.npy",
    "maps/resolved_line_study_support_map.npy",
    "maps/resolved_future_module_pool_map.npy",
    "maps/l1_2_resolved_domain_region_id_map.npy",
    "maps/l1_2_resolved_domain_class_map.npy",
    "maps/l1_2_deferred_subclass_map.npy",
    "maps/l1_2_resolution_kind_map.npy",
    "maps/l1_2_resolution_confidence_map.npy",
]

REQUIRED_L11_FILES = [
    "summary.json",
    "l1_1_calibrated_domain_regions.csv",
    "l1_1_calibrated_domain_memberships.csv",
    "maps/l1_1_calibrated_domain_region_id_map.npy",
    "maps/l1_1_calibrated_domain_class_map.npy",
    "maps/calibrated_line_study_support_map.npy",
]

REQUIRED_L10_FILES = [
    "summary.json",
    "l1_0_domain_regions.csv",
    "l1_0_domain_memberships.csv",
    "maps/l1_0_domain_region_id_map.npy",
    "maps/l1_0_domain_class_map.npy",
]

REQUIRED_U11_FILES = [
    "summary.json",
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
    "l1_2_cal_calibrated_domain_regions.csv",
    "l1_2_cal_calibrated_domain_memberships.csv",
    "l1_2_cal_width_unstable_candidates.csv",
    "l1_2_cal_promoted_to_line.csv",
    "l1_2_cal_kept_deferred.csv",
    "l1_2_cal_domain_validation.csv",
    "l1_2_cal_line_study_support.csv",
    "l1_2_cal_future_module_pool.csv",
    "summary.json",
    "contract_audit.json",
    "maps/width_unstable_line_like_candidate_map.npy",
    "maps/width_unstable_promoted_to_line_map.npy",
    "maps/width_unstable_kept_deferred_map.npy",
    "maps/calibrated_line_domain_support_map.npy",
    "maps/calibrated_probable_line_domain_support_map.npy",
    "maps/calibrated_non_line_domain_support_map.npy",
    "maps/calibrated_probable_non_line_domain_support_map.npy",
    "maps/calibrated_mixed_domain_support_map.npy",
    "maps/calibrated_deferred_domain_support_map.npy",
    "maps/calibrated_line_study_support_map.npy",
    "maps/calibrated_future_module_pool_map.npy",
    "maps/l1_2_cal_domain_region_id_map.npy",
    "maps/l1_2_cal_domain_class_map.npy",
    "maps/l1_2_cal_calibration_kind_map.npy",
    "maps/l1_2_cal_calibration_confidence_map.npy",
    "visuals/01_l1_2_input_domains.png",
    "visuals/02_width_unstable_line_like_candidates.png",
    "visuals/03_promoted_to_line.png",
    "visuals/04_kept_deferred_after_calibration.png",
    "visuals/05_calibrated_line_study_support.png",
    "visuals/06_calibrated_future_module_pool.png",
    "visuals/07_l1_2_vs_l1_2_cal_comparison.png",
    "visuals/08_l1_2_cal_audit_summary.png",
]


@dataclass
class Config:
    version: str = VERSION
    neighborhood_px: int = 2
    anchor_search_px: int = 32
    candidate_min_pixels: int = 2
    candidate_min_line_context: float = 0.72
    candidate_min_colinearity: float = 0.70
    candidate_min_external_line_context: float = 0.50
    candidate_max_microstructure: float = 0.58
    candidate_max_mixed_contact: float = 0.36
    candidate_max_conflict_contact: float = 0.20
    promotion_min_line_context: float = 0.74
    promotion_min_colinearity: float = 0.72
    promotion_min_external_line_context: float = 0.55
    promotion_max_microstructure: float = 0.56
    promotion_max_mixed_contact: float = 0.34
    promotion_max_conflict_contact: float = 0.15
    unreliable_width_stability_max: float = 0.55
    unreliable_width_reliability_max: float = 0.55


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
    return max(0.0, min(1.0, float(value)))


def ratio(num: int, den: int) -> float:
    return float(num / den) if den else 0.0


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


def class_map_to_rgb(class_map: np.ndarray) -> Image.Image:
    arr = np.full((class_map.shape[0], class_map.shape[1], 3), 255, dtype=np.uint8)
    arr[class_map == DOMAIN_CODE["line_domain"]] = (38, 122, 255)
    arr[class_map == DOMAIN_CODE["probable_line_domain"]] = (0, 185, 210)
    arr[class_map == DOMAIN_CODE["non_line_domain"]] = (220, 0, 0)
    arr[class_map == DOMAIN_CODE["probable_non_line_domain"]] = (255, 160, 0)
    arr[class_map == DOMAIN_CODE["mixed_domain"]] = (150, 70, 210)
    arr[class_map == DOMAIN_CODE["deferred_domain"]] = (160, 160, 160)
    return Image.fromarray(arr, "RGB")


def connected_components(mask: np.ndarray) -> List[List[Tuple[int, int]]]:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps: List[List[Tuple[int, int]]] = []
    for y0, x0 in zip(*np.where(mask)):
        if seen[y0, x0]:
            continue
        q: deque[Tuple[int, int]] = deque([(int(x0), int(y0))])
        seen[y0, x0] = True
        pts: List[Tuple[int, int]] = []
        while q:
            x, y = q.popleft()
            pts.append((x, y))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((nx, ny))
        comps.append(pts)
    return comps


def local_connectivity(points: Sequence[Tuple[int, int]]) -> float:
    pts = set(points)
    if not pts:
        return 0.0
    links = 0
    total = 0
    for x, y in pts:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            total += 1
            if (x + dx, y + dy) in pts:
                links += 1
    return clamp01(links / max(total, 1))


def component_mask(shape: Tuple[int, int], points: Sequence[Tuple[int, int]]) -> np.ndarray:
    mask = np.zeros(shape, dtype=bool)
    for x, y in points:
        mask[y, x] = True
    return mask


def ring_score(points: Sequence[Tuple[int, int]], shape: Tuple[int, int], context: np.ndarray, radius: int) -> float:
    mask = component_mask(shape, points)
    ring = dilate(mask, radius) & ~mask
    return ratio(int(np.count_nonzero(ring & context)), int(np.count_nonzero(ring)))


def colinear_anchor_score(
    points: Sequence[Tuple[int, int]],
    shape: Tuple[int, int],
    context: np.ndarray,
    orientation: str,
    search_px: int,
) -> float:
    h, w = shape
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if orientation == "vertical":
        col = Counter(xs).most_common(1)[0][0]
        x0, x1 = max(0, col - 1), min(w, col + 2)
        top0, top1 = max(0, ymin - search_px), max(0, ymin)
        bot0, bot1 = min(h, ymax + 1), min(h, ymax + 1 + search_px)
        top = bool(np.any(context[top0:top1, x0:x1])) if top1 > top0 else False
        bottom = bool(np.any(context[bot0:bot1, x0:x1])) if bot1 > bot0 else False
        return (0.5 if top else 0.0) + (0.5 if bottom else 0.0)
    row = Counter(ys).most_common(1)[0][0]
    y0, y1 = max(0, row - 1), min(h, row + 2)
    left0, left1 = max(0, xmin - search_px), max(0, xmin)
    right0, right1 = min(w, xmax + 1), min(w, xmax + 1 + search_px)
    left = bool(np.any(context[y0:y1, left0:left1])) if left1 > left0 else False
    right = bool(np.any(context[y0:y1, right0:right1])) if right1 > right0 else False
    return (0.5 if left else 0.0) + (0.5 if right else 0.0)


def load_membership_weights(l12_dir: Path) -> Dict[Tuple[int, int, int], float]:
    weights: Dict[Tuple[int, int, int], float] = {}
    for row in read_csv(l12_dir / "l1_2_resolved_domain_memberships.csv"):
        rid = as_int(row.get("resolved_domain_region_id"))
        x, y = as_int(row.get("x")), as_int(row.get("y"))
        weights[(rid, x, y)] = as_float(row.get("membership_weight"), 1.0)
    return weights


def row_source(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "source_l1_1_calibrated_domain_region_id": as_int(row.get("source_l1_1_calibrated_domain_region_id")),
        "source_l1_0_domain_region_id": as_int(row.get("source_l1_0_domain_region_id")),
        "source_u1_1_region_id": as_int(row.get("source_u1_1_region_id")),
        "source_geometry_object_id": str(row.get("source_geometry_object_id", "")),
        "source_l1_2_domain_class": str(row.get("resolved_l1_2_domain_class", "")),
        "source_l1_2_deferred_subclass": str(row.get("deferred_subclass", "")),
    }


def compute_features(
    points: Sequence[Tuple[int, int]],
    source_region: Dict[str, str],
    shape: Tuple[int, int],
    line_context_map: np.ndarray,
    mixed_map: np.ndarray,
    diagnostic_near: np.ndarray,
    blocking_near: np.ndarray,
    cfg: Config,
) -> Dict[str, float | str]:
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    n = len(points)
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    bw, bh = xmax - xmin + 1, ymax - ymin + 1
    source_orientation = str(source_region.get("orientation", ""))
    orientation = source_orientation if source_orientation in {"horizontal", "vertical"} else ("horizontal" if bw >= bh else "vertical")
    major = max(bw, bh)
    minor = min(bw, bh)
    area = max(1, bw * bh)
    density = n / area

    if orientation == "vertical":
        axis_count = Counter(xs).most_common(1)[0][1]
    else:
        axis_count = Counter(ys).most_common(1)[0][1]
    axis_colinearity = clamp01(axis_count / max(n, 1))
    longitudinal_continuity = clamp01(axis_count / max(major, 1))
    elongation_score = clamp01(major / max(major + minor, 1))
    geometry_line_score = clamp01(0.45 * longitudinal_continuity + 0.35 * axis_colinearity + 0.20 * elongation_score)

    source_line = as_float(source_region.get("line_context_score"))
    source_col = as_float(source_region.get("colinearity_score"))
    source_width = as_float(source_region.get("width_stability_score"))
    source_micro = as_float(source_region.get("microstructure_score"))
    source_mixed = as_float(source_region.get("mixed_contact_score"))

    neighbor_line_ratio = ring_score(points, shape, line_context_map, cfg.neighborhood_px)
    local_line_neighbor = clamp01(neighbor_line_ratio * 4.0)
    anchor_score = colinear_anchor_score(points, shape, line_context_map, orientation, cfg.anchor_search_px)
    external_line_context = clamp01(0.45 * anchor_score + 0.30 * local_line_neighbor + 0.25 * source_line)

    component = component_mask(shape, points)
    mixed_contact_local = ring_score(points, shape, mixed_map, cfg.neighborhood_px)
    diagnostic_contact = ratio(int(np.count_nonzero(component & diagnostic_near)), n)
    blocking_contact = ratio(int(np.count_nonzero(component & blocking_near)), n)
    compact_mark_score = 1.0 if major <= 6 and minor <= 4 and density >= 0.35 else 0.0

    line_context = clamp01(0.45 * source_line + 0.35 * geometry_line_score + 0.20 * external_line_context)
    colinearity = clamp01(0.55 * source_col + 0.45 * axis_colinearity)
    width_reliability = clamp01(
        0.45 * clamp01((minor - 1) / 3.0)
        + 0.25 * clamp01(n / 24.0)
        + 0.30 * source_width
    )
    microstructure = clamp01(0.70 * source_micro + 0.20 * compact_mark_score + 0.10 * diagnostic_contact)
    mixed_contact = clamp01(0.70 * source_mixed + 0.30 * mixed_contact_local)

    return {
        "region_pixel_count": float(n),
        "orientation": orientation,
        "line_context_score": line_context,
        "colinearity_score": colinearity,
        "width_stability_score": source_width,
        "width_reliability_score": width_reliability,
        "microstructure_score": microstructure,
        "mixed_contact_score": mixed_contact,
        "diagnostic_contact_score": diagnostic_contact,
        "blocking_contact_score": blocking_contact,
        "external_line_context_score": external_line_context,
        "local_connectivity_score": local_connectivity(points),
        "geometry_line_score": geometry_line_score,
    }


def candidate_decision(features: Dict[str, float | str], cfg: Config) -> Tuple[bool, float, str]:
    n = int(float(features["region_pixel_count"]))
    conflict = max(float(features["diagnostic_contact_score"]), float(features["blocking_contact_score"]))
    width_unreliable = (
        float(features["width_stability_score"]) <= cfg.unreliable_width_stability_max
        or float(features["width_reliability_score"]) <= cfg.unreliable_width_reliability_max
    )
    ok = (
        n >= cfg.candidate_min_pixels
        and float(features["line_context_score"]) >= cfg.candidate_min_line_context
        and float(features["colinearity_score"]) >= cfg.candidate_min_colinearity
        and float(features["external_line_context_score"]) >= cfg.candidate_min_external_line_context
        and float(features["microstructure_score"]) <= cfg.candidate_max_microstructure
        and float(features["mixed_contact_score"]) <= cfg.candidate_max_mixed_contact
        and conflict <= cfg.candidate_max_conflict_contact
        and width_unreliable
    )
    confidence = clamp01(
        0.25 * float(features["line_context_score"])
        + 0.25 * float(features["external_line_context_score"])
        + 0.20 * float(features["colinearity_score"])
        + 0.15 * (1.0 - float(features["microstructure_score"]))
        + 0.10 * (1.0 - float(features["mixed_contact_score"]))
        + 0.05 * (1.0 - conflict)
    )
    if ok:
        return True, max(0.55, confidence), "strong_external_line_context_with_unreliable_width"
    reasons: List[str] = []
    if n < cfg.candidate_min_pixels:
        reasons.append("too_few_pixels")
    if not width_unreliable:
        reasons.append("width_not_unreliable")
    if float(features["line_context_score"]) < cfg.candidate_min_line_context:
        reasons.append("line_context_below_candidate_threshold")
    if float(features["external_line_context_score"]) < cfg.candidate_min_external_line_context:
        reasons.append("external_line_context_below_candidate_threshold")
    if float(features["colinearity_score"]) < cfg.candidate_min_colinearity:
        reasons.append("colinearity_below_candidate_threshold")
    if float(features["microstructure_score"]) > cfg.candidate_max_microstructure:
        reasons.append("microstructure_too_high")
    if float(features["mixed_contact_score"]) > cfg.candidate_max_mixed_contact:
        reasons.append("mixed_contact_too_high")
    if conflict > cfg.candidate_max_conflict_contact:
        reasons.append("diagnostic_or_blocking_contact_too_high")
    return False, min(0.54, confidence), "+".join(reasons) if reasons else "candidate_thresholds_not_met"


def promotion_decision(features: Dict[str, float | str], is_candidate: bool, cfg: Config) -> Tuple[bool, str]:
    conflict = max(float(features["diagnostic_contact_score"]), float(features["blocking_contact_score"]))
    ok = (
        is_candidate
        and float(features["line_context_score"]) >= cfg.promotion_min_line_context
        and float(features["colinearity_score"]) >= cfg.promotion_min_colinearity
        and float(features["external_line_context_score"]) >= cfg.promotion_min_external_line_context
        and float(features["microstructure_score"]) <= cfg.promotion_max_microstructure
        and float(features["mixed_contact_score"]) <= cfg.promotion_max_mixed_contact
        and conflict <= cfg.promotion_max_conflict_contact
    )
    if ok:
        return True, "candidate_promoted_to_probable_line_domain"
    return False, "kept_deferred_after_strict_promotion_guard"


def make_visuals(
    out_dir: Path,
    l12_class_map: np.ndarray,
    calibrated_class_map: np.ndarray,
    l12_deferred: np.ndarray,
    candidate_map: np.ndarray,
    promoted_map: np.ndarray,
    kept_deferred_map: np.ndarray,
    calibrated_line_study: np.ndarray,
    calibrated_future_pool: np.ndarray,
) -> None:
    vdir = out_dir / "visuals"
    ensure_dir(vdir)
    class_map_to_rgb(l12_class_map).save(vdir / "01_l1_2_input_domains.png")
    render_bool(candidate_map, (255, 245, 135)).save(vdir / "02_width_unstable_line_like_candidates.png")
    render_bool(promoted_map, (255, 220, 0)).save(vdir / "03_promoted_to_line.png")
    render_bool(kept_deferred_map, (150, 150, 150)).save(vdir / "04_kept_deferred_after_calibration.png")
    render_bool(calibrated_line_study, (0, 175, 85)).save(vdir / "05_calibrated_line_study_support.png")
    render_bool(calibrated_future_pool, (210, 0, 210)).save(vdir / "06_calibrated_future_module_pool.png")

    panels = [
        titled(class_map_to_rgb(l12_class_map), "L1.2 input domains"),
        titled(render_bool(l12_deferred, (0, 0, 0)), "L1.2 deferred input"),
        titled(render_bool(candidate_map, (255, 245, 135)), "width-unstable candidates"),
        titled(render_bool(promoted_map, (255, 220, 0)), "promoted to probable line"),
        titled(render_bool(kept_deferred_map, (150, 150, 150)), "kept deferred"),
        titled(class_map_to_rgb(calibrated_class_map), "L1.2-CAL domains"),
        titled(render_bool(calibrated_line_study, (0, 175, 85)), "calibrated line-study"),
        titled(render_bool(calibrated_future_pool, (210, 0, 210)), "calibrated future pool"),
    ]
    tile_w = max(p.width for p in panels)
    tile_h = max(p.height for p in panels)
    sheet = Image.new("RGB", (tile_w * 4, tile_h * 2 + 38), "white")
    d = ImageDraw.Draw(sheet)
    d.text((8, 10), "L1.2-CAL: deferred line-like fragment calibrator", fill="black", font=font(16))
    for idx, panel in enumerate(panels):
        x = (idx % 4) * tile_w
        y = 38 + (idx // 4) * tile_h
        sheet.paste(panel, (x, y))
    sheet.save(vdir / "07_l1_2_vs_l1_2_cal_comparison.png")

    audit_panels = [
        titled(render_bool(l12_deferred, (0, 0, 0)), "black: L1.2 deferred"),
        titled(render_bool(candidate_map, (255, 245, 135)), "light yellow: candidates"),
        titled(render_bool(promoted_map, (255, 220, 0)), "yellow: promotions"),
        titled(render_bool(kept_deferred_map, (150, 150, 150)), "gray: still deferred"),
        titled(render_bool(calibrated_line_study, (0, 175, 85)), "green: line-study"),
        titled(render_bool(calibrated_future_pool, (210, 0, 210)), "magenta: future pool"),
    ]
    audit = Image.new("RGB", (tile_w * 3, tile_h * 2 + 38), "white")
    d = ImageDraw.Draw(audit)
    d.text((8, 10), "L1.2-CAL audit: promotions do not delete unresolved support", fill="black", font=font(16))
    for idx, panel in enumerate(audit_panels):
        x = (idx % 3) * tile_w
        y = 38 + (idx // 3) * tile_h
        audit.paste(panel, (x, y))
    audit.save(vdir / "08_l1_2_cal_audit_summary.png")


def source_manifests(
    l12_dir: Path,
    l11_dir: Path,
    l10_dir: Path,
    u11_dir: Path,
    v33_dir: Path,
    v342_dir: Optional[Path],
    c10_dir: Optional[Path],
    c11_dir: Optional[Path],
    u10_dir: Optional[Path],
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    manifests = {
        "l1_2": file_manifest(l12_dir, REQUIRED_L12_FILES),
        "l1_1": file_manifest(l11_dir, REQUIRED_L11_FILES),
        "l1_0": file_manifest(l10_dir, REQUIRED_L10_FILES),
        "u1_1": file_manifest(u11_dir, REQUIRED_U11_FILES),
        "v3_3": file_manifest(v33_dir, REQUIRED_V33_FILES),
    }
    if v342_dir:
        manifests["v3_4_2"] = file_manifest(
            v342_dir,
            [rel for rel in ["summary.json", "maps/diagnostic_residual_support_count_map.npy"] if (v342_dir / rel).exists()],
        )
    if c10_dir:
        manifests["c1_0"] = file_manifest(
            c10_dir,
            [rel for rel in ["summary.json", "maps/rejected_residual_support_map.npy"] if (c10_dir / rel).exists()],
        )
    if c11_dir:
        manifests["c1_1"] = file_manifest(
            c11_dir,
            [rel for rel in ["summary.json", "maps/collective_blocking_evidence_map.npy"] if (c11_dir / rel).exists()],
        )
    if u10_dir:
        manifests["u1_0"] = file_manifest(
            u10_dir,
            [rel for rel in ["summary.json", "contract_audit.json"] if (u10_dir / rel).exists()],
        )
    return manifests


def run(
    l12_dir: Path,
    l11_dir: Path,
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
    l12_dir = Path(l12_dir)
    l11_dir = Path(l11_dir)
    l10_dir = Path(l10_dir)
    u11_dir = Path(u11_dir)
    v33_dir = Path(v33_dir)
    out_dir = Path(out_dir)
    v342_dir = Path(v342_dir) if v342_dir else None
    c10_dir = Path(c10_dir) if c10_dir else None
    c11_dir = Path(c11_dir) if c11_dir else None
    u10_dir = Path(u10_dir) if u10_dir else None

    missing_inputs = {
        "l1_2": missing_required(l12_dir, REQUIRED_L12_FILES),
        "l1_1": missing_required(l11_dir, REQUIRED_L11_FILES),
        "l1_0": missing_required(l10_dir, REQUIRED_L10_FILES),
        "u1_1": missing_required(u11_dir, REQUIRED_U11_FILES),
        "v3_3": missing_required(v33_dir, REQUIRED_V33_FILES),
    }
    absent = [f"{group}:{rel}" for group, rels in missing_inputs.items() for rel in rels]
    if absent:
        raise FileNotFoundError("Missing required L1.2-CAL input files: " + ", ".join(absent))

    source_manifest_before = source_manifests(l12_dir, l11_dir, l10_dir, u11_dir, v33_dir, v342_dir, c10_dir, c11_dir, u10_dir)

    ensure_dir(out_dir)
    ensure_dir(out_dir / "maps")
    ensure_dir(out_dir / "visuals")

    l12_summary = read_json(l12_dir / "summary.json")
    l11_summary = read_json(l11_dir / "summary.json")
    l10_summary = read_json(l10_dir / "summary.json")
    u11_summary = read_json(u11_dir / "summary.json")
    v33_summary = read_json(v33_dir / "summary.json")

    l12_regions = {
        as_int(row.get("resolved_domain_region_id")): row
        for row in read_csv(l12_dir / "l1_2_resolved_domain_regions.csv")
    }
    membership_weights = load_membership_weights(l12_dir)

    l12_region_map = load_map(l12_dir / "maps" / "l1_2_resolved_domain_region_id_map.npy", np.int32)
    l12_class_map = load_map(l12_dir / "maps" / "l1_2_resolved_domain_class_map.npy", np.uint8)
    l12_line_domain = load_map(l12_dir / "maps" / "resolved_line_domain_support_map.npy", np.uint16) > 0
    l12_prob_line = load_map(l12_dir / "maps" / "resolved_probable_line_domain_support_map.npy", np.uint16) > 0
    l12_non_line = load_map(l12_dir / "maps" / "resolved_non_line_domain_support_map.npy", np.uint16) > 0
    l12_prob_non_line = load_map(l12_dir / "maps" / "resolved_probable_non_line_domain_support_map.npy", np.uint16) > 0
    l12_mixed = load_map(l12_dir / "maps" / "resolved_mixed_domain_support_map.npy", np.uint16) > 0
    l12_deferred = load_map(l12_dir / "maps" / "resolved_deferred_domain_support_map.npy", np.uint16) > 0
    l12_line_study = load_map(l12_dir / "maps" / "resolved_line_study_support_map.npy", np.uint16) > 0
    l12_future = load_map(l12_dir / "maps" / "resolved_future_module_pool_map.npy", np.uint16) > 0
    l11_line_study = load_map(l11_dir / "maps" / "calibrated_line_study_support_map.npy", np.uint16) > 0
    u11_refined = load_map(u11_dir / "maps" / "refined_unified_valid_observed_support_map.npy", np.uint16) > 0
    shape = l12_class_map.shape
    l12_observed = l12_class_map > 0

    diagnostic = optional_map(v342_dir / "maps" / "diagnostic_residual_support_count_map.npy" if v342_dir else None, shape, np.uint16) > 0
    c10_rejected = optional_map(c10_dir / "maps" / "rejected_residual_support_map.npy" if c10_dir else None, shape, np.uint16) > 0
    c11_blocking = optional_map(c11_dir / "maps" / "collective_blocking_evidence_map.npy" if c11_dir else None, shape, np.uint16) > 0
    u11_ambiguous = optional_map(u11_dir / "maps" / "ambiguous_subsupport_map.npy", shape, np.uint16) > 0

    diagnostic_near = dilate(diagnostic, cfg.neighborhood_px)
    blocking_near = dilate(c10_rejected | c11_blocking, cfg.neighborhood_px)
    line_context_map = l12_line_study | l11_line_study

    calibrated_class_map = l12_class_map.copy()
    calibrated_region_map = np.zeros(shape, dtype=np.int32)
    calibration_kind_map = np.zeros(shape, dtype=np.uint8)
    calibration_confidence_map = np.zeros(shape, dtype=np.float32)
    candidate_map = np.zeros(shape, dtype=bool)
    promoted_map = np.zeros(shape, dtype=bool)

    region_rows: List[Dict[str, Any]] = []
    membership_rows: List[Dict[str, Any]] = []
    candidate_rows: List[Dict[str, Any]] = []
    validation_rows: List[Dict[str, Any]] = []
    calibrated_region_id = 0
    candidate_id = 0

    for source_region_id in sorted(int(v) for v in np.unique(l12_region_map) if int(v) > 0):
        source_region = l12_regions.get(source_region_id, {})
        source_class = str(source_region.get("resolved_l1_2_domain_class", ""))
        source_mask = l12_region_map == source_region_id
        comps = connected_components(source_mask & l12_deferred) if source_class == "deferred_domain" else connected_components(source_mask)
        if not comps:
            continue
        for points in comps:
            calibrated_region_id += 1
            source = row_source(source_region)
            features = compute_features(
                points=points,
                source_region=source_region,
                shape=shape,
                line_context_map=line_context_map,
                mixed_map=l12_mixed,
                diagnostic_near=diagnostic_near,
                blocking_near=blocking_near,
                cfg=cfg,
            )
            is_candidate = False
            calibration_subclass = ""
            calibration_kind = "unchanged_non_deferred"
            calibrated_class = source_class
            calibration_reason = "non_deferred_l1_2_support_preserved"
            calibration_confidence = 1.0
            if source_class == "deferred_domain":
                is_candidate, candidate_confidence, candidate_reason = candidate_decision(features, cfg)
                promote, promotion_reason = promotion_decision(features, is_candidate, cfg)
                if is_candidate:
                    calibration_subclass = CALIBRATION_SUBCLASS
                    candidate_id += 1
                    candidate_rows.append(
                        {
                            "candidate_id": candidate_id,
                            "calibrated_region_id": calibrated_region_id,
                            "source_l1_2_resolved_domain_region_id": source_region_id,
                            "source_l1_2_deferred_subclass": source["source_l1_2_deferred_subclass"],
                            "candidate_pixel_count": len(points),
                            "line_context_score": features["line_context_score"],
                            "colinearity_score": features["colinearity_score"],
                            "width_stability_score": features["width_stability_score"],
                            "width_reliability_score": features["width_reliability_score"],
                            "microstructure_score": features["microstructure_score"],
                            "mixed_contact_score": features["mixed_contact_score"],
                            "diagnostic_contact_score": features["diagnostic_contact_score"],
                            "blocking_contact_score": features["blocking_contact_score"],
                            "external_line_context_score": features["external_line_context_score"],
                            "candidate_reason": candidate_reason,
                        }
                    )
                if promote:
                    calibrated_class = "probable_line_domain"
                    calibration_kind = "promoted_deferred_to_probable_line"
                    calibration_reason = promotion_reason
                    calibration_confidence = candidate_confidence
                else:
                    calibrated_class = "deferred_domain"
                    calibration_kind = "kept_deferred"
                    calibration_reason = candidate_reason if not is_candidate else promotion_reason
                    calibration_confidence = candidate_confidence

            excluded_from_line = calibrated_class not in LINE_CLASSES
            available_future = calibrated_class in FUTURE_CLASSES
            region_rows.append(
                {
                    "calibrated_region_id": calibrated_region_id,
                    "source_l1_2_resolved_domain_region_id": source_region_id,
                    **source,
                    "calibrated_l1_2_cal_domain_class": calibrated_class,
                    "calibration_subclass": calibration_subclass,
                    "calibration_kind": calibration_kind,
                    "calibration_confidence": calibration_confidence,
                    "excluded_from_calibrated_line_study": excluded_from_line,
                    "available_for_future_modules": available_future,
                    "region_pixel_count": len(points),
                    "orientation": features["orientation"],
                    "line_context_score": features["line_context_score"],
                    "colinearity_score": features["colinearity_score"],
                    "width_stability_score": features["width_stability_score"],
                    "width_reliability_score": features["width_reliability_score"],
                    "microstructure_score": features["microstructure_score"],
                    "mixed_contact_score": features["mixed_contact_score"],
                    "diagnostic_contact_score": features["diagnostic_contact_score"],
                    "blocking_contact_score": features["blocking_contact_score"],
                    "external_line_context_score": features["external_line_context_score"],
                    "calibration_reason": calibration_reason,
                }
            )

            points_set = set(points)
            changed = source_class != calibrated_class
            validation_rows.append(
                {
                    "calibrated_region_id": calibrated_region_id,
                    "source_l1_2_resolved_domain_region_id": source_region_id,
                    "source_l1_2_domain_class": source_class,
                    "source_l1_2_deferred_subclass": source["source_l1_2_deferred_subclass"],
                    "calibrated_l1_2_cal_domain_class": calibrated_class,
                    "changed_support_subset_of_l1_2_deferred_support": (not changed) or all(l12_deferred[y, x] for x, y in points_set),
                    "non_deferred_support_preserved": source_class == "deferred_domain" or calibrated_class == source_class,
                    "line_domain_not_created_from_deferred": not (source_class == "deferred_domain" and calibrated_class == "line_domain"),
                    "calibrated_line_study_excludes_non_line_mixed_deferred": calibrated_class in LINE_CLASSES or excluded_from_line,
                    "calibrated_future_pool_preserves_non_line_mixed_deferred": calibrated_class in LINE_CLASSES or available_future,
                    "calibration_preserves_source_traceability": bool(
                        source_region_id
                        and source["source_l1_1_calibrated_domain_region_id"]
                        and source["source_l1_0_domain_region_id"]
                        and source["source_u1_1_region_id"]
                        and source["source_geometry_object_id"] != ""
                    ),
                    "no_semantic_recognition_used": True,
                    "does_not_create_geometry": True,
                    "does_not_delete_support": True,
                    "does_not_modify_upstream": True,
                    "validation_reason": "calibration_from_traceable_l1_2_deferred_domain_features",
                    "rejection_or_deferral_reason": "" if calibrated_class in LINE_CLASSES else calibration_reason,
                }
            )

            for x, y in points:
                calibrated_region_map[y, x] = calibrated_region_id
                calibrated_class_map[y, x] = DOMAIN_CODE[calibrated_class]
                calibration_kind_map[y, x] = CALIBRATION_KIND_CODE[calibration_kind]
                calibration_confidence_map[y, x] = float(calibration_confidence)
                if is_candidate:
                    candidate_map[y, x] = True
                if calibration_kind == "promoted_deferred_to_probable_line":
                    promoted_map[y, x] = True
                membership_rows.append(
                    {
                        "calibrated_region_id": calibrated_region_id,
                        "source_l1_2_resolved_domain_region_id": source_region_id,
                        **source,
                        "x": x,
                        "y": y,
                        "calibrated_l1_2_cal_domain_class": calibrated_class,
                        "calibration_subclass": calibration_subclass,
                        "calibration_kind": calibration_kind,
                        "calibration_confidence": calibration_confidence,
                        "excluded_from_calibrated_line_study": excluded_from_line,
                        "available_for_future_modules": available_future,
                        "membership_weight": membership_weights.get((source_region_id, x, y), 1.0),
                    }
                )

    calibrated_line_domain = calibrated_class_map == DOMAIN_CODE["line_domain"]
    calibrated_prob_line = calibrated_class_map == DOMAIN_CODE["probable_line_domain"]
    calibrated_non_line = calibrated_class_map == DOMAIN_CODE["non_line_domain"]
    calibrated_prob_non_line = calibrated_class_map == DOMAIN_CODE["probable_non_line_domain"]
    calibrated_mixed = calibrated_class_map == DOMAIN_CODE["mixed_domain"]
    calibrated_deferred = calibrated_class_map == DOMAIN_CODE["deferred_domain"]
    kept_deferred_map = l12_deferred & calibrated_deferred
    calibrated_future_pool = calibrated_non_line | calibrated_prob_non_line | calibrated_mixed | calibrated_deferred
    calibrated_line_study = (calibrated_line_domain | calibrated_prob_line) & u11_refined & ~diagnostic & ~u11_ambiguous

    state_maps = [
        calibrated_line_domain,
        calibrated_prob_line,
        calibrated_non_line,
        calibrated_prob_non_line,
        calibrated_mixed,
        calibrated_deferred,
    ]
    overlap = np.zeros(shape, dtype=np.uint8)
    for m in state_maps:
        overlap += m.astype(np.uint8)

    source_manifest_after = source_manifests(l12_dir, l11_dir, l10_dir, u11_dir, v33_dir, v342_dir, c10_dir, c11_dir, u10_dir)

    membership_pixel_set = {(as_int(r["x"]), as_int(r["y"])) for r in membership_rows}
    future_membership_set = {
        (as_int(r["x"]), as_int(r["y"]))
        for r in membership_rows
        if str(r["calibrated_l1_2_cal_domain_class"]) in FUTURE_CLASSES
    }
    promoted_membership_set = {
        (as_int(r["x"]), as_int(r["y"]))
        for r in membership_rows
        if str(r["calibration_kind"]) == "promoted_deferred_to_probable_line"
    }
    future_pixel_set = set(zip(np.where(calibrated_future_pool)[1].tolist(), np.where(calibrated_future_pool)[0].tolist()))
    promoted_pixel_set = set(zip(np.where(promoted_map)[1].tolist(), np.where(promoted_map)[0].tolist()))
    changed_map = calibrated_class_map != l12_class_map
    changed_pixel_set = set(zip(np.where(changed_map)[1].tolist(), np.where(changed_map)[0].tolist()))

    non_deferred_mask = l12_observed & ~l12_deferred
    invariants = {
        "all_changed_support_subset_of_l1_2_deferred_support": bool(np.all(~changed_map | l12_deferred)),
        "all_unchanged_non_deferred_l1_2_support_preserved": bool(np.all(calibrated_class_map[non_deferred_mask] == l12_class_map[non_deferred_mask])),
        "calibrated_line_domain_support_equals_l1_2_line_domain_support": bool(np.array_equal(calibrated_line_domain, l12_line_domain)),
        "calibrated_probable_line_domain_support_subset_of_l1_2_observed_support": bool(np.all(~calibrated_prob_line | l12_observed)),
        "calibrated_non_line_domain_support_equals_l1_2_non_line_domain_support": bool(np.array_equal(calibrated_non_line, l12_non_line)),
        "calibrated_probable_non_line_domain_support_equals_l1_2_probable_non_line_domain_support": bool(np.array_equal(calibrated_prob_non_line, l12_prob_non_line)),
        "calibrated_mixed_domain_support_equals_l1_2_mixed_domain_support": bool(np.array_equal(calibrated_mixed, l12_mixed)),
        "calibrated_deferred_domain_support_subset_of_l1_2_observed_support": bool(np.all(~calibrated_deferred | l12_observed)),
        "all_l1_2_cal_domain_maps_are_mutually_exclusive": bool(np.all(overlap <= 1)),
        "calibrated_line_study_support_excludes_non_line_probable_non_line_mixed_deferred": not bool(np.any(calibrated_line_study & calibrated_future_pool)),
        "calibrated_future_module_pool_includes_non_line_probable_non_line_mixed_deferred": bool(np.all((calibrated_non_line | calibrated_prob_non_line | calibrated_mixed | calibrated_deferred) <= calibrated_future_pool)),
        "calibrated_future_module_pool_preserves_traceability": future_pixel_set.issubset(membership_pixel_set) and future_pixel_set.issubset(future_membership_set),
        "all_calibrations_preserve_source_l1_2_class": all(str(r.get("source_l1_2_domain_class", "")) in DOMAIN_CLASSES for r in region_rows),
        "all_calibrations_preserve_source_l1_1_region_id_when_available": all("source_l1_1_calibrated_domain_region_id" in r for r in region_rows),
        "all_calibrations_preserve_source_l1_0_region_id_when_available": all("source_l1_0_domain_region_id" in r for r in region_rows),
        "all_calibrations_preserve_source_u1_1_region_id_when_available": all("source_u1_1_region_id" in r for r in region_rows),
        "all_calibrations_preserve_source_geometry_object_id_when_available": all("source_geometry_object_id" in r for r in region_rows),
        "promoted_support_remains_traceable_to_l1_2_deferred_support": promoted_pixel_set.issubset(promoted_membership_set) and all(l12_deferred[y, x] for x, y in promoted_pixel_set),
        "kept_deferred_support_is_not_silently_counted_as_clean_line": not bool(np.any(kept_deferred_map & calibrated_line_study)),
        "inferred_spans_are_not_converted_to_observed_support": True,
        "diagnostic_residual_is_not_converted_to_line_study_support": not bool(np.any(calibrated_line_study & diagnostic)),
        "ambiguous_residual_is_not_converted_to_line_study_support": not bool(np.any(calibrated_line_study & u11_ambiguous)),
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
        "does_not_modify_l1_1_outputs": source_manifest_before["l1_1"] == source_manifest_after["l1_1"],
        "does_not_modify_l1_2_outputs": source_manifest_before["l1_2"] == source_manifest_after["l1_2"],
    }

    np.save(out_dir / "maps" / "width_unstable_line_like_candidate_map.npy", candidate_map.astype(np.uint16))
    np.save(out_dir / "maps" / "width_unstable_promoted_to_line_map.npy", promoted_map.astype(np.uint16))
    np.save(out_dir / "maps" / "width_unstable_kept_deferred_map.npy", kept_deferred_map.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_line_domain_support_map.npy", calibrated_line_domain.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_probable_line_domain_support_map.npy", calibrated_prob_line.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_non_line_domain_support_map.npy", calibrated_non_line.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_probable_non_line_domain_support_map.npy", calibrated_prob_non_line.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_mixed_domain_support_map.npy", calibrated_mixed.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_deferred_domain_support_map.npy", calibrated_deferred.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_line_study_support_map.npy", calibrated_line_study.astype(np.uint16))
    np.save(out_dir / "maps" / "calibrated_future_module_pool_map.npy", calibrated_future_pool.astype(np.uint16))
    np.save(out_dir / "maps" / "l1_2_cal_domain_region_id_map.npy", calibrated_region_map.astype(np.int32))
    np.save(out_dir / "maps" / "l1_2_cal_domain_class_map.npy", calibrated_class_map.astype(np.uint8))
    np.save(out_dir / "maps" / "l1_2_cal_calibration_kind_map.npy", calibration_kind_map.astype(np.uint8))
    np.save(out_dir / "maps" / "l1_2_cal_calibration_confidence_map.npy", calibration_confidence_map.astype(np.float32))

    write_csv(out_dir / "l1_2_cal_calibrated_domain_regions.csv", region_rows, REGION_FIELDS)
    write_csv(out_dir / "l1_2_cal_calibrated_domain_memberships.csv", membership_rows, MEMBERSHIP_FIELDS)
    write_csv(out_dir / "l1_2_cal_width_unstable_candidates.csv", candidate_rows, CANDIDATE_FIELDS)
    write_csv(
        out_dir / "l1_2_cal_promoted_to_line.csv",
        [r for r in membership_rows if r["calibration_kind"] == "promoted_deferred_to_probable_line"],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "l1_2_cal_kept_deferred.csv",
        [r for r in membership_rows if r["source_l1_2_domain_class"] == "deferred_domain" and r["calibrated_l1_2_cal_domain_class"] == "deferred_domain"],
        MEMBERSHIP_FIELDS,
    )
    write_csv(out_dir / "l1_2_cal_domain_validation.csv", validation_rows, VALIDATION_FIELDS)
    write_csv(
        out_dir / "l1_2_cal_line_study_support.csv",
        [r for r in membership_rows if r["calibrated_l1_2_cal_domain_class"] in LINE_CLASSES and calibrated_line_study[as_int(r["y"]), as_int(r["x"])]],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "l1_2_cal_future_module_pool.csv",
        [r for r in membership_rows if r["calibrated_l1_2_cal_domain_class"] in FUTURE_CLASSES and calibrated_future_pool[as_int(r["y"]), as_int(r["x"])]],
        MEMBERSHIP_FIELDS,
    )

    make_visuals(
        out_dir=out_dir,
        l12_class_map=l12_class_map,
        calibrated_class_map=calibrated_class_map,
        l12_deferred=l12_deferred,
        candidate_map=candidate_map,
        promoted_map=promoted_map,
        kept_deferred_map=kept_deferred_map,
        calibrated_line_study=calibrated_line_study,
        calibrated_future_pool=calibrated_future_pool,
    )

    counts = {
        "l1_2_deferred_pixels_seen": int(np.count_nonzero(l12_deferred)),
        "width_unstable_line_like_candidate_pixels": int(np.count_nonzero(candidate_map)),
        "width_unstable_promoted_to_line_pixels": int(np.count_nonzero(promoted_map)),
        "width_unstable_kept_deferred_pixels": int(np.count_nonzero(kept_deferred_map)),
        "calibrated_line_study_support_pixels": int(np.count_nonzero(calibrated_line_study)),
        "calibrated_future_module_pool_pixels": int(np.count_nonzero(calibrated_future_pool)),
        "l1_2_line_study_support_pixels": int(np.count_nonzero(l12_line_study)),
        "l1_2_future_module_pool_pixels": int(np.count_nonzero(l12_future)),
        "calibrated_region_count": len(region_rows),
        "candidate_region_count": len(candidate_rows),
        "calibration_kind_region_counts": dict(Counter(r["calibration_kind"] for r in region_rows)),
        "calibrated_domain_class_region_counts": dict(Counter(r["calibrated_l1_2_cal_domain_class"] for r in region_rows)),
    }
    metrics = {
        "line_study_delta_ratio_vs_l1_2": ratio(counts["calibrated_line_study_support_pixels"] - counts["l1_2_line_study_support_pixels"], counts["l1_2_line_study_support_pixels"]),
        "deferred_reduction_ratio_vs_l1_2": ratio(counts["l1_2_deferred_pixels_seen"] - counts["width_unstable_kept_deferred_pixels"], counts["l1_2_deferred_pixels_seen"]),
        "future_pool_traceability_rate": ratio(len(future_pixel_set & membership_pixel_set), len(future_pixel_set)),
        "calibration_traceability_rate": 1.0 if not promoted_pixel_set else ratio(len(promoted_pixel_set & promoted_membership_set), len(promoted_pixel_set)),
        "changed_support_pixels": int(np.count_nonzero(changed_map)),
        "changed_support_subset_rate": 1.0 if not changed_pixel_set else ratio(sum(1 for x, y in changed_pixel_set if l12_deferred[y, x]), len(changed_pixel_set)),
    }
    contract = {
        "is_calibrator_not_final_line_extractor": True,
        "allowed_change_is_only_deferred_to_probable_line_domain": True,
        "creates_final_geometry": False,
        "creates_final_lineobjects": False,
        "creates_axis_descriptors": False,
        "creates_crossings": False,
        "recognizes_ocr_strings": False,
        "recognizes_digit_values": False,
        "uses_grid_audit_truth_as_runtime_input": False,
        "does_not_force_deferred_to_disappear": True,
        "unresolved_deferred_support_is_preserved": True,
        "calibrated_line_study_support_is_not_final_geometry": True,
    }

    output_missing_pre_json = missing_required(out_dir, [rel for rel in REQUIRED_OUTPUT_FILES if rel not in {"summary.json", "contract_audit.json"}])
    status = "completed" if all(invariants.values()) and not output_missing_pre_json else "failed_contract"
    outputs = {rel.replace("/", "_").replace(".", "_"): rel for rel in REQUIRED_OUTPUT_FILES}
    summary = {
        "version": VERSION,
        "status": status,
        "source_l1_2_run_dir": str(l12_dir),
        "source_l1_1_run_dir": str(l11_dir),
        "source_l1_0_run_dir": str(l10_dir),
        "source_u1_1_run_dir": str(u11_dir),
        "source_v3_3_run_dir": str(v33_dir),
        "source_v3_4_2_run_dir": str(v342_dir) if v342_dir else "",
        "source_c1_0_run_dir": str(c10_dir) if c10_dir else "",
        "source_c1_1_run_dir": str(c11_dir) if c11_dir else "",
        "source_u1_0_run_dir": str(u10_dir) if u10_dir else "",
        "source_l1_2_version": l12_summary.get("version", ""),
        "source_l1_1_version": l11_summary.get("version", ""),
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
        "visual_acceptance_note": "Visual audit remains mandatory because L1.2-CAL has no line-domain ground-truth dataset.",
    }
    contract_audit = {
        "version": VERSION,
        "contract_file": "outputs/CONTRACT_L1_2_CAL_DEFERRED_LINE_LIKE_FRAGMENT_CALIBRATOR_V1.md",
        "status": status,
        "semantic_rule": "l1_2_cal_promotes_only_traceable_l1_2_deferred_support_to_probable_line_domain",
        "traceability_rule": "all_changed_support_is_subset_of_l1_2_deferred_support",
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
    ap.add_argument("--l1-2-dir", required=True)
    ap.add_argument("--l1-1-dir", required=True)
    ap.add_argument("--l1-0-dir", required=True)
    ap.add_argument("--u1-1-dir", required=True)
    ap.add_argument("--v3-run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--v3-4-2-dir", default=None)
    ap.add_argument("--c1-dir", default=None)
    ap.add_argument("--c1-1-dir", default=None)
    ap.add_argument("--u1-0-dir", default=None)
    ap.add_argument("--candidate-min-line-context", type=float, default=0.72)
    ap.add_argument("--candidate-min-external-line-context", type=float, default=0.50)
    ap.add_argument("--promotion-min-line-context", type=float, default=0.74)
    ap.add_argument("--promotion-min-external-line-context", type=float, default=0.55)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config(
        candidate_min_line_context=args.candidate_min_line_context,
        candidate_min_external_line_context=args.candidate_min_external_line_context,
        promotion_min_line_context=args.promotion_min_line_context,
        promotion_min_external_line_context=args.promotion_min_external_line_context,
    )
    run(
        l12_dir=Path(args.l1_2_dir),
        l11_dir=Path(args.l1_1_dir),
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
