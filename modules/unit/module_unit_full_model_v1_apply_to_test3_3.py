#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assemble the full unit model application on a named test sample.

This script does not rerun or modify upstream modules. It reads the approved
U/L/G outputs plus the G1.0-CAL V1 unit adapter, then writes a single auditable
unit-level result: final line-study support, future pool, stage
contributions, and visuals.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_UNIT_FULL_MODEL_V1_APPLY"

STAGES = [
    {
        "key": "l1_0",
        "label": "L1.0",
        "map": "l1_0/maps/line_study_support_map.npy",
    },
    {
        "key": "l1_1",
        "label": "L1.1",
        "map": "l1_1/maps/calibrated_line_study_support_map.npy",
    },
    {
        "key": "l1_2",
        "label": "L1.2",
        "map": "l1_2/maps/resolved_line_study_support_map.npy",
    },
    {
        "key": "l1_2_cal",
        "label": "L1.2-CAL",
        "map": "l1_2_cal/maps/calibrated_line_study_support_map.npy",
    },
    {
        "key": "g1_0",
        "label": "G1.0",
        "map": "g1_0/maps/g1_0_calibrated_line_study_support_map.npy",
    },
    {
        "key": "g1_0_cal_v1",
        "label": "G1.0-CAL V1",
        "map": "g1_0_cal_v1/maps/g1_0_cal_v1_calibrated_line_study_support_map.npy",
    },
]

CONTRIBUTION_CODES = {
    "l1_0_kept": 1,
    "l1_1_added": 2,
    "l1_2_added": 3,
    "l1_2_cal_added": 4,
    "g1_0_added": 5,
    "g1_0_cal_v1_added": 6,
    "g1_0_cal_v1_demoted": 7,
}

CONTRIBUTION_COLORS = {
    0: (255, 255, 255),
    1: (36, 130, 80),
    2: (52, 162, 220),
    3: (230, 178, 35),
    4: (230, 110, 35),
    5: (156, 83, 210),
    6: (38, 122, 255),
    7: (220, 0, 0),
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


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(to_jsonable(obj), indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], fields: Sequence[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(to_jsonable(row))


def font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def load_bool(path: Path) -> np.ndarray:
    return np.load(path).astype(bool)


def count(mask: np.ndarray) -> int:
    return int(np.count_nonzero(mask))


def ratio(num: int, den: int) -> float:
    return float(num / den) if den else 0.0


def make_path_map(args: argparse.Namespace) -> Dict[str, Path]:
    return {
        "u1_1": Path(args.u1_1_dir),
        "l1_0": Path(args.l1_0_dir),
        "l1_1": Path(args.l1_1_dir),
        "l1_2": Path(args.l1_2_dir),
        "l1_2_cal": Path(args.l1_2_cal_dir),
        "g1_0": Path(args.g1_0_dir),
        "g1_0_cal_v1": Path(args.g1_0_cal_v1_dir),
    }


def resolve_stage_path(stage: Dict[str, str], paths: Dict[str, Path]) -> Path:
    prefix, rel = stage["map"].split("/", 1)
    return paths[prefix] / rel


def contribution_map(stage_maps: Dict[str, np.ndarray]) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    shape = next(iter(stage_maps.values())).shape
    contrib = np.zeros(shape, dtype=np.uint8)
    rows: List[Dict[str, Any]] = []
    previous = np.zeros(shape, dtype=bool)
    for stage in STAGES:
        key = stage["key"]
        current = stage_maps[key]
        added = current & ~previous
        removed = previous & ~current
        if key == "l1_0":
            contrib[added] = CONTRIBUTION_CODES["l1_0_kept"]
            rows.append(
                {
                    "stage": key,
                    "label": stage["label"],
                    "line_study_pixels": count(current),
                    "added_pixels_vs_previous": count(added),
                    "removed_pixels_vs_previous": 0,
                    "net_delta_pixels_vs_previous": count(current),
                }
            )
        else:
            code_key = f"{key}_added"
            if code_key in CONTRIBUTION_CODES:
                contrib[added] = CONTRIBUTION_CODES[code_key]
            if key == "g1_0_cal_v1":
                contrib[removed] = CONTRIBUTION_CODES["g1_0_cal_v1_demoted"]
            rows.append(
                {
                    "stage": key,
                    "label": stage["label"],
                    "line_study_pixels": count(current),
                    "added_pixels_vs_previous": count(added),
                    "removed_pixels_vs_previous": count(removed),
                    "net_delta_pixels_vs_previous": count(current) - count(previous),
                }
            )
        previous = current
    return contrib, rows


def rgb_from_mask(mask: np.ndarray, color: Tuple[int, int, int], base: np.ndarray | None = None) -> Image.Image:
    h, w = mask.shape
    arr = np.full((h, w, 3), 255, dtype=np.uint8)
    if base is not None:
        arr[base] = (225, 225, 225)
    arr[mask] = color
    return Image.fromarray(arr, "RGB")


def rgb_contribution(contrib: np.ndarray, base: np.ndarray) -> Image.Image:
    h, w = contrib.shape
    arr = np.full((h, w, 3), 255, dtype=np.uint8)
    arr[base] = (230, 230, 230)
    for code, color in CONTRIBUTION_COLORS.items():
        if code == 0:
            continue
        arr[contrib == code] = color
    return Image.fromarray(arr, "RGB")


def final_domain_overlay(line_study: np.ndarray, future_pool: np.ndarray, base: np.ndarray) -> Image.Image:
    h, w = line_study.shape
    arr = np.full((h, w, 3), 255, dtype=np.uint8)
    arr[base] = (232, 232, 232)
    arr[future_pool] = (238, 165, 70)
    arr[line_study] = (0, 158, 92)
    overlap = line_study & future_pool
    arr[overlap] = (220, 0, 0)
    return Image.fromarray(arr, "RGB")


def add_title(img: Image.Image, title: str, size: int = 12) -> Image.Image:
    out = img.copy()
    d = ImageDraw.Draw(out, "RGBA")
    d.rectangle((0, 0, out.width, 30), fill=(255, 255, 255, 235))
    d.text((8, 8), title, fill=(0, 0, 0), font=font(size))
    return out


def contact_sheet(panels: Sequence[Tuple[str, Image.Image]], out_path: Path, title: str, cols: int = 3) -> None:
    thumbs = []
    for panel_title, img in panels:
        thumb = img.copy()
        thumb.thumbnail((440, 440))
        canvas = Image.new("RGB", (440, 470), "white")
        canvas.paste(thumb, ((440 - thumb.width) // 2, 34))
        d = ImageDraw.Draw(canvas)
        d.text((8, 8), panel_title, fill=(0, 0, 0), font=font(13))
        thumbs.append(canvas)
    rows = int(np.ceil(len(thumbs) / cols))
    sheet = Image.new("RGB", (cols * 440, rows * 470 + 36), "white")
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), title, fill=(0, 0, 0), font=font(18))
    for idx, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((idx % cols) * 440, 36 + (idx // cols) * 470))
    ensure_dir(out_path.parent)
    sheet.save(out_path)


def legend_image(out_path: Path) -> None:
    labels = [
        (1, "L1.0 base line-study"),
        (2, "L1.1 added"),
        (3, "L1.2 added"),
        (4, "L1.2-CAL added"),
        (5, "G1.0 added"),
        (6, "G1.0-CAL V1 added"),
        (7, "G1.0-CAL V1 demoted"),
    ]
    img = Image.new("RGB", (520, 260), "white")
    d = ImageDraw.Draw(img)
    d.text((12, 12), "Unit contribution legend", fill=(0, 0, 0), font=font(18))
    y = 48
    for code, label in labels:
        d.rectangle((16, y, 46, y + 20), fill=CONTRIBUTION_COLORS[code])
        d.text((58, y + 3), label, fill=(0, 0, 0), font=font(14))
        y += 28
    ensure_dir(out_path.parent)
    img.save(out_path)


def run(paths: Dict[str, Path], out_dir: Path, sample_id: str = "test3.3") -> Dict[str, Any]:
    out_dir = Path(out_dir)
    ensure_dir(out_dir / "maps")
    ensure_dir(out_dir / "visuals")

    observed = (
        load_bool(paths["u1_1"] / "maps/grid_consistent_subsupport_map.npy")
        | load_bool(paths["u1_1"] / "maps/suspicious_subsupport_map.npy")
        | load_bool(paths["u1_1"] / "maps/blocking_like_subsupport_map.npy")
        | load_bool(paths["u1_1"] / "maps/deferred_subsupport_map.npy")
        | load_bool(paths["u1_1"] / "maps/ambiguous_subsupport_map.npy")
    )
    u1_1_clean = load_bool(paths["u1_1"] / "maps/refined_unified_valid_observed_support_map.npy")
    u1_1_excluded = load_bool(paths["u1_1"] / "maps/excluded_subsupport_map.npy")

    stage_maps = {stage["key"]: load_bool(resolve_stage_path(stage, paths)) for stage in STAGES}
    final_line = stage_maps["g1_0_cal_v1"]
    final_future = load_bool(paths["g1_0_cal_v1"] / "maps/g1_0_cal_v1_calibrated_future_module_pool_map.npy")
    g1_candidate = load_bool(paths["g1_0"] / "maps/g1_0_family_explained_candidate_map.npy")
    g1_cal_action = np.load(paths["g1_0_cal_v1"] / "maps/g1_0_cal_v1_action_map.npy")

    contrib, stage_rows = contribution_map(stage_maps)
    accounted = final_line | final_future

    np.save(out_dir / "maps/unit_final_line_study_support_map.npy", final_line)
    np.save(out_dir / "maps/unit_final_future_module_pool_map.npy", final_future)
    np.save(out_dir / "maps/unit_stage_contribution_map.npy", contrib)
    np.save(out_dir / "maps/unit_observed_support_map.npy", observed)
    np.save(out_dir / "maps/unit_accounted_support_map.npy", accounted)
    np.save(out_dir / "maps/unit_unaccounted_observed_support_map.npy", observed & ~accounted)

    write_csv(
        out_dir / "unit_stage_metrics.csv",
        stage_rows,
        ["stage", "label", "line_study_pixels", "added_pixels_vs_previous", "removed_pixels_vs_previous", "net_delta_pixels_vs_previous"],
    )

    counts = {
        "observed_support_pixels": count(observed),
        "u1_1_refined_valid_observed_support_pixels": count(u1_1_clean),
        "u1_1_excluded_subsupport_pixels": count(u1_1_excluded),
        "final_line_study_support_pixels": count(final_line),
        "final_future_module_pool_pixels": count(final_future),
        "final_accounted_support_pixels": count(accounted),
        "unaccounted_observed_support_pixels": count(observed & ~accounted),
        "g1_0_family_candidate_pixels": count(g1_candidate),
        "g1_0_cal_v1_added_pixels": int(next(r for r in stage_rows if r["stage"] == "g1_0_cal_v1")["added_pixels_vs_previous"]),
        "g1_0_cal_v1_demoted_pixels": int(next(r for r in stage_rows if r["stage"] == "g1_0_cal_v1")["removed_pixels_vs_previous"]),
    }
    metrics = {
        "final_line_study_ratio_of_observed": ratio(counts["final_line_study_support_pixels"], counts["observed_support_pixels"]),
        "final_future_pool_ratio_of_observed": ratio(counts["final_future_module_pool_pixels"], counts["observed_support_pixels"]),
        "accounted_ratio_of_observed": ratio(counts["final_accounted_support_pixels"], counts["observed_support_pixels"]),
        "unaccounted_ratio_of_observed": ratio(counts["unaccounted_observed_support_pixels"], counts["observed_support_pixels"]),
        "final_line_study_ratio_of_u1_1_valid": ratio(counts["final_line_study_support_pixels"], counts["u1_1_refined_valid_observed_support_pixels"]),
    }
    invariants = {
        "all_stage_maps_same_shape": len({tuple(m.shape) for m in stage_maps.values()}) == 1,
        "final_line_and_future_disjoint": bool(np.count_nonzero(final_line & final_future) == 0),
        "final_line_subset_of_observed": bool(np.all(~final_line | observed)),
        "final_future_subset_of_observed": bool(np.all(~final_future | observed)),
        "g1_0_cal_changes_subset_of_g1_0_family_candidates": bool(np.all((g1_cal_action == 0) | g1_candidate)),
        "does_not_create_final_geometry": True,
        "does_not_modify_upstream_outputs": True,
    }
    summary = {
        "version": VERSION,
        "status": "completed",
        "sample_id": sample_id,
        "out_dir": str(out_dir),
        "source_dirs": {k: str(v) for k, v in paths.items()},
        "stage_order": [{k: stage[k] for k in ("key", "label")} for stage in STAGES],
        "counts": counts,
        "metrics": metrics,
        "invariants": invariants,
        "stage_metrics_csv": "unit_stage_metrics.csv",
        "outputs": {
            "unit_final_line_study_support_map": "maps/unit_final_line_study_support_map.npy",
            "unit_final_future_module_pool_map": "maps/unit_final_future_module_pool_map.npy",
            "unit_stage_contribution_map": "maps/unit_stage_contribution_map.npy",
            "unit_stage_metrics": "unit_stage_metrics.csv",
            "summary": "summary.json",
            "contract_audit": "contract_audit.json",
            "visual_final": "visuals/01_unit_full_model_final_domains.png",
            "visual_contributions": "visuals/02_unit_full_model_contributions.png",
            "visual_stage_sheet": "visuals/03_unit_full_model_stage_sheet.png",
            "visual_legend": "visuals/04_unit_full_model_legend.png",
        },
        "interpretation_note": "Full unit result is line-study/future-pool support, not final virtualized geometry.",
        "semantic_reservation": f"G1.0-CAL V1 remains under semantic reserve on real {sample_id} because visual crops may include possible text/label promotion.",
    }
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "contract_audit.json", {"status": "PASS" if all(invariants.values()) else "FAIL", "invariants": invariants})

    final_img = add_title(
        final_domain_overlay(final_line, final_future, observed),
        f"Full unit model {sample_id}: green=line-study, orange=future pool, gray=observed background",
        11,
    )
    final_img.save(out_dir / "visuals/01_unit_full_model_final_domains.png")

    contrib_img = add_title(
        rgb_contribution(contrib, observed),
        "Full unit model contributions by stage",
        11,
    )
    contrib_img.save(out_dir / "visuals/02_unit_full_model_contributions.png")
    legend_image(out_dir / "visuals/04_unit_full_model_legend.png")

    panels = [
        ("U1.1 refined valid support", rgb_from_mask(u1_1_clean, (0, 145, 92), observed)),
        ("L1.0 line-study", rgb_from_mask(stage_maps["l1_0"], (0, 145, 92), observed)),
        ("L1.1 line-study", rgb_from_mask(stage_maps["l1_1"], (0, 145, 92), observed)),
        ("L1.2 line-study", rgb_from_mask(stage_maps["l1_2"], (0, 145, 92), observed)),
        ("L1.2-CAL line-study", rgb_from_mask(stage_maps["l1_2_cal"], (0, 145, 92), observed)),
        ("G1.0 line-study", rgb_from_mask(stage_maps["g1_0"], (0, 145, 92), observed)),
        ("G1.0-CAL V1 line-study", rgb_from_mask(final_line, (0, 145, 92), observed)),
        ("Final future pool", rgb_from_mask(final_future, (238, 165, 70), observed)),
        ("Stage contributions", rgb_contribution(contrib, observed)),
    ]
    contact_sheet(panels, out_dir / "visuals/03_unit_full_model_stage_sheet.png", f"Full unit model applied to {sample_id}")

    print(
        json.dumps(
            {
                "status": "completed",
                "final_line_study_support_pixels": counts["final_line_study_support_pixels"],
                "final_future_module_pool_pixels": counts["final_future_module_pool_pixels"],
                "observed_support_pixels": counts["observed_support_pixels"],
                "accounted_ratio_of_observed": metrics["accounted_ratio_of_observed"],
                "invariants_pass": all(invariants.values()),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return summary


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--u1-1-dir", default="outputs/u1_1_subobject_clean_grid_geometry_purity_gate_test3_3_unit/test3_3")
    ap.add_argument("--l1-0-dir", default="outputs/l1_0_observed_support_domain_stratifier_test3_3/test3_3")
    ap.add_argument("--l1-1-dir", default="outputs/l1_1_observed_support_domain_calibration_layer_test3_3/test3_3")
    ap.add_argument("--l1-2-dir", default="outputs/l1_2_deferred_domain_subsupport_resolver_test3_3/test3_3")
    ap.add_argument("--l1-2-cal-dir", default="outputs/l1_2_cal_deferred_line_like_fragment_calibrator_test3_3/test3_3")
    ap.add_argument("--g1-0-dir", default="outputs/g1_0_deferred_line_family_resolver_test3_3/test3_3")
    ap.add_argument("--g1-0-cal-v1-dir", default="outputs/g1_0_cal_v1_trainable_calibrator_test3_3_unit/test3_3")
    ap.add_argument("--out", default="outputs/unit_full_model_v1_test3_3/test3_3")
    ap.add_argument("--sample-id", default="test3.3")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    run(make_path_map(args), Path(args.out), sample_id=args.sample_id)


if __name__ == "__main__":
    main()
