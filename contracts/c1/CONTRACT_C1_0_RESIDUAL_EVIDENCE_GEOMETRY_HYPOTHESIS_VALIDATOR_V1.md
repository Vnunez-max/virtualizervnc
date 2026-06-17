# CONTRACT C1.0 - RESIDUAL EVIDENCE GEOMETRY HYPOTHESIS VALIDATOR V1

Version: `MODULE_C1_0_V1_RESIDUAL_EVIDENCE_GEOMETRY_HYPOTHESIS_VALIDATOR`

Date: 2026-06-13

## 1. Purpose

C1.0 is a post-B-stage hypothesis validator.

It consumes residual evidence stratified by B1 V3.4.2 and measures whether that
evidence can support local geometric hypotheses.

It must not create final geometry.
It must not replace B1 V3.4.2.
It must not modify B1 V3.4.2 outputs.

Core principle:

```text
Residual evidence may propose a hypothesis.
Residual evidence is not final geometry.
No module may gain interpretation by losing geometric traceability.
```

C1.0 answers only:

```text
Given V3.4.2 residual evidence, can this evidence support a local geometric
hypothesis with explicit observed support, explicit inferred span, and explicit
relation to upstream geometry?
```

It does not answer:

```text
Is this a final line?
Is this an axis?
Is this a crossing?
Is this a family?
Is this a grid, table, panel, row, column, chart, coordinate system, or
semantic structure?
```

## 2. Pipeline Position

Required conceptual order:

```text
B1 V3.3 geometry extraction
-> B1 V3.4.2 residual evidence stratification
-> C1.0 residual evidence geometry hypothesis validation
-> later integration module, if any
```

C1.0 occupies only this level:

```text
residual evidence
-> proposed residual geometry hypothesis
-> validated / rejected / needs_context state
```

C1.0 is intentionally named as a C-stage module to avoid confusing it with B
modules that create or measure line and axis objects.

## 3. Fundamental Ontology

### 3.1 Residual Evidence Object

A residual evidence object is an object emitted by B1 V3.4.2.

It may belong to classes such as:

```text
strong_residual_geometry
candidate_residual_geometry
thickness_or_jitter_evidence
crossing_context_evidence
diagnostic_text_like_residual
diagnostic_noise_residual
ambiguous_residual_evidence
```

C1.0 may read these objects, but must not rewrite their class, coordinates,
membership, or source maps.

### 3.2 Observed Support

Observed support is a set of pixels already present in V3.4.2 residual evidence.

Observed support must remain traceable to:

```text
source residual object id
source evidence class
source evidence layer
source membership pixels
```

Observed support is the only support that may count as measured evidence.

### 3.3 Inferred Span

An inferred span is a proposed interpolation, continuation, or gap span derived
from geometric reasoning.

An inferred span:

- is not observed support;
- must not be counted as residual evidence;
- must be stored separately from observed support;
- must be marked as inferred;
- must preserve the reason for inference.

### 3.4 Residual Geometry Hypothesis

A residual geometry hypothesis is a local, traceable proposal derived from
observed residual evidence.

It is not:

- a LineObject;
- an AxisDescriptor;
- a crossing;
- a family;
- a semantic object;
- final geometry.

Every hypothesis must have:

```text
hypothesis_id
hypothesis_type
validation_state
source_residual_object_ids
source_evidence_classes
source_evidence_layers
observed_support_pixel_count
inferred_span_pixel_count
orientation
axis_px
x1
y1
x2
y2
nearest_upstream_geometry_object_ids
relation_to_upstream_geometry
confidence
overpromotion_risk
underpromotion_risk
validation_reason
rejection_reason
```

## 4. Allowed Hypothesis Types

C1.0 may emit only these hypothesis types:

```text
residual_line_extension_hypothesis
residual_gap_repair_hypothesis
residual_thickness_repair_hypothesis
residual_alignment_context_hypothesis
```

These names are mandatory: each includes `hypothesis` to prevent accidental
promotion to final geometry.

## 5. Allowed Validation States

Each hypothesis must be assigned exactly one validation state:

```text
proposed
validated
rejected
needs_context
```

Definitions:

`proposed`
: The hypothesis was generated from residual evidence but has not passed enough
validation checks.

`validated`
: The hypothesis passed local geometric validation. It is still not final
geometry.

`rejected`
: The hypothesis failed validation or was blocked by diagnostic or ambiguous
evidence.

`needs_context`
: The evidence is plausible but insufficient for validation without later
context.

## 6. Required Inputs

C1.0 reads a B1 V3.4.2 output directory.

Required V3.4.2 files:

```text
summary.json
residual_evidence_objects.csv
residual_geometry_candidates.csv
strong_residual_geometry_objects.csv
diagnostic_residual_objects.csv
residual_geometry_memberships.csv
residual_layer_audit.json
maps/residual_object_id_map.npy
maps/residual_geometry_support_count_map.npy
maps/candidate_residual_geometry_support_count_map.npy
maps/evidence_strong_residual_geometry_support_count_map.npy
maps/diagnostic_residual_support_count_map.npy
maps/residual_evidence_class_map.npy
```

Required upstream V3.3 files, normally found through the V3.4.2 summary:

```text
summary.json
geometry_objects.csv
maps/combined_geometry_support_count_map.npy
maps/residual_after_geometry_mask.npy
```

Optional image:

```text
--image path/to/mask.png
```

The image is visual and audit context only. It must not become an independent
source of new geometry.

## 7. Required Outputs

C1.0 must write:

```text
residual_geometry_hypotheses.csv
residual_hypothesis_memberships.csv
residual_hypothesis_validation.csv
rejected_residual_evidence.csv
contract_audit.json
summary.json
```

Required maps:

```text
maps/proposed_hypothesis_observed_support_map.npy
maps/validated_hypothesis_observed_support_map.npy
maps/inferred_span_map.npy
maps/rejected_residual_support_map.npy
maps/hypothesis_id_map.npy
```

Required visuals:

```text
visuals/01_v3_4_2_residual_evidence_input.png
visuals/02_proposed_hypotheses.png
visuals/03_validated_hypotheses.png
visuals/04_rejected_and_blocking_evidence.png
visuals/05_observed_support_vs_inferred_span.png
visuals/06_visual_summary.png
```

## 8. Source Evidence Policy

### 8.1 Strong Residual Geometry

`strong_residual_geometry` may initiate a hypothesis.

It may not instantiate final geometry by itself.

### 8.2 Candidate Residual Geometry

`candidate_residual_geometry` may support a hypothesis or provide local context.

It should not initiate a validated hypothesis unless there is independent
geometric validation against upstream geometry.

### 8.3 Thickness Or Jitter Evidence

`thickness_or_jitter_evidence` may support only:

```text
residual_thickness_repair_hypothesis
residual_alignment_context_hypothesis
```

It must remain near explicit upstream geometry.

### 8.4 Diagnostic Evidence

The following classes must not be used as structural observed support:

```text
diagnostic_text_like_residual
diagnostic_noise_residual
```

They may only be used as blocking, rejection, or audit context.

### 8.5 Ambiguous Evidence

`ambiguous_residual_evidence` must not be promoted to validated structural
support.

It may cause:

```text
needs_context
rejected
```

## 9. Validation Requirements

A hypothesis may become `validated` only if all mandatory checks pass:

```text
has observed support
observed support is inside V3.4.2 organized residual
validated observed support is inside candidate or strong residual geometry
diagnostic evidence is not used as structural support
orientation is horizontal or vertical
local relation to upstream geometry is explicit
distance to upstream geometry is within declared threshold
collinearity or parallelism is measured
inferred span, if present, is separated from observed support
overpromotion risk is below declared threshold
```

Default validation thresholds:

```text
max_axis_distance_to_upstream_px = 4.0
max_collinearity_error_px = 2.0
max_gap_for_inferred_span_px = 12
min_observed_support_pixels = 4
min_validation_score = 0.80
min_needs_context_score = 0.55
max_overpromotion_risk_for_validation = 0.30
```

Thresholds may be configurable, but each run must record them in `summary.json`
and `contract_audit.json`.

## 10. Scoring

C1.0 may compute a validation score, but the score is advisory unless all hard
invariants pass.

Recommended score components:

```text
validation_score =
  evidence_quality
+ collinearity_score
+ proximity_score
+ continuity_score
+ support_density_score
- diagnostic_overlap_penalty
- ambiguity_penalty
- inferred_span_penalty
- overpromotion_risk_penalty
```

No single score may override a hard traceability violation.

## 11. Invariants

Mandatory invariants:

```text
observed_support subset_of V3.4.2 organized_residual
validated_observed_support subset_of candidate_residual_geometry union strong_residual_geometry
strong_used_support subset_of evidence_strong_residual_geometry
diagnostic_support_used_as_geometry == 0
ambiguous_support_used_as_validated_geometry == 0
inferred_span intersection observed_support == empty
observed_support subset_of mask
observed_support subset_of V3.3 residual_after_geometry_mask
no synthetic observed support
V3.3 outputs unchanged
V3.4.2 outputs unchanged
```

If any invariant fails, the run must be marked:

```text
status = failed_contract
```

## 12. Prohibitions

C1.0 must not create or declare:

- final LineObjects;
- modified line coordinates;
- extended upstream lines;
- merged upstream lines;
- deleted upstream lines;
- AxisDescriptors;
- crossings;
- crossing graphs;
- axis families;
- topology graphs;
- grids;
- tables;
- panels;
- rows;
- columns;
- cells;
- charts;
- coordinate systems;
- clinical interpretation;
- final virtualization.

C1.0 must not use:

- Hough transform as final geometry;
- skeletonization as final geometry;
- global projection as geometry;
- morphology as structural interpretation;
- diagnostic residual as structural support.

## 13. Visualization Rules

Visuals must separate:

```text
upstream geometry context
V3.4.2 evidence consumed
proposed hypotheses
validated hypotheses
rejected hypotheses
diagnostic blocking evidence
observed support
inferred span
```

Recommended colors:

```text
green = validated observed support
blue = proposed or candidate observed support
orange = inferred span
red = diagnostic blocking evidence
gray = rejected evidence
black = upstream context
```

No visual may merge observed support and inferred span into a single
"recovered geometry" layer.

## 14. Summary Requirements

`summary.json` must include:

```text
version
status
source_v3_4_2_run_dir
source_v3_3_run_dir
config
counts
metrics
invariants
contract
outputs
```

Required counts:

```text
proposed_hypothesis_count
validated_hypothesis_count
rejected_hypothesis_count
needs_context_hypothesis_count
observed_support_pixels_used
validated_observed_support_pixels
inferred_span_pixels
diagnostic_pixels_used_as_support
ambiguous_pixels_used_as_validated_support
```

Required metrics:

```text
validated_ratio
rejected_ratio
needs_context_ratio
mean_validation_score
mean_overpromotion_risk
mean_underpromotion_risk
observed_to_inferred_ratio
```

## 15. Contract Verdict

C1.0 is valid only if it remains a hypothesis validator.

It becomes invalid if it converts:

```text
strong_residual_geometry -> final geometry
candidate_residual_geometry -> final geometry
inferred_span -> observed support
diagnostic residual -> structural support
```

Final rule:

```text
Every gain in interpretation must preserve, not weaken, geometric traceability.
```
