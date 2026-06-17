#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module G1.0 - Deferred Line Family Resolver.

G1.0 promotes only L1.2-CAL deferred support that can be explained by a
traceable horizontal or vertical line family built from already accepted
calibrated line-study support. It does not create final geometry, repair gaps,
recognize text, or modify upstream outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_G1_0_V1_DEFERRED_LINE_FAMILY_RESOLVER"

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

LINE_CLASSES = {"line_domain", "probable_line_domain"}
FUTURE_CLASSES = {"non_line_domain", "probable_non_line_domain", "mixed_domain", "deferred_domain"}

RESOLUTION_KIND_CODE = {
    "unchanged_non_deferred": 0,
    "promoted_deferred_by_family": 1,
    "kept_deferred_no_family": 2,
    "kept_deferred_failed_family_guard": 3,
}

REQUIRED_INPUT_FILES = [
    "summary.json",
    "contract_audit.json",
    "l1_2_cal_calibrated_domain_regions.csv",
    "l1_2_cal_calibrated_domain_memberships.csv",
    "l1_2_cal_domain_validation.csv",
    "l1_2_cal_line_study_support.csv",
    "l1_2_cal_future_module_pool.csv",
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
]

REQUIRED_OUTPUT_FILES = [
    "g1_0_line_families.csv",
    "g1_0_deferred_family_associations.csv",
    "g1_0_calibrated_domain_regions.csv",
    "g1_0_calibrated_domain_memberships.csv",
    "g1_0_promoted_to_line.csv",
    "g1_0_kept_deferred.csv",
    "g1_0_domain_validation.csv",
    "g1_0_line_study_support.csv",
    "g1_0_future_module_pool.csv",
    "summary.json",
    "contract_audit.json",
    "maps/g1_0_line_family_corridor_map.npy",
    "maps/g1_0_family_explained_candidate_map.npy",
    "maps/g1_0_family_promoted_to_line_map.npy",
    "maps/g1_0_family_kept_deferred_map.npy",
    "maps/g1_0_family_id_map.npy",
    "maps/g1_0_calibrated_line_domain_support_map.npy",
    "maps/g1_0_calibrated_probable_line_domain_support_map.npy",
    "maps/g1_0_calibrated_non_line_domain_support_map.npy",
    "maps/g1_0_calibrated_probable_non_line_domain_support_map.npy",
    "maps/g1_0_calibrated_mixed_domain_support_map.npy",
    "maps/g1_0_calibrated_deferred_domain_support_map.npy",
    "maps/g1_0_calibrated_line_study_support_map.npy",
    "maps/g1_0_calibrated_future_module_pool_map.npy",
    "maps/g1_0_domain_region_id_map.npy",
    "maps/g1_0_domain_class_map.npy",
    "maps/g1_0_resolution_kind_map.npy",
    "maps/g1_0_resolution_confidence_map.npy",
    "visuals/01_input_l1_2_cal_domains.png",
    "visuals/02_line_family_corridors.png",
    "visuals/03_family_explained_deferred_candidates.png",
    "visuals/04_family_promoted_to_line.png",
    "visuals/05_kept_deferred_after_family_resolution.png",
    "visuals/06_g1_0_calibrated_line_study_support.png",
    "visuals/07_g1_0_future_module_pool.png",
    "visuals/08_l1_2_cal_vs_g1_0_comparison.png",
]

FAMILY_FIELDS = [
    "family_id",
    "orientation",
    "baseline",
    "corridor_min",
    "corridor_max",
    "support_pixels",
    "coverage_pixels",
    "longest_run",
    "span_extent",
    "run_count",
    "family_strength_score",
    "parallel_context_score",
    "source",
]

ASSOCIATION_FIELDS = [
    "association_id",
    "g1_0_region_id",
    "source_l1_2_cal_region_id",
    "family_id",
    "orientation",
    "component_pixel_count",
    "component_bbox_x0",
    "component_bbox_y0",
    "component_bbox_x1",
    "component_bbox_y1",
    "family_distance",
    "anchor_score",
    "family_strength_score",
    "component_colinearity_score",
    "component_run_score",
    "source_line_context_score",
    "source_external_line_context_score",
    "source_microstructure_score",
    "source_mixed_contact_score",
    "source_conflict_contact_score",
    "association_score",
    "promoted_to_probable_line",
    "decision_reason",
]

REGION_FIELDS = [
    "g1_0_region_id",
    "source_l1_2_cal_region_id",
    "source_l1_2_resolved_domain_region_id",
    "source_l1_1_calibrated_domain_region_id",
    "source_l1_0_domain_region_id",
    "source_u1_1_region_id",
    "source_geometry_object_id",
    "source_l1_2_cal_domain_class",
    "source_l1_2_deferred_subclass",
    "g1_0_domain_class",
    "g1_0_resolution_kind",
    "g1_0_resolution_confidence",
    "line_family_id",
    "line_family_orientation",
    "association_score",
    "excluded_from_g1_0_line_study",
    "available_for_future_modules",
    "region_pixel_count",
    "calibration_reason",
]

MEMBERSHIP_FIELDS = [
    "g1_0_region_id",
    "source_l1_2_cal_region_id",
    "source_l1_2_resolved_domain_region_id",
    "source_l1_1_calibrated_domain_region_id",
    "source_l1_0_domain_region_id",
    "source_u1_1_region_id",
    "source_geometry_object_id",
    "x",
    "y",
    "source_l1_2_cal_domain_class",
    "source_l1_2_deferred_subclass",
    "g1_0_domain_class",
    "g1_0_resolution_kind",
    "g1_0_resolution_confidence",
    "line_family_id",
    "association_score",
    "excluded_from_g1_0_line_study",
    "available_for_future_modules",
    "membership_weight",
]

VALIDATION_FIELDS = [
    "g1_0_region_id",
    "source_l1_2_cal_region_id",
    "source_l1_2_cal_domain_class",
    "g1_0_domain_class",
    "changed_support_subset_of_l1_2_cal_deferred_support",
    "non_deferred_support_preserved",
    "line_domain_not_created_from_deferred",
    "promoted_support_has_family_id",
    "g1_0_line_study_excludes_non_line_mixed_deferred",
    "g1_0_future_pool_preserves_non_line_mixed_deferred",
    "resolution_preserves_source_traceability",
    "no_semantic_recognition_used",
    "does_not_create_geometry",
    "does_not_delete_support",
    "does_not_modify_upstream",
    "validation_reason",
    "rejection_or_deferral_reason",
]


@dataclass
class Config:
    version: str = VERSION
    family_min_axis_count: int = 18
    family_min_long_run: int = 14
    family_min_span_extent: int = 40
    family_group_gap_px: int = 2
    association_max_distance_px: float = 5.0
    association_anchor_search_px: int = 56
    association_span_margin_px: int = 30
    min_component_pixels: int = 2
    min_association_score: float = 0.47
    min_family_strength_score: float = 0.32
    strong_family_strength_score: float = 0.75
    min_anchor_score: float = 0.50
    min_component_colinearity_score: float = 0.45
    min_component_run_score: float = 0.12
    max_microstructure_score: float = 0.66
    max_mixed_contact_score: float = 0.48
    max_conflict_contact_score: float = 0.30


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


def class_map_to_rgb(class_map: np.ndarray) -> Image.Image:
    arr = np.full((class_map.shape[0], class_map.shape[1], 3), 255, dtype=np.uint8)
    arr[class_map == DOMAIN_CODE["line_domain"]] = (38, 122, 255)
    arr[class_map == DOMAIN_CODE["probable_line_domain"]] = (0, 185, 210)
    arr[class_map == DOMAIN_CODE["non_line_domain"]] = (220, 0, 0)
    arr[class_map == DOMAIN_CODE["probable_non_line_domain"]] = (255, 160, 0)
    arr[class_map == DOMAIN_CODE["mixed_domain"]] = (150, 70, 210)
    arr[class_map == DOMAIN_CODE["deferred_domain"]] = (160, 160, 160)
    return Image.fromarray(arr, "RGB")


def runs_1d(values: np.ndarray) -> List[Tuple[int, int, int]]:
    runs: List[Tuple[int, int, int]] = []
    i = 0
    n = len(values)
    while i < n:
        if not bool(values[i]):
            i += 1
            continue
        j = i
        while j + 1 < n and bool(values[j + 1]):
            j += 1
        runs.append((i, j, j - i + 1))
        i = j + 1
    return runs


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


def load_membership_weights(input_dir: Path) -> Dict[Tuple[int, int, int], float]:
    weights: Dict[Tuple[int, int, int], float] = {}
    for row in read_csv(input_dir / "l1_2_cal_calibrated_domain_memberships.csv"):
        rid = as_int(row.get("calibrated_region_id"))
        x, y = as_int(row.get("x")), as_int(row.get("y"))
        weights[(rid, x, y)] = as_float(row.get("membership_weight"), 1.0)
    return weights


def build_axis_families(line_map: np.ndarray, orientation: str, start_id: int, cfg: Config) -> List[Dict[str, Any]]:
    h, w = line_map.shape
    axis_len = h if orientation == "horizontal" else w
    ortho_len = w if orientation == "horizontal" else h
    axis_rows: List[Tuple[int, int, int, int, List[Tuple[int, int, int]]]] = []

    for idx in range(axis_len):
        vec = line_map[idx, :] if orientation == "horizontal" else line_map[:, idx]
        runs = runs_1d(vec)
        count = int(np.count_nonzero(vec))
        longest = max([r[2] for r in runs], default=0)
        coords = np.where(vec)[0]
        span = int(coords[-1] - coords[0] + 1) if coords.size else 0
        long_runs = sum(1 for r in runs if r[2] >= cfg.family_min_long_run)
        if count >= cfg.family_min_axis_count and (
            longest >= cfg.family_min_long_run
            or (span >= cfg.family_min_span_extent and long_runs >= 1)
        ):
            axis_rows.append((idx, count, longest, span, runs))

    groups: List[List[Tuple[int, int, int, int, List[Tuple[int, int, int]]]]] = []
    for item in axis_rows:
        if not groups or item[0] - groups[-1][-1][0] > cfg.family_group_gap_px:
            groups.append([item])
        else:
            groups[-1].append(item)

    families: List[Dict[str, Any]] = []
    for offset, group in enumerate(groups):
        support = sum(item[1] for item in group)
        if support <= 0:
            continue
        baseline = sum(item[0] * item[1] for item in group) / support
        idxs = [item[0] for item in group]
        union_vec = np.zeros(ortho_len, dtype=bool)
        for idx, *_ in group:
            union_vec |= line_map[idx, :] if orientation == "horizontal" else line_map[:, idx]
        family_runs = runs_1d(union_vec)
        coverage = int(np.count_nonzero(union_vec))
        longest = max(item[2] for item in group)
        span = max(item[3] for item in group)
        strength = clamp01(
            0.35 * (longest / 40.0)
            + 0.25 * (coverage / 180.0)
            + 0.25 * (support / 220.0)
            + 0.15 * (span / 260.0)
        )
        families.append(
            {
                "family_id": start_id + offset,
                "orientation": orientation,
                "baseline": baseline,
                "corridor_min": min(idxs),
                "corridor_max": max(idxs),
                "support_pixels": support,
                "coverage_pixels": coverage,
                "longest_run": longest,
                "span_extent": span,
                "run_count": len(family_runs),
                "runs": family_runs,
                "family_strength_score": strength,
                "parallel_context_score": 0.0,
                "source": "g1_0_from_l1_2_cal_line_study_support",
            }
        )

    for family in families:
        neighbors = [
            other
            for other in families
            if other is not family and 6 <= abs(other["baseline"] - family["baseline"]) <= 80
        ]
        family["parallel_context_score"] = clamp01(len(neighbors) / 6.0)
        family["family_strength_score"] = clamp01(
            0.82 * family["family_strength_score"] + 0.18 * family["parallel_context_score"]
        )
    return families


def build_family_corridor_map(shape: Tuple[int, int], families: Sequence[Dict[str, Any]]) -> np.ndarray:
    h, w = shape
    out = np.zeros(shape, dtype=np.uint16)
    for family in families:
        fid = int(family["family_id"])
        c0 = max(0, int(family["corridor_min"]) - 1)
        c1 = int(family["corridor_max"]) + 1
        if family["orientation"] == "horizontal":
            out[c0 : min(h, c1 + 1), :] = np.where(out[c0 : min(h, c1 + 1), :] == 0, fid, out[c0 : min(h, c1 + 1), :])
        else:
            out[:, c0 : min(w, c1 + 1)] = np.where(out[:, c0 : min(w, c1 + 1)] == 0, fid, out[:, c0 : min(w, c1 + 1)])
    return out


def component_family_association(
    points: Sequence[Tuple[int, int]],
    families: Sequence[Dict[str, Any]],
    cfg: Config,
) -> Optional[Dict[str, Any]]:
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    n = len(points)
    if n <= 0:
        return None
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    orientation = "horizontal" if bw >= bh else "vertical"
    axis_values = ys if orientation == "horizontal" else xs
    axis_count = Counter(axis_values).most_common(1)[0][1]
    component_colinearity = clamp01(axis_count / max(n, 1))
    major = max(bw, bh)
    component_run = clamp01(axis_count / max(major, 1))
    center = sum(ys) / n if orientation == "horizontal" else sum(xs) / n
    start = x0 if orientation == "horizontal" else y0
    end = x1 if orientation == "horizontal" else y1
    candidates = [family for family in families if family["orientation"] == orientation]
    best: Optional[Dict[str, Any]] = None

    for family in candidates:
        dist = abs(center - float(family["baseline"]))
        if dist > cfg.association_max_distance_px:
            continue
        runs = family["runs"]
        family_start = min([r[0] for r in runs], default=0)
        family_end = max([r[1] for r in runs], default=-1)
        if not (start >= family_start - cfg.association_span_margin_px and end <= family_end + cfg.association_span_margin_px):
            continue
        left_anchor = False
        right_anchor = False
        crossing_anchor = False
        for a, b, _length in runs:
            if b < start and start - b <= cfg.association_anchor_search_px:
                left_anchor = True
            if a > end and a - end <= cfg.association_anchor_search_px:
                right_anchor = True
            if a <= start <= b or a <= end <= b or (start <= a and b <= end):
                crossing_anchor = True
        anchor_score = (0.5 if left_anchor else 0.0) + (0.5 if right_anchor else 0.0)
        if crossing_anchor:
            anchor_score = max(anchor_score, 0.75)
        family_strength = float(family["family_strength_score"])
        association_score = clamp01(
            0.27 * (1.0 - dist / max(cfg.association_max_distance_px, 1e-6))
            + 0.23 * anchor_score
            + 0.25 * family_strength
            + 0.15 * min(1.0, major / 16.0)
            + 0.10 * component_colinearity
        )
        assoc = {
            "family_id": int(family["family_id"]),
            "orientation": orientation,
            "bbox": (x0, y0, x1, y1),
            "family_distance": dist,
            "anchor_score": anchor_score,
            "family_strength_score": family_strength,
            "component_colinearity_score": component_colinearity,
            "component_run_score": component_run,
            "association_score": association_score,
        }
        if best is None or association_score > float(best["association_score"]):
            best = assoc
    return best


def decide_promotion(
    n: int,
    assoc: Optional[Dict[str, Any]],
    source_region: Dict[str, str],
    cfg: Config,
) -> Tuple[bool, float, str]:
    if assoc is None:
        return False, 0.0, "no_traceable_line_family_association"
    micro = as_float(source_region.get("microstructure_score"))
    mixed = as_float(source_region.get("mixed_contact_score"))
    conflict = max(
        as_float(source_region.get("diagnostic_contact_score")),
        as_float(source_region.get("blocking_contact_score")),
    )
    has_anchor_or_strong_family = (
        float(assoc["anchor_score"]) >= cfg.min_anchor_score
        or float(assoc["family_strength_score"]) >= cfg.strong_family_strength_score
    )
    ok = (
        n >= cfg.min_component_pixels
        and float(assoc["association_score"]) >= cfg.min_association_score
        and float(assoc["family_strength_score"]) >= cfg.min_family_strength_score
        and has_anchor_or_strong_family
        and float(assoc["component_colinearity_score"]) >= cfg.min_component_colinearity_score
        and float(assoc["component_run_score"]) >= cfg.min_component_run_score
        and micro <= cfg.max_microstructure_score
        and mixed <= cfg.max_mixed_contact_score
        and conflict <= cfg.max_conflict_contact_score
    )
    confidence = clamp01(
        0.35 * float(assoc["association_score"])
        + 0.25 * float(assoc["family_strength_score"])
        + 0.20 * float(assoc["anchor_score"])
        + 0.10 * (1.0 - micro)
        + 0.10 * (1.0 - max(mixed, conflict))
    )
    if ok:
        return True, max(0.55, confidence), "deferred_component_explained_by_traceable_line_family"
    reasons: List[str] = []
    if n < cfg.min_component_pixels:
        reasons.append("too_few_pixels")
    if float(assoc["association_score"]) < cfg.min_association_score:
        reasons.append("association_score_below_threshold")
    if float(assoc["family_strength_score"]) < cfg.min_family_strength_score:
        reasons.append("family_strength_below_threshold")
    if not has_anchor_or_strong_family:
        reasons.append("no_anchor_or_strong_family")
    if float(assoc["component_colinearity_score"]) < cfg.min_component_colinearity_score:
        reasons.append("component_colinearity_below_threshold")
    if float(assoc["component_run_score"]) < cfg.min_component_run_score:
        reasons.append("component_run_below_threshold")
    if micro > cfg.max_microstructure_score:
        reasons.append("microstructure_too_high")
    if mixed > cfg.max_mixed_contact_score:
        reasons.append("mixed_contact_too_high")
    if conflict > cfg.max_conflict_contact_score:
        reasons.append("diagnostic_or_blocking_contact_too_high")
    return False, min(0.54, confidence), "+".join(reasons) if reasons else "family_guard_failed"


def render_family_corridors(shape: Tuple[int, int], families: Sequence[Dict[str, Any]], line_map: np.ndarray) -> Image.Image:
    arr = np.full((shape[0], shape[1], 3), 255, dtype=np.uint8)
    arr[line_map] = (0, 175, 85)
    for family in families:
        c0 = max(0, int(family["corridor_min"]) - 1)
        c1 = int(family["corridor_max"]) + 1
        color = (70, 145, 255) if family["orientation"] == "horizontal" else (0, 200, 220)
        if family["orientation"] == "horizontal":
            arr[c0 : min(shape[0], c1 + 1), :, :] = np.where(
                line_map[c0 : min(shape[0], c1 + 1), :, None],
                arr[c0 : min(shape[0], c1 + 1), :, :],
                np.array(color, dtype=np.uint8),
            )
        else:
            arr[:, c0 : min(shape[1], c1 + 1), :] = np.where(
                line_map[:, c0 : min(shape[1], c1 + 1), None],
                arr[:, c0 : min(shape[1], c1 + 1), :],
                np.array(color, dtype=np.uint8),
            )
    return Image.fromarray(arr, "RGB")


def make_visuals(
    out_dir: Path,
    input_class_map: np.ndarray,
    output_class_map: np.ndarray,
    input_line_study: np.ndarray,
    families: Sequence[Dict[str, Any]],
    candidate_map: np.ndarray,
    promoted_map: np.ndarray,
    kept_deferred_map: np.ndarray,
    line_study: np.ndarray,
    future_pool: np.ndarray,
) -> None:
    vdir = out_dir / "visuals"
    ensure_dir(vdir)
    class_map_to_rgb(input_class_map).save(vdir / "01_input_l1_2_cal_domains.png")
    family_img = render_family_corridors(input_class_map.shape, families, input_line_study)
    family_img.save(vdir / "02_line_family_corridors.png")
    render_bool(candidate_map, (255, 245, 135)).save(vdir / "03_family_explained_deferred_candidates.png")
    render_bool(promoted_map, (255, 220, 0)).save(vdir / "04_family_promoted_to_line.png")
    render_bool(kept_deferred_map, (150, 150, 150)).save(vdir / "05_kept_deferred_after_family_resolution.png")
    render_bool(line_study, (0, 175, 85)).save(vdir / "06_g1_0_calibrated_line_study_support.png")
    render_bool(future_pool, (210, 0, 210)).save(vdir / "07_g1_0_future_module_pool.png")

    panels = [
        titled(class_map_to_rgb(input_class_map), "L1.2-CAL input domains"),
        titled(family_img, "line family corridors"),
        titled(render_bool(candidate_map, (255, 245, 135)), "family-explained candidates"),
        titled(render_bool(promoted_map, (255, 220, 0)), "promoted by family"),
        titled(render_bool(kept_deferred_map, (150, 150, 150)), "kept deferred"),
        titled(class_map_to_rgb(output_class_map), "G1.0 domains"),
        titled(render_bool(line_study, (0, 175, 85)), "G1.0 line-study"),
        titled(render_bool(future_pool, (210, 0, 210)), "G1.0 future pool"),
    ]
    tile_w = max(p.width for p in panels)
    tile_h = max(p.height for p in panels)
    sheet = Image.new("RGB", (tile_w * 4, tile_h * 2 + 38), "white")
    d = ImageDraw.Draw(sheet)
    d.text((8, 10), "G1.0 deferred line family resolver", fill="black", font=font(16))
    for idx, panel in enumerate(panels):
        x = (idx % 4) * tile_w
        y = 38 + (idx // 4) * tile_h
        sheet.paste(panel, (x, y))
    sheet.save(vdir / "08_l1_2_cal_vs_g1_0_comparison.png")


def source_from_region(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "source_l1_2_resolved_domain_region_id": as_int(row.get("source_l1_2_resolved_domain_region_id")),
        "source_l1_1_calibrated_domain_region_id": as_int(row.get("source_l1_1_calibrated_domain_region_id")),
        "source_l1_0_domain_region_id": as_int(row.get("source_l1_0_domain_region_id")),
        "source_u1_1_region_id": as_int(row.get("source_u1_1_region_id")),
        "source_geometry_object_id": str(row.get("source_geometry_object_id", "")),
        "source_l1_2_cal_domain_class": str(row.get("calibrated_l1_2_cal_domain_class", "")),
        "source_l1_2_deferred_subclass": str(row.get("source_l1_2_deferred_subclass", "")),
    }


def run(input_dir: Path, out_dir: Path, cfg: Optional[Config] = None) -> Dict[str, Any]:
    cfg = cfg or Config()
    input_dir = Path(input_dir)
    out_dir = Path(out_dir)
    missing_inputs = {"l1_2_cal": missing_required(input_dir, REQUIRED_INPUT_FILES)}
    if missing_inputs["l1_2_cal"]:
        raise FileNotFoundError("Missing required G1.0 input files: " + ", ".join(missing_inputs["l1_2_cal"]))

    source_manifest_before = {"l1_2_cal": file_manifest(input_dir, REQUIRED_INPUT_FILES)}
    ensure_dir(out_dir)
    ensure_dir(out_dir / "maps")
    ensure_dir(out_dir / "visuals")

    input_summary = read_json(input_dir / "summary.json")
    input_regions = {
        as_int(row.get("calibrated_region_id")): row
        for row in read_csv(input_dir / "l1_2_cal_calibrated_domain_regions.csv")
    }
    membership_weights = load_membership_weights(input_dir)

    input_class_map = load_map(input_dir / "maps" / "l1_2_cal_domain_class_map.npy", np.uint8)
    input_region_map = load_map(input_dir / "maps" / "l1_2_cal_domain_region_id_map.npy", np.int32)
    input_line_domain = load_map(input_dir / "maps" / "calibrated_line_domain_support_map.npy", np.uint16) > 0
    input_prob_line = load_map(input_dir / "maps" / "calibrated_probable_line_domain_support_map.npy", np.uint16) > 0
    input_non_line = load_map(input_dir / "maps" / "calibrated_non_line_domain_support_map.npy", np.uint16) > 0
    input_prob_non_line = load_map(input_dir / "maps" / "calibrated_probable_non_line_domain_support_map.npy", np.uint16) > 0
    input_mixed = load_map(input_dir / "maps" / "calibrated_mixed_domain_support_map.npy", np.uint16) > 0
    input_deferred = load_map(input_dir / "maps" / "calibrated_deferred_domain_support_map.npy", np.uint16) > 0
    input_line_study = load_map(input_dir / "maps" / "calibrated_line_study_support_map.npy", np.uint16) > 0
    input_future_pool = load_map(input_dir / "maps" / "calibrated_future_module_pool_map.npy", np.uint16) > 0
    input_observed = input_class_map > 0
    shape = input_class_map.shape

    horizontal_families = build_axis_families(input_line_study, "horizontal", 1, cfg)
    vertical_families = build_axis_families(input_line_study, "vertical", len(horizontal_families) + 1, cfg)
    families = horizontal_families + vertical_families
    family_rows = [
        {
            key: value
            for key, value in family.items()
            if key in FAMILY_FIELDS
        }
        for family in families
    ]

    output_class_map = input_class_map.copy()
    output_region_map = np.zeros(shape, dtype=np.int32)
    resolution_kind_map = np.zeros(shape, dtype=np.uint8)
    resolution_confidence_map = np.zeros(shape, dtype=np.float32)
    candidate_map = np.zeros(shape, dtype=bool)
    promoted_map = np.zeros(shape, dtype=bool)
    family_id_map = np.zeros(shape, dtype=np.uint16)

    region_rows: List[Dict[str, Any]] = []
    membership_rows: List[Dict[str, Any]] = []
    association_rows: List[Dict[str, Any]] = []
    validation_rows: List[Dict[str, Any]] = []
    g_region_id = 0
    association_id = 0

    for source_region_id in sorted(int(v) for v in np.unique(input_region_map) if int(v) > 0):
        source_region = input_regions.get(source_region_id, {})
        source_class = str(source_region.get("calibrated_l1_2_cal_domain_class", ""))
        source_mask = input_region_map == source_region_id
        comps = connected_components(source_mask & input_deferred) if source_class == "deferred_domain" else connected_components(source_mask)
        if not comps:
            continue

        for points in comps:
            g_region_id += 1
            source = source_from_region(source_region)
            assoc = component_family_association(points, families, cfg) if source_class == "deferred_domain" else None
            promote, confidence, reason = decide_promotion(len(points), assoc, source_region, cfg) if source_class == "deferred_domain" else (False, 1.0, "non_deferred_l1_2_cal_support_preserved")
            if source_class == "deferred_domain" and assoc is not None:
                candidate_ok = (
                    float(assoc["association_score"]) >= cfg.min_association_score * 0.92
                    and float(assoc["family_strength_score"]) >= cfg.min_family_strength_score * 0.85
                )
                if candidate_ok:
                    association_id += 1
                    x0, y0, x1, y1 = assoc["bbox"]
                    conflict = max(
                        as_float(source_region.get("diagnostic_contact_score")),
                        as_float(source_region.get("blocking_contact_score")),
                    )
                    association_rows.append(
                        {
                            "association_id": association_id,
                            "g1_0_region_id": g_region_id,
                            "source_l1_2_cal_region_id": source_region_id,
                            "family_id": assoc["family_id"],
                            "orientation": assoc["orientation"],
                            "component_pixel_count": len(points),
                            "component_bbox_x0": x0,
                            "component_bbox_y0": y0,
                            "component_bbox_x1": x1,
                            "component_bbox_y1": y1,
                            "family_distance": assoc["family_distance"],
                            "anchor_score": assoc["anchor_score"],
                            "family_strength_score": assoc["family_strength_score"],
                            "component_colinearity_score": assoc["component_colinearity_score"],
                            "component_run_score": assoc["component_run_score"],
                            "source_line_context_score": as_float(source_region.get("line_context_score")),
                            "source_external_line_context_score": as_float(source_region.get("external_line_context_score")),
                            "source_microstructure_score": as_float(source_region.get("microstructure_score")),
                            "source_mixed_contact_score": as_float(source_region.get("mixed_contact_score")),
                            "source_conflict_contact_score": conflict,
                            "association_score": assoc["association_score"],
                            "promoted_to_probable_line": promote,
                            "decision_reason": reason,
                        }
                    )
                    for x, y in points:
                        candidate_map[y, x] = True

            output_class = "probable_line_domain" if promote else source_class
            resolution_kind = (
                "promoted_deferred_by_family"
                if promote
                else "kept_deferred_no_family"
                if source_class == "deferred_domain" and assoc is None
                else "kept_deferred_failed_family_guard"
                if source_class == "deferred_domain"
                else "unchanged_non_deferred"
            )
            line_family_id = int(assoc["family_id"]) if assoc is not None else 0
            assoc_score = float(assoc["association_score"]) if assoc is not None else 0.0
            excluded = output_class not in LINE_CLASSES
            available_future = output_class in FUTURE_CLASSES
            if promote:
                for x, y in points:
                    promoted_map[y, x] = True
                    family_id_map[y, x] = line_family_id

            region_rows.append(
                {
                    "g1_0_region_id": g_region_id,
                    "source_l1_2_cal_region_id": source_region_id,
                    **source,
                    "g1_0_domain_class": output_class,
                    "g1_0_resolution_kind": resolution_kind,
                    "g1_0_resolution_confidence": confidence,
                    "line_family_id": line_family_id,
                    "line_family_orientation": assoc["orientation"] if assoc else "",
                    "association_score": assoc_score,
                    "excluded_from_g1_0_line_study": excluded,
                    "available_for_future_modules": available_future,
                    "region_pixel_count": len(points),
                    "calibration_reason": reason,
                }
            )

            changed = output_class != source_class
            validation_rows.append(
                {
                    "g1_0_region_id": g_region_id,
                    "source_l1_2_cal_region_id": source_region_id,
                    "source_l1_2_cal_domain_class": source_class,
                    "g1_0_domain_class": output_class,
                    "changed_support_subset_of_l1_2_cal_deferred_support": (not changed) or all(input_deferred[y, x] for x, y in points),
                    "non_deferred_support_preserved": source_class == "deferred_domain" or output_class == source_class,
                    "line_domain_not_created_from_deferred": not (source_class == "deferred_domain" and output_class == "line_domain"),
                    "promoted_support_has_family_id": (not promote) or line_family_id > 0,
                    "g1_0_line_study_excludes_non_line_mixed_deferred": output_class in LINE_CLASSES or excluded,
                    "g1_0_future_pool_preserves_non_line_mixed_deferred": output_class in LINE_CLASSES or available_future,
                    "resolution_preserves_source_traceability": bool(
                        source_region_id
                        and source["source_l1_2_resolved_domain_region_id"]
                        and source["source_l1_1_calibrated_domain_region_id"]
                        and source["source_l1_0_domain_region_id"]
                        and source["source_u1_1_region_id"]
                        and source["source_geometry_object_id"] != ""
                    ),
                    "no_semantic_recognition_used": True,
                    "does_not_create_geometry": True,
                    "does_not_delete_support": True,
                    "does_not_modify_upstream": True,
                    "validation_reason": "deferred_support_resolved_by_traceable_line_family" if promote else "support_preserved_or_family_guard_failed",
                    "rejection_or_deferral_reason": "" if output_class in LINE_CLASSES else reason,
                }
            )

            for x, y in points:
                output_region_map[y, x] = g_region_id
                output_class_map[y, x] = DOMAIN_CODE[output_class]
                resolution_kind_map[y, x] = RESOLUTION_KIND_CODE[resolution_kind]
                resolution_confidence_map[y, x] = float(confidence)
                membership_rows.append(
                    {
                        "g1_0_region_id": g_region_id,
                        "source_l1_2_cal_region_id": source_region_id,
                        **source,
                        "x": x,
                        "y": y,
                        "g1_0_domain_class": output_class,
                        "g1_0_resolution_kind": resolution_kind,
                        "g1_0_resolution_confidence": confidence,
                        "line_family_id": line_family_id if promote else 0,
                        "association_score": assoc_score,
                        "excluded_from_g1_0_line_study": excluded,
                        "available_for_future_modules": available_future,
                        "membership_weight": membership_weights.get((source_region_id, x, y), 1.0),
                    }
                )

    output_line_domain = output_class_map == DOMAIN_CODE["line_domain"]
    output_prob_line = output_class_map == DOMAIN_CODE["probable_line_domain"]
    output_non_line = output_class_map == DOMAIN_CODE["non_line_domain"]
    output_prob_non_line = output_class_map == DOMAIN_CODE["probable_non_line_domain"]
    output_mixed = output_class_map == DOMAIN_CODE["mixed_domain"]
    output_deferred = output_class_map == DOMAIN_CODE["deferred_domain"]
    kept_deferred_map = input_deferred & output_deferred
    output_line_study = input_line_study | promoted_map
    output_future_pool = output_non_line | output_prob_non_line | output_mixed | output_deferred

    state_maps = [output_line_domain, output_prob_line, output_non_line, output_prob_non_line, output_mixed, output_deferred]
    overlap = np.zeros(shape, dtype=np.uint8)
    for m in state_maps:
        overlap += m.astype(np.uint8)

    source_manifest_after = {"l1_2_cal": file_manifest(input_dir, REQUIRED_INPUT_FILES)}
    membership_pixel_set = {(as_int(r["x"]), as_int(r["y"])) for r in membership_rows}
    future_membership_set = {
        (as_int(r["x"]), as_int(r["y"]))
        for r in membership_rows
        if str(r["g1_0_domain_class"]) in FUTURE_CLASSES
    }
    promoted_membership_set = {
        (as_int(r["x"]), as_int(r["y"]))
        for r in membership_rows
        if str(r["g1_0_resolution_kind"]) == "promoted_deferred_by_family"
    }
    family_membership_set = {
        (as_int(r["x"]), as_int(r["y"]))
        for r in membership_rows
        if as_int(r["line_family_id"]) > 0
    }
    future_pixel_set = set(zip(np.where(output_future_pool)[1].tolist(), np.where(output_future_pool)[0].tolist()))
    promoted_pixel_set = set(zip(np.where(promoted_map)[1].tolist(), np.where(promoted_map)[0].tolist()))
    changed_map = output_class_map != input_class_map
    changed_pixel_set = set(zip(np.where(changed_map)[1].tolist(), np.where(changed_map)[0].tolist()))
    non_deferred_mask = input_observed & ~input_deferred

    invariants = {
        "all_changed_support_subset_of_l1_2_cal_deferred_support": bool(np.all(~changed_map | input_deferred)),
        "all_unchanged_non_deferred_l1_2_cal_support_preserved": bool(np.all(output_class_map[non_deferred_mask] == input_class_map[non_deferred_mask])),
        "g1_0_line_domain_support_equals_l1_2_cal_line_domain_support": bool(np.array_equal(output_line_domain, input_line_domain)),
        "g1_0_probable_line_domain_support_subset_of_l1_2_cal_observed_support": bool(np.all(~output_prob_line | input_observed)),
        "g1_0_non_line_domain_support_equals_l1_2_cal_non_line_domain_support": bool(np.array_equal(output_non_line, input_non_line)),
        "g1_0_probable_non_line_domain_support_equals_l1_2_cal_probable_non_line_domain_support": bool(np.array_equal(output_prob_non_line, input_prob_non_line)),
        "g1_0_mixed_domain_support_equals_l1_2_cal_mixed_domain_support": bool(np.array_equal(output_mixed, input_mixed)),
        "g1_0_deferred_domain_support_subset_of_l1_2_cal_observed_support": bool(np.all(~output_deferred | input_observed)),
        "all_g1_0_domain_maps_are_mutually_exclusive": bool(np.all(overlap <= 1)),
        "g1_0_line_study_support_excludes_non_line_probable_non_line_mixed_deferred": not bool(np.any(output_line_study & output_future_pool)),
        "g1_0_future_module_pool_includes_non_line_probable_non_line_mixed_deferred": bool(np.all((output_non_line | output_prob_non_line | output_mixed | output_deferred) <= output_future_pool)),
        "g1_0_future_module_pool_preserves_traceability": future_pixel_set.issubset(membership_pixel_set) and future_pixel_set.issubset(future_membership_set),
        "promoted_support_remains_traceable_to_l1_2_cal_deferred_support": promoted_pixel_set.issubset(promoted_membership_set) and all(input_deferred[y, x] for x, y in promoted_pixel_set),
        "promoted_support_has_traceable_family_id": promoted_pixel_set.issubset(family_membership_set) and all(family_id_map[y, x] > 0 for x, y in promoted_pixel_set),
        "kept_deferred_support_is_not_silently_counted_as_clean_line": not bool(np.any(kept_deferred_map & output_line_study)),
        "does_not_create_geometry": True,
        "does_not_create_final_lineobjects": True,
        "does_not_create_axisdescriptors": True,
        "does_not_create_crossings": True,
        "does_not_recognize_text_or_digits": True,
        "does_not_modify_l1_2_cal_outputs": source_manifest_before["l1_2_cal"] == source_manifest_after["l1_2_cal"],
    }

    family_corridor_map = build_family_corridor_map(shape, families)
    np.save(out_dir / "maps" / "g1_0_line_family_corridor_map.npy", family_corridor_map.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_family_explained_candidate_map.npy", candidate_map.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_family_promoted_to_line_map.npy", promoted_map.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_family_kept_deferred_map.npy", kept_deferred_map.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_family_id_map.npy", family_id_map.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_calibrated_line_domain_support_map.npy", output_line_domain.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_calibrated_probable_line_domain_support_map.npy", output_prob_line.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_calibrated_non_line_domain_support_map.npy", output_non_line.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_calibrated_probable_non_line_domain_support_map.npy", output_prob_non_line.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_calibrated_mixed_domain_support_map.npy", output_mixed.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_calibrated_deferred_domain_support_map.npy", output_deferred.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_calibrated_line_study_support_map.npy", output_line_study.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_calibrated_future_module_pool_map.npy", output_future_pool.astype(np.uint16))
    np.save(out_dir / "maps" / "g1_0_domain_region_id_map.npy", output_region_map.astype(np.int32))
    np.save(out_dir / "maps" / "g1_0_domain_class_map.npy", output_class_map.astype(np.uint8))
    np.save(out_dir / "maps" / "g1_0_resolution_kind_map.npy", resolution_kind_map.astype(np.uint8))
    np.save(out_dir / "maps" / "g1_0_resolution_confidence_map.npy", resolution_confidence_map.astype(np.float32))

    write_csv(out_dir / "g1_0_line_families.csv", family_rows, FAMILY_FIELDS)
    write_csv(out_dir / "g1_0_deferred_family_associations.csv", association_rows, ASSOCIATION_FIELDS)
    write_csv(out_dir / "g1_0_calibrated_domain_regions.csv", region_rows, REGION_FIELDS)
    write_csv(out_dir / "g1_0_calibrated_domain_memberships.csv", membership_rows, MEMBERSHIP_FIELDS)
    write_csv(
        out_dir / "g1_0_promoted_to_line.csv",
        [r for r in membership_rows if r["g1_0_resolution_kind"] == "promoted_deferred_by_family"],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "g1_0_kept_deferred.csv",
        [r for r in membership_rows if r["source_l1_2_cal_domain_class"] == "deferred_domain" and r["g1_0_domain_class"] == "deferred_domain"],
        MEMBERSHIP_FIELDS,
    )
    write_csv(out_dir / "g1_0_domain_validation.csv", validation_rows, VALIDATION_FIELDS)
    write_csv(
        out_dir / "g1_0_line_study_support.csv",
        [r for r in membership_rows if r["g1_0_domain_class"] in LINE_CLASSES and output_line_study[as_int(r["y"]), as_int(r["x"])]],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "g1_0_future_module_pool.csv",
        [r for r in membership_rows if r["g1_0_domain_class"] in FUTURE_CLASSES and output_future_pool[as_int(r["y"]), as_int(r["x"])]],
        MEMBERSHIP_FIELDS,
    )

    make_visuals(
        out_dir=out_dir,
        input_class_map=input_class_map,
        output_class_map=output_class_map,
        input_line_study=input_line_study,
        families=families,
        candidate_map=candidate_map,
        promoted_map=promoted_map,
        kept_deferred_map=kept_deferred_map,
        line_study=output_line_study,
        future_pool=output_future_pool,
    )

    counts = {
        "input_l1_2_cal_deferred_pixels_seen": int(np.count_nonzero(input_deferred)),
        "line_family_count": len(families),
        "horizontal_line_family_count": len(horizontal_families),
        "vertical_line_family_count": len(vertical_families),
        "family_explained_candidate_pixels": int(np.count_nonzero(candidate_map)),
        "family_promoted_to_line_pixels": int(np.count_nonzero(promoted_map)),
        "family_kept_deferred_pixels": int(np.count_nonzero(kept_deferred_map)),
        "g1_0_line_study_support_pixels": int(np.count_nonzero(output_line_study)),
        "g1_0_future_module_pool_pixels": int(np.count_nonzero(output_future_pool)),
        "input_l1_2_cal_line_study_support_pixels": int(np.count_nonzero(input_line_study)),
        "input_l1_2_cal_future_module_pool_pixels": int(np.count_nonzero(input_future_pool)),
        "g1_0_region_count": len(region_rows),
        "family_association_region_count": len(association_rows),
        "resolution_kind_region_counts": dict(Counter(r["g1_0_resolution_kind"] for r in region_rows)),
        "g1_0_domain_class_region_counts": dict(Counter(r["g1_0_domain_class"] for r in region_rows)),
    }
    metrics = {
        "line_study_delta_ratio_vs_l1_2_cal": ratio(counts["g1_0_line_study_support_pixels"] - counts["input_l1_2_cal_line_study_support_pixels"], counts["input_l1_2_cal_line_study_support_pixels"]),
        "deferred_reduction_ratio_vs_l1_2_cal": ratio(counts["input_l1_2_cal_deferred_pixels_seen"] - counts["family_kept_deferred_pixels"], counts["input_l1_2_cal_deferred_pixels_seen"]),
        "future_pool_traceability_rate": ratio(len(future_pixel_set & membership_pixel_set), len(future_pixel_set)),
        "family_resolution_traceability_rate": 1.0 if not promoted_pixel_set else ratio(len(promoted_pixel_set & promoted_membership_set), len(promoted_pixel_set)),
        "family_id_traceability_rate": 1.0 if not promoted_pixel_set else ratio(len(promoted_pixel_set & family_membership_set), len(promoted_pixel_set)),
        "changed_support_pixels": int(np.count_nonzero(changed_map)),
        "changed_support_subset_rate": 1.0 if not changed_pixel_set else ratio(sum(1 for x, y in changed_pixel_set if input_deferred[y, x]), len(changed_pixel_set)),
    }
    contract = {
        "is_family_resolver_not_final_line_extractor": True,
        "builds_families_from_l1_2_cal_line_study_support": True,
        "allowed_change_is_only_deferred_to_probable_line_domain": True,
        "creates_final_geometry": False,
        "creates_final_lineobjects": False,
        "creates_axis_descriptors": False,
        "creates_crossings": False,
        "recognizes_ocr_strings": False,
        "recognizes_digit_values": False,
        "uses_grid_audit_truth_as_runtime_input": False,
        "unresolved_deferred_support_is_preserved": True,
        "g1_0_line_study_support_is_not_final_geometry": True,
    }

    output_missing_pre_json = missing_required(out_dir, [rel for rel in REQUIRED_OUTPUT_FILES if rel not in {"summary.json", "contract_audit.json"}])
    status = "completed" if all(invariants.values()) and not output_missing_pre_json else "failed_contract"
    outputs = {rel.replace("/", "_").replace(".", "_"): rel for rel in REQUIRED_OUTPUT_FILES}
    summary = {
        "version": VERSION,
        "status": status,
        "source_l1_2_cal_run_dir": str(input_dir),
        "source_l1_2_cal_version": input_summary.get("version", ""),
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
        "visual_acceptance_note": "Visual audit remains mandatory because G1.0 has no line-domain ground-truth dataset.",
    }
    contract_audit = {
        "version": VERSION,
        "status": status,
        "semantic_rule": "g1_0_promotes_only_traceable_l1_2_cal_deferred_support_explained_by_line_family",
        "traceability_rule": "all_promoted_support_has_source_pixels_and_family_id",
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
    ap.add_argument("--l1-2-cal-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-association-score", type=float, default=0.47)
    ap.add_argument("--max-microstructure-score", type=float, default=0.66)
    ap.add_argument("--max-mixed-contact-score", type=float, default=0.48)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config(
        min_association_score=args.min_association_score,
        max_microstructure_score=args.max_microstructure_score,
        max_mixed_contact_score=args.max_mixed_contact_score,
    )
    run(
        input_dir=Path(args.l1_2_cal_dir),
        out_dir=Path(args.out),
        cfg=cfg,
    )


if __name__ == "__main__":
    main()
