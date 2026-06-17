# CONTRACT U1.1 - SUBOBJECT CLEAN GRID GEOMETRY PURITY GATE V1

Version: `MODULE_U1_1_V1_SUBOBJECT_CLEAN_GRID_GEOMETRY_PURITY_GATE`

Date: 2026-06-14

## 1. Purpose

U1.1 is a subobject / pixel-level refinement of U1.0.

U1.0 gates V3.3 observed geometry at object level. GRID_AUDIT_V1 showed that
object-level gating is too coarse when blocking or ambiguous support is mixed
inside large V3.3 objects or multipart bands.

U1.1 answers only:

```text
Given a traceable V3.3 observed geometry object, which internal pixels or
subsegments remain clean-grid-consistent and which pixels/subsegments must be
excluded as suspicious, blocking-like, ambiguous, or deferred?
```

U1.1 must not:

- create geometry;
- repair absent gaps;
- move coordinates;
- modify V3.3, V3.4.2, C1.0, C1.1, or U1.0 outputs;
- convert inferred spans into observed support;
- use GRID_AUDIT_V1 truth as runtime input;
- hide excluded support.

Core principle:

```text
Object-level support may be mixed.
Subobject support must remain traceable.
No module may gain interpretation by losing geometric traceability.
```

## 2. Pipeline Position

Required conceptual order:

```text
B1 V3.3 geometry extraction
-> B1 V3.4.2 residual evidence stratification
-> C1.0 individual residual hypothesis validation
-> C1.1 collective residual hypothesis validation
-> U1.0 clean-grid geometry purity gate
-> U1.1 subobject clean-grid geometry purity gate
-> later C2.0 negative gap hypothesis, if any
-> later integration module, if any
```

U1.1 refines support inside existing observed geometry. It is not an extractor,
not a residual validator, and not a final virtualizer.

## 3. Fundamental Ontology

### 3.1 Source Object

A source object is a V3.3 geometry object that has already been seen by U1.0.

U1.1 may split a source object's observed support into subobject regions. It
must not split the source object itself in upstream files.

Every source object must remain traceable by:

```text
source_geometry_object_id
source_object_type
source_module
source_membership_source
source_pixel_coordinates
```

### 3.2 Subobject Region

A subobject region is a connected or profile-consistent subset of observed
pixels inside one source object.

A subobject region is not:

```text
a final line
an axis
a crossing
a family
a repaired gap
a semantic grid element
```

Each subobject region must preserve:

```text
subobject_region_id
source_geometry_object_id
region_pixel_count
region_gate_state
region_gate_reason
region_score
membership pixels
```

### 3.3 Core Support

Core support is the part of the source object that lies near the object's
estimated local axis or local support ridge.

Core support may become `grid_consistent` only if it remains traceable to
observed V3.3 support.

### 3.4 Fringe Support

Fringe support is observed support away from the local support ridge, often
caused by width, overlap, nearby marks, multipart absorption, or crossing
neighborhoods.

Fringe support may be:

```text
grid_consistent
suspicious
blocking_like
ambiguous
deferred
```

depending on local evidence.

### 3.5 Excluded Support

Excluded support is still observed support. U1.1 must preserve it in maps and
memberships. Excluded support must not be counted as unified valid observed
support.

## 4. Allowed Gate States

U1.1 may emit only:

```text
grid_consistent
suspicious
blocking_like
ambiguous
deferred
```

Definitions:

`grid_consistent`
: Pixel/subregion passes subobject clean-grid checks.

`suspicious`
: Pixel/subregion is observed and traceable but risky.

`blocking_like`
: Pixel/subregion contradicts clean-grid consistency locally.

`ambiguous`
: Pixel/subregion is insufficiently classifiable.

`deferred`
: Required context is missing.

No state means final geometry.

## 5. Required Inputs

Required V3.3 files:

```text
summary.json
geometry_objects.csv
pixel_geometry_memberships.csv
maps/combined_geometry_support_count_map.npy
maps/residual_after_geometry_mask.npy
```

If `pixel_geometry_memberships.csv` is missing, U1.1 may use U1.0 membership
rows only if they preserve source pixel coordinates.

Required V3.4.2 files:

```text
summary.json
residual_evidence_objects.csv
residual_geometry_memberships.csv
residual_layer_audit.json
maps/diagnostic_residual_support_count_map.npy
maps/residual_evidence_class_map.npy
maps/residual_object_id_map.npy
```

Required C1.0 files:

```text
summary.json
contract_audit.json
maps/validated_hypothesis_observed_support_map.npy
maps/inferred_span_map.npy
maps/rejected_residual_support_map.npy
```

Required C1.1 files:

```text
summary.json
contract_audit.json
maps/collective_validated_observed_support_map.npy
maps/collective_inferred_span_map.npy
maps/collective_blocking_evidence_map.npy
```

Required U1.0 files:

```text
summary.json
contract_audit.json
u1_0_geometry_gate_objects.csv
u1_0_geometry_gate_memberships.csv
u1_0_geometry_gate_validation.csv
maps/grid_consistent_observed_geometry_map.npy
maps/suspicious_observed_geometry_map.npy
maps/blocking_like_observed_geometry_map.npy
maps/ambiguous_observed_geometry_map.npy
maps/deferred_observed_geometry_map.npy
maps/excluded_from_unified_observed_support_map.npy
maps/u1_0_gate_state_map.npy
maps/unified_valid_observed_support_map.npy
```

Optional GRID_AUDIT_V1 audit-only files:

```text
sample_manifest.json
masks/observed_valid_geometry.npy
masks/blocking_geometry_evidence.npy
masks/ambiguous_geometry_evidence.npy
masks/missing_not_recoverable_geometry.npy
objects/damages.csv
```

GRID_AUDIT_V1 truth files may be used only for benchmark metrics. They must not
be used as runtime inference inputs.

## 6. Required Outputs

U1.1 must write:

```text
u1_1_subobject_regions.csv
u1_1_subobject_memberships.csv
u1_1_subobject_validation.csv
u1_1_excluded_subsupport.csv
u1_1_blocking_like_subsupport.csv
u1_1_ambiguous_subsupport.csv
summary.json
contract_audit.json
```

Required maps:

```text
maps/grid_consistent_subsupport_map.npy
maps/suspicious_subsupport_map.npy
maps/blocking_like_subsupport_map.npy
maps/ambiguous_subsupport_map.npy
maps/deferred_subsupport_map.npy
maps/excluded_subsupport_map.npy
maps/u1_1_subobject_region_id_map.npy
maps/u1_1_subobject_gate_state_map.npy
maps/refined_unified_valid_observed_support_map.npy
```

Required visuals:

```text
visuals/01_u1_0_input_gate_state.png
visuals/02_subobject_grid_consistent_support.png
visuals/03_subobject_excluded_support.png
visuals/04_blocking_and_ambiguous_subsupport.png
visuals/05_refined_unified_valid_observed_support.png
visuals/06_u1_1_gate_summary.png
```

## 7. Required CSV Schemas

### 7.1 `u1_1_subobject_regions.csv`

Required fields:

```text
subobject_region_id
source_geometry_object_id
source_u1_0_gate_state
orientation
axis_estimate_px
region_longitudinal_start
region_longitudinal_end
region_pixel_count
core_pixel_count
fringe_pixel_count
gate_state
subobject_score
axis_distance_median_px
axis_distance_p95_px
local_width_estimate_px
local_continuity_score
local_density_score
local_conflict_score
local_blocking_score
local_ambiguity_score
gate_reason
```

### 7.2 `u1_1_subobject_memberships.csv`

Required fields:

```text
subobject_region_id
source_geometry_object_id
x
y
source_layer
source_membership_role
source_u1_0_gate_state
u1_1_gate_state
membership_source
membership_weight
```

### 7.3 `u1_1_subobject_validation.csv`

Required fields:

```text
subobject_region_id
source_geometry_object_id
u1_1_gate_state
support_subset_of_v3_3_observed
excluded_support_not_counted_as_refined_unified
blocking_not_counted_as_clean_grid_support
ambiguous_not_counted_as_clean_grid_support
inferred_span_not_counted_as_observed_support
does_not_modify_upstream_geometry
does_not_create_geometry
validation_reason
rejection_or_deferral_reason
```

## 8. Subobject Segmentation Rules

U1.1 must segment source observed support without creating synthetic support.

Allowed segmentation primitives:

```text
connected components inside source object support
longitudinal runs along source orientation
axis-distance bands
local width/profile bands
local conflict neighborhoods
```

Forbidden segmentation primitives:

```text
ground truth labels at runtime
semantic object classes
text or digit detection
final line reconstruction
axis descriptor creation
gap repair
```

If multiple segmentation primitives disagree, U1.1 must preserve all pixels and
assign the most conservative gate state:

```text
blocking_like > ambiguous > suspicious > deferred > grid_consistent
```

## 9. Runtime Gate Logic

U1.1 must evaluate each source pixel or local subregion using traceable runtime
features only.

Required feature families:

```text
axis distance inside source object
local support width
local density
longitudinal continuity
source U1.0 gate state
diagnostic residual proximity
ambiguous residual proximity
C1.0 rejected support proximity
C1.1 blocking evidence proximity
inferred span exclusion
source object type
source membership role
```

Recommended default thresholds:

```text
max_core_axis_distance_px = 3.0
max_grid_consistent_p95_axis_distance_px = 5.0
max_local_width_for_clean_support_px = 9.0
min_local_density_score = 0.35
min_local_continuity_score = 0.40
max_conflict_score_for_grid_consistent = 0.00
max_conflict_score_for_suspicious = 0.15
min_subobject_pixels = 2
```

Hard rules:

```text
inferred span pixels cannot become observed support
diagnostic residual cannot become clean-grid support
ambiguous residual cannot become clean-grid support
U1.0 blocking_like support cannot become grid_consistent without explicit
subobject evidence and zero local conflict
```

## 10. Refined Unified Support Policy

The refined unified valid observed support after U1.1 is:

```text
U1.1 grid_consistent_subsupport
+ V3.4.2 strong residual geometry not blocked by U1.1
+ C1.0 validated observed support not blocked by U1.1
+ C1.1 validated observed support not blocked by U1.1
```

It must not include:

```text
U1.1 suspicious_subsupport
U1.1 blocking_like_subsupport
U1.1 ambiguous_subsupport
U1.1 deferred_subsupport
C1.0 inferred spans
C1.1 inferred spans
diagnostic residual
ambiguous residual
missing gap truth
GRID_AUDIT_V1 truth labels
```

U1.1 may remove pixels from the refined unified observed support map. It must
not remove them from traceability outputs.

## 11. Trainable Calibration Policy

U1.1 V1 is deterministic.

A later trainable calibrator may learn thresholds or scores only from
traceable subobject features:

```text
axis_distance_median_px
axis_distance_p95_px
local_width_estimate_px
local_density_score
local_continuity_score
local_conflict_score
source_u1_0_gate_state
source_membership_role
source_object_type
```

Forbidden trainable targets:

```text
raw mask -> subobject state
raw mask -> final geometry
raw mask -> lines/axes/crossings
untraceable embeddings as sole decision source
GRID_AUDIT_V1 truth as runtime input
```

## 12. Required Metrics

Summary metrics:

```text
grid_consistent_subsupport_pixels
suspicious_subsupport_pixels
blocking_like_subsupport_pixels
ambiguous_subsupport_pixels
deferred_subsupport_pixels
excluded_subsupport_pixels
refined_unified_valid_observed_support_pixels
subobject_region_count
mean_subobject_score
mean_axis_distance_p95_px
mean_local_width_estimate_px
mean_local_conflict_score
```

GRID_AUDIT_V1 benchmark metrics, when truth is available:

```text
observed_geometry_precision_after_u1_1
observed_geometry_recall_after_u1_1
blocking_false_observed_rate_after_u1_1
ambiguous_false_observed_rate_after_u1_1
not_recoverable_false_observed_rate_after_u1_1
clean_grid_observed_coverage_after_u1_1
wrong_exclusion_rate_after_u1_1
wrong_inclusion_rate_after_u1_1
```

## 13. Invariants

Mandatory invariants:

```text
grid_consistent_subsupport subset_of V3.3 observed support
suspicious_subsupport subset_of V3.3 observed support
blocking_like_subsupport subset_of V3.3 observed support
ambiguous_subsupport subset_of V3.3 observed support
deferred_subsupport subset_of V3.3 observed support
all U1.1 gate state maps are mutually exclusive
refined_unified_valid_observed_support excludes suspicious/blocking/ambiguous/deferred
refined_unified_valid_observed_support excludes inferred spans
refined_unified_valid_observed_support excludes diagnostic residual
refined_unified_valid_observed_support excludes ambiguous residual
no synthetic observed support
excluded support remains traceable
V3.3 outputs unchanged
V3.4.2 outputs unchanged
C1.0 outputs unchanged
C1.1 outputs unchanged
U1.0 outputs unchanged
```

If any invariant fails, status must be:

```text
failed_contract
```

## 14. Prohibitions

U1.1 must not create or declare:

- final LineObjects;
- modified coordinates;
- extended lines;
- merged lines;
- deleted lines;
- AxisDescriptors;
- crossings;
- crossing graphs;
- axis families as final geometry;
- topology graphs;
- grids;
- tables;
- panels;
- rows;
- columns;
- cells;
- coordinate systems;
- clinical interpretation;
- final virtualization.

U1.1 must not:

- use inferred spans as observed support;
- use diagnostic residual as clean-grid support;
- use ambiguous residual as validated support;
- use GRID_AUDIT_V1 ground truth as runtime inference input;
- hide excluded observed support;
- erase excluded support from audit;
- repair absent gaps.

## 15. Visualization Rules

Visuals must separate:

```text
U1.0 input gate state
U1.1 grid_consistent subsupport
U1.1 suspicious subsupport
U1.1 blocking_like subsupport
U1.1 ambiguous subsupport
U1.1 deferred subsupport
refined unified valid observed support
inferred spans as audit-only context
```

Recommended colors:

```text
green = grid_consistent
yellow = suspicious
red = blocking_like
purple = ambiguous
gray = deferred
blue = refined unified valid observed support
orange = inferred span audit-only
black = source V3.3 observed support
```

No visual may present excluded or inferred support as final geometry.

## 16. Summary Requirements

`summary.json` must include:

```text
version
status
source_v3_3_run_dir
source_v3_4_2_run_dir
source_c1_0_run_dir
source_c1_1_run_dir
source_u1_0_run_dir
config
counts
metrics
invariants
contract
outputs
```

Required contract flags:

```text
creates_final_geometry == false
creates_line_objects == false
creates_axis_descriptors == false
creates_crossings == false
modifies_v3_3_outputs == false
modifies_v3_4_2_outputs == false
modifies_c1_0_outputs == false
modifies_c1_1_outputs == false
modifies_u1_0_outputs == false
uses_grid_audit_truth_as_runtime_input == false
separates_observed_support_from_inferred_span == true
excluded_support_remains_traceable == true
```

## 17. Acceptance Criteria On GRID_AUDIT_V1

Minimum acceptance targets for U1.1 V1:

```text
blocking_false_observed_rate_after_u1_1 <= 0.10
ambiguous_false_observed_rate_after_u1_1 <= 0.20
observed_geometry_recall_after_u1_1 >= 0.965
observed_geometry_precision_after_u1_1 >= 0.985
not_recoverable_false_observed_rate_after_u1_1 == 0.00
```

Recoverable missing gap recall is not a U1.1 acceptance target. That belongs
to C2.0 negative gap reasoning.

## 18. Contract Verdict

U1.1 is valid only if it remains a subobject purity gate over traceable
observed support.

It becomes invalid if it converts:

```text
subobject gate state -> final geometry
excluded support -> nonexistent support
inferred span -> observed support
GRID_AUDIT_V1 truth -> runtime inference
pixel exclusion -> upstream deletion
```

Final rule:

```text
U1.1 may refine observed support by excluding unsafe pixels.
U1.1 may not invent support to recover coverage.
```
