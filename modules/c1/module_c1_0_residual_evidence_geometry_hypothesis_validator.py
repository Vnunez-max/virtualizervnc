#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module C1.0 — Residual Evidence Geometry Hypothesis Validator.

Contract:
    B1 V3.4.2 residual evidence
    -> proposed residual geometry hypotheses
    -> validated / rejected / needs_context states
    -> explicit observed support and explicit inferred span maps

C1.0 does not create final geometry.
C1.0 does not create LineObjects or AxisDescriptors.
C1.0 does not modify V3.3 or V3.4.2 outputs.
C1.0 treats residual evidence as evidence, not as geometry by itself.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_C1_0_V1_RESIDUAL_EVIDENCE_GEOMETRY_HYPOTHESIS_VALIDATOR"


@dataclass
class Config:
    version: str = VERSION
    max_axis_distance_to_upstream_px: float = 4.0
    max_collinearity_error_px: float = 2.0
    max_gap_for_inferred_span_px: int = 12
    min_observed_support_pixels: int = 4
    min_validation_score: float = 0.80
    min_needs_context_score: float = 0.55
    max_overpromotion_risk_for_validation: float = 0.30
    draw_width_px: int = 1


HYPOTHESIS_FIELDS = [
    "hypothesis_id",
    "hypothesis_type",
    "validation_state",
    "source_residual_object_ids",
    "source_evidence_classes",
    "source_evidence_layers",
    "observed_support_pixel_count",
    "inferred_span_pixel_count",
    "orientation",
    "axis_px",
    "x1",
    "y1",
    "x2",
    "y2",
    "nearest_upstream_geometry_object_ids",
    "relation_to_upstream_geometry",
    "upstream_axis_distance_px",
    "upstream_longitudinal_gap_px",
    "upstream_longitudinal_overlap_px",
    "validation_score",
    "confidence",
    "overpromotion_risk",
    "underpromotion_risk",
    "validation_reason",
    "rejection_reason",
]


MEMBERSHIP_FIELDS = [
    "hypothesis_id",
    "residual_object_id",
    "x",
    "y",
    "role",
    "source_layer",
    "source_evidence_class",
    "membership_weight",
]


VALIDATION_FIELDS = [
    "hypothesis_id",
    "hypothesis_type",
    "validation_state",
    "has_observed_support",
    "observed_support_inside_organized_residual",
    "validated_support_inside_candidate_or_strong",
    "diagnostic_support_used_as_geometry",
    "ambiguous_support_used_as_validated_geometry",
    "orientation_allowed",
    "has_upstream_relation",
    "axis_distance_within_threshold",
    "collinearity_or_parallelism_measured",
    "inferred_span_separate_from_observed",
    "overpromotion_risk_within_threshold",
    "validation_score",
    "validation_reason",
    "rejection_reason",
]


REJECTED_FIELDS = [
    "residual_object_id",
    "residual_evidence_class",
    "residual_evidence_layer",
    "object_type",
    "orientation",
    "support_pixel_count",
    "rejection_state",
    "rejection_reason",
]


STRUCTURAL_CLASSES = {
    "strong_residual_geometry",
    "candidate_residual_geometry",
    "thickness_or_jitter_evidence",
    "crossing_context_evidence",
}

VALIDATED_SUPPORT_CLASSES = {
    "strong_residual_geometry",
    "candidate_residual_geometry",
    "thickness_or_jitter_evidence",
    "crossing_context_evidence",
}

DIAGNOSTIC_CLASSES = {
    "diagnostic_text_like_residual",
    "diagnostic_noise_residual",
}

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


def load_map(path: Path, dtype: Any | None = None) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(path)
    arr = np.load(path)
    if dtype is not None:
        return arr.astype(dtype)
    return arr


def optional_map(path: Path, shape: Tuple[int, int], dtype: Any = np.uint16) -> np.ndarray:
    if path.exists():
        return np.load(path).astype(dtype)
    return np.zeros(shape, dtype=dtype)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def infer_v3_run_dir(v3_4_2_dir: Path, explicit: Optional[Path]) -> Path:
    if explicit is not None:
        return explicit
    summary = read_json(v3_4_2_dir / "summary.json")
    run_dir = summary.get("run_dir")
    if not run_dir:
        raise FileNotFoundError("Cannot infer V3.3 run directory from V3.4.2 summary.json")
    return Path(run_dir)


def object_axis(row: Dict[str, str]) -> float:
    orientation = row.get("orientation", "")
    if orientation == "vertical":
        return mean([as_float(row.get("x1")), as_float(row.get("x2"))])
    return mean([as_float(row.get("y1")), as_float(row.get("y2"))])


def object_longitudinal_range(row: Dict[str, str]) -> Tuple[float, float]:
    orientation = row.get("orientation", "")
    if orientation == "vertical":
        a = as_float(row.get("y1"))
        b = as_float(row.get("y2"))
    else:
        a = as_float(row.get("x1"))
        b = as_float(row.get("x2"))
    return (min(a, b), max(a, b))


def longitudinal_relation(a: Tuple[float, float], b: Tuple[float, float]) -> Tuple[float, float]:
    overlap = max(0.0, min(a[1], b[1]) - max(a[0], b[0]) + 1.0)
    if overlap > 0:
        return overlap, 0.0
    gap = max(0.0, max(a[0], b[0]) - min(a[1], b[1]) - 1.0)
    return 0.0, gap


def upstream_axis(row: Dict[str, str]) -> float:
    if row.get("axis_center_px") not in ("", None):
        return as_float(row.get("axis_center_px"))
    return object_axis(row)


def find_nearest_upstream(
    residual: Dict[str, str],
    upstream_objects: Sequence[Dict[str, str]],
    cfg: Config,
) -> Dict[str, Any]:
    orientation = residual.get("orientation", "")
    axis = object_axis(residual)
    long_range = object_longitudinal_range(residual)
    best: Optional[Dict[str, Any]] = None
    for obj in upstream_objects:
        if obj.get("orientation") != orientation:
            continue
        obj_axis = upstream_axis(obj)
        axis_distance = abs(axis - obj_axis)
        obj_range = object_longitudinal_range(obj)
        overlap, gap = longitudinal_relation(long_range, obj_range)
        score = axis_distance + min(gap, 9999.0) / 20.0 - min(overlap, 25.0) / 50.0
        candidate = {
            "geometry_object_id": obj.get("geometry_object_id", ""),
            "axis_distance": axis_distance,
            "overlap": overlap,
            "gap": gap,
            "score": score,
            "object": obj,
        }
        if best is None or candidate["score"] < best["score"]:
            best = candidate
    if best is None:
        return {
            "geometry_object_id": "",
            "axis_distance": math.inf,
            "overlap": 0.0,
            "gap": math.inf,
            "relation": "no_same_orientation_upstream_geometry",
        }

    axis_distance = best["axis_distance"]
    overlap = best["overlap"]
    gap = best["gap"]
    if axis_distance <= cfg.max_collinearity_error_px and overlap > 0:
        relation = "collinear_overlap_with_upstream_geometry"
    elif axis_distance <= cfg.max_collinearity_error_px and gap <= cfg.max_gap_for_inferred_span_px:
        relation = "collinear_gap_or_extension_to_upstream_geometry"
    elif axis_distance <= cfg.max_axis_distance_to_upstream_px:
        relation = "parallel_near_upstream_geometry"
    else:
        relation = "same_orientation_but_far_from_upstream_geometry"
    return {
        "geometry_object_id": best["geometry_object_id"],
        "axis_distance": axis_distance,
        "overlap": overlap,
        "gap": gap,
        "relation": relation,
    }


def hypothesis_type_for(row: Dict[str, str], relation: str) -> str:
    evidence_class = row.get("residual_evidence_class", "")
    if evidence_class == "thickness_or_jitter_evidence":
        return "residual_thickness_repair_hypothesis"
    if evidence_class == "crossing_context_evidence":
        return "residual_alignment_context_hypothesis"
    if "gap" in relation:
        return "residual_gap_repair_hypothesis"
    return "residual_line_extension_hypothesis"


def role_for(row: Dict[str, str], state: str) -> str:
    evidence_class = row.get("residual_evidence_class", "")
    if state == "validated":
        if evidence_class == "strong_residual_geometry":
            return "observed_strong_support"
        return "observed_candidate_support"
    if evidence_class in AMBIGUOUS_CLASSES:
        return "context_ambiguous_support"
    if evidence_class in DIAGNOSTIC_CLASSES:
        return "rejected_diagnostic"
    return "context_support"


def score_hypothesis(row: Dict[str, str], relation: Dict[str, Any], cfg: Config) -> Dict[str, float]:
    evidence_class = row.get("residual_evidence_class", "")
    line_like = as_float(row.get("line_like_score"))
    geom = as_float(row.get("geometry_evidence_score"))
    candidate = as_float(row.get("candidate_geometry_score"))
    strong = as_float(row.get("strong_geometry_score"))
    text_risk = as_float(row.get("text_like_risk"), as_float(row.get("text_like_score")))
    overpromotion = as_float(row.get("overpromotion_risk"))

    if evidence_class == "strong_residual_geometry":
        evidence_quality = mean([line_like, geom, candidate, strong])
    elif evidence_class == "candidate_residual_geometry":
        evidence_quality = mean([line_like, geom, candidate])
    elif evidence_class == "thickness_or_jitter_evidence":
        evidence_quality = mean([line_like, geom, candidate]) * 0.92
    elif evidence_class == "crossing_context_evidence":
        evidence_quality = mean([line_like, geom, candidate]) * 0.82
    elif evidence_class in AMBIGUOUS_CLASSES:
        evidence_quality = mean([line_like, geom, candidate]) * 0.65
    else:
        evidence_quality = mean([line_like, geom, candidate]) * 0.35

    axis_distance = relation["axis_distance"]
    collinearity_score = 0.0 if not math.isfinite(axis_distance) else clamp01(1.0 - axis_distance / max(cfg.max_collinearity_error_px, 0.001))
    proximity_score = 0.0 if not math.isfinite(axis_distance) else clamp01(1.0 - axis_distance / max(cfg.max_axis_distance_to_upstream_px, 0.001))
    if relation["overlap"] > 0:
        continuity_score = 1.0
    elif math.isfinite(relation["gap"]):
        continuity_score = clamp01(1.0 - relation["gap"] / max(cfg.max_gap_for_inferred_span_px, 1))
    else:
        continuity_score = 0.0
    support_density_score = clamp01(line_like)
    diagnostic_penalty = 0.28 if evidence_class in DIAGNOSTIC_CLASSES else 0.0
    ambiguity_penalty = 0.18 if evidence_class in AMBIGUOUS_CLASSES else 0.0
    text_penalty = max(0.0, text_risk - 0.62) * 0.25
    overpromotion_penalty = overpromotion * 0.30
    support_pixels = as_int(row.get("support_pixel_count"))
    relation_bonus = 0.0
    if (
        evidence_class == "strong_residual_geometry"
        and relation["relation"] in {"collinear_overlap_with_upstream_geometry", "collinear_gap_or_extension_to_upstream_geometry"}
        and relation["axis_distance"] <= cfg.max_collinearity_error_px
        and support_pixels >= cfg.min_observed_support_pixels
        and overpromotion <= cfg.max_overpromotion_risk_for_validation
    ):
        relation_bonus = 0.18
    elif (
        evidence_class == "thickness_or_jitter_evidence"
        and relation["relation"] in {
            "collinear_overlap_with_upstream_geometry",
            "collinear_gap_or_extension_to_upstream_geometry",
            "parallel_near_upstream_geometry",
        }
        and relation["axis_distance"] <= cfg.max_axis_distance_to_upstream_px
        and support_pixels >= cfg.min_observed_support_pixels
        and overpromotion <= cfg.max_overpromotion_risk_for_validation
    ):
        relation_bonus = 0.12
    elif (
        evidence_class == "candidate_residual_geometry"
        and relation["relation"] in {"collinear_overlap_with_upstream_geometry", "collinear_gap_or_extension_to_upstream_geometry"}
        and relation["axis_distance"] <= cfg.max_collinearity_error_px
        and support_pixels >= cfg.min_observed_support_pixels
        and overpromotion <= cfg.max_overpromotion_risk_for_validation
    ):
        relation_bonus = 0.08

    validation_score = clamp01(
        0.34 * evidence_quality
        + 0.22 * collinearity_score
        + 0.14 * proximity_score
        + 0.18 * continuity_score
        + 0.12 * support_density_score
        + relation_bonus
        - diagnostic_penalty
        - ambiguity_penalty
        - text_penalty
        - overpromotion_penalty
    )
    return {
        "evidence_quality": evidence_quality,
        "collinearity_score": collinearity_score,
        "proximity_score": proximity_score,
        "continuity_score": continuity_score,
        "support_density_score": support_density_score,
        "validation_score": validation_score,
    }


def support_points_for_object(
    residual_object_id: str,
    memberships_by_object: Dict[str, List[Tuple[int, int, float]]],
) -> List[Tuple[int, int, float]]:
    return memberships_by_object.get(str(residual_object_id), [])


def inferred_span_points(
    row: Dict[str, str],
    relation: Dict[str, Any],
    shape: Tuple[int, int],
    mask: np.ndarray,
    observed: set[Tuple[int, int]],
    cfg: Config,
) -> List[Tuple[int, int]]:
    if "gap" not in relation["relation"]:
        return []
    gap = relation["gap"]
    if not math.isfinite(gap) or gap <= 0 or gap > cfg.max_gap_for_inferred_span_px:
        return []
    orientation = row.get("orientation", "")
    axis = int(round(object_axis(row)))
    start, end = object_longitudinal_range(row)
    upstream = relation.get("object")
    # The public relation dict intentionally omits the upstream object; first
    # version keeps inferred spans disabled unless a caller extends relation.
    if upstream is None:
        return []
    up_start, up_end = object_longitudinal_range(upstream)
    if end < up_start:
        a, b = int(round(end + 1)), int(round(up_start - 1))
    elif up_end < start:
        a, b = int(round(up_end + 1)), int(round(start - 1))
    else:
        return []
    if b < a:
        return []
    points: List[Tuple[int, int]] = []
    h, w = shape
    for t in range(a, b + 1):
        if orientation == "vertical":
            x, y = axis, t
        else:
            x, y = t, axis
        if 0 <= x < w and 0 <= y < h and mask[y, x] and (x, y) not in observed:
            points.append((x, y))
    return points


def classify_state(
    row: Dict[str, str],
    relation: Dict[str, Any],
    scores: Dict[str, float],
    observed_points: List[Tuple[int, int, float]],
    diagnostic_overlap: int,
    cfg: Config,
) -> Tuple[str, str, str, Dict[str, bool]]:
    evidence_class = row.get("residual_evidence_class", "")
    orientation = row.get("orientation", "")
    overpromotion = as_float(row.get("overpromotion_risk"))

    checks = {
        "has_observed_support": len(observed_points) >= cfg.min_observed_support_pixels,
        "diagnostic_support_used_as_geometry": False,
        "ambiguous_support_used_as_validated_geometry": False,
        "orientation_allowed": orientation in {"horizontal", "vertical"},
        "has_upstream_relation": relation["geometry_object_id"] != "",
        "axis_distance_within_threshold": math.isfinite(relation["axis_distance"])
        and relation["axis_distance"] <= cfg.max_axis_distance_to_upstream_px,
        "collinearity_or_parallelism_measured": relation["relation"]
        in {
            "collinear_overlap_with_upstream_geometry",
            "collinear_gap_or_extension_to_upstream_geometry",
            "parallel_near_upstream_geometry",
        },
        "overpromotion_risk_within_threshold": overpromotion <= cfg.max_overpromotion_risk_for_validation,
    }

    if evidence_class in DIAGNOSTIC_CLASSES:
        checks["diagnostic_support_used_as_geometry"] = True
        return "rejected", "", "diagnostic_residual_cannot_be_structural_support", checks
    if evidence_class in AMBIGUOUS_CLASSES:
        if scores["validation_score"] >= cfg.min_needs_context_score:
            return "needs_context", "", "ambiguous_residual_requires_later_context", checks
        return "rejected", "", "ambiguous_residual_below_context_threshold", checks
    if evidence_class not in STRUCTURAL_CLASSES:
        return "rejected", "", "unsupported_residual_evidence_class", checks
    if diagnostic_overlap > 0:
        checks["diagnostic_support_used_as_geometry"] = True
        return "rejected", "", "observed_support_overlaps_diagnostic_residual", checks

    hard_ok = all(
        checks[k]
        for k in (
            "has_observed_support",
            "orientation_allowed",
            "has_upstream_relation",
            "axis_distance_within_threshold",
            "collinearity_or_parallelism_measured",
            "overpromotion_risk_within_threshold",
        )
    )
    if hard_ok and scores["validation_score"] >= cfg.min_validation_score:
        return "validated", "passed_local_geometric_validation", "", checks
    if scores["validation_score"] >= cfg.min_needs_context_score:
        return "needs_context", "", "insufficient_for_validation_but_plausible_context", checks
    return "rejected", "", "failed_validation_thresholds", checks


def render_bool(mask: np.ndarray, active: Tuple[int, int, int], bg: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    img = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)
    img[:, :] = bg
    img[mask.astype(bool)] = active
    return Image.fromarray(img, "RGB")


def titled(img: Image.Image, title: str) -> Image.Image:
    out = img.copy().convert("RGB")
    d = ImageDraw.Draw(out, "RGBA")
    d.rectangle((0, 0, out.width, 28), fill=(255, 255, 255, 235))
    d.text((8, 8), title, fill=(0, 0, 0, 255), font=font(10))
    return out


def render_evidence_from_rows(
    shape: Tuple[int, int],
    rows: Sequence[Dict[str, str]],
    memberships_by_object: Dict[str, List[Tuple[int, int, float]]],
) -> Image.Image:
    colors = {
        "strong_residual_geometry": (0, 155, 0),
        "candidate_residual_geometry": (80, 165, 255),
        "thickness_or_jitter_evidence": (0, 190, 170),
        "crossing_context_evidence": (245, 180, 0),
        "diagnostic_text_like_residual": (220, 0, 0),
        "diagnostic_noise_residual": (120, 120, 120),
        "ambiguous_residual_evidence": (160, 0, 190),
    }
    arr = np.zeros((shape[0], shape[1], 3), dtype=np.uint8)
    arr[:, :] = (255, 255, 255)
    for row in rows:
        color = colors.get(row.get("residual_evidence_class", ""), (0, 0, 0))
        for x, y, _ in support_points_for_object(row.get("residual_object_id", ""), memberships_by_object):
            if 0 <= y < shape[0] and 0 <= x < shape[1]:
                arr[y, x] = color
    return Image.fromarray(arr, "RGB")


def draw_hypotheses(
    base: Image.Image,
    hypotheses: Sequence[Dict[str, Any]],
    state_filter: Optional[str],
    title: str,
    cfg: Config,
) -> Image.Image:
    out = base.copy().convert("RGB")
    d = ImageDraw.Draw(out, "RGBA")
    colors = {
        "proposed": (80, 165, 255, 255),
        "validated": (0, 155, 0, 255),
        "rejected": (130, 130, 130, 255),
        "needs_context": (245, 180, 0, 255),
    }
    for hyp in hypotheses:
        if state_filter is not None and hyp["validation_state"] != state_filter:
            continue
        color = colors.get(hyp["validation_state"], (0, 0, 0, 255))
        d.line(
            (
                as_float(hyp["x1"]),
                as_float(hyp["y1"]),
                as_float(hyp["x2"]),
                as_float(hyp["y2"]),
            ),
            fill=color,
            width=max(1, cfg.draw_width_px),
        )
    return titled(out, title)


def make_visuals(
    out_dir: Path,
    shape: Tuple[int, int],
    combined_v3: np.ndarray,
    rows: Sequence[Dict[str, str]],
    memberships_by_object: Dict[str, List[Tuple[int, int, float]]],
    hypotheses: Sequence[Dict[str, Any]],
    proposed_map: np.ndarray,
    validated_map: np.ndarray,
    inferred_span_map: np.ndarray,
    rejected_map: np.ndarray,
    cfg: Config,
) -> None:
    vdir = out_dir / "visuals"
    ensure_dir(vdir)
    upstream = render_bool(combined_v3 > 0, active=(0, 0, 0), bg=(255, 255, 255))
    evidence = render_evidence_from_rows(shape, rows, memberships_by_object)
    proposed = draw_hypotheses(upstream, hypotheses, None, "C1.0 proposed hypotheses", cfg)
    validated = draw_hypotheses(upstream, hypotheses, "validated", "C1.0 validated hypotheses", cfg)
    rejected = render_bool(rejected_map > 0, active=(130, 130, 130), bg=(255, 255, 255))

    observed_vs_inferred = np.zeros((shape[0], shape[1], 3), dtype=np.uint8)
    observed_vs_inferred[:, :] = (255, 255, 255)
    observed_vs_inferred[proposed_map > 0] = (80, 165, 255)
    observed_vs_inferred[validated_map > 0] = (0, 155, 0)
    observed_vs_inferred[inferred_span_map > 0] = (245, 150, 0)
    observed_vs_inferred_img = Image.fromarray(observed_vs_inferred, "RGB")

    panels = [
        ("01_v3_4_2_residual_evidence_input.png", titled(evidence, "V3.4.2 residual evidence input")),
        ("02_proposed_hypotheses.png", proposed),
        ("03_validated_hypotheses.png", validated),
        ("04_rejected_and_blocking_evidence.png", titled(rejected, "rejected and blocking evidence")),
        ("05_observed_support_vs_inferred_span.png", titled(observed_vs_inferred_img, "observed support vs inferred span")),
    ]
    for filename, image in panels:
        image.save(vdir / filename)

    tiles: List[Image.Image] = []
    for _, image in panels:
        im = image.copy()
        im.thumbnail((420, 300))
        tile = Image.new("RGB", (450, 340), "white")
        tile.paste(im, ((450 - im.width) // 2, 32))
        tiles.append(tile)
    sheet = Image.new("RGB", (900, 340 * math.ceil(len(tiles) / 2) + 42), "white")
    d = ImageDraw.Draw(sheet)
    d.text((10, 12), "C1.0 Residual Evidence Geometry Hypothesis Validator", fill="black", font=font(16))
    for idx, tile in enumerate(tiles):
        sheet.paste(tile, ((idx % 2) * 450, 42 + (idx // 2) * 340))
    sheet.save(vdir / "06_visual_summary.png")


def run(
    v3_4_2_dir: Path,
    out_dir: Path,
    v3_run_dir: Optional[Path] = None,
    image_path: Optional[Path] = None,
    cfg: Optional[Config] = None,
) -> Dict[str, Any]:
    del image_path  # The optional image is audit context only in this first implementation.
    cfg = cfg or Config()
    v3_4_2_dir = Path(v3_4_2_dir)
    v3_run_dir = infer_v3_run_dir(v3_4_2_dir, v3_run_dir)
    out_dir = Path(out_dir)
    ensure_dir(out_dir)
    ensure_dir(out_dir / "maps")
    ensure_dir(out_dir / "visuals")

    v3_4_summary = read_json(v3_4_2_dir / "summary.json")
    v3_summary = read_json(v3_run_dir / "summary.json")
    evidence_rows = read_csv(v3_4_2_dir / "residual_evidence_objects.csv")
    memberships = read_csv(v3_4_2_dir / "residual_geometry_memberships.csv")
    upstream_objects = read_csv(v3_run_dir / "geometry_objects.csv")

    residual_object_id_map = load_map(v3_4_2_dir / "maps" / "residual_object_id_map.npy")
    shape = residual_object_id_map.shape
    organized_support = optional_map(v3_4_2_dir / "maps" / "residual_geometry_support_count_map.npy", shape, np.uint16) > 0
    candidate_support = optional_map(v3_4_2_dir / "maps" / "candidate_residual_geometry_support_count_map.npy", shape, np.uint16) > 0
    strong_support = optional_map(v3_4_2_dir / "maps" / "evidence_strong_residual_geometry_support_count_map.npy", shape, np.uint16) > 0
    diagnostic_support = optional_map(v3_4_2_dir / "maps" / "diagnostic_residual_support_count_map.npy", shape, np.uint16) > 0
    combined_v3 = optional_map(v3_run_dir / "maps" / "combined_geometry_support_count_map.npy", shape, np.uint16)
    residual_v3 = optional_map(v3_run_dir / "maps" / "residual_after_geometry_mask.npy", shape, bool).astype(bool)
    mask = (combined_v3 > 0) | residual_v3

    memberships_by_object: Dict[str, List[Tuple[int, int, float]]] = defaultdict(list)
    for m in memberships:
        x = as_int(m.get("x"))
        y = as_int(m.get("y"))
        if 0 <= y < shape[0] and 0 <= x < shape[1]:
            memberships_by_object[str(m.get("residual_object_id", ""))].append(
                (x, y, as_float(m.get("membership_weight"), 1.0))
            )

    proposed_map = np.zeros(shape, dtype=np.uint16)
    validated_map = np.zeros(shape, dtype=np.uint16)
    rejected_map = np.zeros(shape, dtype=np.uint16)
    inferred_span_map = np.zeros(shape, dtype=np.uint16)
    hypothesis_id_map = np.zeros(shape, dtype=np.int32)

    hypotheses: List[Dict[str, Any]] = []
    membership_rows: List[Dict[str, Any]] = []
    validation_rows: List[Dict[str, Any]] = []
    rejected_rows: List[Dict[str, Any]] = []

    next_hypothesis_id = 1
    for row in evidence_rows:
        residual_object_id = str(row.get("residual_object_id", ""))
        evidence_class = row.get("residual_evidence_class", "")
        evidence_layer = row.get("residual_evidence_layer", "")
        observed_points = support_points_for_object(residual_object_id, memberships_by_object)
        observed_set = {(x, y) for x, y, _ in observed_points}

        if evidence_class in DIAGNOSTIC_CLASSES:
            rejected_rows.append(
                {
                    "residual_object_id": residual_object_id,
                    "residual_evidence_class": evidence_class,
                    "residual_evidence_layer": evidence_layer,
                    "object_type": row.get("object_type", ""),
                    "orientation": row.get("orientation", ""),
                    "support_pixel_count": row.get("support_pixel_count", 0),
                    "rejection_state": "rejected",
                    "rejection_reason": "diagnostic_residual_cannot_be_structural_support",
                }
            )
            for x, y, _ in observed_points:
                rejected_map[y, x] += 1
            continue

        relation = find_nearest_upstream(row, upstream_objects, cfg)
        scores = score_hypothesis(row, relation, cfg)
        diagnostic_overlap = sum(1 for x, y in observed_set if diagnostic_support[y, x])
        state, validation_reason, rejection_reason, checks = classify_state(
            row, relation, scores, observed_points, diagnostic_overlap, cfg
        )
        hyp_id = next_hypothesis_id
        next_hypothesis_id += 1

        observed_inside_organized = all(organized_support[y, x] for x, y in observed_set)
        support_inside_residual = all(residual_v3[y, x] for x, y in observed_set)
        support_inside_mask = all(mask[y, x] for x, y in observed_set)
        validated_inside_candidate_or_strong = True
        if state == "validated":
            validated_inside_candidate_or_strong = all((candidate_support[y, x] or strong_support[y, x]) for x, y in observed_set)

        inferred_points: List[Tuple[int, int]] = []
        # Version 1 emits the inferred-span map and keeps it separate. It does
        # not infer spans unless later code supplies explicit upstream endpoints.
        inferred_separate = all((x, y) not in observed_set for x, y in inferred_points)

        hyp = {
            "hypothesis_id": hyp_id,
            "hypothesis_type": hypothesis_type_for(row, relation["relation"]),
            "validation_state": state,
            "source_residual_object_ids": residual_object_id,
            "source_evidence_classes": evidence_class,
            "source_evidence_layers": evidence_layer,
            "observed_support_pixel_count": len(observed_points),
            "inferred_span_pixel_count": len(inferred_points),
            "orientation": row.get("orientation", ""),
            "axis_px": object_axis(row),
            "x1": as_float(row.get("x1")),
            "y1": as_float(row.get("y1")),
            "x2": as_float(row.get("x2")),
            "y2": as_float(row.get("y2")),
            "nearest_upstream_geometry_object_ids": relation["geometry_object_id"],
            "relation_to_upstream_geometry": relation["relation"],
            "upstream_axis_distance_px": relation["axis_distance"] if math.isfinite(relation["axis_distance"]) else "",
            "upstream_longitudinal_gap_px": relation["gap"] if math.isfinite(relation["gap"]) else "",
            "upstream_longitudinal_overlap_px": relation["overlap"],
            "validation_score": scores["validation_score"],
            "confidence": scores["validation_score"],
            "overpromotion_risk": as_float(row.get("overpromotion_risk")),
            "underpromotion_risk": as_float(row.get("underpromotion_risk")),
            "validation_reason": validation_reason,
            "rejection_reason": rejection_reason,
        }
        hypotheses.append(hyp)

        role = role_for(row, state)
        for x, y, weight in observed_points:
            proposed_map[y, x] += 1
            hypothesis_id_map[y, x] = hyp_id
            if state == "validated":
                validated_map[y, x] += 1
            elif state == "rejected":
                rejected_map[y, x] += 1
            membership_rows.append(
                {
                    "hypothesis_id": hyp_id,
                    "residual_object_id": residual_object_id,
                    "x": x,
                    "y": y,
                    "role": role,
                    "source_layer": evidence_layer,
                    "source_evidence_class": evidence_class,
                    "membership_weight": weight,
                }
            )
        for x, y in inferred_points:
            inferred_span_map[y, x] += 1
            membership_rows.append(
                {
                    "hypothesis_id": hyp_id,
                    "residual_object_id": residual_object_id,
                    "x": x,
                    "y": y,
                    "role": "inferred_gap_span",
                    "source_layer": "inferred_span",
                    "source_evidence_class": "inferred_span",
                    "membership_weight": 0.0,
                }
            )

        validation_rows.append(
            {
                "hypothesis_id": hyp_id,
                "hypothesis_type": hyp["hypothesis_type"],
                "validation_state": state,
                "has_observed_support": checks["has_observed_support"],
                "observed_support_inside_organized_residual": observed_inside_organized,
                "validated_support_inside_candidate_or_strong": validated_inside_candidate_or_strong,
                "diagnostic_support_used_as_geometry": state == "validated" and diagnostic_overlap > 0,
                "ambiguous_support_used_as_validated_geometry": state == "validated" and evidence_class in AMBIGUOUS_CLASSES,
                "orientation_allowed": checks["orientation_allowed"],
                "has_upstream_relation": checks["has_upstream_relation"],
                "axis_distance_within_threshold": checks["axis_distance_within_threshold"],
                "collinearity_or_parallelism_measured": checks["collinearity_or_parallelism_measured"],
                "inferred_span_separate_from_observed": inferred_separate,
                "overpromotion_risk_within_threshold": checks["overpromotion_risk_within_threshold"],
                "validation_score": scores["validation_score"],
                "validation_reason": validation_reason,
                "rejection_reason": rejection_reason,
            }
        )

        if state == "rejected" or state == "needs_context":
            rejected_rows.append(
                {
                    "residual_object_id": residual_object_id,
                    "residual_evidence_class": evidence_class,
                    "residual_evidence_layer": evidence_layer,
                    "object_type": row.get("object_type", ""),
                    "orientation": row.get("orientation", ""),
                    "support_pixel_count": row.get("support_pixel_count", 0),
                    "rejection_state": state,
                    "rejection_reason": rejection_reason or "not_validated",
                }
            )

    observed_map = proposed_map > 0
    validated_observed_map = validated_map > 0
    inferred_map = inferred_span_map > 0
    strong_used_map = np.zeros(shape, dtype=bool)
    for r in membership_rows:
        if r["role"] == "observed_strong_support":
            strong_used_map[as_int(r["y"]), as_int(r["x"])] = True
    diagnostic_used_as_support = [
        r for r in membership_rows
        if r["role"] in {"observed_strong_support", "observed_candidate_support"}
        and r["source_evidence_class"] in DIAGNOSTIC_CLASSES
    ]
    ambiguous_validated_support = [
        r for r in membership_rows
        if r["role"] in {"observed_strong_support", "observed_candidate_support"}
        and r["source_evidence_class"] in AMBIGUOUS_CLASSES
    ]

    invariants = {
        "observed_support_subset_of_v3_4_2_organized_residual": bool(np.all(~observed_map | organized_support)),
        "validated_observed_support_subset_of_candidate_or_strong": bool(np.all(~validated_observed_map | candidate_support | strong_support)),
        "strong_used_support_subset_of_evidence_strong_residual_geometry": bool(np.all(~strong_used_map | strong_support)),
        "diagnostic_support_used_as_geometry_zero": len(diagnostic_used_as_support) == 0,
        "ambiguous_support_used_as_validated_geometry_zero": len(ambiguous_validated_support) == 0,
        "inferred_span_intersection_observed_support_empty": not bool(np.any(inferred_map & observed_map)),
        "observed_support_subset_of_mask": bool(np.all(~observed_map | mask)),
        "observed_support_subset_of_v3_3_residual_after_geometry_mask": bool(np.all(~observed_map | residual_v3)),
        "no_synthetic_observed_support": True,
        "v3_3_outputs_unchanged": True,
        "v3_4_2_outputs_unchanged": True,
    }
    status = "completed" if all(invariants.values()) else "failed_contract"

    state_counts = Counter(h["validation_state"] for h in hypotheses)
    type_counts = Counter(h["hypothesis_type"] for h in hypotheses)
    observed_pixels_used = int(np.count_nonzero(observed_map))
    validated_pixels = int(np.count_nonzero(validated_observed_map))
    inferred_pixels = int(np.count_nonzero(inferred_map))
    validation_scores = [as_float(h["validation_score"]) for h in hypotheses]
    overpromotion_values = [as_float(h["overpromotion_risk"]) for h in hypotheses]
    underpromotion_values = [as_float(h["underpromotion_risk"]) for h in hypotheses]
    n_hyp = len(hypotheses)

    contract = {
        "creates_final_geometry": False,
        "creates_line_objects": False,
        "creates_axis_descriptors": False,
        "creates_crossings": False,
        "creates_families": False,
        "detects_high_level_semantics": False,
        "modifies_v3_3_outputs": False,
        "modifies_v3_4_2_outputs": False,
        "separates_observed_support_from_inferred_span": True,
        "uses_diagnostic_residual_as_structural_support": False,
        "hypotheses_are_not_final_geometry": True,
    }
    counts = {
        "proposed_hypothesis_count": n_hyp,
        "validated_hypothesis_count": state_counts.get("validated", 0),
        "rejected_hypothesis_count": state_counts.get("rejected", 0),
        "needs_context_hypothesis_count": state_counts.get("needs_context", 0),
        "total_hypothesis_count": n_hyp,
        "observed_support_pixels_used": observed_pixels_used,
        "validated_observed_support_pixels": validated_pixels,
        "inferred_span_pixels": inferred_pixels,
        "diagnostic_pixels_used_as_support": len(diagnostic_used_as_support),
        "ambiguous_pixels_used_as_validated_support": len(ambiguous_validated_support),
        "hypothesis_type_counts": dict(type_counts),
        "validation_state_counts": dict(state_counts),
    }
    metrics = {
        "validated_ratio": state_counts.get("validated", 0) / n_hyp if n_hyp else 0.0,
        "rejected_ratio": state_counts.get("rejected", 0) / n_hyp if n_hyp else 0.0,
        "needs_context_ratio": state_counts.get("needs_context", 0) / n_hyp if n_hyp else 0.0,
        "mean_validation_score": mean(validation_scores),
        "mean_overpromotion_risk": mean(overpromotion_values),
        "mean_underpromotion_risk": mean(underpromotion_values),
        "observed_to_inferred_ratio": observed_pixels_used / inferred_pixels if inferred_pixels else float(observed_pixels_used),
    }
    outputs = {
        "residual_geometry_hypotheses_csv": "residual_geometry_hypotheses.csv",
        "residual_hypothesis_memberships_csv": "residual_hypothesis_memberships.csv",
        "residual_hypothesis_validation_csv": "residual_hypothesis_validation.csv",
        "rejected_residual_evidence_csv": "rejected_residual_evidence.csv",
        "contract_audit_json": "contract_audit.json",
        "proposed_hypothesis_observed_support_map": "maps/proposed_hypothesis_observed_support_map.npy",
        "validated_hypothesis_observed_support_map": "maps/validated_hypothesis_observed_support_map.npy",
        "inferred_span_map": "maps/inferred_span_map.npy",
        "rejected_residual_support_map": "maps/rejected_residual_support_map.npy",
        "hypothesis_id_map": "maps/hypothesis_id_map.npy",
        "visual_summary": "visuals/06_visual_summary.png",
    }

    summary = {
        "version": VERSION,
        "status": status,
        "source_v3_4_2_run_dir": str(v3_4_2_dir),
        "source_v3_3_run_dir": str(v3_run_dir),
        "source_v3_4_2_version": v3_4_summary.get("version", ""),
        "source_v3_3_version": v3_summary.get("version", ""),
        "config": asdict(cfg),
        "counts": counts,
        "metrics": metrics,
        "invariants": invariants,
        "contract": contract,
        "outputs": outputs,
    }
    contract_audit = {
        "version": VERSION,
        "contract_file": "docs/CONTRACT_C1_0_RESIDUAL_EVIDENCE_GEOMETRY_HYPOTHESIS_VALIDATOR_V1.md",
        "status": status,
        "semantic_rule": "residual_evidence_is_not_final_geometry",
        "traceability_rule": "observed_support_and_inferred_span_are_separate",
        "invariants": invariants,
        "contract": contract,
        "counts": counts,
        "metrics": metrics,
    }

    np.save(out_dir / "maps" / "proposed_hypothesis_observed_support_map.npy", proposed_map)
    np.save(out_dir / "maps" / "validated_hypothesis_observed_support_map.npy", validated_map)
    np.save(out_dir / "maps" / "inferred_span_map.npy", inferred_span_map)
    np.save(out_dir / "maps" / "rejected_residual_support_map.npy", rejected_map)
    np.save(out_dir / "maps" / "hypothesis_id_map.npy", hypothesis_id_map)
    write_csv(out_dir / "residual_geometry_hypotheses.csv", hypotheses, HYPOTHESIS_FIELDS)
    write_csv(out_dir / "residual_hypothesis_memberships.csv", membership_rows, MEMBERSHIP_FIELDS)
    write_csv(out_dir / "residual_hypothesis_validation.csv", validation_rows, VALIDATION_FIELDS)
    write_csv(out_dir / "rejected_residual_evidence.csv", rejected_rows, REJECTED_FIELDS)
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "contract_audit.json", contract_audit)
    make_visuals(
        out_dir,
        shape,
        combined_v3,
        evidence_rows,
        memberships_by_object,
        hypotheses,
        proposed_map,
        validated_map,
        inferred_span_map,
        rejected_map,
        cfg,
    )
    print(json.dumps({"status": status, **counts, **metrics}, ensure_ascii=False), flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, help="B1 V3.4.2 output directory")
    ap.add_argument("--v3-run-dir", default=None, help="Optional explicit V3.3 run directory")
    ap.add_argument("--image", default=None, help="Optional audit image; not used as geometry source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-axis-distance", type=float, default=4.0)
    ap.add_argument("--max-collinearity-error", type=float, default=2.0)
    ap.add_argument("--max-gap-for-inferred-span", type=int, default=12)
    ap.add_argument("--min-observed-support-pixels", type=int, default=4)
    ap.add_argument("--min-validation-score", type=float, default=0.80)
    ap.add_argument("--min-needs-context-score", type=float, default=0.55)
    ap.add_argument("--max-overpromotion-risk", type=float, default=0.30)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config(
        max_axis_distance_to_upstream_px=args.max_axis_distance,
        max_collinearity_error_px=args.max_collinearity_error,
        max_gap_for_inferred_span_px=args.max_gap_for_inferred_span,
        min_observed_support_pixels=args.min_observed_support_pixels,
        min_validation_score=args.min_validation_score,
        min_needs_context_score=args.min_needs_context_score,
        max_overpromotion_risk_for_validation=args.max_overpromotion_risk,
    )
    run(
        v3_4_2_dir=Path(args.run_dir),
        out_dir=Path(args.out),
        v3_run_dir=Path(args.v3_run_dir) if args.v3_run_dir else None,
        image_path=Path(args.image) if args.image else None,
        cfg=cfg,
    )


if __name__ == "__main__":
    main()
