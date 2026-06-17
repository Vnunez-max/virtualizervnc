#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X3.0 trainable geometric evidence unit.

X3.0 consumes already-produced modular evidence and readable trained assets. It
does not train at runtime, does not call upstream modules, and does not create
final virtualized geometry.

Critical rule:
    No module may gain interpretation by losing geometric traceability.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_X3_0_TRAINABLE_GEOMETRIC_EVIDENCE_UNIT"

CLASS_BACKGROUND = 0
CLASS_UNIT_LINE_STUDY = 1
CLASS_D1_GRID_LINE = 2
CLASS_FUTURE_POOL = 3
CLASS_D1_TEXT_OR_DIGIT = 4
CLASS_D1_TICK_OR_SCALE = 5
CLASS_D1_BORDER_OR_LAYOUT = 6
CLASS_D1_CURVE_OR_TRACE = 7
CLASS_D1_AMBIGUOUS = 8
CLASS_UNACCOUNTED = 9

CLASS_NAMES = {
    CLASS_BACKGROUND: "background",
    CLASS_UNIT_LINE_STUDY: "unit_line_study",
    CLASS_D1_GRID_LINE: "d1_grid_line_candidate",
    CLASS_FUTURE_POOL: "future_module_pool",
    CLASS_D1_TEXT_OR_DIGIT: "d1_text_or_digit_stroke",
    CLASS_D1_TICK_OR_SCALE: "d1_tick_or_scale_mark",
    CLASS_D1_BORDER_OR_LAYOUT: "d1_page_border_or_layout_box",
    CLASS_D1_CURVE_OR_TRACE: "d1_curve_or_data_trace",
    CLASS_D1_AMBIGUOUS: "d1_ambiguous_linear",
    CLASS_UNACCOUNTED: "unaccounted_observed",
}

CLASS_COLORS = {
    CLASS_BACKGROUND: (14, 14, 14),
    CLASS_UNIT_LINE_STUDY: (58, 166, 255),
    CLASS_D1_GRID_LINE: (255, 214, 64),
    CLASS_FUTURE_POOL: (255, 96, 96),
    CLASS_D1_TEXT_OR_DIGIT: (192, 122, 255),
    CLASS_D1_TICK_OR_SCALE: (255, 164, 64),
    CLASS_D1_BORDER_OR_LAYOUT: (255, 132, 48),
    CLASS_D1_CURVE_OR_TRACE: (50, 220, 155),
    CLASS_D1_AMBIGUOUS: (220, 220, 220),
    CLASS_UNACCOUNTED: (255, 255, 255),
}

SOURCE_BITS = {
    "unit_base_line": 1,
    "unit_base_future": 2,
    "g1_0_cal_v1_trainable_candidate": 4,
    "g1_0_cal_v1_changed_decision": 8,
    "d1_0_simple_linearity": 16,
    "d1_1_role_classifier": 32,
    "x3_fusion": 64,
    "c1_0_functional_evidence": 128,
    "c1_1_functional_evidence": 256,
}

G1_ACTION_NAMES = {
    0: "none",
    1: "kept_g1_0_promotion",
    2: "promoted_by_cal_v1_from_g1_0_deferred",
    3: "demoted_from_g1_0_promotion_to_future_pool",
    4: "reserved_for_future_non_line",
    5: "kept_non_promoted_deferred",
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    return value


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(to_jsonable(obj), indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], fields: Sequence[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(to_jsonable(row))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_map(path: Path, dtype: Any | None = None) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(str(path))
    arr = np.load(path)
    if dtype is not None:
        arr = arr.astype(dtype)
    return arr


def load_bool(path: Path) -> np.ndarray:
    return load_map(path).astype(bool)


def load_optional_bool(root: Optional[Path], rel_path: str, shape: Tuple[int, int]) -> Tuple[np.ndarray, bool, str]:
    if root is None:
        return np.zeros(shape, dtype=bool), False, ""
    path = Path(root) / rel_path
    if not path.exists():
        return np.zeros(shape, dtype=bool), False, str(path)
    arr = np.load(path).astype(bool)
    if arr.shape != shape:
        raise ValueError(f"Optional map has wrong shape: {path} {arr.shape} != {shape}")
    return arr, True, str(path)


def maps_dir(root: Path) -> Path:
    return Path(root) / "maps"


def check_same_shape(named: Dict[str, np.ndarray]) -> Tuple[int, int]:
    shapes = {name: arr.shape for name, arr in named.items()}
    unique = sorted(set(shapes.values()))
    if len(unique) != 1:
        raise ValueError(f"Input maps have inconsistent shapes: {shapes}")
    return unique[0]


def font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def make_overlay(class_map: np.ndarray, observed: np.ndarray) -> Image.Image:
    h, w = class_map.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[:, :] = CLASS_COLORS[CLASS_BACKGROUND]
    rgb[observed] = (50, 50, 50)
    for code, color in CLASS_COLORS.items():
        if code == CLASS_BACKGROUND:
            continue
        rgb[class_map == code] = color
    return Image.fromarray(rgb, mode="RGB")


def bool_rgb(mask: np.ndarray, color: Tuple[int, int, int], background: Tuple[int, int, int] = (18, 18, 18)) -> Image.Image:
    rgb = np.zeros((*mask.shape, 3), dtype=np.uint8)
    rgb[:, :] = background
    rgb[mask] = color
    return Image.fromarray(rgb, mode="RGB")


def make_contact_sheet(images: List[Tuple[str, Image.Image]], out: Path) -> None:
    if not images:
        return
    thumb_w = 360
    label_h = 28
    padding = 12
    cols = 2
    rows = int(np.ceil(len(images) / cols))
    thumbs: List[Tuple[str, Image.Image]] = []
    for label, img in images:
        ratio = thumb_w / img.width
        thumb_h = max(1, int(img.height * ratio))
        thumbs.append((label, img.resize((thumb_w, thumb_h), Image.Resampling.NEAREST)))
    row_h = max(img.height for _, img in thumbs) + label_h + padding
    sheet = Image.new("RGB", (cols * (thumb_w + padding) + padding, rows * row_h + padding), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    fnt = font(12)
    for idx, (label, img) in enumerate(thumbs):
        col = idx % cols
        row = idx // cols
        x = padding + col * (thumb_w + padding)
        y = padding + row * row_h
        draw.text((x, y), label, fill=(240, 240, 240), font=fnt)
        sheet.paste(img, (x, y + label_h))
    ensure_dir(out.parent)
    sheet.save(out)


def verify_model_assets(model_dir: Path) -> Dict[str, Any]:
    config_path = model_dir / "model_config.json"
    scaler_path = model_dir / "feature_scaler.json"
    coefficients_path = model_dir / "coefficients.csv"
    missing = [str(p) for p in (config_path, scaler_path, coefficients_path) if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing X3 trainable runtime assets: " + ", ".join(missing))
    config = load_json(config_path)
    scaler = load_json(scaler_path)
    with coefficients_path.open("r", encoding="utf-8", newline="") as handle:
        coeff_rows = list(csv.DictReader(handle))
    if not config.get("feature_names") or not config.get("targets"):
        raise ValueError("model_config.json lacks feature_names/targets")
    if not scaler.get("mean") or not scaler.get("std"):
        raise ValueError("feature_scaler.json lacks mean/std")
    if not coeff_rows:
        raise ValueError("coefficients.csv is empty")
    return {
        "model_dir": str(model_dir),
        "feature_count": len(config.get("feature_names", [])),
        "targets": config.get("targets", []),
        "coefficient_rows": len(coeff_rows),
        "assets_readable": True,
    }


def count(mask: np.ndarray) -> int:
    return int(np.count_nonzero(mask))


def build_class_rows(class_map: np.ndarray, observed: np.ndarray) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    observed_count = max(count(observed), 1)
    for code in sorted(CLASS_NAMES):
        pixels = int(np.count_nonzero((class_map == code) & observed))
        rows.append({
            "class_code": code,
            "class_name": CLASS_NAMES[code],
            "pixel_count": pixels,
            "ratio_of_observed": float(pixels / observed_count),
        })
    return rows


def build_action_rows(action_map: np.ndarray, candidate: np.ndarray) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for code in sorted(set(int(v) for v in np.unique(action_map)) | set(G1_ACTION_NAMES)):
        pixels = int(np.count_nonzero((action_map == code) & candidate))
        rows.append({
            "action_code": code,
            "action_name": G1_ACTION_NAMES.get(code, "unknown"),
            "candidate_pixel_count": pixels,
        })
    return rows


def run(
    unit_dir: Path,
    g1_cal_dir: Path,
    d1_0_dir: Path,
    d1_1_dir: Path,
    model_dir: Path,
    out_dir: Path,
    sample_id: str = "sample",
    c1_0_dir: Optional[Path] = None,
    c1_1_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    unit_maps = maps_dir(unit_dir)
    g1_maps = maps_dir(g1_cal_dir)
    d1_0_maps = maps_dir(d1_0_dir)
    d1_1_maps = maps_dir(d1_1_dir)
    out_dir = Path(out_dir)
    map_out = out_dir / "maps"
    table_out = out_dir / "tables"
    visual_out = out_dir / "visuals"
    for path in (map_out, table_out, visual_out):
        ensure_dir(path)

    model_audit = verify_model_assets(Path(model_dir))

    observed = load_bool(unit_maps / "unit_observed_support_map.npy")
    unit_line = load_bool(unit_maps / "unit_final_line_study_support_map.npy")
    unit_future = load_bool(unit_maps / "unit_final_future_module_pool_map.npy")
    unit_unaccounted = load_bool(unit_maps / "unit_unaccounted_observed_support_map.npy")
    unit_stage = load_map(unit_maps / "unit_stage_contribution_map.npy").astype(np.uint8)

    g1_candidate = load_bool(g1_maps / "g1_0_cal_v1_promoted_to_line_map.npy") | load_bool(
        g1_maps / "g1_0_cal_v1_non_promoted_candidate_map.npy"
    )
    g1_action = load_map(g1_maps / "g1_0_cal_v1_action_map.npy").astype(np.uint8)
    g1_promoted = load_bool(g1_maps / "g1_0_cal_v1_promoted_to_line_map.npy")
    g1_future = load_bool(g1_maps / "g1_0_cal_v1_calibrated_future_module_pool_map.npy")
    g1_deferred = load_bool(g1_maps / "g1_0_cal_v1_calibrated_deferred_domain_support_map.npy")

    d1_candidate = load_bool(d1_0_maps / "simple_linearity_candidate_map.npy")
    d1_hypothesis = load_map(d1_0_maps / "linearity_hypothesis_id_map.npy").astype(np.int32)
    d1_role = load_map(d1_1_maps / "d1_1_role_class_map.npy").astype(np.uint8)
    d1_confidence = load_map(d1_1_maps / "d1_1_role_confidence_map.npy").astype(np.float32)
    d1_grid = load_bool(d1_1_maps / "grid_line_candidate_map.npy")
    d1_text = load_bool(d1_1_maps / "text_or_digit_stroke_map.npy")
    d1_tick = load_bool(d1_1_maps / "tick_or_scale_mark_map.npy")
    d1_border = load_bool(d1_1_maps / "page_border_or_layout_box_map.npy")
    d1_curve = load_bool(d1_1_maps / "curve_or_data_trace_map.npy")
    d1_ambiguous = load_bool(d1_1_maps / "ambiguous_linear_map.npy")

    shape = check_same_shape({
        "observed": observed,
        "unit_line": unit_line,
        "unit_future": unit_future,
        "unit_unaccounted": unit_unaccounted,
        "unit_stage": unit_stage,
        "g1_candidate": g1_candidate,
        "g1_action": g1_action,
        "g1_promoted": g1_promoted,
        "g1_future": g1_future,
        "g1_deferred": g1_deferred,
        "d1_candidate": d1_candidate,
        "d1_hypothesis": d1_hypothesis,
        "d1_role": d1_role,
        "d1_confidence": d1_confidence,
        "d1_grid": d1_grid,
        "d1_text": d1_text,
        "d1_tick": d1_tick,
        "d1_border": d1_border,
        "d1_curve": d1_curve,
        "d1_ambiguous": d1_ambiguous,
    })

    c1_0_validated, c1_0_supplied, c1_0_source = load_optional_bool(
        c1_0_dir,
        "maps/validated_hypothesis_observed_support_map.npy",
        shape,
    )
    c1_1_validated, c1_1_supplied, c1_1_source = load_optional_bool(
        c1_1_dir,
        "maps/collective_validated_observed_support_map.npy",
        shape,
    )
    c1_functional_evidence = (c1_0_validated | c1_1_validated) & observed

    trainable_changed = g1_candidate & np.isin(g1_action, [2, 3, 4])
    trainable_influence = g1_candidate & observed
    trainable_line_support = g1_promoted & observed

    d1_grid_added = d1_grid & observed & ~unit_line
    x3_line = (unit_line | d1_grid_added) & observed
    d1_reserved_future = (d1_text | d1_tick | d1_border | d1_curve | d1_ambiguous) & observed & ~x3_line
    x3_future = (unit_future | g1_future | d1_reserved_future | (g1_deferred & observed & ~x3_line)) & observed & ~x3_line
    x3_accounted = x3_line | x3_future
    x3_unaccounted = observed & ~x3_accounted

    class_map = np.zeros(shape, dtype=np.uint8)
    class_map[observed] = CLASS_UNACCOUNTED
    class_map[x3_future] = CLASS_FUTURE_POOL
    class_map[d1_text & observed & ~x3_line] = CLASS_D1_TEXT_OR_DIGIT
    class_map[d1_tick & observed & ~x3_line] = CLASS_D1_TICK_OR_SCALE
    class_map[d1_border & observed & ~x3_line] = CLASS_D1_BORDER_OR_LAYOUT
    class_map[d1_curve & observed & ~x3_line] = CLASS_D1_CURVE_OR_TRACE
    class_map[d1_ambiguous & observed & ~x3_line] = CLASS_D1_AMBIGUOUS
    class_map[unit_line & observed] = CLASS_UNIT_LINE_STUDY
    class_map[d1_grid_added] = CLASS_D1_GRID_LINE
    class_map[x3_unaccounted] = CLASS_UNACCOUNTED

    source_bit = np.zeros(shape, dtype=np.uint16)
    for name, mask in [
        ("unit_base_line", unit_line),
        ("unit_base_future", unit_future),
        ("g1_0_cal_v1_trainable_candidate", g1_candidate),
        ("g1_0_cal_v1_changed_decision", trainable_changed),
        ("d1_0_simple_linearity", d1_candidate),
        ("d1_1_role_classifier", d1_role > 0),
        ("x3_fusion", x3_accounted),
        ("c1_0_functional_evidence", c1_0_validated),
        ("c1_1_functional_evidence", c1_1_validated),
    ]:
        source_bit[mask & observed] |= SOURCE_BITS[name]

    trainable_influence_code = np.zeros(shape, dtype=np.uint8)
    trainable_influence_code[trainable_influence] = 1
    trainable_influence_code[trainable_changed] = 2
    trainable_influence_code[trainable_line_support] = np.maximum(trainable_influence_code[trainable_line_support], 3)

    np.save(map_out / "x3_observed_support_map.npy", observed.astype(np.uint8))
    np.save(map_out / "x3_unit_line_study_support_map.npy", unit_line.astype(np.uint8))
    np.save(map_out / "x3_trainable_g1_0_cal_v1_influence_map.npy", trainable_influence_code.astype(np.uint8))
    np.save(map_out / "x3_trainable_changed_decision_map.npy", trainable_changed.astype(np.uint8))
    np.save(map_out / "x3_d1_grid_line_added_map.npy", d1_grid_added.astype(np.uint8))
    np.save(map_out / "x3_fused_line_study_support_map.npy", x3_line.astype(np.uint8))
    np.save(map_out / "x3_fused_future_module_pool_map.npy", x3_future.astype(np.uint8))
    np.save(map_out / "x3_unaccounted_observed_support_map.npy", x3_unaccounted.astype(np.uint8))
    np.save(map_out / "x3_fused_class_map.npy", class_map.astype(np.uint8))
    np.save(map_out / "x3_source_bit_map.npy", source_bit.astype(np.uint16))
    np.save(map_out / "x3_d1_role_class_map.npy", d1_role.astype(np.uint8))
    np.save(map_out / "x3_d1_role_confidence_map.npy", d1_confidence.astype(np.float32))
    np.save(map_out / "x3_d1_hypothesis_id_map.npy", d1_hypothesis.astype(np.int32))
    np.save(map_out / "x3_c1_functional_evidence_map.npy", c1_functional_evidence.astype(np.uint8))

    class_rows = build_class_rows(class_map, observed)
    write_csv(table_out / "x3_fused_class_summary.csv", class_rows, [
        "class_code", "class_name", "pixel_count", "ratio_of_observed",
    ])
    write_csv(table_out / "x3_trainable_action_summary.csv", build_action_rows(g1_action, g1_candidate), [
        "action_code", "action_name", "candidate_pixel_count",
    ])
    trainable_rows = [
        {
            "layer_key": "g1_0_cal_v1",
            "status": "active_trainable_runtime_asset",
            "scope": "component_family_candidate_calibration",
            "runtime_truth_labels_allowed": False,
            "candidate_pixels": count(g1_candidate & observed),
            "changed_decision_pixels": count(trainable_changed),
            "model_dir": str(model_dir),
        },
        {
            "layer_key": "u1_1_cal",
            "status": "upstream_calibrable_layer",
            "scope": "purity_thresholds_hysteresis",
            "runtime_truth_labels_allowed": False,
            "candidate_pixels": 0,
            "changed_decision_pixels": 0,
            "model_dir": "",
        },
        {
            "layer_key": "l1_1",
            "status": "upstream_calibrable_layer",
            "scope": "domain_thresholds",
            "runtime_truth_labels_allowed": False,
            "candidate_pixels": 0,
            "changed_decision_pixels": 0,
            "model_dir": "",
        },
        {
            "layer_key": "l1_2_cal",
            "status": "upstream_calibrable_layer",
            "scope": "deferred_line_like_thresholds",
            "runtime_truth_labels_allowed": False,
            "candidate_pixels": 0,
            "changed_decision_pixels": 0,
            "model_dir": "",
        },
        {
            "layer_key": "c1_cal_future",
            "status": "reserved_trainable_slot_not_runtime_active",
            "scope": "future_residual_geometry_hypothesis_calibration",
            "runtime_truth_labels_allowed": False,
            "candidate_pixels": count(c1_functional_evidence),
            "changed_decision_pixels": 0,
            "model_dir": "",
        },
        {
            "layer_key": "d1_cal_future",
            "status": "reserved_trainable_slot_not_runtime_active",
            "scope": "future_deferred_role_calibration",
            "runtime_truth_labels_allowed": False,
            "candidate_pixels": count(d1_candidate & observed),
            "changed_decision_pixels": 0,
            "model_dir": "",
        },
    ]
    write_csv(table_out / "x3_trainable_layers.csv", trainable_rows, [
        "layer_key",
        "status",
        "scope",
        "runtime_truth_labels_allowed",
        "candidate_pixels",
        "changed_decision_pixels",
        "model_dir",
    ])
    functional_rows = [
        {
            "layer_key": "c1_0",
            "status": "active_functional_layer",
            "supplied_to_x3_run": c1_0_supplied,
            "role": "individual_residual_geometry_hypothesis_validation",
            "evidence_pixels": count(c1_0_validated & observed),
            "source": c1_0_source,
        },
        {
            "layer_key": "c1_1",
            "status": "active_functional_layer",
            "supplied_to_x3_run": c1_1_supplied,
            "role": "collective_residual_geometry_hypothesis_validation",
            "evidence_pixels": count(c1_1_validated & observed),
            "source": c1_1_source,
        },
        {
            "layer_key": "d1_0",
            "status": "active_functional_layer",
            "supplied_to_x3_run": True,
            "role": "deferred_simple_linearity",
            "evidence_pixels": count(d1_candidate & observed),
            "source": str(d1_0_dir),
        },
        {
            "layer_key": "d1_1",
            "status": "active_functional_layer",
            "supplied_to_x3_run": True,
            "role": "deferred_linear_role_classification",
            "evidence_pixels": count(d1_role > 0),
            "source": str(d1_1_dir),
        },
    ]
    write_csv(table_out / "x3_functional_layers.csv", functional_rows, [
        "layer_key",
        "status",
        "supplied_to_x3_run",
        "role",
        "evidence_pixels",
        "source",
    ])
    trace_rows = [
        {"source": name, "bit": bit, "pixel_count": int(np.count_nonzero((source_bit & bit) > 0))}
        for name, bit in SOURCE_BITS.items()
    ]
    write_csv(table_out / "x3_source_traceability_summary.csv", trace_rows, [
        "source", "bit", "pixel_count",
    ])

    overlay = make_overlay(class_map, observed)
    overlay.save(visual_out / "01_x3_fused_class_overlay.png")
    bool_rgb(x3_line, (58, 166, 255)).save(visual_out / "02_x3_fused_line_study.png")
    bool_rgb(x3_future, (255, 96, 96)).save(visual_out / "03_x3_future_module_pool.png")
    bool_rgb(trainable_influence, (84, 255, 180)).save(visual_out / "04_x3_trainable_g1_influence.png")
    bool_rgb(d1_grid_added, (255, 214, 64)).save(visual_out / "05_x3_d1_grid_added.png")
    bool_rgb(c1_functional_evidence, (255, 118, 210)).save(visual_out / "06_x3_c1_functional_evidence.png")
    influence_rgb = np.zeros((*shape, 3), dtype=np.uint8)
    influence_rgb[:, :] = (16, 16, 16)
    influence_rgb[trainable_influence_code == 1] = (84, 180, 255)
    influence_rgb[trainable_influence_code == 2] = (255, 214, 64)
    influence_rgb[trainable_influence_code == 3] = (84, 255, 180)
    Image.fromarray(influence_rgb, mode="RGB").save(visual_out / "07_x3_trainable_influence_codes.png")
    make_contact_sheet([
        ("X3 fused class overlay", overlay),
        ("X3 fused line-study", Image.open(visual_out / "02_x3_fused_line_study.png")),
        ("X3 future-module pool", Image.open(visual_out / "03_x3_future_module_pool.png")),
        ("G1.0-CAL trainable influence", Image.open(visual_out / "04_x3_trainable_g1_influence.png")),
        ("D1 grid-line additions", Image.open(visual_out / "05_x3_d1_grid_added.png")),
        ("C1 functional evidence", Image.open(visual_out / "06_x3_c1_functional_evidence.png")),
        ("Trainable influence codes", Image.open(visual_out / "07_x3_trainable_influence_codes.png")),
    ], visual_out / "08_x3_audit_summary.png")

    counts = {
        "observed_support_pixels": count(observed),
        "unit_line_study_support_pixels": count(unit_line),
        "unit_future_module_pool_pixels": count(unit_future),
        "g1_0_cal_v1_candidate_pixels": count(g1_candidate & observed),
        "g1_0_cal_v1_changed_decision_pixels": count(trainable_changed),
        "g1_0_cal_v1_promoted_pixels": count(g1_promoted & observed),
        "d1_0_simple_linearity_candidate_pixels": count(d1_candidate & observed),
        "d1_1_grid_line_candidate_pixels": count(d1_grid & observed),
        "c1_0_functional_evidence_pixels": count(c1_0_validated & observed),
        "c1_1_functional_evidence_pixels": count(c1_1_validated & observed),
        "c1_functional_evidence_pixels": count(c1_functional_evidence),
        "x3_d1_grid_line_added_pixels": count(d1_grid_added),
        "x3_fused_line_study_support_pixels": count(x3_line),
        "x3_fused_future_module_pool_pixels": count(x3_future),
        "x3_unaccounted_observed_support_pixels": count(x3_unaccounted),
    }
    metrics = {
        "x3_line_delta_vs_unit_pixels": counts["x3_fused_line_study_support_pixels"] - counts["unit_line_study_support_pixels"],
        "x3_future_delta_vs_unit_pixels": counts["x3_fused_future_module_pool_pixels"] - counts["unit_future_module_pool_pixels"],
        "x3_accounted_ratio_of_observed": float(count(x3_accounted) / max(count(observed), 1)),
        "trainable_changed_ratio_of_candidate": float(count(trainable_changed) / max(count(g1_candidate & observed), 1)),
        "d1_grid_added_ratio_of_observed": float(count(d1_grid_added) / max(count(observed), 1)),
        "c1_functional_evidence_ratio_of_observed": float(count(c1_functional_evidence) / max(count(observed), 1)),
    }
    invariants = {
        "all_input_maps_same_shape": True,
        "x3_line_subset_of_observed": bool(np.all(~x3_line | observed)),
        "x3_future_subset_of_observed": bool(np.all(~x3_future | observed)),
        "x3_line_and_future_disjoint": bool(not np.any(x3_line & x3_future)),
        "d1_grid_added_subset_of_d1_candidate": bool(np.all(~d1_grid_added | d1_candidate)),
        "trainable_influence_subset_of_g1_candidate": bool(np.all(~trainable_influence | g1_candidate)),
        "trainable_changed_subset_of_g1_candidate": bool(np.all(~trainable_changed | g1_candidate)),
        "source_trace_for_all_x3_line_pixels": bool(np.all(source_bit[x3_line] > 0)),
        "source_trace_for_all_x3_future_pixels": bool(np.all(source_bit[x3_future] > 0)),
        "c1_functional_evidence_subset_of_observed": bool(np.all(~c1_functional_evidence | observed)),
        "g1_trainable_model_assets_readable": bool(model_audit["assets_readable"]),
        "runtime_truth_labels_not_used": True,
        "does_not_create_final_geometry": True,
        "does_not_modify_upstream_outputs": True,
        "does_not_modify_v3_4_2": True,
    }
    summary = {
        "version": VERSION,
        "status": "completed" if all(invariants.values()) else "completed_with_invariant_failure",
        "sample_id": sample_id,
        "counts": counts,
        "metrics": metrics,
        "invariants": invariants,
        "model_audit": model_audit,
        "trainable_policy": {
            "unit_is_trainable_monolith": False,
            "active_trainable_runtime_layers": ["g1_0_cal_v1"],
            "active_functional_layers": ["c1_0", "c1_1", "d1_0", "d1_1"],
            "calibrable_upstream_layers": ["u1_1_cal", "l1_1", "l1_2_cal"],
            "reserved_trainable_slots_not_runtime_active": ["c1_cal_future", "d1_cal_future"],
            "runtime_truth_labels_allowed": False,
        },
        "outputs": {
            "maps_dir": "maps",
            "tables_dir": "tables",
            "visuals_dir": "visuals",
            "summary_json": "summary.json",
            "contract_audit_json": "contract_audit.json",
        },
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "contract_audit.json", {
        "version": VERSION,
        "contract": "CONTRACT_X3_0_TRAINABLE_GEOMETRIC_EVIDENCE_UNIT",
        "critical_rule": "No module may gain interpretation by losing geometric traceability.",
        "invariants": invariants,
        "acceptance_pass": bool(all(invariants.values())),
    })

    print(
        json.dumps(
            {
                "status": summary["status"],
                "observed_support_pixels": counts["observed_support_pixels"],
                "x3_fused_line_study_support_pixels": counts["x3_fused_line_study_support_pixels"],
                "x3_fused_future_module_pool_pixels": counts["x3_fused_future_module_pool_pixels"],
                "g1_0_cal_v1_changed_decision_pixels": counts["g1_0_cal_v1_changed_decision_pixels"],
                "c1_functional_evidence_pixels": counts["c1_functional_evidence_pixels"],
                "x3_d1_grid_line_added_pixels": counts["x3_d1_grid_line_added_pixels"],
                "invariants_pass": all(invariants.values()),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return summary


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit-dir", required=True)
    ap.add_argument("--g1-cal-dir", required=True)
    ap.add_argument("--d1-0-dir", required=True)
    ap.add_argument("--d1-1-dir", required=True)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample-id", default="sample")
    ap.add_argument("--c1-0-dir", default=None)
    ap.add_argument("--c1-1-dir", default=None)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    run(
        unit_dir=Path(args.unit_dir),
        g1_cal_dir=Path(args.g1_cal_dir),
        d1_0_dir=Path(args.d1_0_dir),
        d1_1_dir=Path(args.d1_1_dir),
        model_dir=Path(args.model_dir),
        out_dir=Path(args.out),
        sample_id=args.sample_id,
        c1_0_dir=Path(args.c1_0_dir) if args.c1_0_dir else None,
        c1_1_dir=Path(args.c1_1_dir) if args.c1_1_dir else None,
    )


if __name__ == "__main__":
    main()
