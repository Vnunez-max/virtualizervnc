#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply C1-CAL V1 residual hypothesis calibrator to C1.0/C1.1 outputs.

Runtime inference uses only C1 feature tables and readable model assets. It
does not use dataset truth labels and does not create final geometry.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_C1_CAL_V1_APPLY_RESIDUAL_HYPOTHESIS_CALIBRATOR"
SOURCE_MODEL_VERSION = "MODULE_C1_CAL_V1_TRAINABLE_RESIDUAL_HYPOTHESIS_CALIBRATOR"

TARGETS = [
    "promote_residual_geometry",
    "keep_context",
    "reserve_non_geometry",
]

FEATURE_NAMES = [
    "observed_pixel_count_log",
    "inferred_span_pixel_count_log",
    "validation_score",
    "overpromotion_risk",
    "upstream_axis_distance_px",
    "axis_distance_term",
    "gap_score",
    "support_density",
    "aspect_ratio_log",
    "slenderness_score",
    "blocking_score",
    "ambiguous_score",
    "collective_member_score",
    "orientation_horizontal",
    "orientation_vertical",
    "near_upstream_score",
]

PREDICTION_FIELDS = [
    "sample_id",
    "hypothesis_id",
    "baseline_c1_state",
    "predicted_target",
    "action_vs_c1",
    "p_promote_residual_geometry",
    "p_keep_context",
    "p_reserve_non_geometry",
    *FEATURE_NAMES,
]

PIXEL_FIELDS = [
    "sample_id",
    "hypothesis_id",
    "x",
    "y",
    "predicted_target",
    "action_vs_c1",
    "membership_weight",
]

ACTION_CODE = {
    "none": 0,
    "kept_promoted": 1,
    "promoted_from_context_or_rejected": 2,
    "demoted_to_context": 3,
    "reserved_for_non_geometry": 4,
    "kept_context_or_rejected": 5,
}


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
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(to_jsonable(obj), indent=2, ensure_ascii=False), encoding="utf-8")


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], fields: Sequence[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
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


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def load_model(model_dir: Path) -> Tuple[List[str], List[str], Dict[str, float], Dict[str, float], np.ndarray]:
    config = read_json(model_dir / "model_config.json")
    scaler = read_json(model_dir / "feature_scaler.json")
    targets = list(config["targets"])
    feature_names = list(config["feature_names"])
    if config.get("version") != SOURCE_MODEL_VERSION:
        raise ValueError(f"Unexpected C1-CAL model version: {config.get('version')}")
    mean = {k: float(v) for k, v in scaler["mean"].items()}
    std = {k: float(v) for k, v in scaler["std"].items()}
    rows = read_csv(model_dir / "coefficients.csv")
    by_feature = {row["feature"]: row for row in rows}
    weights = np.zeros((len(feature_names) + 1, len(targets)), dtype=np.float64)
    for i, name in enumerate(feature_names + ["bias"]):
        for j, target in enumerate(targets):
            weights[i, j] = as_float(by_feature[name][target])
    return feature_names, targets, mean, std, weights


def softmax(logits: np.ndarray) -> np.ndarray:
    z = logits - np.max(logits)
    exp = np.exp(z)
    return exp / np.sum(exp)


def bbox_features(row: Dict[str, str]) -> Tuple[int, int, int, int, int, int, int]:
    x0 = as_int(row.get("x1"))
    y0 = as_int(row.get("y1"))
    x1 = as_int(row.get("x2"))
    y1 = as_int(row.get("y2"))
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    width = max(1, x1 - x0 + 1)
    height = max(1, y1 - y0 + 1)
    return x0, y0, x1, y1, width, height, max(width, height)


def parse_collective_scores(c1_1_dir: Optional[Path]) -> Dict[int, float]:
    scores: Dict[int, float] = {}
    if c1_1_dir is None:
        return scores
    rows = read_csv(c1_1_dir / "collective_residual_hypotheses.csv")
    for row in rows:
        score = as_float(row.get("collective_validation_score"))
        for raw in str(row.get("member_hypothesis_ids", "")).replace("|", ";").replace(",", ";").split(";"):
            hid = as_int(raw, 0)
            if hid > 0:
                scores[hid] = max(scores.get(hid, 0.0), score)
    return scores


def feature_dict(row: Dict[str, str], collective_scores: Dict[int, float]) -> Dict[str, float]:
    hid = as_int(row.get("hypothesis_id"))
    x0, y0, x1, y1, width, height, major = bbox_features(row)
    minor = min(width, height)
    area = max(1, width * height)
    n = as_int(row.get("observed_support_pixel_count"))
    inferred = as_int(row.get("inferred_span_pixel_count"))
    distance = as_float(row.get("upstream_axis_distance_px"), 9.0)
    orientation = row.get("orientation", "")
    validation_score = as_float(row.get("validation_score"))
    overpromotion = as_float(row.get("overpromotion_risk"))
    density = clamp01(n / area)
    slender = clamp01((major - minor) / max(major, 1))
    ambiguous = 1.0 if row.get("validation_state") == "needs_context" else 0.0
    blocking = 1.0 if row.get("validation_state") == "rejected" else 0.0
    return {
        "observed_pixel_count_log": math.log1p(n),
        "inferred_span_pixel_count_log": math.log1p(inferred),
        "validation_score": validation_score,
        "overpromotion_risk": overpromotion,
        "upstream_axis_distance_px": distance,
        "axis_distance_term": clamp01(1.0 - distance / 8.0),
        "gap_score": clamp01(inferred / max(major, 1)),
        "support_density": density,
        "aspect_ratio_log": math.log(max(major / max(minor, 1), 1.0)),
        "slenderness_score": slender,
        "blocking_score": blocking,
        "ambiguous_score": ambiguous,
        "collective_member_score": collective_scores.get(hid, 0.0),
        "orientation_horizontal": 1.0 if orientation == "horizontal" else 0.0,
        "orientation_vertical": 1.0 if orientation == "vertical" else 0.0,
        "near_upstream_score": clamp01(1.0 - distance / 6.0),
    }


def predict(feats: Dict[str, float], feature_names: Sequence[str], targets: Sequence[str], mean: Dict[str, float], std: Dict[str, float], weights: np.ndarray) -> Tuple[str, np.ndarray]:
    x = np.array([(feats[name] - mean[name]) / max(std[name], 1e-9) for name in feature_names] + [1.0], dtype=np.float64)
    probs = softmax(x @ weights)
    return targets[int(np.argmax(probs))], probs


def action_for(baseline_state: str, target: str) -> str:
    baseline_promoted = baseline_state == "validated"
    if target == "promote_residual_geometry" and baseline_promoted:
        return "kept_promoted"
    if target == "promote_residual_geometry":
        return "promoted_from_context_or_rejected"
    if target == "keep_context" and baseline_promoted:
        return "demoted_to_context"
    if target == "reserve_non_geometry":
        return "reserved_for_non_geometry"
    return "kept_context_or_rejected"


def color_overlay(promoted: np.ndarray, keep: np.ndarray, reserve: np.ndarray) -> Image.Image:
    rgb = np.full((*promoted.shape, 3), 255, dtype=np.uint8)
    rgb[keep] = (135, 135, 135)
    rgb[reserve] = (220, 45, 45)
    rgb[promoted] = (0, 165, 90)
    return Image.fromarray(rgb, "RGB")


def run(c1_0_dir: Path, model_dir: Path, out_dir: Path, sample_id: str, c1_1_dir: Optional[Path] = None) -> Dict[str, Any]:
    out_dir = Path(out_dir)
    map_out = out_dir / "maps"
    table_out = out_dir / "tables"
    visual_out = out_dir / "visuals"
    for path in (map_out, table_out, visual_out):
        ensure_dir(path)

    feature_names, targets, mean, std, weights = load_model(Path(model_dir))
    hypotheses = read_csv(c1_0_dir / "residual_geometry_hypotheses.csv")
    memberships = read_csv(c1_0_dir / "residual_hypothesis_memberships.csv")
    candidate_source = np.load(c1_0_dir / "maps" / "proposed_hypothesis_observed_support_map.npy").astype(bool)
    shape = candidate_source.shape
    collective_scores = parse_collective_scores(c1_1_dir)

    predictions: Dict[int, Dict[str, Any]] = {}
    prediction_rows: List[Dict[str, Any]] = []
    for row in hypotheses:
        hid = as_int(row.get("hypothesis_id"))
        if hid <= 0:
            continue
        feats = feature_dict(row, collective_scores)
        target, probs = predict(feats, feature_names, targets, mean, std, weights)
        baseline = row.get("validation_state", "")
        action = action_for(baseline, target)
        predictions[hid] = {"target": target, "action": action, "probs": probs, "features": feats}
        prediction_rows.append(
            {
                "sample_id": sample_id,
                "hypothesis_id": hid,
                "baseline_c1_state": baseline,
                "predicted_target": target,
                "action_vs_c1": action,
                "p_promote_residual_geometry": float(probs[targets.index("promote_residual_geometry")]),
                "p_keep_context": float(probs[targets.index("keep_context")]),
                "p_reserve_non_geometry": float(probs[targets.index("reserve_non_geometry")]),
                **feats,
            }
        )

    candidate = np.zeros(shape, dtype=bool)
    promoted = np.zeros(shape, dtype=bool)
    keep = np.zeros(shape, dtype=bool)
    reserve = np.zeros(shape, dtype=bool)
    changed = np.zeros(shape, dtype=bool)
    action_map = np.zeros(shape, dtype=np.uint8)
    hid_map = np.zeros(shape, dtype=np.uint16)
    pixel_rows: List[Dict[str, Any]] = []
    for row in memberships:
        hid = as_int(row.get("hypothesis_id"))
        pred = predictions.get(hid)
        x = as_int(row.get("x"))
        y = as_int(row.get("y"))
        if pred is None or not (0 <= y < shape[0] and 0 <= x < shape[1]):
            continue
        target = pred["target"]
        action = pred["action"]
        candidate[y, x] = True
        hid_map[y, x] = hid
        action_map[y, x] = ACTION_CODE[action]
        if target == "promote_residual_geometry":
            promoted[y, x] = True
        elif target == "reserve_non_geometry":
            reserve[y, x] = True
        else:
            keep[y, x] = True
        if action in {"promoted_from_context_or_rejected", "demoted_to_context", "reserved_for_non_geometry"}:
            changed[y, x] = True
        pixel_rows.append(
            {
                "sample_id": sample_id,
                "hypothesis_id": hid,
                "x": x,
                "y": y,
                "predicted_target": target,
                "action_vs_c1": action,
                "membership_weight": as_float(row.get("membership_weight"), 1.0),
            }
        )

    np.save(map_out / "c1_cal_v1_candidate_map.npy", candidate.astype(np.uint8))
    np.save(map_out / "c1_cal_v1_promoted_residual_geometry_map.npy", promoted.astype(np.uint8))
    np.save(map_out / "c1_cal_v1_keep_context_map.npy", keep.astype(np.uint8))
    np.save(map_out / "c1_cal_v1_reserved_non_geometry_map.npy", reserve.astype(np.uint8))
    np.save(map_out / "c1_cal_v1_action_map.npy", action_map.astype(np.uint8))
    np.save(map_out / "c1_cal_v1_changed_decision_map.npy", changed.astype(np.uint8))
    np.save(map_out / "c1_cal_v1_hypothesis_id_map.npy", hid_map.astype(np.uint16))
    write_csv(table_out / "c1_cal_v1_predictions.csv", prediction_rows, PREDICTION_FIELDS)
    write_csv(table_out / "c1_cal_v1_pixel_memberships.csv", pixel_rows, PIXEL_FIELDS)

    overlay = color_overlay(promoted, keep, reserve)
    canvas = Image.new("RGB", (overlay.width, overlay.height + 34), "white")
    canvas.paste(overlay, (0, 34))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 9), f"C1-CAL V1 predictions - {sample_id}", fill=(0, 0, 0), font=font(13))
    canvas.save(visual_out / "01_c1_cal_v1_prediction_overlay.png")
    canvas.save(visual_out / "02_c1_cal_v1_audit_summary.png")

    class_sum = promoted.astype(np.uint8) + keep.astype(np.uint8) + reserve.astype(np.uint8)
    invariants = {
        "promoted_pixels_subset_of_c1_candidate_support": bool(np.all(~promoted | candidate)),
        "keep_context_subset_of_c1_candidate_support": bool(np.all(~keep | candidate)),
        "reserved_non_geometry_subset_of_c1_candidate_support": bool(np.all(~reserve | candidate)),
        "output_classes_mutually_exclusive": bool(np.all(class_sum <= 1)),
        "every_output_pixel_has_hypothesis_trace": bool(np.all(~candidate | (hid_map > 0))),
        "runtime_truth_labels_not_used": True,
        "does_not_create_final_geometry": True,
        "does_not_modify_c1_outputs": True,
        "does_not_modify_v3_4_2": True,
    }
    counts = {
        "candidate_pixels": int(np.count_nonzero(candidate)),
        "promoted_residual_geometry_pixels": int(np.count_nonzero(promoted)),
        "keep_context_pixels": int(np.count_nonzero(keep)),
        "reserved_non_geometry_pixels": int(np.count_nonzero(reserve)),
        "changed_decision_pixels": int(np.count_nonzero(changed)),
        "hypothesis_count": len(prediction_rows),
    }
    summary = {
        "version": VERSION,
        "source_model_version": SOURCE_MODEL_VERSION,
        "status": "completed" if all(invariants.values()) else "failed_contract",
        "sample_id": sample_id,
        "source_c1_0_dir": str(c1_0_dir),
        "source_c1_1_dir": str(c1_1_dir) if c1_1_dir else "",
        "model_dir": str(model_dir),
        "counts": counts,
        "invariants": invariants,
        "interpretation_note": "C1-CAL promotes residual geometry evidence only; it does not create final geometry.",
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "contract_audit.json", {"version": VERSION, "acceptance_pass": bool(all(invariants.values())), "invariants": invariants})
    print(json.dumps({"status": summary["status"], **counts, "invariants_pass": all(invariants.values())}, ensure_ascii=False), flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--c1-0-dir", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--sample-id", default="sample")
    parser.add_argument("--c1-1-dir", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(
        c1_0_dir=Path(args.c1_0_dir),
        model_dir=Path(args.model_dir),
        out_dir=Path(args.out),
        sample_id=args.sample_id,
        c1_1_dir=Path(args.c1_1_dir) if args.c1_1_dir else None,
    )


if __name__ == "__main__":
    main()

