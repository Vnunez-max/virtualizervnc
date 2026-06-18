# CONTRACT D1-CAL V1 - TRAINABLE DEFERRED LINEAR ROLE CALIBRATOR

Version: `MODULE_D1_CAL_V1_TRAINABLE_DEFERRED_LINEAR_ROLE_CALIBRATOR`

Date: 2026-06-18

## Purpose

D1-CAL V1 calibrates the role assigned to D1.0/D1.1 deferred lineality
hypotheses with a small, readable trainable model.

It answers only this decision:

```text
D1.0 lineality hypothesis -> grid / axis / tick / border / text / curve / ambiguous
```

It does not create final geometry. It only relabels observed D1.0 candidate
support.

## Critical Rule

```text
No module may gain interpretation by losing geometric traceability.
```

## Allowed Target Roles

```text
grid_line_candidate
axis_line_candidate
tick_or_scale_mark
page_border_or_layout_box
text_or_digit_stroke
curve_or_data_trace
ambiguous_linear
```

## Dataset Boundary

Dataset truth is allowed only for dataset generation, training, validation,
holdout evaluation, and audit. It is forbidden at runtime.

Required traceability:

```text
sample_id
linearity_hypothesis_id
x
y
role_label
source_deferred_candidate
label_provenance
```

Required dataset files:

```text
dataset_manifest.json
dataset_audit.json
dataset_balance_report.csv
splits/train.txt
splits/validation.txt
splits/holdout.txt
samples/<sample_id>/input_mask.png
samples/<sample_id>/maps/truth_role_class_map.npy
samples/<sample_id>/maps/d1_candidate_map.npy
samples/<sample_id>/maps/line_study_context_map.npy
samples/<sample_id>/maps/linearity_hypothesis_id_map.npy
samples/<sample_id>/tables/linearity_role_labels.csv
samples/<sample_id>/tables/linearity_features.csv
samples/<sample_id>/tables/pixel_trace.csv
samples/<sample_id>/visuals/audit_summary.png
visuals/dataset_contact_sheet.png
```

The dataset is synthetic and auditable. It must not use clinical images,
OCR-derived labels, or manual sample-specific coordinates.

## Runtime Inputs

D1-CAL V1 runtime apply consumes:

```text
D1.0 d1_0_linearity_hypotheses.csv
D1.0 d1_0_candidate_memberships.csv
D1.0 maps/simple_linearity_candidate_map.npy
D1.1 d1_1_role_hypotheses.csv
D1.1 d1_1_role_memberships.csv
D1.1 maps/d1_1_role_class_map.npy
readable D1-CAL V1 model assets
```

Readable model assets:

```text
model_config.json
feature_scaler.json
coefficients.csv
```

## Runtime Outputs

```text
maps/d1_cal_v1_candidate_map.npy
maps/d1_cal_v1_role_class_map.npy
maps/d1_cal_v1_role_confidence_map.npy
maps/d1_cal_v1_role_hypothesis_id_map.npy
maps/d1_cal_v1_changed_decision_map.npy
maps/d1_cal_v1_action_map.npy
maps/d1_cal_v1_grid_line_candidate_map.npy
maps/d1_cal_v1_axis_line_candidate_map.npy
maps/d1_cal_v1_tick_or_scale_mark_map.npy
maps/d1_cal_v1_page_border_or_layout_box_map.npy
maps/d1_cal_v1_text_or_digit_stroke_map.npy
maps/d1_cal_v1_curve_or_data_trace_map.npy
maps/d1_cal_v1_ambiguous_linear_map.npy
tables/d1_cal_v1_role_predictions.csv
tables/d1_cal_v1_role_memberships.csv
visuals/01_d1_cal_v1_role_overlay.png
visuals/02_d1_cal_v1_audit_summary.png
summary.json
contract_audit.json
```

## Required Invariants

```text
classified_pixels_subset_of_d1_0_candidates == true
role_maps_mutually_exclusive == true
every_classified_pixel_has_role_and_hypothesis == true
runtime_truth_labels_not_used == true
does_not_create_final_geometry == true
does_not_modify_d1_outputs == true
does_not_modify_v3_4_2 == true
```

## X3 Integration

When D1-CAL V1 outputs are supplied, X3 uses them as the active D1 role source.
If D1-CAL V1 is not supplied, X3 falls back to D1.1 fixed-rule roles.

`grid_line_candidate` may be added to X3 evidence-level line-study support.
All other D1-CAL roles remain in future-module pool or explicit non-grid
linear evidence. None of these are final geometry.

## Acceptance

D1-CAL V1 is accepted only when:

```text
dataset traceability rate == 1.0
splits are sample-id disjoint
all target roles are present
hard-negative ratio >= 0.30
holdout accuracy is reported
readable runtime assets exist
runtime apply does not use truth labels
visual audit exists
```

