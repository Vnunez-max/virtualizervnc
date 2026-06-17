# Contract B1 V3.4.2 — Residual Evidence Stratifier

## Identity

`MODULE_B1_V3_4_2_RESIDUAL_EVIDENCE_STRATIFIER`

This module is a new version derived from frozen V3.4.1. It does not modify V3.4.1.

## Purpose

V3.4.2 receives V3.3 output and organizes the residual mask into residual objects, as V3.4.1 did, but adds a stricter language of evidence:

```text
V3.3 residual pixels
-> residual objects
-> residual evidence classes
-> candidate geometry residual support
-> strong geometry residual support
-> diagnostic residual support
-> residual evidence audit
```

The aim is not to create new geometry, but to prevent downstream modules from confusing all organized residual pixels with reliable geometry.

## Input

- A V3.3 run directory containing:
  - `summary.json`
  - `geometry_objects.csv`
  - `maps/combined_geometry_support_count_map.npy`
  - `maps/residual_after_geometry_mask.npy`
- Optional image path for mask loading.

## Output

V3.4.2 preserves V3.4.1 outputs and adds:

- `residual_evidence_objects.csv`
- `residual_geometry_candidates.csv`
- `strong_residual_geometry_objects.csv`
- `diagnostic_residual_objects.csv`
- `residual_evidence_audit.csv`
- `residual_layer_audit.json`
- `maps/candidate_residual_geometry_support_count_map.npy`
- `maps/diagnostic_residual_support_count_map.npy`
- `maps/residual_evidence_class_map.npy`
- additional visual audit panels.

## Evidence Classes

Allowed `residual_evidence_class` values:

- `strong_residual_geometry`
- `candidate_residual_geometry`
- `thickness_or_jitter_evidence`
- `crossing_context_evidence`
- `diagnostic_text_like_residual`
- `diagnostic_noise_residual`
- `ambiguous_residual_evidence`

These are evidence classes, not final geometry classes.

## Strict Prohibitions

V3.4.2 must not:

- create `LineObjects`;
- create `AxisDescriptors`;
- create crossings;
- create families;
- declare grids, tables, panels, charts, rows, columns, coordinate systems, or clinical meaning;
- modify V3.3 outputs;
- modify mask pixels;
- invent support outside the observed residual;
- train or require training.

## Invariants

Mandatory invariants:

- all residual object support stays inside the original mask;
- all residual object support stays inside V3.3 residual pixels;
- candidate/strong/diagnostic support are subsets of organized residual support;
- strong support is a subset of candidate support;
- no support is synthetic;
- V3.3 support remains preserved;
- residual object IDs remain traceable to membership pixels.

## Semantic Rule

`organized_residual_pixels` is not the same as `geometry_residual_pixels`.

V3.4.2 must explicitly separate:

```text
organized residual
candidate geometry residual
strong geometry residual
diagnostic residual
unexplained residual
```

## Downstream Meaning

V3.4.2 may provide evidence hints for later modules, but it must not make those later decisions.

Examples:

- `line_recovery_evidence_hint`
- `axis_evidence_hint`
- `crossing_context_hint`
- `thickness_repair_hint`
- `diagnostic_only_hint`

These are hints, not permissions to create geometry inside V3.4.2.

