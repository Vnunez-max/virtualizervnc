# CONTRACT D1.1 - DEFERRED LINEAR ROLE CLASSIFIER V1

Version: `MODULE_D1_1_V1_DEFERRED_LINEAR_ROLE_CLASSIFIER`

Date: 2026-06-14

## 1. Purpose

D1.1 classifies D1.0 deferred simple-linearity hypotheses by geometric role.

Input unit:

```text
D1.0 simple_linearity_candidate + hypothesis_id
```

Output role:

```text
grid_line_candidate
axis_line_candidate
tick_or_scale_mark
page_border_or_layout_box
text_or_digit_stroke
curve_or_data_trace
ambiguous_linear
```

## 2. Non-Negotiable Rule

```text
No module may gain interpretation by losing geometric traceability.
```

Every classified pixel must remain:

```text
observed
deferred in the source D1.0 input
member of a D1.0 hypothesis
linked to a role decision and feature row
```

## 3. Scope

Allowed:

```text
read D1.0 hypotheses, memberships and maps
read unit line-study/observed maps as geometric context
classify D1.0 candidate hypotheses by simple geometric features
write role maps, hypothesis tables, memberships, metrics and visuals
```

Forbidden:

```text
modify V3.4.1
modify V3.4.2
modify U/L/G/G1.0/G1.0-CAL/D1.0 outputs
create final geometry
create LineObjects
create AxisDescriptors
create crossings
create OCR or clinical semantics
use truth labels
use manual sample-specific coordinates
classify pixels outside D1.0 candidates
promote grid_line_candidate into final line geometry
```

## 4. Feature Families

Allowed features:

```text
orientation
span
pixel_count
density
longest_run
lineality_score
bbox
edge distance
same-axis line-study extension score
near line-study contact score
parallel line-study context count
local observed-context score
```

Not allowed:

```text
OCR text
clinical semantics
ground truth role labels
manual chart-specific regions
sample-specific coordinates
```

## 5. Required Outputs

```text
summary.json
contract_audit.json
d1_1_role_hypotheses.csv
d1_1_role_memberships.csv
d1_1_role_summary.csv
maps/d1_1_role_class_map.npy
maps/d1_1_role_hypothesis_id_map.npy
maps/grid_line_candidate_map.npy
maps/axis_line_candidate_map.npy
maps/tick_or_scale_mark_map.npy
maps/page_border_or_layout_box_map.npy
maps/text_or_digit_stroke_map.npy
maps/curve_or_data_trace_map.npy
maps/ambiguous_linear_map.npy
visuals/01_d1_1_role_overlay.png
visuals/02_grid_line_candidates.png
visuals/03_non_grid_linear_roles.png
visuals/04_d1_1_audit_summary.png
```

## 6. Acceptance

```text
classified_pixels_subset_of_d1_0_candidates == true
role_maps_mutually_exclusive == true
role_memberships_subset_of_d1_0_candidates == true
every_classified_pixel_has_role_and_hypothesis == true
grid_line_candidate_is_not_final_geometry == true
does_not_modify_upstream_outputs == true
```

## 7. Interpretation

D1.1 creates role evidence, not final geometry.

`grid_line_candidate` means:

```text
this D1.0 deferred-linear support has geometric evidence consistent with a grid line
```

It does not mean:

```text
final virtualized line
```
