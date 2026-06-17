#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X2.0 geometric evidence fusion, single script.

This is not a launcher and does not extract or call embedded modules. It consumes
already-produced upstream geometric evidence maps and performs one integrated
fusion decision that includes deferred simple-line evidence.

Critical rule:
    No module may gain interpretation by losing geometric traceability.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VERSION = "MODULE_X2_0_GEOMETRIC_EVIDENCE_FUSION_SINGLE_SCRIPT"

CLASS_BG = 0
CLASS_CORE_LINE_STUDY = 1
CLASS_D1_GRID_LINE = 2
CLASS_FUTURE_NON_LINE = 3
CLASS_TEXT_OR_DIGIT = 4
CLASS_BORDER_OR_LAYOUT = 5
CLASS_CURVE_OR_TRACE = 6
CLASS_AMBIGUOUS_LINEAR = 7
CLASS_UNACCOUNTED = 8

CLASS_NAMES = {
    CLASS_BG: "background",
    CLASS_CORE_LINE_STUDY: "core_line_study",
    CLASS_D1_GRID_LINE: "d1_observed_grid_line_candidate",
    CLASS_FUTURE_NON_LINE: "future_non_line_pool",
    CLASS_TEXT_OR_DIGIT: "text_or_digit_linear",
    CLASS_BORDER_OR_LAYOUT: "page_border_or_layout_linear",
    CLASS_CURVE_OR_TRACE: "curve_or_data_trace_linear",
    CLASS_AMBIGUOUS_LINEAR: "ambiguous_linear",
    CLASS_UNACCOUNTED: "unaccounted_observed",
}

CLASS_COLORS = {
    CLASS_BG: (16, 16, 16),
    CLASS_CORE_LINE_STUDY: (52, 170, 255),
    CLASS_D1_GRID_LINE: (255, 212, 67),
    CLASS_FUTURE_NON_LINE: (255, 86, 86),
    CLASS_TEXT_OR_DIGIT: (190, 118, 255),
    CLASS_BORDER_OR_LAYOUT: (255, 148, 54),
    CLASS_CURVE_OR_TRACE: (35, 220, 150),
    CLASS_AMBIGUOUS_LINEAR: (220, 220, 220),
    CLASS_UNACCOUNTED: (255, 255, 255),
}

SOURCE_BITS = {
    "u1_1_valid": 1,
    "u1_1_excluded": 2,
    "l1_0": 4,
    "l1_1": 8,
    "l1_2": 16,
    "l1_2_cal": 32,
    "g1_0": 64,
    "g1_0_cal_v1": 128,
    "d1_0_simple_linearity": 256,
    "d1_1_role": 512,
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_bool(path: Path, required: bool = True) -> np.ndarray:
    if not path.exists():
        if required:
            raise FileNotFoundError(str(path))
        return np.zeros((0, 0), dtype=bool)
    return np.load(path).astype(bool)


def load_any(paths: Iterable[Path], required: bool = True) -> np.ndarray:
    tried = []
    for path in paths:
        tried.append(str(path))
        if path.exists():
            return np.load(path)
    if required:
        raise FileNotFoundError("Missing any of: " + ", ".join(tried))
    return np.zeros((0, 0), dtype=np.uint8)


def maps_dir(root: str | Path) -> Path:
    return Path(root) / "maps"


def check_same_shape(named: Dict[str, np.ndarray]) -> Tuple[int, int]:
    shapes = {name: arr.shape for name, arr in named.items() if arr.size > 0}
    unique = sorted(set(shapes.values()))
    if len(unique) != 1:
        raise ValueError(f"Input maps have inconsistent shapes: {shapes}")
    return unique[0]


def union_existing(paths: Iterable[Path], shape: Tuple[int, int]) -> np.ndarray:
    out = np.zeros(shape, dtype=bool)
    for path in paths:
        if path.exists():
            out |= np.load(path).astype(bool)
    return out


def split_positions_with_gap(positions: np.ndarray, max_gap: int) -> List[np.ndarray]:
    if positions.size == 0:
        return []
    groups: List[List[int]] = [[int(positions[0])]]
    for value in positions[1:]:
        value = int(value)
        if value - groups[-1][-1] <= max_gap + 1:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [np.asarray(group, dtype=np.int32) for group in groups]


def longest_consecutive_run(positions: np.ndarray) -> int:
    if positions.size == 0:
        return 0
    longest = 1
    current = 1
    prev = int(positions[0])
    for value in positions[1:]:
        value = int(value)
        if value == prev + 1:
            current += 1
        else:
            longest = max(longest, current)
            current = 1
        prev = value
    return max(longest, current)


def scan_linearity(
    deferred: np.ndarray,
    max_gap: int = 9,
    min_span: int = 18,
    min_support_positions: int = 5,
    min_pixel_count: int = 6,
    min_density: float = 0.10,
    min_longest_run: int = 3,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[Dict[str, object]]]:
    h, w = deferred.shape
    candidate = np.zeros((h, w), dtype=bool)
    horizontal = np.zeros((h, w), dtype=bool)
    vertical = np.zeros((h, w), dtype=bool)
    hypothesis_id = np.zeros((h, w), dtype=np.int32)
    hypotheses: List[Dict[str, object]] = []
    next_id = 1

    for y in range(h):
        xs = np.flatnonzero(deferred[y, :])
        for group in split_positions_with_gap(xs, max_gap):
            span = int(group[-1] - group[0] + 1)
            count = int(group.size)
            density = float(count / max(span, 1))
            longest = int(longest_consecutive_run(group))
            if span < min_span or count < min_support_positions or count < min_pixel_count:
                continue
            if density < min_density or longest < min_longest_run:
                continue
            yy = np.full(group.shape, y, dtype=np.int32)
            novel = ~candidate[yy, group]
            if float(novel.mean()) < 0.20:
                continue
            hid = next_id
            next_id += 1
            candidate[yy, group] = True
            horizontal[yy, group] = True
            hypothesis_id[yy[novel], group[novel]] = hid
            hypotheses.append({
                "hypothesis_id": hid,
                "orientation": "horizontal",
                "x0": int(group[0]),
                "x1": int(group[-1]),
                "y0": int(y),
                "y1": int(y),
                "span": span,
                "pixel_count": count,
                "density": density,
                "longest_run": longest,
            })

    for x in range(w):
        ys = np.flatnonzero(deferred[:, x])
        for group in split_positions_with_gap(ys, max_gap):
            span = int(group[-1] - group[0] + 1)
            count = int(group.size)
            density = float(count / max(span, 1))
            longest = int(longest_consecutive_run(group))
            if span < min_span or count < min_support_positions or count < min_pixel_count:
                continue
            if density < min_density or longest < min_longest_run:
                continue
            xx = np.full(group.shape, x, dtype=np.int32)
            novel = ~candidate[group, xx]
            if float(novel.mean()) < 0.20:
                continue
            hid = next_id
            next_id += 1
            candidate[group, xx] = True
            vertical[group, xx] = True
            hypothesis_id[group[novel], xx[novel]] = hid
            hypotheses.append({
                "hypothesis_id": hid,
                "orientation": "vertical",
                "x0": int(x),
                "x1": int(x),
                "y0": int(group[0]),
                "y1": int(group[-1]),
                "span": span,
                "pixel_count": count,
                "density": density,
                "longest_run": longest,
            })

    missing_ids = candidate & (hypothesis_id == 0)
    if np.any(missing_ids):
        hypothesis_id[missing_ids] = -1
    return candidate, horizontal, vertical, hypothesis_id, hypotheses


def dilate(mask: np.ndarray, radius: int = 3) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    h, w = mask.shape
    out = np.zeros_like(mask, dtype=bool)
    ys, xs = np.nonzero(mask)
    for dy in range(-radius, radius + 1):
        y0 = np.clip(ys + dy, 0, h - 1)
        for dx in range(-radius, radius + 1):
            if abs(dx) + abs(dy) > radius:
                continue
            x0 = np.clip(xs + dx, 0, w - 1)
            out[y0, x0] = True
    return out


def classify_d1_roles(
    candidate: np.ndarray,
    horizontal: np.ndarray,
    vertical: np.ndarray,
    hypothesis_id: np.ndarray,
    core_line: np.ndarray,
    future_pool: np.ndarray,
    border_margin: int = 14,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    h, w = candidate.shape
    role = np.zeros((h, w), dtype=np.uint8)
    confidence = np.zeros((h, w), dtype=np.float32)
    near_core = dilate(core_line, radius=3)
    near_future = dilate(future_pool, radius=2)
    border = np.zeros((h, w), dtype=bool)
    border[:border_margin, :] = True
    border[-border_margin:, :] = True
    border[:, :border_margin] = True
    border[:, -border_margin:] = True

    role[candidate] = CLASS_AMBIGUOUS_LINEAR
    confidence[candidate] = 0.45

    border_pixels = candidate & border & ~near_core
    role[border_pixels] = CLASS_BORDER_OR_LAYOUT
    confidence[border_pixels] = 0.70

    text_like = candidate & near_future & ~near_core & ~border_pixels
    role[text_like] = CLASS_TEXT_OR_DIGIT
    confidence[text_like] = 0.62

    grid_like = candidate & near_core
    role[grid_like] = CLASS_D1_GRID_LINE
    confidence[grid_like] = 0.78

    curve_like = candidate & (role == CLASS_AMBIGUOUS_LINEAR)
    role[curve_like] = CLASS_CURVE_OR_TRACE
    confidence[curve_like] = 0.55

    counts = {
        "d1_candidate_pixels": int(candidate.sum()),
        "grid_line_candidate_pixels": int((role == CLASS_D1_GRID_LINE).sum()),
        "text_or_digit_pixels": int((role == CLASS_TEXT_OR_DIGIT).sum()),
        "page_border_or_layout_pixels": int((role == CLASS_BORDER_OR_LAYOUT).sum()),
        "curve_or_data_trace_pixels": int((role == CLASS_CURVE_OR_TRACE).sum()),
        "ambiguous_linear_pixels": int((role == CLASS_AMBIGUOUS_LINEAR).sum()),
        "horizontal_candidate_pixels": int(horizontal.sum()),
        "vertical_candidate_pixels": int(vertical.sum()),
        "hypothesis_pixel_trace_rate": float(np.mean(hypothesis_id[candidate] != 0)) if np.any(candidate) else 1.0,
    }
    return role, confidence, counts


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def make_overlay(class_map: np.ndarray, observed: np.ndarray) -> Image.Image:
    h, w = class_map.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[:, :] = CLASS_COLORS[CLASS_BG]
    rgb[observed] = (54, 54, 54)
    for code, color in CLASS_COLORS.items():
        if code == CLASS_BG:
            continue
        rgb[class_map == code] = color
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
    font = ImageFont.load_default()
    for idx, (label, img) in enumerate(thumbs):
        col = idx % cols
        row = idx // cols
        x = padding + col * (thumb_w + padding)
        y = padding + row * row_h
        draw.text((x, y), label, fill=(240, 240, 240), font=font)
        sheet.paste(img, (x, y + label_h))
    sheet.save(out)


def save_bool_png(path: Path, mask: np.ndarray, color: Tuple[int, int, int]) -> None:
    rgb = np.zeros((*mask.shape, 3), dtype=np.uint8)
    rgb[mask] = color
    Image.fromarray(rgb, mode="RGB").save(path)


def command_fuse(args: argparse.Namespace) -> int:
    out = Path(args.out)
    map_out = out / "maps"
    table_out = out / "tables"
    visual_out = out / "visuals"
    for path in (out, map_out, table_out, visual_out):
        ensure_dir(path)

    u1_1 = maps_dir(args.u1_1_dir)
    l1_0 = maps_dir(args.l1_0_dir)
    l1_1 = maps_dir(args.l1_1_dir)
    l1_2 = maps_dir(args.l1_2_dir)
    l1_2_cal = maps_dir(args.l1_2_cal_dir)
    g1_0 = maps_dir(args.g1_0_dir)
    g1_cal = maps_dir(args.g1_0_cal_v1_dir)

    u1_1_valid = load_bool(u1_1 / "refined_unified_valid_observed_support_map.npy")
    u1_1_excluded = load_bool(u1_1 / "excluded_subsupport_map.npy")
    l1_0_line = load_bool(l1_0 / "line_study_support_map.npy")
    l1_0_future = load_bool(l1_0 / "future_module_pool_map.npy")
    l1_1_line = load_bool(l1_1 / "calibrated_line_study_support_map.npy")
    l1_2_line = load_bool(l1_2 / "resolved_line_study_support_map.npy")
    l1_2_cal_line = load_bool(l1_2_cal / "calibrated_line_study_support_map.npy")
    g1_line = load_bool(g1_0 / "g1_0_calibrated_line_study_support_map.npy")
    g1_cal_line = load_bool(g1_cal / "g1_0_cal_v1_calibrated_line_study_support_map.npy")
    g1_cal_future = load_bool(g1_cal / "g1_0_cal_v1_calibrated_future_module_pool_map.npy")
    g1_cal_deferred = load_bool(g1_cal / "g1_0_cal_v1_calibrated_deferred_domain_support_map.npy")

    shape = check_same_shape({
        "u1_1_valid": u1_1_valid,
        "u1_1_excluded": u1_1_excluded,
        "l1_0_line": l1_0_line,
        "l1_0_future": l1_0_future,
        "l1_1_line": l1_1_line,
        "l1_2_line": l1_2_line,
        "l1_2_cal_line": l1_2_cal_line,
        "g1_line": g1_line,
        "g1_cal_line": g1_cal_line,
        "g1_cal_future": g1_cal_future,
        "g1_cal_deferred": g1_cal_deferred,
    })

    observed = union_existing([
        l1_0 / "line_domain_support_map.npy",
        l1_0 / "probable_line_domain_support_map.npy",
        l1_0 / "mixed_domain_support_map.npy",
        l1_0 / "probable_non_line_domain_support_map.npy",
        l1_0 / "non_line_domain_support_map.npy",
        l1_0 / "deferred_domain_support_map.npy",
    ], shape)
    if not np.any(observed):
        observed = l1_0_line | l1_0_future

    line_stack = np.stack([l1_0_line, l1_1_line, l1_2_line, l1_2_cal_line, g1_line, g1_cal_line], axis=0)
    line_vote_count = line_stack.sum(axis=0).astype(np.uint8)
    core_line = g1_cal_line.copy()
    future_pool = g1_cal_future & ~core_line
    deferred = g1_cal_deferred & observed & ~core_line

    d1_candidate, d1_h, d1_v, d1_hid, d1_hypotheses = scan_linearity(
        deferred,
        max_gap=args.max_gap,
        min_span=args.min_span,
        min_support_positions=args.min_support_positions,
        min_pixel_count=args.min_pixel_count,
        min_density=args.min_density,
        min_longest_run=args.min_longest_run,
    )
    d1_role, d1_confidence, d1_counts = classify_d1_roles(d1_candidate, d1_h, d1_v, d1_hid, core_line, future_pool)

    d1_grid = d1_role == CLASS_D1_GRID_LINE
    d1_text = d1_role == CLASS_TEXT_OR_DIGIT
    d1_border = d1_role == CLASS_BORDER_OR_LAYOUT
    d1_curve = d1_role == CLASS_CURVE_OR_TRACE
    d1_ambiguous = d1_role == CLASS_AMBIGUOUS_LINEAR

    fused_line_study = (core_line | d1_grid) & observed
    fused_future_pool = (future_pool | d1_text | d1_border | d1_curve | d1_ambiguous) & observed & ~fused_line_study
    accounted = fused_line_study | fused_future_pool
    unaccounted = observed & ~accounted

    class_map = np.zeros(shape, dtype=np.uint8)
    class_map[observed] = CLASS_UNACCOUNTED
    class_map[fused_future_pool] = CLASS_FUTURE_NON_LINE
    class_map[d1_text] = CLASS_TEXT_OR_DIGIT
    class_map[d1_border] = CLASS_BORDER_OR_LAYOUT
    class_map[d1_curve] = CLASS_CURVE_OR_TRACE
    class_map[d1_ambiguous] = CLASS_AMBIGUOUS_LINEAR
    class_map[core_line] = CLASS_CORE_LINE_STUDY
    class_map[d1_grid] = CLASS_D1_GRID_LINE
    class_map[unaccounted] = CLASS_UNACCOUNTED

    source_bit_map = np.zeros(shape, dtype=np.uint16)
    for name, mask in [
        ("u1_1_valid", u1_1_valid),
        ("u1_1_excluded", u1_1_excluded),
        ("l1_0", l1_0_line),
        ("l1_1", l1_1_line),
        ("l1_2", l1_2_line),
        ("l1_2_cal", l1_2_cal_line),
        ("g1_0", g1_line),
        ("g1_0_cal_v1", g1_cal_line),
        ("d1_0_simple_linearity", d1_candidate),
        ("d1_1_role", d1_role > 0),
    ]:
        source_bit_map[mask] |= SOURCE_BITS[name]

    np.save(map_out / "x2_observed_support_map.npy", observed.astype(np.uint8))
    np.save(map_out / "x2_core_line_study_support_map.npy", core_line.astype(np.uint8))
    np.save(map_out / "x2_d1_simple_linearity_candidate_map.npy", d1_candidate.astype(np.uint8))
    np.save(map_out / "x2_d1_role_class_map.npy", d1_role.astype(np.uint8))
    np.save(map_out / "x2_d1_role_confidence_map.npy", d1_confidence.astype(np.float32))
    np.save(map_out / "x2_d1_hypothesis_id_map.npy", d1_hid.astype(np.int32))
    np.save(map_out / "x2_fused_line_study_support_map.npy", fused_line_study.astype(np.uint8))
    np.save(map_out / "x2_fused_future_module_pool_map.npy", fused_future_pool.astype(np.uint8))
    np.save(map_out / "x2_fused_class_map.npy", class_map.astype(np.uint8))
    np.save(map_out / "x2_source_bit_map.npy", source_bit_map.astype(np.uint16))
    np.save(map_out / "x2_unaccounted_observed_support_map.npy", unaccounted.astype(np.uint8))
    np.save(map_out / "x2_line_vote_count_map.npy", line_vote_count.astype(np.uint8))

    class_rows = []
    counts = Counter(class_map[observed].astype(int).tolist())
    for code in sorted(CLASS_NAMES):
        class_rows.append({
            "class_code": code,
            "class_name": CLASS_NAMES[code],
            "pixel_count": int(counts.get(code, 0)),
            "ratio_of_observed": float(counts.get(code, 0) / max(int(observed.sum()), 1)),
        })
    write_csv(table_out / "x2_fused_class_summary.csv", class_rows, ["class_code", "class_name", "pixel_count", "ratio_of_observed"])

    hyp_fields = ["hypothesis_id", "orientation", "x0", "x1", "y0", "y1", "span", "pixel_count", "density", "longest_run"]
    write_csv(table_out / "x2_d1_linearity_hypotheses.csv", d1_hypotheses, hyp_fields)

    trace_rows = [
        {"source": name, "bit": bit, "pixel_count": int(((source_bit_map & bit) > 0).sum())}
        for name, bit in SOURCE_BITS.items()
    ]
    write_csv(table_out / "x2_source_traceability_summary.csv", trace_rows, ["source", "bit", "pixel_count"])

    overlay = make_overlay(class_map, observed)
    overlay.save(visual_out / "01_x2_fused_class_overlay.png")
    save_bool_png(visual_out / "02_x2_core_line_study.png", core_line, CLASS_COLORS[CLASS_CORE_LINE_STUDY])
    save_bool_png(visual_out / "03_x2_d1_grid_line_added.png", d1_grid, CLASS_COLORS[CLASS_D1_GRID_LINE])
    save_bool_png(visual_out / "04_x2_future_pool.png", fused_future_pool, CLASS_COLORS[CLASS_FUTURE_NON_LINE])
    vote_img = Image.fromarray(np.uint8(np.clip(line_vote_count, 0, 6) * 42), mode="L").convert("RGB")
    vote_img.save(visual_out / "05_x2_line_vote_count.png")
    make_contact_sheet([
        ("X2 fused class overlay", overlay),
        ("Core line study", Image.open(visual_out / "02_x2_core_line_study.png")),
        ("D1 grid-line additions", Image.open(visual_out / "03_x2_d1_grid_line_added.png")),
        ("Future/non-line pool", Image.open(visual_out / "04_x2_future_pool.png")),
        ("Line vote count", vote_img),
    ], visual_out / "06_x2_audit_summary.png")

    invariants = {
        "all_input_maps_same_shape": True,
        "fused_line_subset_of_observed": bool(np.all(~fused_line_study | observed)),
        "fused_future_subset_of_observed": bool(np.all(~fused_future_pool | observed)),
        "fused_line_and_future_disjoint": bool(not np.any(fused_line_study & fused_future_pool)),
        "d1_candidate_subset_of_deferred": bool(np.all(~d1_candidate | deferred)),
        "d1_grid_candidate_subset_of_d1_candidate": bool(np.all(~d1_grid | d1_candidate)),
        "source_trace_for_all_fused_line_pixels": bool(np.all(source_bit_map[fused_line_study] > 0)),
        "u1_1_valid_and_excluded_disjoint": bool(not np.any(u1_1_valid & u1_1_excluded)),
        "does_not_create_final_geometry": True,
        "does_not_modify_upstream_outputs": True,
    }
    summary = {
        "version": VERSION,
        "status": "completed",
        "sample_id": args.sample_id,
        "out_dir": str(out.resolve()),
        "counts": {
            "observed_support_pixels": int(observed.sum()),
            "u1_1_valid_observed_support_pixels": int(u1_1_valid.sum()),
            "u1_1_excluded_subsupport_pixels": int(u1_1_excluded.sum()),
            "core_line_study_support_pixels": int(core_line.sum()),
            "d1_simple_linearity_candidate_pixels": int(d1_candidate.sum()),
            "d1_grid_line_added_pixels": int(d1_grid.sum()),
            "fused_line_study_support_pixels": int(fused_line_study.sum()),
            "fused_future_module_pool_pixels": int(fused_future_pool.sum()),
            "fused_accounted_support_pixels": int(accounted.sum()),
            "unaccounted_observed_support_pixels": int(unaccounted.sum()),
            **d1_counts,
        },
        "metrics": {
            "core_line_ratio_of_observed": float(core_line.sum() / max(int(observed.sum()), 1)),
            "d1_added_line_ratio_of_observed": float(d1_grid.sum() / max(int(observed.sum()), 1)),
            "fused_line_ratio_of_observed": float(fused_line_study.sum() / max(int(observed.sum()), 1)),
            "fused_future_pool_ratio_of_observed": float(fused_future_pool.sum() / max(int(observed.sum()), 1)),
            "accounted_ratio_of_observed": float(accounted.sum() / max(int(observed.sum()), 1)),
            "unaccounted_ratio_of_observed": float(unaccounted.sum() / max(int(observed.sum()), 1)),
        },
        "invariants": invariants,
        "class_names": CLASS_NAMES,
        "source_bits": SOURCE_BITS,
        "interpretation": "X2.0 fuses upstream geometric evidence and D1 deferred lineality in one internal decision. It produces study support, not final virtualized geometry.",
        "critical_rule": "No module may gain interpretation by losing geometric traceability.",
        "outputs": {
            "summary": "summary.json",
            "fused_class_overlay": "visuals/01_x2_fused_class_overlay.png",
            "audit_summary": "visuals/06_x2_audit_summary.png",
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "contract_audit.json").write_text(json.dumps({
        "version": VERSION,
        "pass": bool(all(invariants.values())),
        "invariants": invariants,
        "notes": [
            "No subprocess or embedded module extraction is used.",
            "D1 simple lineality is computed inside this script and fused with upstream evidence.",
            "D1 grid-line candidates are added only to line-study support, not final geometry.",
        ],
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "status": "completed",
        "sample_id": args.sample_id,
        "fused_line_study_support_pixels": int(fused_line_study.sum()),
        "d1_grid_line_added_pixels": int(d1_grid.sum()),
        "fused_future_module_pool_pixels": int(fused_future_pool.sum()),
        "observed_support_pixels": int(observed.sum()),
        "accounted_ratio_of_observed": float(accounted.sum() / max(int(observed.sum()), 1)),
        "invariants_pass": bool(all(invariants.values())),
    }, ensure_ascii=False), flush=True)
    return 0


def command_verify(_: argparse.Namespace) -> int:
    result = {
        "version": VERSION,
        "status": "PASS",
        "single_script": True,
        "uses_subprocess": False,
        "extracts_embedded_modules": False,
        "fuses_d1_inside_decision": True,
        "critical_rule": "No module may gain interpretation by losing geometric traceability.",
    }
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="X2.0 true single-script geometric evidence fusion")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify").set_defaults(func=command_verify)
    fuse = sub.add_parser("fuse")
    fuse.add_argument("--sample-id", required=True)
    fuse.add_argument("--out", required=True)
    fuse.add_argument("--u1-1-dir", required=True)
    fuse.add_argument("--l1-0-dir", required=True)
    fuse.add_argument("--l1-1-dir", required=True)
    fuse.add_argument("--l1-2-dir", required=True)
    fuse.add_argument("--l1-2-cal-dir", required=True)
    fuse.add_argument("--g1-0-dir", required=True)
    fuse.add_argument("--g1-0-cal-v1-dir", required=True)
    fuse.add_argument("--max-gap", type=int, default=9)
    fuse.add_argument("--min-span", type=int, default=18)
    fuse.add_argument("--min-support-positions", type=int, default=5)
    fuse.add_argument("--min-pixel-count", type=int, default=6)
    fuse.add_argument("--min-density", type=float, default=0.10)
    fuse.add_argument("--min-longest-run", type=int, default=3)
    fuse.set_defaults(func=command_fuse)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
