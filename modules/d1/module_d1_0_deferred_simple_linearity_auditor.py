#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D1.0 deferred-only simple linearity auditor.

This module reads deferred support left by the unit model and searches simple
horizontal/vertical line-like alignments. It only marks observed deferred pixels;
it does not fill gaps or create final geometry.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_D1_0_V1_DEFERRED_SIMPLE_LINEARITY_AUDITOR"

HYPOTHESIS_FIELDS = [
    "linearity_hypothesis_id",
    "sample_id",
    "orientation",
    "baseline",
    "band_min",
    "band_max",
    "longitudinal_start",
    "longitudinal_end",
    "span_px",
    "support_positions",
    "pixel_count",
    "density",
    "longest_run",
    "lineality_score",
    "novel_pixel_fraction",
    "decision",
    "reason",
]

MEMBERSHIP_FIELDS = [
    "sample_id",
    "x",
    "y",
    "linearity_hypothesis_id",
    "orientation",
    "baseline",
    "source_domain",
    "membership_weight",
]

REJECTED_FIELDS = [
    "sample_id",
    "orientation",
    "baseline",
    "band_min",
    "band_max",
    "longitudinal_start",
    "longitudinal_end",
    "span_px",
    "support_positions",
    "pixel_count",
    "density",
    "longest_run",
    "lineality_score",
    "reason",
]


@dataclass
class Config:
    version: str = VERSION
    band_radius_px: int = 1
    max_gap_px: int = 9
    min_span_px: int = 18
    min_support_positions: int = 5
    min_pixel_count: int = 6
    min_density: float = 0.10
    min_longest_run: int = 3
    min_lineality_score: float = 0.40
    max_duplicate_overlap_fraction: float = 0.65
    min_novel_pixel_fraction: float = 0.20


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
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(to_jsonable(row))


def load_bool(path: Path) -> np.ndarray:
    return np.load(path).astype(bool)


def count(mask: np.ndarray) -> int:
    return int(np.count_nonzero(mask))


def ratio(num: int, den: int) -> float:
    return float(num / den) if den else 0.0


def font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def runs_from_indices(indices: np.ndarray, max_gap: int) -> List[Tuple[int, int]]:
    if len(indices) == 0:
        return []
    groups: List[Tuple[int, int]] = []
    start = int(indices[0])
    prev = int(indices[0])
    for value in indices[1:]:
        value = int(value)
        if value - prev <= max_gap + 1:
            prev = value
            continue
        groups.append((start, prev))
        start = value
        prev = value
    groups.append((start, prev))
    return groups


def longest_true_run(vec: np.ndarray, start: int, end: int) -> int:
    longest = 0
    current = 0
    for value in vec[start : end + 1]:
        if value:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return int(longest)


def hypothesis_mask(
    shape: Tuple[int, int],
    orientation: str,
    band_min: int,
    band_max: int,
    start: int,
    end: int,
    deferred: np.ndarray,
) -> np.ndarray:
    mask = np.zeros(shape, dtype=bool)
    if orientation == "horizontal":
        mask[band_min : band_max + 1, start : end + 1] = deferred[band_min : band_max + 1, start : end + 1]
    else:
        mask[start : end + 1, band_min : band_max + 1] = deferred[start : end + 1, band_min : band_max + 1]
    return mask


def score_window(span: int, support_positions: int, pixel_count: int, density: float, longest_run: int) -> float:
    density_score = min(1.0, density / 0.35)
    run_score = min(1.0, longest_run / 14.0)
    span_score = min(1.0, span / 90.0)
    pixel_score = min(1.0, pixel_count / 64.0)
    return float(0.30 * density_score + 0.25 * run_score + 0.25 * span_score + 0.20 * pixel_score)


def reject_reason(
    cfg: Config,
    span: int,
    support_positions: int,
    pixel_count: int,
    density: float,
    longest_run: int,
    score: float,
) -> str:
    reasons: List[str] = []
    if span < cfg.min_span_px:
        reasons.append("span_below_min")
    if support_positions < cfg.min_support_positions:
        reasons.append("support_positions_below_min")
    if pixel_count < cfg.min_pixel_count:
        reasons.append("pixel_count_below_min")
    if density < cfg.min_density and longest_run < cfg.min_longest_run:
        reasons.append("density_and_run_below_min")
    if score < cfg.min_lineality_score:
        reasons.append("lineality_score_below_min")
    return "+".join(reasons) if reasons else "accepted"


def scan_orientation(
    deferred: np.ndarray,
    orientation: str,
    cfg: Config,
    sample_id: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    h, w = deferred.shape
    axis_len = h if orientation == "horizontal" else w
    raw: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for baseline in range(axis_len):
        band_min = max(0, baseline - cfg.band_radius_px)
        band_max = min(axis_len - 1, baseline + cfg.band_radius_px)
        if orientation == "horizontal":
            vec = np.any(deferred[band_min : band_max + 1, :], axis=0)
        else:
            vec = np.any(deferred[:, band_min : band_max + 1], axis=1)
        indices = np.where(vec)[0]
        if len(indices) == 0:
            continue
        for start, end in runs_from_indices(indices, cfg.max_gap_px):
            span = int(end - start + 1)
            support_positions = int(np.count_nonzero(vec[start : end + 1]))
            mask = hypothesis_mask(deferred.shape, orientation, band_min, band_max, start, end, deferred)
            pixel_count = count(mask)
            density = ratio(support_positions, span)
            longest_run = longest_true_run(vec, start, end)
            score = score_window(span, support_positions, pixel_count, density, longest_run)
            reason = reject_reason(cfg, span, support_positions, pixel_count, density, longest_run, score)
            row = {
                "sample_id": sample_id,
                "orientation": orientation,
                "baseline": baseline,
                "band_min": band_min,
                "band_max": band_max,
                "longitudinal_start": start,
                "longitudinal_end": end,
                "span_px": span,
                "support_positions": support_positions,
                "pixel_count": pixel_count,
                "density": density,
                "longest_run": longest_run,
                "lineality_score": score,
                "reason": reason,
                "_mask": mask,
            }
            if reason == "accepted":
                raw.append(row)
            else:
                rejected.append({k: v for k, v in row.items() if k != "_mask"})

    return raw, rejected


def deduplicate(raw: List[Dict[str, Any]], cfg: Config, shape: Tuple[int, int]) -> List[Dict[str, Any]]:
    kept: List[Dict[str, Any]] = []
    union_by_orientation = {
        "horizontal": np.zeros(shape, dtype=bool),
        "vertical": np.zeros(shape, dtype=bool),
    }
    for row in sorted(raw, key=lambda r: (float(r["lineality_score"]), int(r["pixel_count"]), int(r["span_px"])), reverse=True):
        mask = row["_mask"]
        orientation = str(row["orientation"])
        overlap = count(mask & union_by_orientation[orientation])
        pixels = count(mask)
        overlap_fraction = ratio(overlap, pixels)
        novel_fraction = 1.0 - overlap_fraction
        if overlap_fraction > cfg.max_duplicate_overlap_fraction and novel_fraction < cfg.min_novel_pixel_fraction:
            continue
        row["novel_pixel_fraction"] = novel_fraction
        kept.append(row)
        union_by_orientation[orientation] |= mask
    for idx, row in enumerate(kept, start=1):
        row["linearity_hypothesis_id"] = idx
        row["decision"] = "simple_linearity_candidate"
    return kept


def render_context(deferred: np.ndarray, line_study: np.ndarray, observed: np.ndarray) -> Image.Image:
    arr = np.full((deferred.shape[0], deferred.shape[1], 3), 255, dtype=np.uint8)
    arr[observed] = (232, 232, 232)
    arr[line_study] = (0, 150, 90)
    arr[deferred] = (245, 155, 50)
    return Image.fromarray(arr, "RGB")


def render_candidates(
    deferred: np.ndarray,
    line_study: np.ndarray,
    horizontal: np.ndarray,
    vertical: np.ndarray,
) -> Image.Image:
    arr = np.full((deferred.shape[0], deferred.shape[1], 3), 255, dtype=np.uint8)
    arr[line_study] = (220, 238, 225)
    arr[deferred] = (210, 210, 210)
    arr[horizontal] = (38, 122, 255)
    arr[vertical] = (0, 190, 205)
    overlap = horizontal & vertical
    arr[overlap] = (155, 70, 220)
    return Image.fromarray(arr, "RGB")


def render_corridors(corridor: np.ndarray, candidate: np.ndarray, line_study: np.ndarray) -> Image.Image:
    arr = np.full((corridor.shape[0], corridor.shape[1], 3), 255, dtype=np.uint8)
    arr[line_study] = (226, 236, 226)
    arr[corridor > 0] = (205, 225, 255)
    arr[candidate] = (20, 90, 255)
    return Image.fromarray(arr, "RGB")


def add_title(img: Image.Image, title: str) -> Image.Image:
    out = img.copy()
    d = ImageDraw.Draw(out, "RGBA")
    d.rectangle((0, 0, out.width, 30), fill=(255, 255, 255, 235))
    d.text((8, 8), title, fill=(0, 0, 0), font=font(11))
    return out


def contact_sheet(panels: Sequence[Tuple[str, Image.Image]], out_path: Path, title: str) -> None:
    thumbs: List[Image.Image] = []
    for panel_title, img in panels:
        thumb = img.copy()
        thumb.thumbnail((420, 420))
        canvas = Image.new("RGB", (420, 452), "white")
        canvas.paste(thumb, ((420 - thumb.width) // 2, 30))
        d = ImageDraw.Draw(canvas)
        d.text((8, 8), panel_title, fill=(0, 0, 0), font=font(12))
        thumbs.append(canvas)
    cols = 2
    rows = int(np.ceil(len(thumbs) / cols))
    sheet = Image.new("RGB", (cols * 420, rows * 452 + 36), "white")
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), title, fill=(0, 0, 0), font=font(17))
    for idx, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((idx % cols) * 420, 36 + (idx // cols) * 452))
    ensure_dir(out_path.parent)
    sheet.save(out_path)


def run(
    g1_cal_dir: Path,
    unit_dir: Path,
    out_dir: Path,
    sample_id: str,
    cfg: Config,
) -> Dict[str, Any]:
    out_dir = Path(out_dir)
    ensure_dir(out_dir / "maps")
    ensure_dir(out_dir / "visuals")

    deferred = load_bool(g1_cal_dir / "maps" / "g1_0_cal_v1_calibrated_deferred_domain_support_map.npy")
    line_study = load_bool(unit_dir / "maps" / "unit_final_line_study_support_map.npy")
    observed = load_bool(unit_dir / "maps" / "unit_observed_support_map.npy")

    horizontal_raw, horizontal_rejected = scan_orientation(deferred, "horizontal", cfg, sample_id)
    vertical_raw, vertical_rejected = scan_orientation(deferred, "vertical", cfg, sample_id)
    kept = deduplicate(horizontal_raw + vertical_raw, cfg, deferred.shape)

    candidate = np.zeros_like(deferred, dtype=bool)
    horizontal_candidate = np.zeros_like(deferred, dtype=bool)
    vertical_candidate = np.zeros_like(deferred, dtype=bool)
    hypothesis_id_map = np.zeros(deferred.shape, dtype=np.uint16)
    corridor = np.zeros(deferred.shape, dtype=np.uint16)
    memberships: List[Dict[str, Any]] = []
    hypotheses: List[Dict[str, Any]] = []

    for row in kept:
        hid = int(row["linearity_hypothesis_id"])
        mask = row["_mask"].astype(bool)
        candidate |= mask
        if row["orientation"] == "horizontal":
            horizontal_candidate |= mask
        else:
            vertical_candidate |= mask
        empty_slots = mask & (hypothesis_id_map == 0)
        hypothesis_id_map[empty_slots] = hid
        if row["orientation"] == "horizontal":
            corridor[int(row["band_min"]) : int(row["band_max"]) + 1, int(row["longitudinal_start"]) : int(row["longitudinal_end"]) + 1] = hid
        else:
            corridor[int(row["longitudinal_start"]) : int(row["longitudinal_end"]) + 1, int(row["band_min"]) : int(row["band_max"]) + 1] = hid
        ys, xs = np.where(mask)
        for y, x in zip(ys, xs):
            memberships.append(
                {
                    "sample_id": sample_id,
                    "x": int(x),
                    "y": int(y),
                    "linearity_hypothesis_id": hid,
                    "orientation": row["orientation"],
                    "baseline": int(row["baseline"]),
                    "source_domain": "g1_0_cal_v1_deferred",
                    "membership_weight": 1.0,
                }
            )
        hypotheses.append({k: v for k, v in row.items() if k != "_mask"})

    rejected = horizontal_rejected + vertical_rejected

    np.save(out_dir / "maps" / "input_deferred_map.npy", deferred.astype(np.uint16))
    np.save(out_dir / "maps" / "simple_linearity_candidate_map.npy", candidate.astype(np.uint16))
    np.save(out_dir / "maps" / "horizontal_linearity_candidate_map.npy", horizontal_candidate.astype(np.uint16))
    np.save(out_dir / "maps" / "vertical_linearity_candidate_map.npy", vertical_candidate.astype(np.uint16))
    np.save(out_dir / "maps" / "linearity_hypothesis_id_map.npy", hypothesis_id_map)
    np.save(out_dir / "maps" / "linearity_corridor_map.npy", corridor)

    write_csv(out_dir / "d1_0_linearity_hypotheses.csv", hypotheses, HYPOTHESIS_FIELDS)
    write_csv(out_dir / "d1_0_candidate_memberships.csv", memberships, MEMBERSHIP_FIELDS)
    write_csv(out_dir / "d1_0_rejected_windows.csv", rejected, REJECTED_FIELDS)

    candidate_pixel_set = set(zip(*np.where(candidate)))
    membership_pixel_set = {(int(r["y"]), int(r["x"])) for r in memberships}
    hypothesis_ids = {int(r["linearity_hypothesis_id"]) for r in hypotheses}
    membership_ids = {int(r["linearity_hypothesis_id"]) for r in memberships}
    candidate_with_id = candidate & (hypothesis_id_map > 0)
    invariants = {
        "candidate_subset_of_deferred": bool(np.all(~candidate | deferred)),
        "candidate_pixels_have_hypothesis_id": bool(count(candidate) == count(candidate_with_id)),
        "membership_pixels_subset_of_deferred": all(deferred[y, x] for y, x in membership_pixel_set),
        "membership_covers_candidate_pixels": candidate_pixel_set.issubset(membership_pixel_set),
        "hypothesis_ids_present_for_all_memberships": membership_ids.issubset(hypothesis_ids),
        "does_not_create_final_geometry": True,
        "does_not_modify_upstream_outputs": True,
    }
    counts = {
        "input_deferred_pixels": count(deferred),
        "simple_linearity_candidate_pixels": count(candidate),
        "horizontal_candidate_pixels": count(horizontal_candidate),
        "vertical_candidate_pixels": count(vertical_candidate),
        "candidate_overlap_pixels": count(horizontal_candidate & vertical_candidate),
        "non_candidate_deferred_pixels": count(deferred & ~candidate),
        "accepted_hypothesis_count": len(hypotheses),
        "rejected_window_count": len(rejected),
        "raw_accepted_window_count": len(horizontal_raw) + len(vertical_raw),
        "membership_row_count": len(memberships),
    }
    metrics = {
        "candidate_ratio_of_deferred": ratio(counts["simple_linearity_candidate_pixels"], counts["input_deferred_pixels"]),
        "non_candidate_deferred_ratio": ratio(counts["non_candidate_deferred_pixels"], counts["input_deferred_pixels"]),
        "candidate_traceability_rate": ratio(count(candidate_with_id), counts["simple_linearity_candidate_pixels"]),
        "membership_coverage_rate": ratio(len(candidate_pixel_set & membership_pixel_set), len(candidate_pixel_set)),
    }
    summary = {
        "version": VERSION,
        "status": "completed" if all(invariants.values()) else "failed_contract",
        "sample_id": sample_id,
        "source_g1_0_cal_v1_dir": str(g1_cal_dir),
        "source_unit_dir": str(unit_dir),
        "out_dir": str(out_dir),
        "config": asdict(cfg),
        "counts": counts,
        "metrics": metrics,
        "invariants": invariants,
        "outputs": {
            "linearity_hypotheses": "d1_0_linearity_hypotheses.csv",
            "candidate_memberships": "d1_0_candidate_memberships.csv",
            "rejected_windows": "d1_0_rejected_windows.csv",
            "input_deferred_map": "maps/input_deferred_map.npy",
            "simple_linearity_candidate_map": "maps/simple_linearity_candidate_map.npy",
            "linearity_hypothesis_id_map": "maps/linearity_hypothesis_id_map.npy",
            "visual_summary": "visuals/04_d1_0_audit_summary.png",
        },
        "interpretation_note": "D1.0 exposes simple line-like deferred evidence; it is not final geometry.",
    }
    write_json(out_dir / "summary.json", summary)
    write_json(
        out_dir / "contract_audit.json",
        {
            "version": VERSION,
            "status": "PASS" if all(invariants.values()) else "FAIL",
            "invariants": invariants,
            "contract": {
                "deferred_only": True,
                "creates_final_geometry": False,
                "uses_truth_labels": False,
                "uses_manual_coordinates": False,
            },
        },
    )

    context_img = add_title(render_context(deferred, line_study, observed), f"D1.0 input deferred context - {sample_id}")
    candidate_img = add_title(render_candidates(deferred, line_study, horizontal_candidate, vertical_candidate), "D1.0 simple lineality candidates")
    corridor_img = add_title(render_corridors(corridor, candidate, line_study), "D1.0 hypothesis corridors, observed candidates in blue")
    context_img.save(out_dir / "visuals" / "01_input_deferred_context.png")
    candidate_img.save(out_dir / "visuals" / "02_simple_linearity_candidates.png")
    corridor_img.save(out_dir / "visuals" / "03_linearity_corridors.png")
    contact_sheet(
        [
            ("input deferred context", context_img),
            ("simple candidates", candidate_img),
            ("hypothesis corridors", corridor_img),
        ],
        out_dir / "visuals" / "04_d1_0_audit_summary.png",
        f"D1.0 deferred simple linearity auditor - {sample_id}",
    )

    print(
        json.dumps(
            {
                "status": summary["status"],
                "input_deferred_pixels": counts["input_deferred_pixels"],
                "simple_linearity_candidate_pixels": counts["simple_linearity_candidate_pixels"],
                "candidate_ratio_of_deferred": metrics["candidate_ratio_of_deferred"],
                "accepted_hypothesis_count": counts["accepted_hypothesis_count"],
                "invariants_pass": all(invariants.values()),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return summary


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--g1-cal-dir", required=True)
    ap.add_argument("--unit-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample-id", default="sample")
    ap.add_argument("--band-radius", type=int, default=1)
    ap.add_argument("--max-gap", type=int, default=9)
    ap.add_argument("--min-span", type=int, default=18)
    ap.add_argument("--min-support-positions", type=int, default=5)
    ap.add_argument("--min-pixels", type=int, default=6)
    ap.add_argument("--min-density", type=float, default=0.10)
    ap.add_argument("--min-longest-run", type=int, default=3)
    ap.add_argument("--min-score", type=float, default=0.40)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    cfg = Config(
        band_radius_px=args.band_radius,
        max_gap_px=args.max_gap,
        min_span_px=args.min_span,
        min_support_positions=args.min_support_positions,
        min_pixel_count=args.min_pixels,
        min_density=args.min_density,
        min_longest_run=args.min_longest_run,
        min_lineality_score=args.min_score,
    )
    run(
        g1_cal_dir=Path(args.g1_cal_dir),
        unit_dir=Path(args.unit_dir),
        out_dir=Path(args.out),
        sample_id=args.sample_id,
        cfg=cfg,
    )


if __name__ == "__main__":
    main()
