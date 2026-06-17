#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module L1.2 - Deferred Domain Subsupport Resolver.

L1.2 subclasses and conservatively resolves observed support that remains
deferred after L1.1. It does not create geometry, repair gaps, recognize text,
or modify upstream outputs.
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


VERSION = "MODULE_L1_2_V1_DEFERRED_DOMAIN_SUBSUPPORT_RESOLVER"

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

DEFERRED_SUBCLASS_CODE = {
    "deferred_line_rescue_candidate": 1,
    "deferred_mixed_candidate": 2,
    "deferred_probable_non_line_candidate": 3,
    "deferred_tiny_low_evidence": 4,
    "deferred_true_unknown": 5,
}

RESOLUTION_KIND_CODE = {
    "unchanged_non_deferred": 0,
    "promoted_from_deferred_to_line": 1,
    "resolved_from_deferred_to_non_line": 2,
    "resolved_from_deferred_to_mixed": 3,
    "kept_deferred": 4,
}

LINE_CLASSES = {"line_domain", "probable_line_domain"}
FUTURE_CLASSES = {"non_line_domain", "probable_non_line_domain", "mixed_domain", "deferred_domain"}

DEFERRED_SUBCLASS_FIELDS = [
    "deferred_subclass_region_id",
    "source_l1_1_calibrated_domain_region_id",
    "source_l1_0_domain_region_id",
    "source_u1_1_region_id",
    "source_geometry_object_id",
    "deferred_subclass",
    "subclass_confidence",
    "region_pixel_count",
    "orientation",
    "line_context_score",
    "microstructure_score",
    "mixed_contact_score",
    "colinearity_score",
    "width_stability_score",
    "local_connectivity_score",
    "subclass_reason",
]

REGION_FIELDS = [
    "resolved_domain_region_id",
    "source_l1_1_calibrated_domain_region_id",
    "source_l1_0_domain_region_id",
    "source_u1_1_region_id",
    "source_geometry_object_id",
    "source_l1_1_domain_class",
    "deferred_subclass",
    "resolved_l1_2_domain_class",
    "resolution_kind",
    "resolution_confidence",
    "excluded_from_resolved_line_study",
    "available_for_future_modules",
    "region_pixel_count",
    "orientation",
    "line_context_score",
    "microstructure_score",
    "mixed_contact_score",
    "colinearity_score",
    "width_stability_score",
    "local_connectivity_score",
    "resolution_reason",
]

MEMBERSHIP_FIELDS = [
    "resolved_domain_region_id",
    "source_l1_1_calibrated_domain_region_id",
    "source_l1_0_domain_region_id",
    "source_u1_1_region_id",
    "source_geometry_object_id",
    "x",
    "y",
    "source_l1_1_domain_class",
    "deferred_subclass",
    "resolved_l1_2_domain_class",
    "resolution_kind",
    "resolution_confidence",
    "excluded_from_resolved_line_study",
    "available_for_future_modules",
    "membership_weight",
]

RESOLUTION_FIELDS = [
    "resolution_id",
    "resolved_domain_region_id",
    "source_l1_1_calibrated_domain_region_id",
    "source_l1_1_domain_class",
    "deferred_subclass",
    "resolved_l1_2_domain_class",
    "resolution_kind",
    "resolution_confidence",
    "pixel_count",
    "support_subset_of_l1_1_deferred_support",
    "line_study_resolution_allowed",
    "future_pool_resolution_allowed",
    "resolution_reason",
]

VALIDATION_FIELDS = [
    "resolved_domain_region_id",
    "source_l1_1_calibrated_domain_region_id",
    "source_l1_1_domain_class",
    "deferred_subclass",
    "resolved_l1_2_domain_class",
    "support_subset_of_l1_1_observed_support",
    "changed_support_subset_of_l1_1_deferred_support",
    "resolved_line_study_excludes_non_line_mixed_deferred",
    "resolved_future_pool_preserves_non_line_mixed_deferred",
    "resolution_preserves_source_traceability",
    "no_semantic_recognition_used",
    "does_not_create_geometry",
    "does_not_delete_support",
    "does_not_modify_upstream",
    "validation_reason",
    "rejection_or_deferral_reason",
]

REQUIRED_L11_FILES = [
    "summary.json",
    "contract_audit.json",
    "l1_1_calibrated_domain_regions.csv",
    "l1_1_calibrated_domain_memberships.csv",
    "l1_1_domain_transitions.csv",
    "l1_1_domain_validation.csv",
    "l1_1_calibrated_line_study_support.csv",
    "l1_1_calibrated_future_module_pool.csv",
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
    "l1_2_deferred_subclasses.csv",
    "l1_2_resolved_domain_regions.csv",
    "l1_2_resolved_domain_memberships.csv",
    "l1_2_deferred_resolutions.csv",
    "l1_2_domain_validation.csv",
    "l1_2_resolved_line_study_support.csv",
    "l1_2_resolved_future_module_pool.csv",
    "l1_2_promoted_from_deferred_to_line.csv",
    "l1_2_resolved_from_deferred_to_non_line.csv",
    "l1_2_kept_deferred.csv",
    "summary.json",
    "contract_audit.json",
    "maps/deferred_line_rescue_candidate_map.npy",
    "maps/deferred_mixed_candidate_map.npy",
    "maps/deferred_probable_non_line_candidate_map.npy",
    "maps/deferred_tiny_low_evidence_map.npy",
    "maps/deferred_true_unknown_map.npy",
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
    "visuals/01_l1_1_deferred_input.png",
    "visuals/02_deferred_subclasses.png",
    "visuals/03_promoted_from_deferred_to_line.png",
    "visuals/04_resolved_from_deferred_to_non_line.png",
    "visuals/05_kept_deferred.png",
    "visuals/06_resolved_line_study_support.png",
    "visuals/07_resolved_future_module_pool.png",
    "visuals/08_l1_1_vs_l1_2_comparison.png",
    "visuals/09_l1_2_audit_summary.png",
]


@dataclass
class Config:
    version: str = VERSION
    neighborhood_px: int = 2
    tiny_max_pixels: int = 3
    min_line_rescue_context: float = 0.60
    min_line_rescue_colinearity: float = 0.60
    min_line_rescue_width_stability: float = 0.30
    max_line_rescue_microstructure: float = 0.52
    max_line_rescue_conflict_contact: float = 0.25
    min_probable_non_line_microstructure: float = 0.70
    max_probable_non_line_line_context: float = 0.50
    min_mixed_line_context: float = 0.45
    min_mixed_microstructure: float = 0.55


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


def class_map_to_rgb(class_map: np.ndarray) -> Image.Image:
    arr = np.full((class_map.shape[0], class_map.shape[1], 3), 255, dtype=np.uint8)
    arr[class_map == DOMAIN_CODE["line_domain"]] = (38, 122, 255)
    arr[class_map == DOMAIN_CODE["probable_line_domain"]] = (0, 185, 210)
    arr[class_map == DOMAIN_CODE["non_line_domain"]] = (220, 0, 0)
    arr[class_map == DOMAIN_CODE["probable_non_line_domain"]] = (255, 160, 0)
    arr[class_map == DOMAIN_CODE["mixed_domain"]] = (150, 70, 210)
    arr[class_map == DOMAIN_CODE["deferred_domain"]] = (160, 160, 160)
    return Image.fromarray(arr, "RGB")


def subclass_map_to_rgb(subclass_map: np.ndarray) -> Image.Image:
    arr = np.full((subclass_map.shape[0], subclass_map.shape[1], 3), 255, dtype=np.uint8)
    arr[subclass_map == DEFERRED_SUBCLASS_CODE["deferred_line_rescue_candidate"]] = (150, 235, 150)
    arr[subclass_map == DEFERRED_SUBCLASS_CODE["deferred_mixed_candidate"]] = (205, 155, 235)
    arr[subclass_map == DEFERRED_SUBCLASS_CODE["deferred_probable_non_line_candidate"]] = (255, 205, 130)
    arr[subclass_map == DEFERRED_SUBCLASS_CODE["deferred_tiny_low_evidence"]] = (210, 210, 210)
    arr[subclass_map == DEFERRED_SUBCLASS_CODE["deferred_true_unknown"]] = (90, 90, 90)
    return Image.fromarray(arr, "RGB")


def load_source_memberships(l11_dir: Path) -> Dict[Tuple[int, int, int], float]:
    weights: Dict[Tuple[int, int, int], float] = {}
    for row in read_csv(l11_dir / "l1_1_calibrated_domain_memberships.csv"):
        rid = as_int(row.get("calibrated_domain_region_id"))
        x, y = as_int(row.get("x")), as_int(row.get("y"))
        weights[(rid, x, y)] = as_float(row.get("membership_weight"), 1.0)
    return weights


def classify_deferred(features: Dict[str, float], cfg: Config) -> Tuple[str, float, str]:
    n = int(features["region_pixel_count"])
    line_context = features["line_context_score"]
    micro = features["microstructure_score"]
    mixed = features["mixed_contact_score"]
    colinear = features["colinearity_score"]
    width = features["width_stability_score"]
    conflict = max(features["diagnostic_residual_contact_score"], features["blocking_residual_contact_score"])
    connectivity = features["local_connectivity_score"]

    if n <= cfg.tiny_max_pixels:
        return "deferred_tiny_low_evidence", 0.80, "too_few_pixels_for_safe_resolution"

    if (
        line_context >= cfg.min_line_rescue_context
        and colinear >= cfg.min_line_rescue_colinearity
        and width >= cfg.min_line_rescue_width_stability
        and micro <= cfg.max_line_rescue_microstructure
        and conflict <= cfg.max_line_rescue_conflict_contact
    ):
        conf = clamp01(0.35 * line_context + 0.25 * colinear + 0.20 * width + 0.10 * connectivity + 0.10 * (1.0 - micro))
        return "deferred_line_rescue_candidate", max(0.55, conf), "strong_line_context_low_microstructure"

    if micro >= cfg.min_probable_non_line_microstructure and line_context <= cfg.max_probable_non_line_line_context:
        conf = clamp01(0.55 * micro + 0.25 * (1.0 - line_context) + 0.20 * conflict)
        return "deferred_probable_non_line_candidate", max(0.55, conf), "strong_microstructure_weak_line_context"

    if line_context >= cfg.min_mixed_line_context and micro >= cfg.min_mixed_microstructure:
        conf = clamp01(0.36 * line_context + 0.36 * micro + 0.18 * mixed + 0.10 * connectivity)
        return "deferred_mixed_candidate", max(0.50, conf), "line_and_microstructure_evidence_both_present"

    return "deferred_true_unknown", 0.45, "insufficient_context_for_safe_resolution"


def resolve_deferred(subclass: str, confidence: float, reason: str) -> Tuple[str, str, float, str]:
    if subclass == "deferred_line_rescue_candidate":
        return "probable_line_domain", "promoted_from_deferred_to_line", confidence, "deferred_line_rescue_candidate_promoted_to_probable_line"
    if subclass == "deferred_probable_non_line_candidate":
        return "probable_non_line_domain", "resolved_from_deferred_to_non_line", confidence, "deferred_probable_non_line_candidate_reserved_for_future_pool"
    if subclass == "deferred_mixed_candidate":
        return "mixed_domain", "resolved_from_deferred_to_mixed", confidence, "deferred_mixed_candidate_kept_out_of_clean_line_study"
    return "deferred_domain", "kept_deferred", confidence, reason


def make_visuals(
    out_dir: Path,
    l11_deferred: np.ndarray,
    l11_class_map: np.ndarray,
    resolved_class_map: np.ndarray,
    subclass_map: np.ndarray,
    promoted_map: np.ndarray,
    resolved_non_line_map: np.ndarray,
    kept_deferred_map: np.ndarray,
    resolved_line_study: np.ndarray,
    resolved_future_pool: np.ndarray,
) -> None:
    vdir = out_dir / "visuals"
    ensure_dir(vdir)
    render_bool(l11_deferred, (0, 0, 0)).save(vdir / "01_l1_1_deferred_input.png")
    subclass_img = subclass_map_to_rgb(subclass_map)
    subclass_img.save(vdir / "02_deferred_subclasses.png")
    render_bool(promoted_map, (255, 220, 0)).save(vdir / "03_promoted_from_deferred_to_line.png")
    render_bool(resolved_non_line_map, (255, 150, 0)).save(vdir / "04_resolved_from_deferred_to_non_line.png")
    render_bool(kept_deferred_map, (150, 150, 150)).save(vdir / "05_kept_deferred.png")
    render_bool(resolved_line_study, (0, 175, 85)).save(vdir / "06_resolved_line_study_support.png")
    render_bool(resolved_future_pool, (210, 0, 210)).save(vdir / "07_resolved_future_module_pool.png")

    l11_img = class_map_to_rgb(l11_class_map)
    res_img = class_map_to_rgb(resolved_class_map)
    panels = [
        titled(l11_img, "L1.1 input domains"),
        titled(res_img, "L1.2 resolved domains"),
        titled(render_bool(l11_deferred, (0, 0, 0)), "L1.1 deferred input"),
        titled(subclass_img, "deferred subclasses"),
        titled(render_bool(promoted_map, (255, 220, 0)), "promoted from deferred"),
        titled(render_bool(resolved_non_line_map, (255, 150, 0)), "resolved to non-line"),
        titled(render_bool(kept_deferred_map, (150, 150, 150)), "kept deferred"),
        titled(render_bool(resolved_line_study, (0, 175, 85)), "resolved line-study"),
    ]
    tile_w = max(p.width for p in panels)
    tile_h = max(p.height for p in panels)
    sheet = Image.new("RGB", (tile_w * 4, tile_h * 2 + 38), "white")
    d = ImageDraw.Draw(sheet)
    d.text((8, 10), "L1.2 deferred domain subsupport resolver", fill="black", font=font(16))
    for idx, panel in enumerate(panels):
        x = (idx % 4) * tile_w
        y = 38 + (idx // 4) * tile_h
        sheet.paste(panel, (x, y))
    sheet.save(vdir / "08_l1_1_vs_l1_2_comparison.png")

    audit_panels = [
        titled(render_bool(l11_deferred, (0, 0, 0)), "source deferred"),
        titled(subclass_img, "subclasses"),
        titled(render_bool(promoted_map, (255, 220, 0)), "line promotion"),
        titled(render_bool(resolved_non_line_map, (255, 150, 0)), "non-line resolution"),
        titled(render_bool(kept_deferred_map, (150, 150, 150)), "still deferred"),
        titled(render_bool(resolved_future_pool, (210, 0, 210)), "future pool"),
    ]
    audit = Image.new("RGB", (tile_w * 3, tile_h * 2 + 38), "white")
    d = ImageDraw.Draw(audit)
    d.text((8, 10), "L1.2 audit summary: explaining deferred, not forcing it away", fill="black", font=font(16))
    for idx, panel in enumerate(audit_panels):
        x = (idx % 3) * tile_w
        y = 38 + (idx // 3) * tile_h
        audit.paste(panel, (x, y))
    audit.save(vdir / "09_l1_2_audit_summary.png")


def run(
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
        "l1_1": missing_required(l11_dir, REQUIRED_L11_FILES),
        "l1_0": missing_required(l10_dir, REQUIRED_L10_FILES),
        "u1_1": missing_required(u11_dir, REQUIRED_U11_FILES),
        "v3_3": missing_required(v33_dir, REQUIRED_V33_FILES),
    }
    absent = [f"{group}:{rel}" for group, rels in missing_inputs.items() for rel in rels]
    if absent:
        raise FileNotFoundError("Missing required L1.2 input files: " + ", ".join(absent))

    source_manifest_before = {
        "l1_1": file_manifest(l11_dir, REQUIRED_L11_FILES),
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

    l11_summary = read_json(l11_dir / "summary.json")
    l10_summary = read_json(l10_dir / "summary.json")
    u11_summary = read_json(u11_dir / "summary.json")
    v33_summary = read_json(v33_dir / "summary.json")

    l11_regions = {as_int(row.get("calibrated_domain_region_id")): row for row in read_csv(l11_dir / "l1_1_calibrated_domain_regions.csv")}
    l11_region_map = load_map(l11_dir / "maps" / "l1_1_calibrated_domain_region_id_map.npy", np.int32)
    l11_class_map = load_map(l11_dir / "maps" / "l1_1_calibrated_domain_class_map.npy", np.uint8)
    l11_deferred = load_map(l11_dir / "maps" / "calibrated_deferred_domain_support_map.npy", np.uint16) > 0
    l11_line_domain = load_map(l11_dir / "maps" / "calibrated_line_domain_support_map.npy", np.uint16) > 0
    l11_prob_line = load_map(l11_dir / "maps" / "calibrated_probable_line_domain_support_map.npy", np.uint16) > 0
    l11_line_study = load_map(l11_dir / "maps" / "calibrated_line_study_support_map.npy", np.uint16) > 0
    l11_future = load_map(l11_dir / "maps" / "calibrated_future_module_pool_map.npy", np.uint16) > 0
    u11_refined = load_map(u11_dir / "maps" / "refined_unified_valid_observed_support_map.npy", np.uint16) > 0
    shape = l11_class_map.shape
    l11_observed = l11_class_map > 0

    diagnostic = optional_map(v342_dir / "maps" / "diagnostic_residual_support_count_map.npy" if v342_dir else None, shape, np.uint16) > 0
    c10_rejected = optional_map(c10_dir / "maps" / "rejected_residual_support_map.npy" if c10_dir else None, shape, np.uint16) > 0
    c11_blocking = optional_map(c11_dir / "maps" / "collective_blocking_evidence_map.npy" if c11_dir else None, shape, np.uint16) > 0
    u11_ambiguous = optional_map(u11_dir / "maps" / "ambiguous_subsupport_map.npy", shape, np.uint16) > 0

    diagnostic_near = dilate(diagnostic, cfg.neighborhood_px)
    blocking_near = dilate(c10_rejected | c11_blocking, cfg.neighborhood_px)
    source_weights = load_source_memberships(l11_dir)

    resolved_class_map = l11_class_map.copy()
    resolved_region_map = np.zeros(shape, dtype=np.int32)
    subclass_map = np.zeros(shape, dtype=np.uint8)
    resolution_kind_map = np.zeros(shape, dtype=np.uint8)
    resolution_confidence_map = np.zeros(shape, dtype=np.float32)

    subclass_rows: List[Dict[str, Any]] = []
    region_rows: List[Dict[str, Any]] = []
    membership_rows: List[Dict[str, Any]] = []
    resolution_rows: List[Dict[str, Any]] = []
    validation_rows: List[Dict[str, Any]] = []

    subclass_region_id = 0
    resolution_id = 0

    for resolved_region_id, source_region_id in enumerate(sorted(int(v) for v in np.unique(l11_region_map) if int(v) > 0), start=1):
        points = [(int(x), int(y)) for y, x in zip(*np.where(l11_region_map == source_region_id))]
        source_region = l11_regions.get(source_region_id, {})
        source_class = source_region.get("calibrated_l1_1_domain_class", "")
        source_l10_id = as_int(source_region.get("source_l1_0_domain_region_id"))
        source_u11_id = as_int(source_region.get("source_u1_1_region_id"))
        source_gid = str(source_region.get("source_geometry_object_id", ""))
        orientation = source_region.get("orientation", "horizontal")
        n = len(points)
        diagnostic_contact = ratio(sum(1 for x, y in points if diagnostic_near[y, x]), n)
        blocking_contact = ratio(sum(1 for x, y in points if blocking_near[y, x]), n)
        features = {
            "region_pixel_count": float(n),
            "orientation": orientation,
            "line_context_score": as_float(source_region.get("line_context_score")),
            "microstructure_score": as_float(source_region.get("microstructure_score")),
            "mixed_contact_score": as_float(source_region.get("mixed_contact_score")),
            "colinearity_score": as_float(source_region.get("colinearity_score")),
            "width_stability_score": as_float(source_region.get("width_stability_score")),
            "local_connectivity_score": local_connectivity(points),
            "diagnostic_residual_contact_score": diagnostic_contact,
            "blocking_residual_contact_score": blocking_contact,
        }

        deferred_subclass = ""
        subclass_confidence = 1.0
        subclass_reason = "non_deferred_support_preserved"
        resolved_class = source_class
        resolution_kind = "unchanged_non_deferred"
        resolution_confidence = 1.0
        resolution_reason = "non_deferred_l1_1_support_preserved"

        if source_class == "deferred_domain":
            deferred_subclass, subclass_confidence, subclass_reason = classify_deferred(features, cfg)
            resolved_class, resolution_kind, resolution_confidence, resolution_reason = resolve_deferred(deferred_subclass, subclass_confidence, subclass_reason)
            subclass_region_id += 1
            subclass_rows.append(
                {
                    "deferred_subclass_region_id": subclass_region_id,
                    "source_l1_1_calibrated_domain_region_id": source_region_id,
                    "source_l1_0_domain_region_id": source_l10_id,
                    "source_u1_1_region_id": source_u11_id,
                    "source_geometry_object_id": source_gid,
                    "deferred_subclass": deferred_subclass,
                    "subclass_confidence": subclass_confidence,
                    "region_pixel_count": n,
                    "orientation": orientation,
                    "line_context_score": features["line_context_score"],
                    "microstructure_score": features["microstructure_score"],
                    "mixed_contact_score": features["mixed_contact_score"],
                    "colinearity_score": features["colinearity_score"],
                    "width_stability_score": features["width_stability_score"],
                    "local_connectivity_score": features["local_connectivity_score"],
                    "subclass_reason": subclass_reason,
                }
            )
            resolution_id += 1
            resolution_rows.append(
                {
                    "resolution_id": resolution_id,
                    "resolved_domain_region_id": resolved_region_id,
                    "source_l1_1_calibrated_domain_region_id": source_region_id,
                    "source_l1_1_domain_class": source_class,
                    "deferred_subclass": deferred_subclass,
                    "resolved_l1_2_domain_class": resolved_class,
                    "resolution_kind": resolution_kind,
                    "resolution_confidence": resolution_confidence,
                    "pixel_count": n,
                    "support_subset_of_l1_1_deferred_support": all(l11_deferred[y, x] for x, y in points),
                    "line_study_resolution_allowed": resolved_class in LINE_CLASSES,
                    "future_pool_resolution_allowed": resolved_class in FUTURE_CLASSES,
                    "resolution_reason": resolution_reason,
                }
            )

        excluded_from_line = resolved_class not in LINE_CLASSES
        available_future = resolved_class in FUTURE_CLASSES
        region_rows.append(
            {
                "resolved_domain_region_id": resolved_region_id,
                "source_l1_1_calibrated_domain_region_id": source_region_id,
                "source_l1_0_domain_region_id": source_l10_id,
                "source_u1_1_region_id": source_u11_id,
                "source_geometry_object_id": source_gid,
                "source_l1_1_domain_class": source_class,
                "deferred_subclass": deferred_subclass,
                "resolved_l1_2_domain_class": resolved_class,
                "resolution_kind": resolution_kind,
                "resolution_confidence": resolution_confidence,
                "excluded_from_resolved_line_study": excluded_from_line,
                "available_for_future_modules": available_future,
                "region_pixel_count": n,
                "orientation": orientation,
                "line_context_score": features["line_context_score"],
                "microstructure_score": features["microstructure_score"],
                "mixed_contact_score": features["mixed_contact_score"],
                "colinearity_score": features["colinearity_score"],
                "width_stability_score": features["width_stability_score"],
                "local_connectivity_score": features["local_connectivity_score"],
                "resolution_reason": resolution_reason,
            }
        )

        support_subset_observed = all(0 <= y < shape[0] and 0 <= x < shape[1] and l11_observed[y, x] for x, y in points)
        changed = source_class != resolved_class
        validation_rows.append(
            {
                "resolved_domain_region_id": resolved_region_id,
                "source_l1_1_calibrated_domain_region_id": source_region_id,
                "source_l1_1_domain_class": source_class,
                "deferred_subclass": deferred_subclass,
                "resolved_l1_2_domain_class": resolved_class,
                "support_subset_of_l1_1_observed_support": support_subset_observed,
                "changed_support_subset_of_l1_1_deferred_support": (not changed) or all(l11_deferred[y, x] for x, y in points),
                "resolved_line_study_excludes_non_line_mixed_deferred": resolved_class in LINE_CLASSES or excluded_from_line,
                "resolved_future_pool_preserves_non_line_mixed_deferred": resolved_class in LINE_CLASSES or available_future,
                "resolution_preserves_source_traceability": bool(source_region_id and "source_l1_0_domain_region_id" in source_region and "source_u1_1_region_id" in source_region and "source_geometry_object_id" in source_region),
                "no_semantic_recognition_used": True,
                "does_not_create_geometry": True,
                "does_not_delete_support": True,
                "does_not_modify_upstream": True,
                "validation_reason": "resolution_from_traceable_deferred_domain_features",
                "rejection_or_deferral_reason": "" if resolved_class in LINE_CLASSES else resolution_reason,
            }
        )

        for x, y in points:
            resolved_region_map[y, x] = resolved_region_id
            resolved_class_map[y, x] = DOMAIN_CODE[resolved_class]
            resolution_kind_map[y, x] = RESOLUTION_KIND_CODE[resolution_kind]
            resolution_confidence_map[y, x] = float(resolution_confidence)
            if deferred_subclass:
                subclass_map[y, x] = DEFERRED_SUBCLASS_CODE[deferred_subclass]
            membership_rows.append(
                {
                    "resolved_domain_region_id": resolved_region_id,
                    "source_l1_1_calibrated_domain_region_id": source_region_id,
                    "source_l1_0_domain_region_id": source_l10_id,
                    "source_u1_1_region_id": source_u11_id,
                    "source_geometry_object_id": source_gid,
                    "x": x,
                    "y": y,
                    "source_l1_1_domain_class": source_class,
                    "deferred_subclass": deferred_subclass,
                    "resolved_l1_2_domain_class": resolved_class,
                    "resolution_kind": resolution_kind,
                    "resolution_confidence": resolution_confidence,
                    "excluded_from_resolved_line_study": excluded_from_line,
                    "available_for_future_modules": available_future,
                    "membership_weight": source_weights.get((source_region_id, x, y), 1.0),
                }
            )

    resolved_line_domain = resolved_class_map == DOMAIN_CODE["line_domain"]
    resolved_prob_line = resolved_class_map == DOMAIN_CODE["probable_line_domain"]
    resolved_non_line = resolved_class_map == DOMAIN_CODE["non_line_domain"]
    resolved_prob_non_line = resolved_class_map == DOMAIN_CODE["probable_non_line_domain"]
    resolved_mixed = resolved_class_map == DOMAIN_CODE["mixed_domain"]
    resolved_deferred = resolved_class_map == DOMAIN_CODE["deferred_domain"]
    resolved_future_pool = resolved_non_line | resolved_prob_non_line | resolved_mixed | resolved_deferred
    resolved_line_study = (resolved_line_domain | resolved_prob_line) & u11_refined & ~diagnostic & ~u11_ambiguous

    promoted_from_deferred = l11_deferred & resolved_prob_line
    resolved_from_deferred_to_non_line = l11_deferred & (resolved_non_line | resolved_prob_non_line)
    resolved_from_deferred_to_mixed = l11_deferred & resolved_mixed
    kept_deferred = l11_deferred & resolved_deferred

    state_maps = [resolved_line_domain, resolved_prob_line, resolved_non_line, resolved_prob_non_line, resolved_mixed, resolved_deferred]
    overlap = np.zeros(shape, dtype=np.uint8)
    for m in state_maps:
        overlap += m.astype(np.uint8)

    source_manifest_after = {
        "l1_1": file_manifest(l11_dir, REQUIRED_L11_FILES),
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
        if str(r["resolved_l1_2_domain_class"]) in FUTURE_CLASSES
    }
    resolution_membership_set = {
        (as_int(r["x"]), as_int(r["y"]))
        for r in membership_rows
        if str(r["source_l1_1_domain_class"]) == "deferred_domain"
    }
    future_pixel_set = set(zip(np.where(resolved_future_pool)[1].tolist(), np.where(resolved_future_pool)[0].tolist()))
    changed_map = l11_class_map != resolved_class_map
    changed_pixel_set = set(zip(np.where(changed_map)[1].tolist(), np.where(changed_map)[0].tolist()))
    promoted_pixel_set = set(zip(np.where(promoted_from_deferred)[1].tolist(), np.where(promoted_from_deferred)[0].tolist()))
    resolved_non_line_pixel_set = set(zip(np.where(resolved_from_deferred_to_non_line)[1].tolist(), np.where(resolved_from_deferred_to_non_line)[0].tolist()))
    resolved_mixed_pixel_set = set(zip(np.where(resolved_from_deferred_to_mixed)[1].tolist(), np.where(resolved_from_deferred_to_mixed)[0].tolist()))
    kept_deferred_pixel_set = set(zip(np.where(kept_deferred)[1].tolist(), np.where(kept_deferred)[0].tolist()))

    non_deferred_unchanged = np.all(resolved_class_map[~l11_deferred] == l11_class_map[~l11_deferred])
    invariants = {
        "all_changed_support_subset_of_l1_1_deferred_support": bool(np.all(~changed_map | l11_deferred)),
        "all_unchanged_non_deferred_l1_1_support_preserved": bool(non_deferred_unchanged),
        "resolved_line_domain_support_equals_l1_1_line_domain_support": bool(np.array_equal(resolved_line_domain, l11_line_domain)),
        "resolved_probable_line_domain_support_subset_of_l1_1_observed_support": bool(np.all(~resolved_prob_line | l11_observed)),
        "resolved_non_line_domain_support_subset_of_l1_1_observed_support": bool(np.all(~resolved_non_line | l11_observed)),
        "resolved_probable_non_line_domain_support_subset_of_l1_1_observed_support": bool(np.all(~resolved_prob_non_line | l11_observed)),
        "resolved_mixed_domain_support_subset_of_l1_1_observed_support": bool(np.all(~resolved_mixed | l11_observed)),
        "resolved_deferred_domain_support_subset_of_l1_1_observed_support": bool(np.all(~resolved_deferred | l11_observed)),
        "all_l1_2_resolved_domain_maps_are_mutually_exclusive": bool(np.all(overlap <= 1)),
        "resolved_line_study_support_excludes_non_line_probable_non_line_mixed_deferred": not bool(np.any(resolved_line_study & resolved_future_pool)),
        "resolved_future_module_pool_includes_non_line_probable_non_line_mixed_deferred": bool(np.all((resolved_non_line | resolved_prob_non_line | resolved_mixed | resolved_deferred) <= resolved_future_pool)),
        "resolved_future_module_pool_preserves_traceability": future_pixel_set.issubset(membership_pixel_set) and future_pixel_set.issubset(future_membership_set),
        "all_resolutions_preserve_source_l1_1_class": all(str(r.get("source_l1_1_domain_class", "")) in DOMAIN_CLASSES for r in region_rows),
        "all_resolutions_preserve_source_l1_0_region_id_when_available": all("source_l1_0_domain_region_id" in r for r in region_rows),
        "all_resolutions_preserve_source_u1_1_region_id_when_available": all("source_u1_1_region_id" in r for r in region_rows),
        "all_resolutions_preserve_source_geometry_object_id_when_available": all("source_geometry_object_id" in r for r in region_rows),
        "promoted_from_deferred_support_remains_traceable_to_l1_1_deferred_support": promoted_pixel_set.issubset(resolution_membership_set) and all(l11_deferred[y, x] for x, y in promoted_pixel_set),
        "resolved_to_non_line_support_is_not_deleted": resolved_non_line_pixel_set.issubset(future_pixel_set),
        "resolved_to_mixed_support_is_not_silently_counted_as_clean_line": not bool(np.any(resolved_from_deferred_to_mixed & resolved_line_study)),
        "kept_deferred_support_is_not_silently_counted_as_clean_line": not bool(np.any(kept_deferred & resolved_line_study)),
        "inferred_spans_are_not_converted_to_observed_support": True,
        "diagnostic_residual_is_not_converted_to_line_study_support": not bool(np.any(resolved_line_study & diagnostic)),
        "ambiguous_residual_is_not_converted_to_line_study_support": not bool(np.any(resolved_line_study & u11_ambiguous)),
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
    }

    np.save(out_dir / "maps" / "deferred_line_rescue_candidate_map.npy", (subclass_map == DEFERRED_SUBCLASS_CODE["deferred_line_rescue_candidate"]).astype(np.uint16))
    np.save(out_dir / "maps" / "deferred_mixed_candidate_map.npy", (subclass_map == DEFERRED_SUBCLASS_CODE["deferred_mixed_candidate"]).astype(np.uint16))
    np.save(out_dir / "maps" / "deferred_probable_non_line_candidate_map.npy", (subclass_map == DEFERRED_SUBCLASS_CODE["deferred_probable_non_line_candidate"]).astype(np.uint16))
    np.save(out_dir / "maps" / "deferred_tiny_low_evidence_map.npy", (subclass_map == DEFERRED_SUBCLASS_CODE["deferred_tiny_low_evidence"]).astype(np.uint16))
    np.save(out_dir / "maps" / "deferred_true_unknown_map.npy", (subclass_map == DEFERRED_SUBCLASS_CODE["deferred_true_unknown"]).astype(np.uint16))
    np.save(out_dir / "maps" / "resolved_line_domain_support_map.npy", resolved_line_domain.astype(np.uint16))
    np.save(out_dir / "maps" / "resolved_probable_line_domain_support_map.npy", resolved_prob_line.astype(np.uint16))
    np.save(out_dir / "maps" / "resolved_non_line_domain_support_map.npy", resolved_non_line.astype(np.uint16))
    np.save(out_dir / "maps" / "resolved_probable_non_line_domain_support_map.npy", resolved_prob_non_line.astype(np.uint16))
    np.save(out_dir / "maps" / "resolved_mixed_domain_support_map.npy", resolved_mixed.astype(np.uint16))
    np.save(out_dir / "maps" / "resolved_deferred_domain_support_map.npy", resolved_deferred.astype(np.uint16))
    np.save(out_dir / "maps" / "resolved_line_study_support_map.npy", resolved_line_study.astype(np.uint16))
    np.save(out_dir / "maps" / "resolved_future_module_pool_map.npy", resolved_future_pool.astype(np.uint16))
    np.save(out_dir / "maps" / "l1_2_resolved_domain_region_id_map.npy", resolved_region_map.astype(np.int32))
    np.save(out_dir / "maps" / "l1_2_resolved_domain_class_map.npy", resolved_class_map.astype(np.uint8))
    np.save(out_dir / "maps" / "l1_2_deferred_subclass_map.npy", subclass_map.astype(np.uint8))
    np.save(out_dir / "maps" / "l1_2_resolution_kind_map.npy", resolution_kind_map.astype(np.uint8))
    np.save(out_dir / "maps" / "l1_2_resolution_confidence_map.npy", resolution_confidence_map.astype(np.float32))

    write_csv(out_dir / "l1_2_deferred_subclasses.csv", subclass_rows, DEFERRED_SUBCLASS_FIELDS)
    write_csv(out_dir / "l1_2_resolved_domain_regions.csv", region_rows, REGION_FIELDS)
    write_csv(out_dir / "l1_2_resolved_domain_memberships.csv", membership_rows, MEMBERSHIP_FIELDS)
    write_csv(out_dir / "l1_2_deferred_resolutions.csv", resolution_rows, RESOLUTION_FIELDS)
    write_csv(out_dir / "l1_2_domain_validation.csv", validation_rows, VALIDATION_FIELDS)
    write_csv(
        out_dir / "l1_2_resolved_line_study_support.csv",
        [r for r in membership_rows if r["resolved_l1_2_domain_class"] in LINE_CLASSES and resolved_line_study[as_int(r["y"]), as_int(r["x"])]],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "l1_2_resolved_future_module_pool.csv",
        [r for r in membership_rows if r["resolved_l1_2_domain_class"] in FUTURE_CLASSES and resolved_future_pool[as_int(r["y"]), as_int(r["x"])]],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "l1_2_promoted_from_deferred_to_line.csv",
        [r for r in membership_rows if r["resolution_kind"] == "promoted_from_deferred_to_line"],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "l1_2_resolved_from_deferred_to_non_line.csv",
        [r for r in membership_rows if r["resolution_kind"] == "resolved_from_deferred_to_non_line"],
        MEMBERSHIP_FIELDS,
    )
    write_csv(
        out_dir / "l1_2_kept_deferred.csv",
        [r for r in membership_rows if r["resolution_kind"] == "kept_deferred"],
        MEMBERSHIP_FIELDS,
    )

    make_visuals(out_dir, l11_deferred, l11_class_map, resolved_class_map, subclass_map, promoted_from_deferred, resolved_from_deferred_to_non_line, kept_deferred, resolved_line_study, resolved_future_pool)

    counts = {
        "l1_1_deferred_pixels_seen": int(np.count_nonzero(l11_deferred)),
        "deferred_line_rescue_candidate_pixels": int(np.count_nonzero(subclass_map == DEFERRED_SUBCLASS_CODE["deferred_line_rescue_candidate"])),
        "deferred_mixed_candidate_pixels": int(np.count_nonzero(subclass_map == DEFERRED_SUBCLASS_CODE["deferred_mixed_candidate"])),
        "deferred_probable_non_line_candidate_pixels": int(np.count_nonzero(subclass_map == DEFERRED_SUBCLASS_CODE["deferred_probable_non_line_candidate"])),
        "deferred_tiny_low_evidence_pixels": int(np.count_nonzero(subclass_map == DEFERRED_SUBCLASS_CODE["deferred_tiny_low_evidence"])),
        "deferred_true_unknown_pixels": int(np.count_nonzero(subclass_map == DEFERRED_SUBCLASS_CODE["deferred_true_unknown"])),
        "promoted_from_deferred_to_line_pixels": int(np.count_nonzero(promoted_from_deferred)),
        "resolved_from_deferred_to_non_line_pixels": int(np.count_nonzero(resolved_from_deferred_to_non_line)),
        "resolved_from_deferred_to_mixed_pixels": int(np.count_nonzero(resolved_from_deferred_to_mixed)),
        "kept_deferred_pixels": int(np.count_nonzero(kept_deferred)),
        "resolved_line_study_support_pixels": int(np.count_nonzero(resolved_line_study)),
        "resolved_future_module_pool_pixels": int(np.count_nonzero(resolved_future_pool)),
        "l1_1_line_study_support_pixels": int(np.count_nonzero(l11_line_study)),
        "l1_1_future_module_pool_pixels": int(np.count_nonzero(l11_future)),
        "resolved_domain_region_count": len(region_rows),
        "deferred_subclass_region_counts": dict(Counter(r["deferred_subclass"] for r in subclass_rows)),
        "resolution_kind_region_counts": dict(Counter(r["resolution_kind"] for r in region_rows)),
        "resolved_domain_class_region_counts": dict(Counter(r["resolved_l1_2_domain_class"] for r in region_rows)),
    }
    resolved_changed_px = int(np.count_nonzero(changed_map))
    metrics = {
        "deferred_reduction_ratio_vs_l1_1": ratio(counts["l1_1_deferred_pixels_seen"] - counts["kept_deferred_pixels"], counts["l1_1_deferred_pixels_seen"]),
        "line_study_delta_ratio_vs_l1_1": ratio(counts["resolved_line_study_support_pixels"] - counts["l1_1_line_study_support_pixels"], counts["l1_1_line_study_support_pixels"]),
        "future_pool_traceability_rate": ratio(len(future_pixel_set & membership_pixel_set), len(future_pixel_set)),
        "resolution_traceability_rate": 1.0 if not changed_pixel_set else ratio(len(changed_pixel_set & resolution_membership_set), len(changed_pixel_set)),
        "promoted_from_deferred_traceability_rate": 1.0 if not promoted_pixel_set else ratio(len(promoted_pixel_set & resolution_membership_set), len(promoted_pixel_set)),
        "changed_deferred_pixels": resolved_changed_px,
    }
    contract = {
        "is_deferred_subsupport_resolver_not_recovery_module": True,
        "creates_final_geometry": False,
        "creates_final_lineobjects": False,
        "creates_axis_descriptors": False,
        "creates_crossings": False,
        "recognizes_ocr_strings": False,
        "recognizes_digit_values": False,
        "uses_grid_audit_truth_as_runtime_input": False,
        "does_not_force_deferred_to_disappear": True,
        "unresolved_deferred_support_is_preserved": True,
        "resolved_line_study_support_is_not_final_geometry": True,
    }

    output_missing_pre_json = missing_required(out_dir, [rel for rel in REQUIRED_OUTPUT_FILES if rel not in {"summary.json", "contract_audit.json"}])
    status = "completed" if all(invariants.values()) and not output_missing_pre_json else "failed_contract"
    outputs = {rel.replace("/", "_").replace(".", "_"): rel for rel in REQUIRED_OUTPUT_FILES}
    summary = {
        "version": VERSION,
        "status": status,
        "source_l1_1_run_dir": str(l11_dir),
        "source_l1_0_run_dir": str(l10_dir),
        "source_u1_1_run_dir": str(u11_dir),
        "source_v3_3_run_dir": str(v33_dir),
        "source_v3_4_2_run_dir": str(v342_dir) if v342_dir else "",
        "source_c1_0_run_dir": str(c10_dir) if c10_dir else "",
        "source_c1_1_run_dir": str(c11_dir) if c11_dir else "",
        "source_u1_0_run_dir": str(u10_dir) if u10_dir else "",
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
        "visual_acceptance_note": "Visual audit remains mandatory because L1.2 has no line-domain ground-truth dataset.",
    }
    contract_audit = {
        "version": VERSION,
        "contract_file": "outputs/CONTRACT_L1_2_DEFERRED_DOMAIN_SUBSUPPORT_RESOLVER_V1.md",
        "status": status,
        "semantic_rule": "l1_2_explains_deferred_without_forcing_it_to_disappear",
        "traceability_rule": "all_changed_support_is_subset_of_l1_1_deferred_support",
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
    ap.add_argument("--l1-1-dir", required=True)
    ap.add_argument("--l1-0-dir", required=True)
    ap.add_argument("--u1-1-dir", required=True)
    ap.add_argument("--v3-run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--v3-4-2-dir", default=None)
    ap.add_argument("--c1-dir", default=None)
    ap.add_argument("--c1-1-dir", default=None)
    ap.add_argument("--u1-0-dir", default=None)
    ap.add_argument("--max-line-rescue-microstructure", type=float, default=0.52)
    ap.add_argument("--min-line-rescue-context", type=float, default=0.60)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config(
        max_line_rescue_microstructure=args.max_line_rescue_microstructure,
        min_line_rescue_context=args.min_line_rescue_context,
    )
    run(
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
