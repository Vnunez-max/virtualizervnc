#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train C1-CAL V1 residual hypothesis calibrator from a traceable dataset.

The trained runtime assets are readable JSON/CSV files. Dataset labels are not
part of runtime inference.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np


VERSION = "MODULE_C1_CAL_V1_TRAINABLE_RESIDUAL_HYPOTHESIS_CALIBRATOR"

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


@dataclass
class TrainConfig:
    version: str = VERSION
    seed: int = 3420
    epochs: int = 2500
    learning_rate: float = 0.08
    l2: float = 0.001


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


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], fields: Sequence[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(to_jsonable(row))


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_split(path: Path) -> List[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def load_rows(dataset_root: Path, sample_ids: Sequence[str]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for sid in sample_ids:
        rows.extend(read_csv(dataset_root / "samples" / sid / "tables" / "hypothesis_features.csv"))
    return rows


def matrix(rows: Sequence[Dict[str, str]], mean: Dict[str, float] | None = None, std: Dict[str, float] | None = None) -> Tuple[np.ndarray, np.ndarray, Dict[str, float], Dict[str, float]]:
    x_raw = np.array([[as_float(row.get(name)) for name in FEATURE_NAMES] for row in rows], dtype=np.float64)
    y = np.array([TARGETS.index(row["target_label"]) for row in rows], dtype=np.int64)
    if mean is None:
        mean = {name: float(np.mean(x_raw[:, idx])) for idx, name in enumerate(FEATURE_NAMES)}
    if std is None:
        std = {name: float(np.std(x_raw[:, idx]) or 1.0) for idx, name in enumerate(FEATURE_NAMES)}
    x = np.array(
        [[(as_float(row.get(name)) - mean[name]) / max(std[name], 1e-9) for name in FEATURE_NAMES] for row in rows],
        dtype=np.float64,
    )
    x = np.concatenate([x, np.ones((x.shape[0], 1), dtype=np.float64)], axis=1)
    return x, y, mean, std


def softmax(logits: np.ndarray) -> np.ndarray:
    z = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(z)
    return exp / np.sum(exp, axis=1, keepdims=True)


def class_weights(y: np.ndarray) -> np.ndarray:
    counts = np.bincount(y, minlength=len(TARGETS)).astype(np.float64)
    total = max(float(np.sum(counts)), 1.0)
    weights = total / (len(TARGETS) * np.maximum(counts, 1.0))
    return weights


def train(x: np.ndarray, y: np.ndarray, cfg: TrainConfig) -> Tuple[np.ndarray, List[Dict[str, float]], Dict[str, float]]:
    rng = np.random.default_rng(cfg.seed)
    weights = rng.normal(0.0, 0.02, size=(x.shape[1], len(TARGETS)))
    onehot = np.eye(len(TARGETS), dtype=np.float64)[y]
    cls_weights = class_weights(y)
    row_weights = cls_weights[y]
    history: List[Dict[str, float]] = []
    checkpoints = {1, 10, 50, 100, 500, 1000, cfg.epochs}
    for epoch in range(1, cfg.epochs + 1):
        probs = softmax(x @ weights)
        err = (probs - onehot) * row_weights[:, None]
        grad = (x.T @ err) / max(len(y), 1)
        grad += cfg.l2 * weights
        weights -= cfg.learning_rate * grad
        if epoch in checkpoints:
            loss = -np.mean(row_weights * np.log(np.maximum(probs[np.arange(len(y)), y], 1e-12)))
            loss += 0.5 * cfg.l2 * float(np.sum(weights * weights))
            history.append({"epoch": epoch, "loss": float(loss)})
    weight_map = {TARGETS[idx]: float(cls_weights[idx]) for idx in range(len(TARGETS))}
    return weights, history, weight_map


def evaluate(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> Dict[str, Any]:
    if len(y) == 0:
        return {"count": 0, "accuracy": 0.0}
    probs = softmax(x @ weights)
    pred = np.argmax(probs, axis=1)
    per_class = {}
    for idx, target in enumerate(TARGETS):
        mask = y == idx
        per_class[target] = {
            "count": int(np.count_nonzero(mask)),
            "accuracy": float(np.mean(pred[mask] == y[mask])) if np.any(mask) else 0.0,
        }
    return {
        "count": int(len(y)),
        "accuracy": float(np.mean(pred == y)),
        "per_class": per_class,
    }


def coefficient_rows(weights: np.ndarray) -> List[Dict[str, Any]]:
    names = FEATURE_NAMES + ["bias"]
    rows: List[Dict[str, Any]] = []
    for idx, name in enumerate(names):
        row: Dict[str, Any] = {"feature": name}
        for target_idx, target in enumerate(TARGETS):
            row[target] = float(weights[idx, target_idx])
        rows.append(row)
    return rows


def run(dataset_root: Path, model_out: Path, cfg: TrainConfig) -> Dict[str, Any]:
    random.seed(cfg.seed)
    dataset_root = Path(dataset_root)
    model_out = Path(model_out)
    manifest = read_json(dataset_root / "dataset_manifest.json")
    train_ids = read_split(dataset_root / "splits" / "train.txt")
    validation_ids = read_split(dataset_root / "splits" / "validation.txt")
    holdout_ids = read_split(dataset_root / "splits" / "holdout.txt")

    train_rows = load_rows(dataset_root, train_ids)
    validation_rows = load_rows(dataset_root, validation_ids)
    holdout_rows = load_rows(dataset_root, holdout_ids)
    x_train, y_train, mean, std = matrix(train_rows)
    x_val, y_val, _, _ = matrix(validation_rows, mean, std)
    x_hold, y_hold, _, _ = matrix(holdout_rows, mean, std)
    weights, history, cls_weights = train(x_train, y_train, cfg)

    report = {
        "train": evaluate(x_train, y_train, weights),
        "validation": evaluate(x_val, y_val, weights),
        "holdout": evaluate(x_hold, y_hold, weights),
    }
    ensure_dir(model_out)
    write_json(
        model_out / "model_config.json",
        {
            "version": VERSION,
            "model_type": "numpy_softmax_regression",
            "targets": TARGETS,
            "feature_names": FEATURE_NAMES,
            "train_config": asdict(cfg),
            "dataset_id": manifest.get("dataset_id", ""),
            "train_info": {
                "class_counts": {target: int(np.count_nonzero(y_train == idx)) for idx, target in enumerate(TARGETS)},
                "class_weights": cls_weights,
                "history": history,
                "evaluation": report,
            },
            "truth_usage_policy": "Truth labels are used only for training, validation, holdout evaluation, and audit.",
            "runtime_prohibitions": {
                "does_not_modify_c1": True,
                "does_not_modify_v3_4_2": True,
                "does_not_create_final_geometry": True,
                "no_ocr": True,
                "no_clinical_semantics": True,
            },
        },
    )
    write_json(model_out / "feature_scaler.json", {"feature_names": FEATURE_NAMES, "mean": mean, "std": std})
    write_csv(model_out / "coefficients.csv", coefficient_rows(weights), ["feature", *TARGETS])
    result = {
        "status": "completed",
        "model_out": str(model_out),
        "holdout_accuracy": report["holdout"]["accuracy"],
        "validation_accuracy": report["validation"]["accuracy"],
        "runtime_truth_labels_allowed": False,
    }
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--model-out", required=True)
    parser.add_argument("--seed", type=int, default=3420)
    parser.add_argument("--epochs", type=int, default=2500)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--l2", type=float, default=0.001)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(
        Path(args.dataset_root),
        Path(args.model_out),
        TrainConfig(seed=args.seed, epochs=args.epochs, learning_rate=args.learning_rate, l2=args.l2),
    )


if __name__ == "__main__":
    main()

