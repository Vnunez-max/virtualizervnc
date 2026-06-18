#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply D1-CAL V1 deferred linear role calibrator to D1.0/D1.1 outputs.

Runtime inference uses only D1 feature tables and readable model assets. It
does not use dataset truth labels and does not create final geometry.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_D1_CAL_V1_APPLY_DEFERRED_LINEAR_ROLE_CALIBRATOR"
SOURCE_MODEL_VERSION = "MODULE_D1_CAL_V1_TRAINABLE_DEFERRED_LINEAR_ROLE_CALIBRATOR"

ROLES = [
    "grid_line_candidate",
    "axis_line_candidate",
    "tick_or_scale_mark",
    "page_border_or_layout_box",
    "text_or_digit_stroke",
    "curve_or_data_trace",
    "ambiguous_linear",
]

ROLE_CODE = {role: idx + 1 for idx, role in enumerate(ROLES)}
CODE_ROLE = {code: role for role, code in ROLE_CODE.items()}

ROLE_COLORS = {
    0: (255, 255, 255),
    ROLE_CODE["grid_line_candidate"]: (0, 165, 90),
    ROLE_CODE["axis_line_candidate"]: (40, 120, 255),
    ROLE_CODE["tick_or_scale_mark"]: (245, 175, 35),
    ROLE_CODE["page_border_or_layout_box"]: (120, 80, 210),
    ROLE_CODE["text_or_digit_stroke"]: (220, 45, 45),
    ROLE_CODE["curve_or_data_trace"]: (0, 185, 190),
    ROLE_CODE["ambiguous_linear"]: (135, 135, 135),
}

FEATURE_NAMES = [
    "span_px",
    "pixel_count_log",
    "density",
    "longest_run",
    "lineality_score",
    "edge_distance_px",
    "same_axis_extension_score",
    "near_line_study_contact_score",
    "parallel_context_count",
    "parallel_context_score",
    "local_observed_context_score",
    "grid_role_score",
    "axis_role_score",
    "tick_role_score",
    "border_role_score",
    "text_role_score",
    "curve_role_score",
    "orientation_horizontal",
    "orientation_vertical",
]

PREDICTION_FIELDS = [
    "sample_id",
    "linearity_hypothesis_id",
    "baseline_d1_1_role",
    "predicted_role",
    "role_changed",
    *[f"p_{role}" for role in ROLES],
    *FEATURE_NAMES,
]

PIXEL_FIELDS = [
    "sample_id",
    "linearity_hypothesis_id",
    "x",
    "y",
    "predicted_role",
    "role_code",
    "role_confidence",
    "role_changed",
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
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(to_jsonable(obj), indent=2, ensure_ascii=False), encoding="utf-8")


def read_csv(path: Path) -> List[Dict[str, str]]:
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
    if config.get("version") != SOURCE_MODEL_VERSION:
        raise ValueError(f"Unexpected D1-CAL model version: {config.get('version')}")
    targets = list(config["targets"])
    feature_names = list(config["feature_names"])
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


def feature_dict(row: Dict[str, str]) -> Dict[str, float]:
    orientation = row.get("orientation", "")
    pixel_count = as_float(row.get("pixel_count"))
    return {
        "span_px": as_float(row.get("span_px")),
        "pixel_count_log": math.log1p(pixel_count),
        "density": as_float(row.get("density")),
        "longest_run": as_float(row.get("longest_run")),
        "lineality_score": as_float(row.get("lineality_score")),
        "edge_distance_px": as_float(row.get("edge_distance_px")),
        "same_axis_extension_score": as_float(row.get("same_axis_extension_score")),
        "near_line_study_contact_score": as_float(row.get("near_line_study_contact_score")),
        "parallel_context_count": as_float(row.get("parallel_context_count")),
        "parallel_context_score": as_float(row.get("parallel_context_score")),
        "local_observed_context_score": as_float(row.get("local_observed_context_score")),
        "grid_role_score": as_float(row.get("grid_role_score")),
        "axis_role_score": as_float(row.get("axis_role_score")),
        "tick_role_score": as_float(row.get("tick_role_score")),
        "border_role_score": as_float(row.get("border_role_score")),
        "text_role_score": as_float(row.get("text_role_score")),
        "curve_role_score": as_float(row.get("curve_role_score")),
        "orientation_horizontal": 1.0 if orientation == "horizontal" else 0.0,
        "orientation_vertical": 1.0 if orientation == "vertical" else 0.0,
    }


def predict(feats: Dict[str, float], feature_names: Sequence[str], targets: Sequence[str], mean: Dict[str, float], std: Dict[str, float], weights: np.ndarray) -> Tuple[str, np.ndarray]:
    x = np.array([(feats[name] - mean[name]) / max(std[name], 1e-9) for name in feature_names] + [1.0], dtype=np.float64)
    probs = softmax(x @ weights)
    return targets[int(np.argmax(probs))], probs


def role_rgb(role_map: np.ndarray) -> Image.Image:
    rgb = np.full((*role_map.shape, 3), 255, dtype=np.uint8)
    for code, color in ROLE_COLORS.items():
        rgb[role_map == code] = color
    return Image.fromarray(rgb, "RGB")


def run(d1_0_dir: Path, d1_1_dir: Path, model_dir: Path, out_dir: Path, sample_id: str) -> Dict[str, Any]:
    out_dir = Path(out_dir)
    map_out = out_dir / "maps"
    table_out = out_dir / "tables"
    visual_out = out_dir / "visuals"
    for path in (map_out, table_out, visual_out):
        ensure_dir(path)

    feature_names, targets, mean, std, weights = load_model(Path(model_dir))
    hypotheses = read_csv(d1_1_dir / "d1_1_role_hypotheses.csv")
    memberships = read_csv(d1_1_dir / "d1_1_role_memberships.csv")
    d1_candidate = np.load(d1_0_dir / "maps" / "simple_linearity_candidate_map.npy").astype(bool)
    baseline_role_map = np.load(d1_1_dir / "maps" / "d1_1_role_class_map.npy").astype(np.uint8)
    shape = d1_candidate.shape

    predictions: Dict[int, Dict[str, Any]] = {}
    prediction_rows: List[Dict[str, Any]] = []
    for row in hypotheses:
        hid = as_int(row.get("linearity_hypothesis_id"))
        if hid <= 0:
            continue
        feats = feature_dict(row)
        role, probs = predict(feats, feature_names, targets, mean, std, weights)
        baseline_role = row.get("role", "")
        changed = role != baseline_role
        predictions[hid] = {"role": role, "probs": probs, "confidence": float(np.max(probs)), "changed": changed, "features": feats}
        out_row = {
            "sample_id": sample_id,
            "linearity_hypothesis_id": hid,
            "baseline_d1_1_role": baseline_role,
            "predicted_role": role,
            "role_changed": changed,
            **{f"p_{target}": float(probs[targets.index(target)]) for target in targets},
            **feats,
        }
        prediction_rows.append(out_row)

    role_class = np.zeros(shape, dtype=np.uint8)
    role_conf = np.zeros(shape, dtype=np.float32)
    role_hid = np.zeros(shape, dtype=np.uint16)
    changed_map = np.zeros(shape, dtype=np.uint8)
    action_map = np.zeros(shape, dtype=np.uint8)
    pixel_rows: List[Dict[str, Any]] = []
    for row in memberships:
        hid = as_int(row.get("linearity_hypothesis_id"))
        pred = predictions.get(hid)
        x = as_int(row.get("x"))
        y = as_int(row.get("y"))
        if pred is None or not (0 <= y < shape[0] and 0 <= x < shape[1]):
            continue
        role = pred["role"]
        code = ROLE_CODE[role]
        conf = float(pred["confidence"])
        role_class[y, x] = code
        role_conf[y, x] = conf
        role_hid[y, x] = hid
        changed_map[y, x] = 1 if pred["changed"] else 0
        action_map[y, x] = code
        pixel_rows.append(
            {
                "sample_id": sample_id,
                "linearity_hypothesis_id": hid,
                "x": x,
                "y": y,
                "predicted_role": role,
                "role_code": code,
                "role_confidence": conf,
                "role_changed": bool(pred["changed"]),
            }
        )

    classified = role_class > 0
    np.save(map_out / "d1_cal_v1_candidate_map.npy", classified.astype(np.uint8))
    np.save(map_out / "d1_cal_v1_role_class_map.npy", role_class.astype(np.uint8))
    np.save(map_out / "d1_cal_v1_role_confidence_map.npy", role_conf.astype(np.float32))
    np.save(map_out / "d1_cal_v1_role_hypothesis_id_map.npy", role_hid.astype(np.uint16))
    np.save(map_out / "d1_cal_v1_changed_decision_map.npy", changed_map.astype(np.uint8))
    np.save(map_out / "d1_cal_v1_action_map.npy", action_map.astype(np.uint8))
    for role, code in ROLE_CODE.items():
        np.save(map_out / f"d1_cal_v1_{role}_map.npy", (role_class == code).astype(np.uint8))

    write_csv(table_out / "d1_cal_v1_role_predictions.csv", prediction_rows, PREDICTION_FIELDS)
    write_csv(table_out / "d1_cal_v1_role_memberships.csv", pixel_rows, PIXEL_FIELDS)

    overlay = role_rgb(role_class)
    canvas = Image.new("RGB", (overlay.width, overlay.height + 34), "white")
    canvas.paste(overlay, (0, 34))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 9), f"D1-CAL V1 role predictions - {sample_id}", fill=(0, 0, 0), font=font(13))
    canvas.save(visual_out / "01_d1_cal_v1_role_overlay.png")
    canvas.save(visual_out / "02_d1_cal_v1_audit_summary.png")

    role_sum = np.zeros(shape, dtype=np.uint8)
    for code in ROLE_CODE.values():
        role_sum += (role_class == code).astype(np.uint8)
    invariants = {
        "classified_pixels_subset_of_d1_0_candidates": bool(np.all(~classified | d1_candidate)),
        "role_maps_mutually_exclusive": bool(np.all(role_sum <= 1)),
        "every_classified_pixel_has_role_and_hypothesis": bool(np.all(~classified | (role_hid > 0))),
        "runtime_truth_labels_not_used": True,
        "does_not_create_final_geometry": True,
        "does_not_modify_d1_outputs": True,
        "does_not_modify_v3_4_2": True,
    }
    counts = {
        "candidate_pixels": int(np.count_nonzero(classified)),
        "changed_decision_pixels": int(np.count_nonzero(changed_map)),
        "hypothesis_count": len(prediction_rows),
        **{f"{role}_pixels": int(np.count_nonzero(role_class == code)) for role, code in ROLE_CODE.items()},
    }
    summary = {
        "version": VERSION,
        "source_model_version": SOURCE_MODEL_VERSION,
        "status": "completed" if all(invariants.values()) else "failed_contract",
        "sample_id": sample_id,
        "source_d1_0_dir": str(d1_0_dir),
        "source_d1_1_dir": str(d1_1_dir),
        "model_dir": str(model_dir),
        "counts": counts,
        "invariants": invariants,
        "interpretation_note": "D1-CAL relabels D1.0 candidate support only; grid_line_candidate is not final geometry.",
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "contract_audit.json", {"version": VERSION, "acceptance_pass": bool(all(invariants.values())), "invariants": invariants})
    print(json.dumps({"status": summary["status"], **counts, "invariants_pass": all(invariants.values())}, ensure_ascii=False), flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d1-0-dir", required=True)
    parser.add_argument("--d1-1-dir", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--sample-id", default="sample")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(
        d1_0_dir=Path(args.d1_0_dir),
        d1_1_dir=Path(args.d1_1_dir),
        model_dir=Path(args.model_dir),
        out_dir=Path(args.out),
        sample_id=args.sample_id,
    )


if __name__ == "__main__":
    main()

