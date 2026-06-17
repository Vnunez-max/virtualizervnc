# CONTRACT U1.1-CAL - GEOMETRIC HYSTERESIS CALIBRATOR V1

Version: `MODULE_U1_1_CAL_V1_GEOMETRIC_HYSTERESIS_CALIBRATOR`

Date: 2026-06-14

## 1. Purpose

U1.1-CAL is an offline calibration module for U1.1.

U1.1-CAL exists because direct visual audit of `grid_audit_v1_000039` showed
that U1.1 V1 is structurally valid but functionally under-calibrated:

```text
U1.1 excludes too much valid clean-grid support.
U1.1 still allows some localized blocking / ambiguous support.
```

The visual diagnosis is:

```text
U1.1 is confusing valid thick-line fringe with local contamination.
```

Therefore, U1.1-CAL must calibrate U1.1 using geometric hysteresis:

```text
strong accept  = traceable ridge/core or stable valid fringe
strong reject  = direct conflict, protrusion, off-axis microcomponent, or local anomaly
middle zone    = suspicious/deferred, preserved but not valid support
```

U1.1-CAL must never become a runtime semantic classifier. It may produce only a
traceable calibration config and audit reports.

## 2. Non-Negotiable Rule

```text
No module may gain interpretation by losing geometric traceability.
```

U1.1-CAL may improve thresholds, weights, and deterministic decisions. It must
not turn raw masks, labels, or untraceable embeddings into final geometry.

## 3. Pipeline Position

Required conceptual order:

```text
B1 V3.3 geometry extraction
-> B1 V3.4.2 residual evidence stratification
-> C1.0 individual residual hypothesis validation
-> C1.1 collective residual hypothesis validation
-> U1.0 clean-grid geometry purity gate
-> U1.1 subobject clean-grid geometry purity gate
-> U1.1-CAL offline calibration, audit only
-> U1.1 rerun with calibrated config
-> later C2.0 negative gap hypothesis, if any
-> later integration module, if any
```

U1.1-CAL is not an extractor, not a virtualizer, and not a final support
integrator.

## 4. Module Boundary

U1.1-CAL may:

```text
read U1.1 outputs
read upstream V3.3 / V3.4.2 / C1.0 / C1.1 / U1.0 outputs
read GRID_AUDIT_V1 truth only in offline calibration/audit mode
compute traceable subobject features
search deterministic threshold/weight configurations
write a calibrated U1.1 config JSON
write calibration reports and audit tables
write diagnostic visuals
```

U1.1-CAL must not:

```text
modify U1.1 script at runtime
modify V3.3, V3.4.2, C1.0, C1.1, U1.0, or U1.1 outputs
write final geometry
repair absent gaps
create lines, axes, crossings, grids, rows, columns, cells, or topology
use GRID_AUDIT truth as runtime input for U1.1
hide excluded support
erase failed cases from audit
```

## 5. Required Inputs

Required dataset:

```text
datasets/grid_audit_v1/dataset_manifest.json
datasets/grid_audit_v1/dataset_manifest.csv
datasets/grid_audit_v1/splits/calibration.txt
datasets/grid_audit_v1/splits/validation.txt
datasets/grid_audit_v1/splits/holdout_contract.txt
datasets/grid_audit_v1/samples/<sample_id>/sample_manifest.json
datasets/grid_audit_v1/samples/<sample_id>/masks/observed_valid_geometry.npy
datasets/grid_audit_v1/samples/<sample_id>/masks/blocking_geometry_evidence.npy
datasets/grid_audit_v1/samples/<sample_id>/masks/ambiguous_geometry_evidence.npy
datasets/grid_audit_v1/samples/<sample_id>/masks/missing_not_recoverable_geometry.npy
datasets/grid_audit_v1/samples/<sample_id>/masks/clean_grid_mask.npy
```

Required module runs per sample:

```text
V3.3 run directory
V3.4.2 run directory
C1.0 run directory
C1.1 run directory
U1.0 run directory
U1.1 baseline run directory, or ability to run U1.1 baseline
```

Required U1.1 files per sample:

```text
summary.json
contract_audit.json
u1_1_subobject_regions.csv
u1_1_subobject_memberships.csv
u1_1_subobject_validation.csv
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

## 6. Required Outputs

U1.1-CAL must write:

```text
u1_1_calibrated_config.json
u1_1_calibration_grid.csv
u1_1_calibration_feature_table.csv
u1_1_calibration_decisions.csv
u1_1_validation_report.json
u1_1_holdout_contract_audit.json
u1_1_calibration_report.md
summary.json
contract_audit.json
```

Required visuals:

```text
visuals/01_baseline_vs_calibrated_grid_support.png
visuals/02_baseline_vs_calibrated_exclusions.png
visuals/03_blocking_ambiguous_error_overlay.png
visuals/04_wrong_exclusion_overlay.png
visuals/05_metric_tradeoff_frontier.png
visuals/06_holdout_visual_summary.png
```

No visual may present calibrated support as final geometry.

## 7. Calibrated Config Schema

`u1_1_calibrated_config.json` must contain only deterministic runtime
parameters:

```text
version
source_calibrator_version
created_at
dataset_id
calibration_split_ids
validation_split_ids
holdout_split_ids
selected_objective
thresholds
weights
decision_policy
contract_acceptance_targets
feature_names
prohibited_runtime_inputs
```

Allowed threshold fields:

```text
max_core_axis_distance_px
max_grid_consistent_p95_axis_distance_px
max_local_width_for_clean_support_px
min_local_density_score
min_local_continuity_score
max_conflict_score_for_grid_consistent
max_conflict_score_for_suspicious
min_subobject_pixels
conflict_neighborhood_px
local_window_radius_px
max_bridge_gap_px
min_longitudinal_run_length_for_valid_fringe
min_ridge_continuity_score_for_valid_fringe
max_protrusion_score_for_valid_fringe
max_asymmetric_fringe_score_for_valid_fringe
max_off_axis_microcomponent_score_for_accept
min_direct_conflict_touch_ratio_for_reject
```

Allowed weight fields:

```text
axis_score_weight
width_score_weight
continuity_score_weight
density_score_weight
ridge_score_weight
valid_fringe_score_weight
protrusion_penalty_weight
direct_conflict_penalty_weight
near_conflict_penalty_weight
source_u1_0_state_weight
```

Forbidden config fields:

```text
raw_mask_pixels
truth_mask_pixels
sample_specific_coordinates
sample_specific_exceptions
learned_untraceable_embeddings
final_line_ids
axis_descriptors
crossing_graphs
semantic_labels
clinical_labels
```

## 8. Feature Families

U1.1-CAL must preserve two classes of features.

### 8.1 Already Present U1.1 Features

```text
axis_distance_median_px
axis_distance_p95_px
local_width_estimate_px
local_density_score
local_continuity_score
local_conflict_score
local_blocking_score
local_ambiguity_score
source_u1_0_gate_state
source_membership_role
region_pixel_count
core_pixel_count
fringe_pixel_count
```

### 8.2 Required New Geometric Hysteresis Features

```text
longitudinal_run_length
ridge_continuity_score
axis_aligned_neighbor_support
valid_fringe_continuity_score
fringe_side_consistency
protrusion_score
asymmetric_fringe_score
off_axis_microcomponent_score
direct_conflict_touch_ratio
near_conflict_touch_ratio
direct_ambiguity_touch_ratio
near_ambiguity_touch_ratio
conflict_component_shape_score
parent_line_reabsorption_score
```

These features must be computed from traceable geometry, maps, and
memberships. They must not require final line reconstruction.

## 9. Geometric Hysteresis Decision Policy

U1.1-CAL must calibrate U1.1 toward a three-zone policy.

### 9.1 Strong Accept

A subobject region may be `grid_consistent` if:

```text
support is traceable to V3.3 observed pixels
region is core/ridge consistent OR valid-fringe consistent
longitudinal continuity is sufficient
direct conflict touch ratio is zero or below configured threshold
direct ambiguity touch ratio is zero or below configured threshold
region is not an inferred span
```

High local width alone must not force exclusion.

### 9.2 Strong Reject

A subobject region must become `blocking_like` or `ambiguous` when:

```text
direct conflict touch ratio exceeds threshold
direct ambiguity touch ratio exceeds threshold
protrusion score exceeds threshold
off-axis microcomponent score exceeds threshold
conflict component shape contradicts clean-grid support
```

### 9.3 Middle Zone

A subobject region must remain `suspicious` or `deferred` when:

```text
support is traceable but too weak for strong accept
support is not anomalous enough for strong reject
source context is incomplete
region is small, isolated, or structurally underdetermined
```

Middle-zone support must remain visible and traceable, but must not be counted
as refined unified valid observed support.

## 10. Calibration Splits

U1.1-CAL must use the dataset splits as follows:

```text
calibration.txt       -> parameter search
validation.txt        -> select final config
holdout_contract.txt  -> final contract audit only
```

Holdout samples must not influence parameter search.

If a sample is missing required upstream outputs, it must be reported as
`missing_runtime_context` and excluded from metric denominators only with an
explicit audit record.

## 11. Objective Function

The objective must be lexicographic, not a single blended score.

Required priority:

```text
1. all structural invariants true
2. no inferred span counted as observed support
3. not_recoverable_false_observed_rate_after_u1_1 == 0.00
4. observed_geometry_precision_after_u1_1 >= 0.985
5. observed_geometry_recall_after_u1_1 >= 0.965
6. blocking_false_observed_rate_after_u1_1 <= 0.10
7. ambiguous_false_observed_rate_after_u1_1 <= 0.20
8. minimize wrong_exclusion_rate_after_u1_1
9. minimize wrong_inclusion_rate_after_u1_1
```

A configuration that reaches high recall by allowing blocking/ambiguous
support must fail.

A configuration that reaches low blocking/ambiguous rates by deleting valid
grid support must fail.

## 12. Search Strategy

U1.1-CAL V1 may use deterministic search:

```text
grid search
coarse-to-fine search
Pareto frontier filtering
rule ablation
holdout replay
```

U1.1-CAL V1 must not use:

```text
black-box neural classifiers
untraceable learned embeddings
sample-specific overrides
post-hoc manual masking
truth-driven runtime decisions
```

Every accepted parameter set must be replayable.

## 13. Required CSV Schemas

### 13.1 `u1_1_calibration_grid.csv`

Required fields:

```text
config_id
split_name
sample_count
status
observed_geometry_precision_after_u1_1
observed_geometry_recall_after_u1_1
blocking_false_observed_rate_after_u1_1
ambiguous_false_observed_rate_after_u1_1
not_recoverable_false_observed_rate_after_u1_1
wrong_exclusion_rate_after_u1_1
wrong_inclusion_rate_after_u1_1
passes_contract_targets
objective_rank
config_json_path
notes
```

### 13.2 `u1_1_calibration_feature_table.csv`

Required fields:

```text
sample_id
subobject_region_id
source_geometry_object_id
source_u1_0_gate_state
baseline_u1_1_gate_state
calibrated_u1_1_gate_state
region_pixel_count
axis_distance_p95_px
local_width_estimate_px
local_density_score
local_continuity_score
longitudinal_run_length
ridge_continuity_score
valid_fringe_continuity_score
protrusion_score
asymmetric_fringe_score
off_axis_microcomponent_score
direct_conflict_touch_ratio
near_conflict_touch_ratio
direct_ambiguity_touch_ratio
near_ambiguity_touch_ratio
parent_line_reabsorption_score
runtime_feature_only
truth_used_for_metric_only
```

### 13.3 `u1_1_calibration_decisions.csv`

Required fields:

```text
sample_id
subobject_region_id
baseline_state
calibrated_state
decision_zone
decision_reason
support_pixel_count
truth_observed_overlap_pixels
truth_blocking_overlap_pixels
truth_ambiguous_overlap_pixels
truth_not_recoverable_overlap_pixels
changed_by_calibration
change_is_metric_improving
```

Truth overlap fields may be used only in calibration/audit reports.

## 14. Required Metrics

Per split:

```text
sample_count
completed_sample_count
failed_sample_count
observed_geometry_precision_after_u1_1
observed_geometry_recall_after_u1_1
blocking_false_observed_rate_after_u1_1
ambiguous_false_observed_rate_after_u1_1
not_recoverable_false_observed_rate_after_u1_1
clean_grid_observed_coverage_after_u1_1
wrong_exclusion_rate_after_u1_1
wrong_inclusion_rate_after_u1_1
mean_grid_consistent_subsupport_ratio
mean_excluded_subsupport_ratio
```

Per decision zone:

```text
strong_accept_region_count
strong_reject_region_count
middle_zone_region_count
strong_accept_wrong_inclusion_pixels
strong_reject_wrong_exclusion_pixels
middle_zone_observed_pixels
```

## 15. Invariants

Mandatory invariants:

```text
calibrated config contains only runtime-safe parameters
GRID_AUDIT truth is never written into runtime config
GRID_AUDIT truth is never consumed by U1.1 runtime
holdout split is not used for parameter search
all U1.1 structural invariants remain true after calibrated rerun
refined unified valid observed support excludes suspicious/blocking/ambiguous/deferred
refined unified valid observed support excludes inferred spans
refined unified valid observed support excludes diagnostic residual
refined unified valid observed support excludes ambiguous residual
excluded support remains traceable
V3.3 outputs unchanged
V3.4.2 outputs unchanged
C1.0 outputs unchanged
C1.1 outputs unchanged
U1.0 outputs unchanged
U1.1 baseline outputs unchanged
```

If any invariant fails, status must be:

```text
failed_contract
```

## 16. Acceptance Criteria

U1.1-CAL is accepted only if the selected config passes holdout contract audit:

```text
observed_geometry_precision_after_u1_1 >= 0.985
observed_geometry_recall_after_u1_1 >= 0.965
blocking_false_observed_rate_after_u1_1 <= 0.10
ambiguous_false_observed_rate_after_u1_1 <= 0.20
not_recoverable_false_observed_rate_after_u1_1 == 0.00
all invariants true
```

If calibration improves metrics but does not pass all acceptance criteria,
status must be:

```text
completed_not_accepted
```

If it passes all acceptance criteria:

```text
accepted
```

## 17. Visual Audit Requirements

U1.1-CAL must preserve visual evidence for:

```text
baseline U1.1 valid support
calibrated U1.1 valid support
baseline exclusions
calibrated exclusions
truth blocking/ambiguous overlays
wrong exclusions
wrong inclusions
holdout summary
```

Visual audit must answer:

```text
Does calibrated U1.1 preserve valid thick-line fringe?
Does calibrated U1.1 reject localized red blocking/ambiguous regions?
Does calibrated U1.1 avoid turning inferred spans into observed support?
Does calibrated U1.1 avoid hiding excluded support?
```

## 18. Prohibitions

U1.1-CAL must not create or declare:

```text
final LineObjects
modified coordinates
extended lines
merged lines
deleted lines
AxisDescriptors
crossings
crossing graphs
axis families as final geometry
topology graphs
grids
tables
panels
rows
columns
cells
coordinate systems
clinical interpretation
final virtualization
```

U1.1-CAL must not:

```text
use inferred spans as observed support
use diagnostic residual as clean-grid support
use ambiguous residual as validated support
use GRID_AUDIT_V1 ground truth as runtime inference input
hide excluded observed support
erase excluded support from audit
repair absent gaps
write sample-specific exceptions into config
```

## 19. Contract Verdict

U1.1-CAL is valid only if it calibrates U1.1 through deterministic,
traceable, runtime-safe parameters.

It becomes invalid if it converts:

```text
truth labels -> runtime decisions
subobject states -> final geometry
pixel exclusion -> upstream deletion
calibration config -> sample-specific mask
visual audit -> manual patch
```

Final rule:

```text
U1.1-CAL may teach U1.1 where to set its geometric thresholds.
U1.1-CAL may not teach U1.1 to ignore traceability.
```
