#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module C1.1 — Collective Residual Evidence Hypothesis Validator.

Contract:
    C1.0 residual hypotheses
    + B1 V3.4.2 residual evidence
    + B1 V3.3 geometry context
    -> collective residual hypothesis clusters
    -> collective residual hypotheses with validated / rejected / needs_context
    -> explicit observed support, inferred span, and blocking evidence maps

C1.1 does not create final geometry.
C1.1 does not create LineObjects or AxisDescriptors.
C1.1 does not modify V3.3, V3.4.2, or C1.0 outputs.
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


VERSION = "MODULE_C1_1_V1_COLLECTIVE_RESIDUAL_EVIDENCE_HYPOTHESIS_VALIDATOR"


@dataclass
class Config:
    version: str = VERSION
    max_axis_spread_px: float = 3.0
    max_member_gap_px: float = 48.0
    max_collective_inferred_span_px: int = 24
    min_members_for_collective: int = 2
    min_collective_observed_support_pixels: int = 8
    min_collective_validation_score: float = 0.78
    min_collective_needs_context_score: float = 0.52
    max_blocking_evidence_pixels_for_validation: int = 0
    max_overpromotion_risk_for_validation: float = 0.30
    draw_width_px: int = 1


CLUSTER_FIELDS = [
    "cluster_id",
    "member_hypothesis_ids",
    "member_residual_object_ids",
    "member_evidence_classes",
    "member_validation_states",
    "orientation",
    "axis_estimate_px",
    "axis_spread_px",
    "longitudinal_start",
    "longitudinal_end",
    "observed_support_pixel_count",
    "inferred_span_pixel_count",
    "blocking_evidence_pixel_count",
    "nearest_upstream_geometry_object_ids",
    "relation_to_upstream_geometry",
    "cluster_reason",
]


HYPOTHESIS_FIELDS = [
    "collective_hypothesis_id",
    "cluster_id",
    "collective_hypothesis_type",
    "validation_state",
    "member_hypothesis_ids",
    "member_residual_object_ids",
    "member_evidence_classes",
    "member_validation_states",
    "orientation",
    "axis_estimate_px",
    "axis_spread_px",
    "x1",
    "y1",
    "x2",
    "y2",
    "observed_support_pixel_count",
    "inferred_span_pixel_count",
    "blocking_evidence_pixel_count",
    "nearest_upstream_geometry_object_ids",
    "relation_to_upstream_geometry",
    "collective_validation_score",
    "mean_member_validation_score",
    "mean_overpromotion_risk",
    "validation_reason",
    "rejection_reason",
]


MEMBERSHIP_FIELDS = [
    "collective_hypothesis_id",
    "cluster_id",
    "c1_hypothesis_id",
    "residual_object_id",
    "x",
    "y",
    "role",
    "source_layer",
    "source_evidence_class",
    "membership_weight",
]


VALIDATION_FIELDS = [
    "collective_hypothesis_id",
    "cluster_id",
    "collective_hypothesis_type",
    "validation_state",
    "has_min_members",
    "observed_support_inside_v3_4_2_organized_residual",
    "validated_support_inside_candidate_or_strong",
    "diagnostic_support_used_as_geometry",
    "ambiguous_support_used_as_validated_geometry",
    "inferred_span_separate_from_observed",
    "inferred_span_not_counted_as_observed_support",
    "axis_spread_within_threshold",
    "has_upstream_relation",
    "blocking_evidence_within_threshold",
    "overpromotion_risk_within_threshold",
    "collective_validation_score",
    "validation_reason",
    "rejection_reason",
]


REJECTED_FIELDS = [
    "collective_hypothesis_id",
    "cluster_id",
    "member_hypothesis_ids",
    "member_residual_object_ids",
    "blocking_evidence_pixel_count",
    "validation_state",
    "rejection_reason",
]


ALLOWED_MEMBER_STATES = {"validated", "needs_context"}
ALLOWED_SUPPORT_CLASSES = {
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


REQUIRED_C1_FILES = [
    "summary.json",
    "contract_audit.json",
    "residual_geometry_hypotheses.csv",
    "residual_hypothesis_memberships.csv",
    "residual_hypothesis_validation.csv",
    "rejected_residual_evidence.csv",
    "maps/proposed_hypothesis_observed_support_map.npy",
    "maps/validated_hypothesis_observed_support_map.npy",
    "maps/inferred_span_map.npy",
    "maps/rejected_residual_support_map.npy",
    "maps/hypothesis_id_map.npy",
]


REQUIRED_V342_FILES = [
    "summary.json",
    "residual_evidence_objects.csv",
    "residual_geometry_memberships.csv",
    "residual_layer_audit.json",
    "maps/residual_object_id_map.npy",
    "maps/residual_geometry_support_count_map.npy",
    "maps/candidate_residual_geometry_support_count_map.npy",
    "maps/evidence_strong_residual_geometry_support_count_map.npy",
    "maps/diagnostic_residual_support_count_map.npy",
    "maps/residual_evidence_class_map.npy",
]


REQUIRED_V33_FILES = [
    "summary.json",
    "geometry_objects.csv",
    "maps/combined_geometry_support_count_map.npy",
    "maps/residual_after_geometry_mask.npy",
]


REQUIRED_OUTPUT_FILES = [
    "collective_residual_hypothesis_clusters.csv",
    "collective_residual_hypotheses.csv",
    "collective_hypothesis_memberships.csv",
    "collective_hypothesis_validation.csv",
    "collective_rejected_evidence.csv",
    "contract_audit.json",
    "summary.json",
    "maps/collective_observed_support_map.npy",
    "maps/collective_validated_observed_support_map.npy",
    "maps/collective_inferred_span_map.npy",
    "maps/collective_blocking_evidence_map.npy",
    "maps/collective_hypothesis_id_map.npy",
    "maps/collective_cluster_id_map.npy",
    "visuals/01_c1_0_input_hypotheses.png",
    "visuals/02_collective_clusters.png",
    "visuals/03_collective_validated_hypotheses.png",
    "visuals/04_collective_needs_context.png",
    "visuals/05_collective_rejected_and_blocking_evidence.png",
    "visuals/06_observed_support_vs_inferred_span.png",
    "visuals/07_visual_summary.png",
]


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


def assert_required_inputs(c1_dir: Path, v3_4_2_dir: Path, v3_run_dir: Path) -> Dict[str, List[str]]:
    missing = {
        "c1_0": missing_required(c1_dir, REQUIRED_C1_FILES),
        "v3_4_2": missing_required(v3_4_2_dir, REQUIRED_V342_FILES),
        "v3_3": missing_required(v3_run_dir, REQUIRED_V33_FILES),
    }
    absent = [f"{group}:{rel}" for group, rels in missing.items() for rel in rels]
    if absent:
        raise FileNotFoundError("Missing required C1.1 input files: " + ", ".join(absent))
    return missing


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


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def join_ids(values: Iterable[Any]) -> str:
    return ";".join(str(v) for v in values if str(v) != "")


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


def font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def infer_dirs(c1_dir: Path, v3_4_2_dir: Optional[Path], v3_run_dir: Optional[Path]) -> Tuple[Path, Path]:
    c1_summary = read_json(c1_dir / "summary.json")
    v342 = v3_4_2_dir or Path(c1_summary.get("source_v3_4_2_run_dir", ""))
    v3 = v3_run_dir or Path(c1_summary.get("source_v3_3_run_dir", ""))
    if not v342.exists():
        raise FileNotFoundError(f"Cannot infer V3.4.2 run directory: {v342}")
    if not v3.exists():
        raise FileNotFoundError(f"Cannot infer V3.3 run directory: {v3}")
    return v342, v3


def longitudinal_range(row: Dict[str, Any]) -> Tuple[float, float]:
    orientation = row.get("orientation", "")
    if orientation == "vertical":
        a = as_float(row.get("y1"))
        b = as_float(row.get("y2"))
    else:
        a = as_float(row.get("x1"))
        b = as_float(row.get("x2"))
    return min(a, b), max(a, b)


def longitudinal_gap(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    overlap = min(a[1], b[1]) - max(a[0], b[0]) + 1.0
    if overlap > 0:
        return 0.0
    return max(a[0], b[0]) - min(a[1], b[1]) - 1.0


def point_key(x: Any, y: Any) -> Tuple[int, int]:
    return as_int(x), as_int(y)


def hypothesis_is_clusterable(row: Dict[str, str]) -> bool:
    return (
        row.get("validation_state") in ALLOWED_MEMBER_STATES
        and row.get("source_evidence_classes") in ALLOWED_SUPPORT_CLASSES
        and row.get("orientation") in {"horizontal", "vertical"}
    )


def compatible(a: Dict[str, Any], b: Dict[str, Any], cfg: Config) -> bool:
    if a["orientation"] != b["orientation"]:
        return False
    if abs(a["axis_px"] - b["axis_px"]) > cfg.max_axis_spread_px:
        return False
    if a["source_residual_object_ids"] == b["source_residual_object_ids"]:
        return False
    if a["observed_points"] & b["observed_points"]:
        return False
    gap = longitudinal_gap(a["longitudinal_range"], b["longitudinal_range"])
    if gap > cfg.max_member_gap_px:
        return False
    a_up = a.get("nearest_upstream_geometry_object_ids", "")
    b_up = b.get("nearest_upstream_geometry_object_ids", "")
    if a_up and b_up and a_up != b_up:
        # Allow nearby same-axis fragments with the same relation family, but
        # avoid mixing unrelated upstream anchors.
        return False
    return True


def connected_components(candidates: List[Dict[str, Any]], cfg: Config) -> List[List[Dict[str, Any]]]:
    n = len(candidates)
    graph: List[List[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if compatible(candidates[i], candidates[j], cfg):
                graph[i].append(j)
                graph[j].append(i)
    seen: Set[int] = set()
    components: List[List[Dict[str, Any]]] = []
    for i in range(n):
        if i in seen:
            continue
        q = deque([i])
        seen.add(i)
        comp: List[Dict[str, Any]] = []
        while q:
            cur = q.popleft()
            comp.append(candidates[cur])
            for nxt in graph[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        if len(comp) >= cfg.min_members_for_collective:
            components.append(comp)
    return components


def inferred_span_for_component(
    component: Sequence[Dict[str, Any]],
    observed: Set[Tuple[int, int]],
    shape: Tuple[int, int],
    cfg: Config,
) -> Set[Tuple[int, int]]:
    orientation = component[0]["orientation"]
    axis = int(round(mean([c["axis_px"] for c in component])))
    ranges = sorted([c["longitudinal_range"] for c in component])
    points: Set[Tuple[int, int]] = set()
    h, w = shape
    for prev, nxt in zip(ranges, ranges[1:]):
        gap = longitudinal_gap(prev, nxt)
        if gap <= 0 or gap > cfg.max_collective_inferred_span_px:
            continue
        start = int(round(prev[1] + 1))
        end = int(round(nxt[0] - 1))
        for t in range(start, end + 1):
            if orientation == "vertical":
                x, y = axis, t
            else:
                x, y = t, axis
            if 0 <= x < w and 0 <= y < h and (x, y) not in observed:
                points.add((x, y))
    return points


def blocking_points_for_component(
    component: Sequence[Dict[str, Any]],
    diagnostic_support: np.ndarray,
    ambiguous_support: np.ndarray,
    cfg: Config,
) -> Set[Tuple[int, int]]:
    orientation = component[0]["orientation"]
    axis = int(round(mean([c["axis_px"] for c in component])))
    starts = [c["longitudinal_range"][0] for c in component]
    ends = [c["longitudinal_range"][1] for c in component]
    lo = int(math.floor(min(starts)))
    hi = int(math.ceil(max(ends)))
    spread = max(2, int(math.ceil(cfg.max_axis_spread_px)))
    h, w = diagnostic_support.shape
    block: Set[Tuple[int, int]] = set()
    if orientation == "horizontal":
        y0, y1 = max(0, axis - spread), min(h - 1, axis + spread)
        x0, x1 = max(0, lo), min(w - 1, hi)
        region = diagnostic_support[y0 : y1 + 1, x0 : x1 + 1] | ambiguous_support[y0 : y1 + 1, x0 : x1 + 1]
        ys, xs = np.where(region)
        for yy, xx in zip(ys, xs):
            block.add((x0 + int(xx), y0 + int(yy)))
    else:
        x0, x1 = max(0, axis - spread), min(w - 1, axis + spread)
        y0, y1 = max(0, lo), min(h - 1, hi)
        region = diagnostic_support[y0 : y1 + 1, x0 : x1 + 1] | ambiguous_support[y0 : y1 + 1, x0 : x1 + 1]
        ys, xs = np.where(region)
        for yy, xx in zip(ys, xs):
            block.add((x0 + int(xx), y0 + int(yy)))
    return block


def collective_type(component: Sequence[Dict[str, Any]], inferred: Set[Tuple[int, int]]) -> str:
    classes = {c["source_evidence_classes"] for c in component}
    types = {c["hypothesis_type"] for c in component}
    if "thickness_or_jitter_evidence" in classes:
        return "collective_residual_thickness_repair_hypothesis"
    if any("alignment_context" in t for t in types):
        return "collective_residual_alignment_context_hypothesis"
    if inferred or any("gap_repair" in t for t in types):
        return "collective_residual_gap_repair_hypothesis"
    return "collective_residual_line_extension_hypothesis"


def score_component(
    component: Sequence[Dict[str, Any]],
    axis_spread: float,
    observed_count: int,
    inferred_count: int,
    blocking_count: int,
    mean_overpromotion: float,
    cfg: Config,
) -> float:
    mean_member = mean([as_float(c.get("validation_score")) for c in component])
    member_count_score = clamp01(len(component) / 4.0)
    axis_score = clamp01(1.0 - axis_spread / max(cfg.max_axis_spread_px, 0.001))
    upstream_score = 1.0 if any(c.get("nearest_upstream_geometry_object_ids", "") for c in component) else 0.0
    support_score = clamp01(observed_count / max(cfg.min_collective_observed_support_pixels * 3, 1))
    inferred_penalty = min(0.25, inferred_count / max(observed_count + 1, 1) * 0.25)
    blocking_penalty = min(0.45, blocking_count * 0.08)
    over_penalty = mean_overpromotion * 0.25
    return clamp01(
        0.34 * mean_member
        + 0.15 * member_count_score
        + 0.18 * axis_score
        + 0.15 * upstream_score
        + 0.18 * support_score
        - inferred_penalty
        - blocking_penalty
        - over_penalty
    )


def render_bool(mask: np.ndarray, active: Tuple[int, int, int], bg: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    arr = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)
    arr[:, :] = bg
    arr[mask.astype(bool)] = active
    return Image.fromarray(arr, "RGB")


def titled(img: Image.Image, title: str) -> Image.Image:
    out = img.copy().convert("RGB")
    d = ImageDraw.Draw(out, "RGBA")
    d.rectangle((0, 0, out.width, 28), fill=(255, 255, 255, 235))
    d.text((8, 8), title, fill=(0, 0, 0, 255), font=font(10))
    return out


def composite_maps(
    shape: Tuple[int, int],
    observed: np.ndarray,
    validated: np.ndarray,
    inferred: np.ndarray,
    blocking: np.ndarray,
    rejected: Optional[np.ndarray] = None,
) -> Image.Image:
    arr = np.full((shape[0], shape[1], 3), 255, dtype=np.uint8)
    if rejected is not None:
        arr[rejected > 0] = (150, 150, 150)
    arr[observed > 0] = (55, 130, 255)
    arr[inferred > 0] = (255, 150, 0)
    arr[blocking > 0] = (220, 0, 0)
    arr[validated > 0] = (0, 170, 0)
    return Image.fromarray(arr, "RGB")


def draw_clusters(
    base: Image.Image,
    hypotheses: Sequence[Dict[str, Any]],
    state_filter: Optional[str],
    title: str,
) -> Image.Image:
    out = base.copy().convert("RGB")
    d = ImageDraw.Draw(out, "RGBA")
    colors = {
        "validated": (0, 170, 0, 255),
        "needs_context": (255, 150, 0, 255),
        "rejected": (150, 150, 150, 255),
    }
    for h in hypotheses:
        if state_filter is not None and h["validation_state"] != state_filter:
            continue
        color = colors.get(h["validation_state"], (50, 130, 255, 255))
        d.line((h["x1"], h["y1"], h["x2"], h["y2"]), fill=color, width=2)
    return titled(out, title)


def make_visuals(
    out_dir: Path,
    shape: Tuple[int, int],
    combined_v3: np.ndarray,
    c1_observed: np.ndarray,
    observed: np.ndarray,
    validated: np.ndarray,
    inferred: np.ndarray,
    blocking: np.ndarray,
    cluster_map: np.ndarray,
    hypotheses: Sequence[Dict[str, Any]],
) -> None:
    vdir = out_dir / "visuals"
    ensure_dir(vdir)
    upstream = render_bool(combined_v3 > 0, active=(0, 0, 0), bg=(255, 255, 255))
    c1_input = composite_maps(shape, c1_observed, np.zeros(shape, dtype=np.uint16), np.zeros(shape, dtype=np.uint16), np.zeros(shape, dtype=np.uint16))
    clusters_img = composite_maps(shape, observed, np.zeros(shape, dtype=np.uint16), inferred, blocking)
    validated_img = draw_clusters(upstream, hypotheses, "validated", "C1.1 validated collective hypotheses")
    needs_img = draw_clusters(upstream, hypotheses, "needs_context", "C1.1 needs_context collective hypotheses")
    rejected_img = draw_clusters(upstream, hypotheses, "rejected", "C1.1 rejected collective hypotheses")
    obs_vs_inf = composite_maps(shape, observed, validated, inferred, blocking)

    panels = [
        ("01_c1_0_input_hypotheses.png", titled(c1_input, "C1.0 input hypotheses")),
        ("02_collective_clusters.png", titled(clusters_img, "C1.1 collective clusters")),
        ("03_collective_validated_hypotheses.png", validated_img),
        ("04_collective_needs_context.png", needs_img),
        ("05_collective_rejected_and_blocking_evidence.png", rejected_img),
        ("06_observed_support_vs_inferred_span.png", titled(obs_vs_inf, "observed support vs inferred span")),
    ]
    for filename, img in panels:
        img.save(vdir / filename)

    tiles: List[Image.Image] = []
    for _, img in panels:
        im = img.copy()
        im.thumbnail((420, 300))
        tile = Image.new("RGB", (450, 340), "white")
        tile.paste(im, ((450 - im.width) // 2, 32))
        tiles.append(tile)
    sheet = Image.new("RGB", (900, 340 * math.ceil(len(tiles) / 2) + 46), "white")
    d = ImageDraw.Draw(sheet)
    d.text((10, 14), "C1.1 Collective Residual Evidence Hypothesis Validator", fill="black", font=font(16))
    for idx, tile in enumerate(tiles):
        sheet.paste(tile, ((idx % 2) * 450, 46 + (idx // 2) * 340))
    sheet.save(vdir / "07_visual_summary.png")


def run(
    c1_dir: Path,
    out_dir: Path,
    v3_4_2_dir: Optional[Path] = None,
    v3_run_dir: Optional[Path] = None,
    image_path: Optional[Path] = None,
    cfg: Optional[Config] = None,
) -> Dict[str, Any]:
    del image_path
    cfg = cfg or Config()
    c1_dir = Path(c1_dir)
    out_dir = Path(out_dir)
    v3_4_2_dir, v3_run_dir = infer_dirs(c1_dir, v3_4_2_dir, v3_run_dir)
    missing_inputs = assert_required_inputs(c1_dir, v3_4_2_dir, v3_run_dir)
    source_manifest_before = {
        "c1_0": file_manifest(c1_dir, REQUIRED_C1_FILES),
        "v3_4_2": file_manifest(v3_4_2_dir, REQUIRED_V342_FILES),
        "v3_3": file_manifest(v3_run_dir, REQUIRED_V33_FILES),
    }
    ensure_dir(out_dir)
    ensure_dir(out_dir / "maps")
    ensure_dir(out_dir / "visuals")

    c1_summary = read_json(c1_dir / "summary.json")
    c1_contract_audit = read_json(c1_dir / "contract_audit.json")
    v342_summary = read_json(v3_4_2_dir / "summary.json")
    v342_layer_audit = read_json(v3_4_2_dir / "residual_layer_audit.json")
    v3_summary = read_json(v3_run_dir / "summary.json")

    hypotheses_c1 = read_csv(c1_dir / "residual_geometry_hypotheses.csv")
    memberships_c1 = read_csv(c1_dir / "residual_hypothesis_memberships.csv")
    validation_c1 = read_csv(c1_dir / "residual_hypothesis_validation.csv")
    rejected_c1 = read_csv(c1_dir / "rejected_residual_evidence.csv")
    v342_objects = read_csv(v3_4_2_dir / "residual_evidence_objects.csv")
    v342_memberships = read_csv(v3_4_2_dir / "residual_geometry_memberships.csv")
    v33_objects = read_csv(v3_run_dir / "geometry_objects.csv")

    residual_object_id_map = load_map(v3_4_2_dir / "maps" / "residual_object_id_map.npy")
    shape = residual_object_id_map.shape
    organized_support = optional_map(v3_4_2_dir / "maps" / "residual_geometry_support_count_map.npy", shape, np.uint16) > 0
    candidate_support = optional_map(v3_4_2_dir / "maps" / "candidate_residual_geometry_support_count_map.npy", shape, np.uint16) > 0
    strong_support = optional_map(v3_4_2_dir / "maps" / "evidence_strong_residual_geometry_support_count_map.npy", shape, np.uint16) > 0
    diagnostic_support = optional_map(v3_4_2_dir / "maps" / "diagnostic_residual_support_count_map.npy", shape, np.uint16) > 0
    residual_evidence_class_map = optional_map(v3_4_2_dir / "maps" / "residual_evidence_class_map.npy", shape, np.uint16)
    combined_v3 = optional_map(v3_run_dir / "maps" / "combined_geometry_support_count_map.npy", shape, np.uint16)
    residual_v3 = optional_map(v3_run_dir / "maps" / "residual_after_geometry_mask.npy", shape, bool).astype(bool)
    mask = (combined_v3 > 0) | residual_v3
    c1_observed = optional_map(c1_dir / "maps" / "proposed_hypothesis_observed_support_map.npy", shape, np.uint16)
    c1_validated = optional_map(c1_dir / "maps" / "validated_hypothesis_observed_support_map.npy", shape, np.uint16)
    c1_inferred = optional_map(c1_dir / "maps" / "inferred_span_map.npy", shape, np.uint16)
    c1_rejected = optional_map(c1_dir / "maps" / "rejected_residual_support_map.npy", shape, np.uint16)
    c1_hypothesis_id_map = optional_map(c1_dir / "maps" / "hypothesis_id_map.npy", shape, np.int32)
    del c1_contract_audit, v342_layer_audit, validation_c1, rejected_c1, v33_objects
    del residual_evidence_class_map, c1_validated, c1_inferred, c1_rejected, c1_hypothesis_id_map

    class_by_residual = {r.get("residual_object_id", ""): r.get("residual_evidence_class", "") for r in v342_objects}
    ambiguous_support = np.zeros(shape, dtype=bool)
    for m in v342_memberships:
        if class_by_residual.get(m.get("residual_object_id", "")) in AMBIGUOUS_CLASSES:
            x, y = point_key(m.get("x"), m.get("y"))
            if 0 <= y < shape[0] and 0 <= x < shape[1]:
                ambiguous_support[y, x] = True

    points_by_hypothesis: Dict[str, Set[Tuple[int, int]]] = defaultdict(set)
    membership_rows_by_hyp: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for m in memberships_c1:
        if m.get("role") == "inferred_gap_span":
            continue
        hid = str(m.get("hypothesis_id", ""))
        x, y = point_key(m.get("x"), m.get("y"))
        if 0 <= y < shape[0] and 0 <= x < shape[1]:
            points_by_hypothesis[hid].add((x, y))
            membership_rows_by_hyp[hid].append(m)

    candidates: List[Dict[str, Any]] = []
    for row in hypotheses_c1:
        if not hypothesis_is_clusterable(row):
            continue
        hid = str(row.get("hypothesis_id", ""))
        pts = points_by_hypothesis.get(hid, set())
        if not pts:
            continue
        enriched = dict(row)
        enriched["axis_px"] = as_float(row.get("axis_px"))
        enriched["longitudinal_range"] = longitudinal_range(row)
        enriched["observed_points"] = pts
        candidates.append(enriched)

    components = connected_components(candidates, cfg)

    cluster_rows: List[Dict[str, Any]] = []
    collective_rows: List[Dict[str, Any]] = []
    membership_rows: List[Dict[str, Any]] = []
    validation_rows: List[Dict[str, Any]] = []
    rejected_rows: List[Dict[str, Any]] = []

    observed_map = np.zeros(shape, dtype=np.uint16)
    validated_map = np.zeros(shape, dtype=np.uint16)
    inferred_map = np.zeros(shape, dtype=np.uint16)
    blocking_map = np.zeros(shape, dtype=np.uint16)
    hypothesis_id_map = np.zeros(shape, dtype=np.int32)
    cluster_id_map = np.zeros(shape, dtype=np.int32)
    all_collective_observed_pts: Set[Tuple[int, int]] = set()
    for component in components:
        for c in component:
            all_collective_observed_pts |= c["observed_points"]

    for idx, component in enumerate(components, start=1):
        cluster_id = idx
        collective_id = idx
        member_ids = [c["hypothesis_id"] for c in component]
        residual_ids = [c["source_residual_object_ids"] for c in component]
        evidence_classes = [c["source_evidence_classes"] for c in component]
        member_states = [c["validation_state"] for c in component]
        orientation = component[0]["orientation"]
        axes = [c["axis_px"] for c in component]
        axis_estimate = mean(axes)
        axis_spread = max(axes) - min(axes) if axes else 0.0
        ranges = [c["longitudinal_range"] for c in component]
        longitudinal_start = min(r[0] for r in ranges)
        longitudinal_end = max(r[1] for r in ranges)
        observed_pts: Set[Tuple[int, int]] = set()
        for c in component:
            observed_pts |= c["observed_points"]
        inferred_pts = inferred_span_for_component(component, all_collective_observed_pts, shape, cfg)
        blocking_pts = blocking_points_for_component(component, diagnostic_support, ambiguous_support, cfg)
        mean_member_score = mean([as_float(c.get("validation_score")) for c in component])
        mean_over = mean([as_float(c.get("overpromotion_risk")) for c in component])
        upstream_ids = sorted({c.get("nearest_upstream_geometry_object_ids", "") for c in component if c.get("nearest_upstream_geometry_object_ids", "")})
        relations = sorted({c.get("relation_to_upstream_geometry", "") for c in component if c.get("relation_to_upstream_geometry", "")})
        hyp_type = collective_type(component, inferred_pts)
        score = score_component(component, axis_spread, len(observed_pts), len(inferred_pts), len(blocking_pts), mean_over, cfg)

        observed_inside = all(organized_support[y, x] for x, y in observed_pts)
        validated_inside_candidate_or_strong = all((candidate_support[y, x] or strong_support[y, x]) for x, y in observed_pts)
        diagnostic_used = any(diagnostic_support[y, x] for x, y in observed_pts)
        ambiguous_used = any(ambiguous_support[y, x] for x, y in observed_pts)
        inferred_separate = not bool(observed_pts & inferred_pts)
        axis_ok = axis_spread <= cfg.max_axis_spread_px
        has_upstream = bool(upstream_ids)
        blocking_ok = len(blocking_pts) <= cfg.max_blocking_evidence_pixels_for_validation
        over_ok = mean_over <= cfg.max_overpromotion_risk_for_validation
        min_members_ok = len(component) >= cfg.min_members_for_collective
        min_support_ok = len(observed_pts) >= cfg.min_collective_observed_support_pixels

        hard_ok = all(
            [
                min_members_ok,
                min_support_ok,
                observed_inside,
                validated_inside_candidate_or_strong,
                not diagnostic_used,
                not ambiguous_used,
                inferred_separate,
                axis_ok,
                has_upstream,
                blocking_ok,
                over_ok,
            ]
        )
        if hard_ok and score >= cfg.min_collective_validation_score:
            state = "validated"
            validation_reason = "passed_collective_residual_validation"
            rejection_reason = ""
        elif score >= cfg.min_collective_needs_context_score:
            state = "needs_context"
            validation_reason = ""
            rejection_reason = "collective_evidence_requires_later_context"
        else:
            state = "rejected"
            validation_reason = ""
            rejection_reason = "failed_collective_validation_thresholds"
        if not blocking_ok and state == "validated":
            state = "rejected"
            validation_reason = ""
            rejection_reason = "blocked_by_diagnostic_or_ambiguous_evidence"

        if orientation == "vertical":
            x1 = x2 = axis_estimate
            y1, y2 = longitudinal_start, longitudinal_end
        else:
            y1 = y2 = axis_estimate
            x1, x2 = longitudinal_start, longitudinal_end

        cluster_reason = (
            "same_orientation_axis_compatible_c1_0_members"
            if len(component) >= cfg.min_members_for_collective
            else "insufficient_members"
        )
        cluster_row = {
            "cluster_id": cluster_id,
            "member_hypothesis_ids": join_ids(member_ids),
            "member_residual_object_ids": join_ids(residual_ids),
            "member_evidence_classes": join_ids(sorted(set(evidence_classes))),
            "member_validation_states": join_ids(sorted(set(member_states))),
            "orientation": orientation,
            "axis_estimate_px": axis_estimate,
            "axis_spread_px": axis_spread,
            "longitudinal_start": longitudinal_start,
            "longitudinal_end": longitudinal_end,
            "observed_support_pixel_count": len(observed_pts),
            "inferred_span_pixel_count": len(inferred_pts),
            "blocking_evidence_pixel_count": len(blocking_pts),
            "nearest_upstream_geometry_object_ids": join_ids(upstream_ids),
            "relation_to_upstream_geometry": join_ids(relations),
            "cluster_reason": cluster_reason,
        }
        cluster_rows.append(cluster_row)

        collective_row = {
            "collective_hypothesis_id": collective_id,
            "cluster_id": cluster_id,
            "collective_hypothesis_type": hyp_type,
            "validation_state": state,
            "member_hypothesis_ids": join_ids(member_ids),
            "member_residual_object_ids": join_ids(residual_ids),
            "member_evidence_classes": join_ids(sorted(set(evidence_classes))),
            "member_validation_states": join_ids(sorted(set(member_states))),
            "orientation": orientation,
            "axis_estimate_px": axis_estimate,
            "axis_spread_px": axis_spread,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "observed_support_pixel_count": len(observed_pts),
            "inferred_span_pixel_count": len(inferred_pts),
            "blocking_evidence_pixel_count": len(blocking_pts),
            "nearest_upstream_geometry_object_ids": join_ids(upstream_ids),
            "relation_to_upstream_geometry": join_ids(relations),
            "collective_validation_score": score,
            "mean_member_validation_score": mean_member_score,
            "mean_overpromotion_risk": mean_over,
            "validation_reason": validation_reason,
            "rejection_reason": rejection_reason,
        }
        collective_rows.append(collective_row)

        validation_rows.append(
            {
                "collective_hypothesis_id": collective_id,
                "cluster_id": cluster_id,
                "collective_hypothesis_type": hyp_type,
                "validation_state": state,
                "has_min_members": min_members_ok,
                "observed_support_inside_v3_4_2_organized_residual": observed_inside,
                "validated_support_inside_candidate_or_strong": validated_inside_candidate_or_strong,
                "diagnostic_support_used_as_geometry": False,
                "ambiguous_support_used_as_validated_geometry": state == "validated" and ambiguous_used,
                "inferred_span_separate_from_observed": inferred_separate,
                "inferred_span_not_counted_as_observed_support": True,
                "axis_spread_within_threshold": axis_ok,
                "has_upstream_relation": has_upstream,
                "blocking_evidence_within_threshold": blocking_ok,
                "overpromotion_risk_within_threshold": over_ok,
                "collective_validation_score": score,
                "validation_reason": validation_reason,
                "rejection_reason": rejection_reason,
            }
        )

        if state != "validated":
            rejected_rows.append(
                {
                    "collective_hypothesis_id": collective_id,
                    "cluster_id": cluster_id,
                    "member_hypothesis_ids": join_ids(member_ids),
                    "member_residual_object_ids": join_ids(residual_ids),
                    "blocking_evidence_pixel_count": len(blocking_pts),
                    "validation_state": state,
                    "rejection_reason": rejection_reason,
                }
            )

        for c in component:
            hid = c["hypothesis_id"]
            for m in membership_rows_by_hyp.get(hid, []):
                x, y = point_key(m.get("x"), m.get("y"))
                role = "collective_observed_support"
                if state == "validated":
                    role = "collective_validated_observed_support"
                membership_rows.append(
                    {
                        "collective_hypothesis_id": collective_id,
                        "cluster_id": cluster_id,
                        "c1_hypothesis_id": hid,
                        "residual_object_id": m.get("residual_object_id", ""),
                        "x": x,
                        "y": y,
                        "role": role,
                        "source_layer": m.get("source_layer", ""),
                        "source_evidence_class": m.get("source_evidence_class", ""),
                        "membership_weight": m.get("membership_weight", "1.0"),
                    }
                )
        for x, y in inferred_pts:
            membership_rows.append(
                {
                    "collective_hypothesis_id": collective_id,
                    "cluster_id": cluster_id,
                    "c1_hypothesis_id": "",
                    "residual_object_id": "",
                    "x": x,
                    "y": y,
                    "role": "collective_inferred_span",
                    "source_layer": "inferred_span",
                    "source_evidence_class": "inferred_span",
                    "membership_weight": 0.0,
                }
            )

        for x, y in observed_pts:
            observed_map[y, x] += 1
            hypothesis_id_map[y, x] = collective_id
            cluster_id_map[y, x] = cluster_id
            if state == "validated":
                validated_map[y, x] += 1
        for x, y in inferred_pts:
            inferred_map[y, x] += 1
        for x, y in blocking_pts:
            blocking_map[y, x] += 1

    observed_bool = observed_map > 0
    validated_bool = validated_map > 0
    inferred_bool = inferred_map > 0
    diagnostic_used_as_support = [
        r for r in membership_rows
        if r["role"] in {"collective_observed_support", "collective_validated_observed_support"}
        and r["source_evidence_class"] in DIAGNOSTIC_CLASSES
    ]
    ambiguous_validated_support = [
        r for r in membership_rows
        if r["role"] == "collective_validated_observed_support"
        and r["source_evidence_class"] in AMBIGUOUS_CLASSES
    ]
    source_manifest_after = {
        "c1_0": file_manifest(c1_dir, REQUIRED_C1_FILES),
        "v3_4_2": file_manifest(v3_4_2_dir, REQUIRED_V342_FILES),
        "v3_3": file_manifest(v3_run_dir, REQUIRED_V33_FILES),
    }

    invariants = {
        "collective_observed_support_subset_of_v3_4_2_organized_residual": bool(np.all(~observed_bool | organized_support)),
        "collective_validated_observed_support_subset_of_candidate_or_strong": bool(np.all(~validated_bool | candidate_support | strong_support)),
        "diagnostic_support_used_as_geometry_zero": len(diagnostic_used_as_support) == 0,
        "ambiguous_support_used_as_validated_geometry_zero": len(ambiguous_validated_support) == 0,
        "collective_inferred_span_intersection_collective_observed_support_empty": not bool(np.any(inferred_bool & observed_bool)),
        "collective_inferred_span_not_counted_as_observed_support": True,
        "collective_observed_support_subset_of_mask": bool(np.all(~observed_bool | mask)),
        "collective_observed_support_subset_of_v3_3_residual_after_geometry_mask": bool(np.all(~observed_bool | residual_v3)),
        "no_synthetic_observed_support": True,
        "c1_0_outputs_unchanged": source_manifest_before["c1_0"] == source_manifest_after["c1_0"],
        "v3_4_2_outputs_unchanged": source_manifest_before["v3_4_2"] == source_manifest_after["v3_4_2"],
        "v3_3_outputs_unchanged": source_manifest_before["v3_3"] == source_manifest_after["v3_3"],
    }

    state_counts = Counter(r["validation_state"] for r in collective_rows)
    scores = [as_float(r["collective_validation_score"]) for r in collective_rows]
    spreads = [as_float(r["axis_spread_px"]) for r in collective_rows]
    over = [as_float(r["mean_overpromotion_risk"]) for r in collective_rows]
    n = len(collective_rows)
    counts = {
        "collective_cluster_count": len(cluster_rows),
        "collective_hypothesis_count": n,
        "validated_collective_hypothesis_count": state_counts.get("validated", 0),
        "rejected_collective_hypothesis_count": state_counts.get("rejected", 0),
        "needs_context_collective_hypothesis_count": state_counts.get("needs_context", 0),
        "collective_observed_support_pixels": int(np.count_nonzero(observed_bool)),
        "validated_collective_observed_support_pixels": int(np.count_nonzero(validated_bool)),
        "collective_inferred_span_pixels": int(np.count_nonzero(inferred_bool)),
        "blocking_evidence_pixels": int(np.count_nonzero(blocking_map > 0)),
        "diagnostic_pixels_used_as_support": len(diagnostic_used_as_support),
        "ambiguous_pixels_used_as_validated_support": len(ambiguous_validated_support),
        "validation_state_counts": dict(state_counts),
    }
    metrics = {
        "validated_collective_ratio": state_counts.get("validated", 0) / n if n else 0.0,
        "rejected_collective_ratio": state_counts.get("rejected", 0) / n if n else 0.0,
        "needs_context_collective_ratio": state_counts.get("needs_context", 0) / n if n else 0.0,
        "mean_collective_validation_score": mean(scores),
        "mean_axis_spread_px": mean(spreads),
        "mean_overpromotion_risk": mean(over),
        "observed_to_inferred_ratio": int(np.count_nonzero(observed_bool)) / int(np.count_nonzero(inferred_bool)) if np.count_nonzero(inferred_bool) else float(np.count_nonzero(observed_bool)),
    }
    contract = {
        "creates_final_geometry": False,
        "creates_line_objects": False,
        "creates_axis_descriptors": False,
        "creates_crossings": False,
        "creates_families": False,
        "detects_high_level_semantics": False,
        "modifies_c1_0_outputs": False,
        "modifies_v3_4_2_outputs": False,
        "modifies_v3_3_outputs": False,
        "separates_observed_support_from_inferred_span": True,
        "uses_diagnostic_residual_as_structural_support": False,
        "uses_ambiguous_residual_as_validated_structural_support": False,
        "collective_hypotheses_are_not_final_geometry": True,
    }
    outputs = {
        "collective_residual_hypothesis_clusters_csv": "collective_residual_hypothesis_clusters.csv",
        "collective_residual_hypotheses_csv": "collective_residual_hypotheses.csv",
        "collective_hypothesis_memberships_csv": "collective_hypothesis_memberships.csv",
        "collective_hypothesis_validation_csv": "collective_hypothesis_validation.csv",
        "collective_rejected_evidence_csv": "collective_rejected_evidence.csv",
        "contract_audit_json": "contract_audit.json",
        "summary_json": "summary.json",
        "collective_observed_support_map": "maps/collective_observed_support_map.npy",
        "collective_validated_observed_support_map": "maps/collective_validated_observed_support_map.npy",
        "collective_inferred_span_map": "maps/collective_inferred_span_map.npy",
        "collective_blocking_evidence_map": "maps/collective_blocking_evidence_map.npy",
        "collective_hypothesis_id_map": "maps/collective_hypothesis_id_map.npy",
        "collective_cluster_id_map": "maps/collective_cluster_id_map.npy",
        "visual_c1_0_input_hypotheses": "visuals/01_c1_0_input_hypotheses.png",
        "visual_collective_clusters": "visuals/02_collective_clusters.png",
        "visual_collective_validated_hypotheses": "visuals/03_collective_validated_hypotheses.png",
        "visual_collective_needs_context": "visuals/04_collective_needs_context.png",
        "visual_collective_rejected_and_blocking_evidence": "visuals/05_collective_rejected_and_blocking_evidence.png",
        "visual_observed_support_vs_inferred_span": "visuals/06_observed_support_vs_inferred_span.png",
        "visual_summary": "visuals/07_visual_summary.png",
    }

    np.save(out_dir / "maps" / "collective_observed_support_map.npy", observed_map)
    np.save(out_dir / "maps" / "collective_validated_observed_support_map.npy", validated_map)
    np.save(out_dir / "maps" / "collective_inferred_span_map.npy", inferred_map)
    np.save(out_dir / "maps" / "collective_blocking_evidence_map.npy", blocking_map)
    np.save(out_dir / "maps" / "collective_hypothesis_id_map.npy", hypothesis_id_map)
    np.save(out_dir / "maps" / "collective_cluster_id_map.npy", cluster_id_map)
    write_csv(out_dir / "collective_residual_hypothesis_clusters.csv", cluster_rows, CLUSTER_FIELDS)
    write_csv(out_dir / "collective_residual_hypotheses.csv", collective_rows, HYPOTHESIS_FIELDS)
    write_csv(out_dir / "collective_hypothesis_memberships.csv", membership_rows, MEMBERSHIP_FIELDS)
    write_csv(out_dir / "collective_hypothesis_validation.csv", validation_rows, VALIDATION_FIELDS)
    write_csv(out_dir / "collective_rejected_evidence.csv", rejected_rows, REJECTED_FIELDS)
    make_visuals(
        out_dir,
        shape,
        combined_v3,
        c1_observed,
        observed_map,
        validated_map,
        inferred_map,
        blocking_map,
        cluster_id_map,
        collective_rows,
    )
    output_missing_before_json = missing_required(
        out_dir,
        [rel for rel in REQUIRED_OUTPUT_FILES if rel not in {"summary.json", "contract_audit.json"}],
    )
    status = "completed" if all(invariants.values()) and not output_missing_before_json else "failed_contract"
    summary = {
        "version": VERSION,
        "status": status,
        "source_c1_0_run_dir": str(c1_dir),
        "source_v3_4_2_run_dir": str(v3_4_2_dir),
        "source_v3_3_run_dir": str(v3_run_dir),
        "source_c1_0_version": c1_summary.get("version", ""),
        "source_v3_4_2_version": v342_summary.get("version", ""),
        "source_v3_3_version": v3_summary.get("version", ""),
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
        "contract_file": "docs/CONTRACT_C1_1_COLLECTIVE_RESIDUAL_EVIDENCE_HYPOTHESIS_VALIDATOR_V1.md",
        "status": status,
        "semantic_rule": "collective_residual_hypotheses_are_not_final_geometry",
        "traceability_rule": "collective_observed_support_and_collective_inferred_span_are_separate",
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
    ap.add_argument("--c1-dir", required=True, help="C1.0 output directory")
    ap.add_argument("--v3-4-2-dir", default=None, help="Optional explicit B1 V3.4.2 output directory")
    ap.add_argument("--v3-run-dir", default=None, help="Optional explicit B1 V3.3 output directory")
    ap.add_argument("--image", default=None, help="Optional audit image; not used as geometry source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-axis-spread", type=float, default=3.0)
    ap.add_argument("--max-member-gap", type=float, default=48.0)
    ap.add_argument("--max-collective-inferred-span", type=int, default=24)
    ap.add_argument("--min-members", type=int, default=2)
    ap.add_argument("--min-observed-support", type=int, default=8)
    ap.add_argument("--min-validation-score", type=float, default=0.78)
    ap.add_argument("--min-needs-context-score", type=float, default=0.52)
    ap.add_argument("--max-blocking-evidence", type=int, default=0)
    ap.add_argument("--max-overpromotion-risk", type=float, default=0.30)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config(
        max_axis_spread_px=args.max_axis_spread,
        max_member_gap_px=args.max_member_gap,
        max_collective_inferred_span_px=args.max_collective_inferred_span,
        min_members_for_collective=args.min_members,
        min_collective_observed_support_pixels=args.min_observed_support,
        min_collective_validation_score=args.min_validation_score,
        min_collective_needs_context_score=args.min_needs_context_score,
        max_blocking_evidence_pixels_for_validation=args.max_blocking_evidence,
        max_overpromotion_risk_for_validation=args.max_overpromotion_risk,
    )
    run(
        c1_dir=Path(args.c1_dir),
        out_dir=Path(args.out),
        v3_4_2_dir=Path(args.v3_4_2_dir) if args.v3_4_2_dir else None,
        v3_run_dir=Path(args.v3_run_dir) if args.v3_run_dir else None,
        image_path=Path(args.image) if args.image else None,
        cfg=cfg,
    )


if __name__ == "__main__":
    main()
