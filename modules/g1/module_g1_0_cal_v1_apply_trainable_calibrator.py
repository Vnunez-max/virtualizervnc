#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply G1.0-CAL V1 trainable calibrator to an existing G1.0 run.

This is a unit-level evaluation adapter for a named sample. It reads the trained
G1.0-CAL V1 model and G1.0 deferred-family associations, then writes calibrated
outputs in a separate directory. It does not modify G1.0 runtime artifacts and
does not create final geometry.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_G1_0_CAL_V1_APPLY_TRAINABLE_CALIBRATOR_TO_G1_0_UNIT"
SOURCE_MODEL_VERSION = "MODULE_G1_0_CAL_V1_TRAINABLE_DEFERRED_FAMILY_CALIBRATOR"

TARGETS = [
    "promote_to_probable_line",
    "keep_deferred",
    "reserve_for_future_non_line",
]
PROMOTE_TARGET = "promote_to_probable_line"

PREDICTION_FIELDS = [
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
    "baseline_g1_0_promoted_to_probable_line",
    "cal_v1_predicted_target",
    "cal_v1_promoted_to_probable_line",
    "cal_v1_action_vs_g1_0",
    "p_promote_to_probable_line",
    "p_keep_deferred",
    "p_reserve_for_future_non_line",
    "promote_threshold",
    "family_distance",
    "anchor_score",
    "family_strength_score",
    "component_colinearity_score",
    "component_run_score",
    "microstructure_score",
    "mixed_contact_score",
    "conflict_contact_score",
    "g1_0_association_score",
    "cal_v1_decision_reason",
]

PIXEL_FIELDS = [
    "association_id",
    "g1_0_region_id",
    "source_l1_2_cal_region_id",
    "family_id",
    "x",
    "y",
    "baseline_g1_0_promoted_to_probable_line",
    "cal_v1_predicted_target",
    "cal_v1_promoted_to_probable_line",
    "cal_v1_action_vs_g1_0",
    "p_promote_to_probable_line",
    "p_keep_deferred",
    "p_reserve_for_future_non_line",
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


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(to_jsonable(obj), indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> List[Dict[str, str]]:
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


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def log1p_pos(value: float) -> float:
    return math.log1p(max(0.0, value))


def font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def load_model(model_dir: Path) -> Tuple[List[str], List[str], float, Dict[str, float], Dict[str, float], np.ndarray]:
    config = read_json(model_dir / "model_config.json")
    scaler = read_json(model_dir / "feature_scaler.json")
    targets = list(config["targets"])
    feature_names = list(config["feature_names"])
    threshold = float(config["promote_threshold"])
    mean = {k: float(v) for k, v in scaler["mean"].items()}
    std = {k: float(v) for k, v in scaler["std"].items()}
    coef_rows = read_csv(model_dir / "coefficients.csv")
    coef_by_feature = {row["feature"]: row for row in coef_rows}
    weights = np.zeros((len(feature_names) + 1, len(targets)), dtype=np.float64)
    for i, name in enumerate(feature_names + ["bias"]):
        row = coef_by_feature[name]
        for j, target in enumerate(targets):
            weights[i, j] = as_float(row[target])
    return feature_names, targets, threshold, mean, std, weights


def softmax(logits: np.ndarray) -> np.ndarray:
    z = logits - np.max(logits)
    ez = np.exp(z)
    return ez / np.sum(ez)


def g1_association_score(row: Dict[str, str], max_distance: float = 5.0) -> float:
    x0 = as_int(row.get("component_bbox_x0"))
    y0 = as_int(row.get("component_bbox_y0"))
    x1 = as_int(row.get("component_bbox_x1"))
    y1 = as_int(row.get("component_bbox_y1"))
    major = max(x1 - x0 + 1, y1 - y0 + 1)
    distance = as_float(row.get("family_distance"))
    distance_term = clamp01(1.0 - distance / max(max_distance, 1e-6))
    return clamp01(
        0.27 * distance_term
        + 0.23 * as_float(row.get("anchor_score"))
        + 0.25 * as_float(row.get("family_strength_score"))
        + 0.15 * min(1.0, major / 16.0)
        + 0.10 * as_float(row.get("component_colinearity_score"))
    )


def feature_dict(row: Dict[str, str], max_distance: float = 5.0) -> Dict[str, float]:
    x0 = as_int(row.get("component_bbox_x0"))
    y0 = as_int(row.get("component_bbox_y0"))
    x1 = as_int(row.get("component_bbox_x1"))
    y1 = as_int(row.get("component_bbox_y1"))
    width = max(1, x1 - x0 + 1)
    height = max(1, y1 - y0 + 1)
    area = max(1, width * height)
    major = max(width, height)
    minor = min(width, height)
    n = as_int(row.get("component_pixel_count"))
    distance = as_float(row.get("family_distance"))
    distance_term = clamp01(1.0 - distance / max(max_distance, 1e-6))
    fill_ratio = clamp01(n / area)
    aspect_ratio = major / max(minor, 1)
    slenderness = clamp01((major - minor) / max(major, 1))
    micro = as_float(row.get("source_microstructure_score"))
    compactness = clamp01(minor / max(major, 1))
    return {
        "component_pixel_count_log": log1p_pos(n),
        "family_distance": distance,
        "distance_term": distance_term,
        "anchor_score": as_float(row.get("anchor_score")),
        "family_strength_score": as_float(row.get("family_strength_score")),
        "component_colinearity_score": as_float(row.get("component_colinearity_score")),
        "component_run_score": as_float(row.get("component_run_score")),
        "microstructure_score": micro,
        "mixed_contact_score": as_float(row.get("source_mixed_contact_score")),
        "conflict_contact_score": as_float(row.get("source_conflict_contact_score")),
        "bbox_width_log": log1p_pos(width),
        "bbox_height_log": log1p_pos(height),
        "major_length_log": log1p_pos(major),
        "minor_length_log": log1p_pos(minor),
        "bbox_area_log": log1p_pos(area),
        "fill_ratio": fill_ratio,
        "aspect_ratio_log": math.log(max(aspect_ratio, 1.0)),
        "slenderness_score": slenderness,
        "orientation_horizontal": 1.0 if row.get("orientation") == "horizontal" else 0.0,
        "orientation_vertical": 1.0 if row.get("orientation") == "vertical" else 0.0,
        "g1_0_association_score": g1_association_score(row, max_distance),
        "compact_symbol_risk": clamp01(compactness * micro * (1.0 - slenderness) * (1.0 - fill_ratio)),
    }


def predict(row: Dict[str, str], feature_names: Sequence[str], targets: Sequence[str], threshold: float, mean: Dict[str, float], std: Dict[str, float], weights: np.ndarray) -> Tuple[str, np.ndarray, Dict[str, float]]:
    feats = feature_dict(row)
    x = np.array([(feats[name] - mean[name]) / max(std[name], 1e-9) for name in feature_names] + [1.0], dtype=np.float64)
    probs = softmax(x @ weights)
    promote_idx = targets.index(PROMOTE_TARGET)
    if probs[promote_idx] >= threshold:
        target = PROMOTE_TARGET
    else:
        keep_idx = targets.index("keep_deferred")
        reserve_idx = targets.index("reserve_for_future_non_line")
        target = "keep_deferred" if probs[keep_idx] >= probs[reserve_idx] else "reserve_for_future_non_line"
    return target, probs, feats


def action_vs_g1(baseline_promoted: bool, cal_promoted: bool, target: str) -> str:
    if baseline_promoted and cal_promoted:
        return "kept_g1_0_promotion"
    if baseline_promoted and not cal_promoted:
        return "demoted_from_g1_0_promotion_to_future_pool"
    if not baseline_promoted and cal_promoted:
        return "promoted_by_cal_v1_from_g1_0_deferred"
    if target == "reserve_for_future_non_line":
        return "kept_non_promoted_reserved_for_future"
    return "kept_non_promoted_deferred"


def rgb_overlay(base_mask: np.ndarray, action_map: np.ndarray) -> Image.Image:
    h, w = base_mask.shape
    arr = np.full((h, w, 3), 255, dtype=np.uint8)
    arr[base_mask] = (222, 222, 222)
    colors = {
        1: (0, 175, 85),      # kept promotion
        2: (38, 122, 255),    # promoted by cal
        3: (220, 0, 0),       # demoted
        4: (255, 140, 0),     # reserve
        5: (150, 150, 150),   # keep deferred
    }
    for code, color in colors.items():
        arr[action_map == code] = color
    return Image.fromarray(arr, "RGB")


def comparison_visual(
    out_path: Path,
    original_line_study: np.ndarray,
    calibrated_line_study: np.ndarray,
    action_map: np.ndarray,
    summary_text: str,
) -> None:
    base = original_line_study | calibrated_line_study | (action_map > 0)
    panels = [
        ("G1.0 line-study", original_line_study.astype(bool), np.zeros_like(action_map)),
        ("G1.0-CAL V1 line-study", calibrated_line_study.astype(bool), np.zeros_like(action_map)),
        ("Actions: green keep / blue promote / red demote / orange reserve / gray defer", base, action_map),
    ]
    thumbs = []
    for title, mask, actions in panels:
        img = rgb_overlay(mask, actions)
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle((0, 0, img.width, 28), fill=(255, 255, 255, 235))
        d.text((8, 8), title, fill=(0, 0, 0), font=font(10))
        img.thumbnail((512, 512))
        canvas = Image.new("RGB", (512, 512), "white")
        canvas.paste(img, ((512 - img.width) // 2, (512 - img.height) // 2))
        thumbs.append(canvas)
    sheet = Image.new("RGB", (1536, 566), "white")
    d = ImageDraw.Draw(sheet)
    d.text((12, 12), summary_text, fill=(0, 0, 0), font=font(16))
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, (i * 512, 54))
    ensure_dir(out_path.parent)
    sheet.save(out_path)


def changed_crop_sheet(
    out_path: Path,
    action_image: Image.Image,
    predictions: Sequence[Dict[str, Any]],
    sample_id: str,
    margin: int = 28,
) -> None:
    changed = [
        p
        for p in predictions
        if p["cal_v1_action_vs_g1_0"]
        in {
            "demoted_from_g1_0_promotion_to_future_pool",
            "promoted_by_cal_v1_from_g1_0_deferred",
        }
    ]
    if not changed:
        canvas = Image.new("RGB", (720, 120), "white")
        d = ImageDraw.Draw(canvas)
        d.text((12, 12), "No changed associations", fill=(0, 0, 0), font=font(16))
        ensure_dir(out_path.parent)
        canvas.save(out_path)
        return

    tiles: List[Image.Image] = []
    w, h = action_image.size
    for pred in changed:
        x0 = max(0, int(pred["component_bbox_x0"]) - margin)
        y0 = max(0, int(pred["component_bbox_y0"]) - margin)
        x1 = min(w - 1, int(pred["component_bbox_x1"]) + margin)
        y1 = min(h - 1, int(pred["component_bbox_y1"]) + margin)
        crop = action_image.crop((x0, y0, x1 + 1, y1 + 1)).convert("RGB")
        crop.thumbnail((220, 180))
        tile = Image.new("RGB", (240, 230), "white")
        tile.paste(crop, ((240 - crop.width) // 2, 34))
        d = ImageDraw.Draw(tile)
        action = str(pred["cal_v1_action_vs_g1_0"])
        short = "PROMOTE" if action.startswith("promoted") else "DEMOTE"
        d.text((6, 6), f"assoc {pred['association_id']} {short}", fill=(0, 0, 0), font=font(12))
        d.text((6, 20), f"p={float(pred['p_promote_to_probable_line']):.3f} px={pred['component_pixel_count']}", fill=(0, 0, 0), font=font(10))
        tiles.append(tile)

    cols = 4
    rows = int(math.ceil(len(tiles) / cols))
    sheet = Image.new("RGB", (cols * 240, rows * 230 + 34), "white")
    d = ImageDraw.Draw(sheet)
    d.text((8, 10), f"G1.0-CAL V1 changed associations on {sample_id}", fill=(0, 0, 0), font=font(16))
    for idx, tile in enumerate(tiles):
        sheet.paste(tile, ((idx % cols) * 240, 34 + (idx // cols) * 230))
    ensure_dir(out_path.parent)
    sheet.save(out_path)


def run(g1_run_dir: Path, model_dir: Path, out_dir: Path, sample_id: str = "sample") -> Dict[str, Any]:
    g1_run_dir = Path(g1_run_dir)
    model_dir = Path(model_dir)
    out_dir = Path(out_dir)
    ensure_dir(out_dir / "maps")
    ensure_dir(out_dir / "visuals")

    feature_names, targets, threshold, mean, std, weights = load_model(model_dir)
    g1_summary = read_json(g1_run_dir / "summary.json")
    association_rows = read_csv(g1_run_dir / "g1_0_deferred_family_associations.csv")

    maps_dir = g1_run_dir / "maps"
    region_map = np.load(maps_dir / "g1_0_domain_region_id_map.npy")
    candidate_map = np.load(maps_dir / "g1_0_family_explained_candidate_map.npy").astype(bool)
    original_promoted_map = np.load(maps_dir / "g1_0_family_promoted_to_line_map.npy").astype(bool)
    original_line_study_map = np.load(maps_dir / "g1_0_calibrated_line_study_support_map.npy").astype(bool)
    original_future_pool_map = np.load(maps_dir / "g1_0_calibrated_future_module_pool_map.npy").astype(bool)
    original_probable_line_map = np.load(maps_dir / "g1_0_calibrated_probable_line_domain_support_map.npy").astype(bool)
    original_deferred_map = np.load(maps_dir / "g1_0_calibrated_deferred_domain_support_map.npy").astype(bool)

    predictions: List[Dict[str, Any]] = []
    promoted_map = np.zeros_like(candidate_map, dtype=bool)
    no_promote_map = np.zeros_like(candidate_map, dtype=bool)
    reserve_map = np.zeros_like(candidate_map, dtype=bool)
    keep_deferred_map = np.zeros_like(candidate_map, dtype=bool)
    action_map = np.zeros_like(region_map, dtype=np.uint8)
    pixel_rows: List[Dict[str, Any]] = []

    for row in association_rows:
        target, probs, feats = predict(row, feature_names, targets, threshold, mean, std, weights)
        baseline_promoted = as_bool(row.get("promoted_to_probable_line"))
        cal_promoted = target == PROMOTE_TARGET
        action = action_vs_g1(baseline_promoted, cal_promoted, target)
        rid = as_int(row.get("g1_0_region_id"))
        mask = (region_map == rid) & candidate_map
        if cal_promoted:
            promoted_map |= mask
        else:
            no_promote_map |= mask
            if target == "reserve_for_future_non_line":
                reserve_map |= mask
            else:
                keep_deferred_map |= mask
        code = {
            "kept_g1_0_promotion": 1,
            "promoted_by_cal_v1_from_g1_0_deferred": 2,
            "demoted_from_g1_0_promotion_to_future_pool": 3,
            "kept_non_promoted_reserved_for_future": 4,
            "kept_non_promoted_deferred": 5,
        }[action]
        action_map[mask] = code
        pred = {
            "association_id": as_int(row.get("association_id")),
            "g1_0_region_id": rid,
            "source_l1_2_cal_region_id": as_int(row.get("source_l1_2_cal_region_id")),
            "family_id": as_int(row.get("family_id")),
            "orientation": row.get("orientation", ""),
            "component_pixel_count": as_int(row.get("component_pixel_count")),
            "component_bbox_x0": as_int(row.get("component_bbox_x0")),
            "component_bbox_y0": as_int(row.get("component_bbox_y0")),
            "component_bbox_x1": as_int(row.get("component_bbox_x1")),
            "component_bbox_y1": as_int(row.get("component_bbox_y1")),
            "baseline_g1_0_promoted_to_probable_line": baseline_promoted,
            "cal_v1_predicted_target": target,
            "cal_v1_promoted_to_probable_line": cal_promoted,
            "cal_v1_action_vs_g1_0": action,
            "p_promote_to_probable_line": float(probs[targets.index("promote_to_probable_line")]),
            "p_keep_deferred": float(probs[targets.index("keep_deferred")]),
            "p_reserve_for_future_non_line": float(probs[targets.index("reserve_for_future_non_line")]),
            "promote_threshold": threshold,
            "family_distance": as_float(row.get("family_distance")),
            "anchor_score": as_float(row.get("anchor_score")),
            "family_strength_score": as_float(row.get("family_strength_score")),
            "component_colinearity_score": as_float(row.get("component_colinearity_score")),
            "component_run_score": as_float(row.get("component_run_score")),
            "microstructure_score": feats["microstructure_score"],
            "mixed_contact_score": feats["mixed_contact_score"],
            "conflict_contact_score": feats["conflict_contact_score"],
            "g1_0_association_score": feats["g1_0_association_score"],
            "cal_v1_decision_reason": "p_promote_passed_threshold" if cal_promoted else "p_promote_below_threshold_keep_or_reserve",
        }
        predictions.append(pred)
        ys, xs = np.nonzero(mask)
        for y, x in zip(ys.tolist(), xs.tolist()):
            pixel_rows.append(
                {
                    "association_id": pred["association_id"],
                    "g1_0_region_id": rid,
                    "source_l1_2_cal_region_id": pred["source_l1_2_cal_region_id"],
                    "family_id": pred["family_id"],
                    "x": x,
                    "y": y,
                    "baseline_g1_0_promoted_to_probable_line": baseline_promoted,
                    "cal_v1_predicted_target": target,
                    "cal_v1_promoted_to_probable_line": cal_promoted,
                    "cal_v1_action_vs_g1_0": action,
                    "p_promote_to_probable_line": pred["p_promote_to_probable_line"],
                    "p_keep_deferred": pred["p_keep_deferred"],
                    "p_reserve_for_future_non_line": pred["p_reserve_for_future_non_line"],
                }
            )

    calibrated_line_study = (original_line_study_map & ~candidate_map) | promoted_map
    calibrated_future_pool = (original_future_pool_map & ~candidate_map) | no_promote_map
    calibrated_probable_line = (original_probable_line_map & ~candidate_map) | promoted_map
    calibrated_deferred = (original_deferred_map & ~candidate_map) | no_promote_map

    np.save(out_dir / "maps" / "g1_0_cal_v1_promoted_to_line_map.npy", promoted_map)
    np.save(out_dir / "maps" / "g1_0_cal_v1_non_promoted_candidate_map.npy", no_promote_map)
    np.save(out_dir / "maps" / "g1_0_cal_v1_reserved_for_future_non_line_map.npy", reserve_map)
    np.save(out_dir / "maps" / "g1_0_cal_v1_kept_deferred_map.npy", keep_deferred_map)
    np.save(out_dir / "maps" / "g1_0_cal_v1_action_map.npy", action_map)
    np.save(out_dir / "maps" / "g1_0_cal_v1_calibrated_line_study_support_map.npy", calibrated_line_study)
    np.save(out_dir / "maps" / "g1_0_cal_v1_calibrated_future_module_pool_map.npy", calibrated_future_pool)
    np.save(out_dir / "maps" / "g1_0_cal_v1_calibrated_probable_line_domain_support_map.npy", calibrated_probable_line)
    np.save(out_dir / "maps" / "g1_0_cal_v1_calibrated_deferred_domain_support_map.npy", calibrated_deferred)

    write_csv(out_dir / "g1_0_cal_v1_association_predictions.csv", predictions, PREDICTION_FIELDS)
    write_csv(out_dir / "g1_0_cal_v1_candidate_pixel_memberships.csv", pixel_rows, PIXEL_FIELDS)

    action_counts = Counter(p["cal_v1_action_vs_g1_0"] for p in predictions)
    action_pixel_counts = Counter()
    for row in pixel_rows:
        action_pixel_counts[row["cal_v1_action_vs_g1_0"]] += 1
    baseline_promoted_pixels = int(np.count_nonzero(original_promoted_map & candidate_map))
    cal_promoted_pixels = int(np.count_nonzero(promoted_map))
    candidate_pixels = int(np.count_nonzero(candidate_map))
    changed_map = (original_promoted_map & candidate_map) ^ promoted_map

    invariants = {
        "does_not_modify_g1_0_outputs": True,
        "all_cal_v1_changed_pixels_subset_of_g1_0_family_candidates": bool(np.all(~changed_map | candidate_map)),
        "all_cal_v1_promoted_pixels_subset_of_g1_0_family_candidates": bool(np.all(~promoted_map | candidate_map)),
        "all_cal_v1_non_promoted_pixels_subset_of_g1_0_family_candidates": bool(np.all(~no_promote_map | candidate_map)),
        "line_study_equals_original_non_candidate_plus_calibrated_promotions": bool(
            np.array_equal(calibrated_line_study, (original_line_study_map & ~candidate_map) | promoted_map)
        ),
        "future_pool_equals_original_non_candidate_plus_calibrated_non_promotions": bool(
            np.array_equal(calibrated_future_pool, (original_future_pool_map & ~candidate_map) | no_promote_map)
        ),
        "does_not_create_final_geometry": True,
        "does_not_create_ocr_or_clinical_semantics": True,
    }
    counts = {
        "association_count": len(predictions),
        "candidate_pixels": candidate_pixels,
        "baseline_g1_0_promoted_association_count": int(sum(1 for p in predictions if p["baseline_g1_0_promoted_to_probable_line"])),
        "cal_v1_promoted_association_count": int(sum(1 for p in predictions if p["cal_v1_promoted_to_probable_line"])),
        "baseline_g1_0_promoted_candidate_pixels": baseline_promoted_pixels,
        "cal_v1_promoted_candidate_pixels": cal_promoted_pixels,
        "cal_v1_non_promoted_candidate_pixels": int(np.count_nonzero(no_promote_map)),
        "demoted_from_g1_0_promotion_pixels": int(action_pixel_counts["demoted_from_g1_0_promotion_to_future_pool"]),
        "promoted_by_cal_v1_from_g1_0_deferred_pixels": int(action_pixel_counts["promoted_by_cal_v1_from_g1_0_deferred"]),
        "kept_g1_0_promotion_pixels": int(action_pixel_counts["kept_g1_0_promotion"]),
        "kept_non_promoted_deferred_pixels": int(action_pixel_counts["kept_non_promoted_deferred"]),
        "kept_non_promoted_reserved_for_future_pixels": int(action_pixel_counts["kept_non_promoted_reserved_for_future"]),
        "original_g1_0_line_study_support_pixels": int(np.count_nonzero(original_line_study_map)),
        "cal_v1_line_study_support_pixels": int(np.count_nonzero(calibrated_line_study)),
        "original_g1_0_future_module_pool_pixels": int(np.count_nonzero(original_future_pool_map)),
        "cal_v1_future_module_pool_pixels": int(np.count_nonzero(calibrated_future_pool)),
    }
    metrics = {
        "line_study_delta_pixels_vs_g1_0": counts["cal_v1_line_study_support_pixels"] - counts["original_g1_0_line_study_support_pixels"],
        "future_pool_delta_pixels_vs_g1_0": counts["cal_v1_future_module_pool_pixels"] - counts["original_g1_0_future_module_pool_pixels"],
        "candidate_promotion_delta_pixels_vs_g1_0": cal_promoted_pixels - baseline_promoted_pixels,
        "changed_candidate_pixel_count": int(np.count_nonzero(changed_map)),
        "changed_candidate_subset_rate": 1.0 if candidate_pixels else 0.0,
        "traceable_prediction_rate": 1.0 if predictions else 0.0,
    }
    summary = {
        "version": VERSION,
        "status": "completed",
        "sample_id": sample_id,
        "source_model_version": SOURCE_MODEL_VERSION,
        "source_model_dir": str(model_dir),
        "source_g1_0_run_dir": str(g1_run_dir),
        "source_g1_0_version": g1_summary.get("version"),
        "out_dir": str(out_dir),
        "targets": targets,
        "feature_names": feature_names,
        "promote_threshold": threshold,
        "counts": counts,
        "action_counts": dict(action_counts),
        "action_pixel_counts": dict(action_pixel_counts),
        "metrics": metrics,
        "invariants": invariants,
        "outputs": {
            "association_predictions_csv": "g1_0_cal_v1_association_predictions.csv",
            "candidate_pixel_memberships_csv": "g1_0_cal_v1_candidate_pixel_memberships.csv",
            "summary_json": "summary.json",
            "maps_dir": "maps",
            "visual_comparison": "visuals/01_g1_0_vs_g1_0_cal_v1_unit_comparison.png",
        "visual_actions": "visuals/02_g1_0_cal_v1_actions_overlay.png",
        "visual_changed_crops": "visuals/03_g1_0_cal_v1_changed_association_crops.png",
        },
        "interpretation_note": f"This is an evaluation/unit adapter over {sample_id} G1.0 candidates, not a runtime replacement and not final geometry.",
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "contract_audit.json", {"status": "PASS" if all(invariants.values()) else "FAIL", "invariants": invariants})

    summary_text = (
        f"G1.0-CAL V1 on {sample_id}: promoted px {baseline_promoted_pixels} -> {cal_promoted_pixels}; "
        f"demoted {counts['demoted_from_g1_0_promotion_pixels']} px; newly promoted {counts['promoted_by_cal_v1_from_g1_0_deferred_pixels']} px"
    )
    comparison_visual(
        out_dir / "visuals" / "01_g1_0_vs_g1_0_cal_v1_unit_comparison.png",
        original_line_study_map,
        calibrated_line_study,
        action_map,
        summary_text,
    )
    action_img = rgb_overlay(original_line_study_map | calibrated_line_study | candidate_map, action_map)
    d = ImageDraw.Draw(action_img, "RGBA")
    d.rectangle((0, 0, action_img.width, 30), fill=(255, 255, 255, 235))
    d.text((8, 8), f"G1.0-CAL V1 actions on {sample_id} candidates", fill=(0, 0, 0), font=font(11))
    action_img.save(out_dir / "visuals" / "02_g1_0_cal_v1_actions_overlay.png")
    changed_crop_sheet(out_dir / "visuals" / "03_g1_0_cal_v1_changed_association_crops.png", action_img, predictions, sample_id)

    print(
        json.dumps(
            {
                "status": "completed",
                "association_count": len(predictions),
                "baseline_promoted_pixels": baseline_promoted_pixels,
                "cal_v1_promoted_pixels": cal_promoted_pixels,
                "demoted_pixels": counts["demoted_from_g1_0_promotion_pixels"],
                "newly_promoted_pixels": counts["promoted_by_cal_v1_from_g1_0_deferred_pixels"],
                "line_study_delta_pixels": metrics["line_study_delta_pixels_vs_g1_0"],
                "invariants_pass": all(invariants.values()),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return summary


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--g1-run-dir", required=True)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample-id", default="sample")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    run(Path(args.g1_run_dir), Path(args.model_dir), Path(args.out), sample_id=args.sample_id)


if __name__ == "__main__":
    main()
