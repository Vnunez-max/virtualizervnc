# CONTRACT C1.1 - COLLECTIVE RESIDUAL EVIDENCE HYPOTHESIS VALIDATOR V1

Version: `MODULE_C1_1_V1_COLLECTIVE_RESIDUAL_EVIDENCE_HYPOTHESIS_VALIDATOR`

Date: 2026-06-13

## 1. Purpose

C1.1 is a post-C1.0 collective hypothesis validator.

It consumes C1.0 residual hypotheses and B1 V3.4.2 residual evidence, then
tests whether multiple compatible residual objects can jointly support a local
collective residual hypothesis.

C1.1 must not create final geometry.
C1.1 must not replace C1.0.
C1.1 must not modify B1 V3.3, B1 V3.4.2, or C1.0 outputs.

Core principle:

```text
Several residual evidence fragments may strengthen a hypothesis.
Several residual evidence fragments still do not become final geometry.
No module may gain interpretation by losing geometric traceability.
```

C1.1 answers only:

```text
Given multiple compatible C1.0 hypotheses and their V3.4.2 source evidence,
does this group support a collective residual hypothesis with explicit observed
support, explicit inferred span, explicit blocking evidence, and explicit
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
-> C1.1 collective residual evidence hypothesis validation
-> later integration module, if any
```

C1.1 occupies only this level:

```text
individual residual hypotheses
-> compatible residual hypothesis clusters
-> collective residual hypotheses
-> validated / rejected / needs_context state
```

C1.1 remains a C-stage module because it reasons over residual evidence and
hypotheses, not over final line or axis objects.

## 3. Fundamental Ontology

### 3.1 C1.0 Residual Hypothesis

A C1.0 residual hypothesis is an individual local hypothesis derived from one
V3.4.2 residual object.

C1.1 may read C1.0 hypotheses, memberships, validation rows, and maps.

C1.1 must not:

- rewrite a C1.0 hypothesis;
- change its validation state;
- change its source residual object;
- promote it to final geometry;
- erase its rejection or needs-context status.

### 3.2 Collective Residual Hypothesis Cluster

A cluster is a group of C1.0 hypotheses that may jointly support a collective
residual hypothesis.

A cluster is not a line.
A cluster is not an axis.
A cluster is not a family.
A cluster is not final geometry.

Every cluster must preserve:

```text
cluster_id
member_hypothesis_ids
member_residual_object_ids
member_evidence_classes
member_validation_states
orientation
axis_estimate_px
axis_spread_px
longitudinal_start
longitudinal_end
observed_support_pixel_count
inferred_span_pixel_count
blocking_evidence_pixel_count
nearest_upstream_geometry_object_ids
relation_to_upstream_geometry
cluster_reason
```

### 3.3 Observed Support

Observed support is the union of real residual pixels from the member C1.0
hypotheses.

Observed support must remain traceable to:

```text
collective_hypothesis_id
C1.0 hypothesis id
V3.4.2 residual object id
V3.4.2 evidence class
V3.4.2 evidence layer
pixel membership
```

Observed support must not include inferred spans.

### 3.4 Inferred Span

An inferred span is any proposed gap, bridge, or continuation between observed
member supports.

An inferred span:

- is not observed support;
- must be stored separately;
- must be marked as inferred;
- must have a source reason;
- must not be counted as evidence pixels;
- must not be used to satisfy support-count thresholds.

### 3.5 Blocking Evidence

Blocking evidence is diagnostic, noise-like, ambiguous, or otherwise unsafe
residual evidence near or between member supports.

Blocking evidence may cause:

```text
rejected
needs_context
```

Blocking evidence must not be used as structural observed support.

## 4. Allowed Collective Hypothesis Types

C1.1 may emit only:

```text
collective_residual_line_extension_hypothesis
collective_residual_gap_repair_hypothesis
collective_residual_thickness_repair_hypothesis
collective_residual_alignment_context_hypothesis
```

Each type must include `hypothesis`.

## 5. Allowed Validation States

Each collective hypothesis must have exactly one state:

```text
validated
rejected
needs_context
```

Definitions:

`validated`
: The collective hypothesis passed all hard traceability and local geometry
checks. It is still not final geometry.

`rejected`
: The group failed validation or was blocked by diagnostic/ambiguous evidence.

`needs_context`
: The group is coherent enough to preserve, but insufficient for validation.

## 6. Required Inputs

C1.1 reads a C1.0 output directory and its source B1 V3.4.2/V3.3 directories.

Required C1.0 files:

```text
summary.json
contract_audit.json
residual_geometry_hypotheses.csv
residual_hypothesis_memberships.csv
residual_hypothesis_validation.csv
rejected_residual_evidence.csv
maps/proposed_hypothesis_observed_support_map.npy
maps/validated_hypothesis_observed_support_map.npy
maps/inferred_span_map.npy
maps/rejected_residual_support_map.npy
maps/hypothesis_id_map.npy
```

Required B1 V3.4.2 files:

```text
summary.json
residual_evidence_objects.csv
residual_geometry_memberships.csv
residual_layer_audit.json
maps/residual_object_id_map.npy
maps/residual_geometry_support_count_map.npy
maps/candidate_residual_geometry_support_count_map.npy
maps/evidence_strong_residual_geometry_support_count_map.npy
maps/diagnostic_residual_support_count_map.npy
maps/residual_evidence_class_map.npy
```

Required upstream V3.3 files:

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

The image is visual/audit context only.

## 7. Required Outputs

C1.1 must write:

```text
collective_residual_hypothesis_clusters.csv
collective_residual_hypotheses.csv
collective_hypothesis_memberships.csv
collective_hypothesis_validation.csv
collective_rejected_evidence.csv
contract_audit.json
summary.json
```

Required maps:

```text
maps/collective_observed_support_map.npy
maps/collective_validated_observed_support_map.npy
maps/collective_inferred_span_map.npy
maps/collective_blocking_evidence_map.npy
maps/collective_hypothesis_id_map.npy
maps/collective_cluster_id_map.npy
```

Required visuals:

```text
visuals/01_c1_0_input_hypotheses.png
visuals/02_collective_clusters.png
visuals/03_collective_validated_hypotheses.png
visuals/04_collective_needs_context.png
visuals/05_collective_rejected_and_blocking_evidence.png
visuals/06_observed_support_vs_inferred_span.png
visuals/07_visual_summary.png
```

## 8. Source Policy

### 8.1 Allowed Member States

C1.1 may cluster C1.0 hypotheses in states:

```text
validated
needs_context
```

Rejected C1.0 hypotheses may be used only as blocking or audit context.

### 8.2 Allowed Source Evidence Classes

Validated collective observed support may include only:

```text
strong_residual_geometry
candidate_residual_geometry
thickness_or_jitter_evidence
crossing_context_evidence
```

### 8.3 Diagnostic Evidence

The following classes must not be used as structural observed support:

```text
diagnostic_text_like_residual
diagnostic_noise_residual
```

They may only be blocking or rejection context.

### 8.4 Ambiguous Evidence

`ambiguous_residual_evidence` must not be part of validated structural support.

Ambiguous evidence near a cluster may produce:

```text
needs_context
rejected
```

## 9. Clustering Rules

C1.1 may cluster hypotheses only when all mandatory compatibility checks pass:

```text
same orientation
axis distance within threshold
member observed supports are distinct
member evidence classes are allowed
member states are validated or needs_context
longitudinal distance/gap within threshold or overlap exists
nearest upstream geometry relation is compatible
no diagnostic support inside observed support
```

Default clustering thresholds:

```text
max_axis_spread_px = 3.0
max_member_gap_px = 48
max_collective_inferred_span_px = 24
min_members_for_collective = 2
min_collective_observed_support_pixels = 8
```

Thresholds must be recorded in `summary.json` and `contract_audit.json`.

## 10. Validation Requirements

A collective hypothesis may become `validated` only if all hard checks pass:

```text
cluster has at least min_members_for_collective members
observed support is inside V3.4.2 organized residual
validated observed support is inside candidate or strong residual geometry
diagnostic support is not used as geometry
ambiguous support is not used as validated geometry
inferred span is separate from observed support
inferred span does not satisfy observed support thresholds
axis spread is within threshold
local relation to upstream geometry is explicit
blocking evidence is absent or below threshold
overpromotion risk is below threshold
```

Default validation thresholds:

```text
min_collective_validation_score = 0.78
min_collective_needs_context_score = 0.52
max_blocking_evidence_pixels_for_validation = 0
max_overpromotion_risk_for_validation = 0.30
```

## 11. Scoring

C1.1 may compute a collective validation score.

Recommended components:

```text
collective_validation_score =
  mean_member_validation_score
+ member_count_score
+ axis_consistency_score
+ upstream_relation_score
+ observed_support_score
- inferred_span_penalty
- blocking_evidence_penalty
- ambiguity_penalty
- overpromotion_risk_penalty
```

No score may override a hard invariant.

## 12. Invariants

Mandatory invariants:

```text
collective_observed_support subset_of V3.4.2 organized_residual
collective_validated_observed_support subset_of candidate_residual_geometry union strong_residual_geometry
diagnostic_support_used_as_geometry == 0
ambiguous_support_used_as_validated_geometry == 0
collective_inferred_span intersection collective_observed_support == empty
collective_inferred_span not_counted_as_observed_support
collective_observed_support subset_of mask
collective_observed_support subset_of V3.3 residual_after_geometry_mask
no synthetic observed support
C1.0 outputs unchanged
V3.4.2 outputs unchanged
V3.3 outputs unchanged
```

If any invariant fails, status must be:

```text
failed_contract
```

## 13. Prohibitions

C1.1 must not create or declare:

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

C1.1 must not use:

- inferred spans as observed support;
- diagnostic residual as structural support;
- ambiguous residual as validated structural support;
- global projection as geometry;
- morphology as structural interpretation.

## 14. Visualization Rules

Visuals must separate:

```text
C1.0 input hypotheses
collective clusters
validated collective hypotheses
needs_context collective hypotheses
rejected collective hypotheses
blocking diagnostic or ambiguous evidence
observed support
inferred span
```

Recommended colors:

```text
green = validated collective observed support
blue = C1.0 member observed support
orange = collective inferred span
red = blocking diagnostic evidence
purple = blocking ambiguous evidence
gray = rejected collective evidence
black = upstream context
```

No visual may present collective inferred span as recovered geometry.

## 15. Summary Requirements

`summary.json` must include:

```text
version
status
source_c1_0_run_dir
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
collective_cluster_count
collective_hypothesis_count
validated_collective_hypothesis_count
rejected_collective_hypothesis_count
needs_context_collective_hypothesis_count
collective_observed_support_pixels
validated_collective_observed_support_pixels
collective_inferred_span_pixels
blocking_evidence_pixels
diagnostic_pixels_used_as_support
ambiguous_pixels_used_as_validated_support
```

Required metrics:

```text
validated_collective_ratio
rejected_collective_ratio
needs_context_collective_ratio
mean_collective_validation_score
mean_axis_spread_px
mean_overpromotion_risk
observed_to_inferred_ratio
```

## 16. Contract Verdict

C1.1 is valid only if it remains a collective residual hypothesis validator.

It becomes invalid if it converts:

```text
cluster -> final line
cluster -> axis descriptor
collective inferred span -> observed support
diagnostic residual -> structural support
ambiguous residual -> validated structural support
```

Final rule:

```text
Collective interpretation is allowed only when collective traceability is stronger,
not weaker, than the individual evidence traceability.
```
