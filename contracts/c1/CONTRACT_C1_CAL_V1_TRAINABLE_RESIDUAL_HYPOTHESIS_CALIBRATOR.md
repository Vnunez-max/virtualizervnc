# CONTRACT C1-CAL V1 - TRAINABLE RESIDUAL HYPOTHESIS CALIBRATOR

Version: `MODULE_C1_CAL_V1_TRAINABLE_RESIDUAL_HYPOTHESIS_CALIBRATOR`

Date: 2026-06-18

## Purpose

C1-CAL V1 calibrates C1.0/C1.1 residual geometry hypotheses with a small,
readable trainable model.

It answers only this decision:

```text
observed residual hypothesis -> promote residual geometry evidence / keep context / reserve non-geometry
```

It does not create final lines, tables, cells, OCR, symbols, or virtualized
objects.

## Critical Rule

```text
No module may gain interpretation by losing geometric traceability.
```

## Dataset Boundary

Dataset truth is allowed only inside dataset generation, training, validation,
holdout evaluation, and audit reports. Dataset truth is forbidden at runtime.

The dataset must preserve:

```text
sample_id
hypothesis_id
x
y
source_hypothesis_state
target_label
label_provenance
```

Allowed target labels:

```text
promote_residual_geometry
keep_context
reserve_non_geometry
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
samples/<sample_id>/maps/truth_residual_geometry_map.npy
samples/<sample_id>/maps/truth_non_geometry_map.npy
samples/<sample_id>/maps/truth_ambiguous_context_map.npy
samples/<sample_id>/maps/hypothesis_id_map.npy
samples/<sample_id>/tables/hypothesis_labels.csv
samples/<sample_id>/tables/hypothesis_features.csv
samples/<sample_id>/tables/pixel_trace.csv
samples/<sample_id>/visuals/audit_summary.png
visuals/dataset_contact_sheet.png
```

The dataset is synthetic and auditable. It must not use clinical images,
OCR-derived labels, or manual sample-specific coordinates.

## Runtime Inputs

C1-CAL V1 runtime apply consumes:

```text
C1.0 residual_geometry_hypotheses.csv
C1.0 residual_hypothesis_memberships.csv
C1.0 maps/validated_hypothesis_observed_support_map.npy
optional C1.1 collective_residual_hypotheses.csv
optional C1.1 collective_hypothesis_memberships.csv
readable C1-CAL V1 model assets
```

Readable model assets:

```text
model_config.json
feature_scaler.json
coefficients.csv
```

## Runtime Outputs

```text
maps/c1_cal_v1_candidate_map.npy
maps/c1_cal_v1_promoted_residual_geometry_map.npy
maps/c1_cal_v1_keep_context_map.npy
maps/c1_cal_v1_reserved_non_geometry_map.npy
maps/c1_cal_v1_action_map.npy
maps/c1_cal_v1_changed_decision_map.npy
maps/c1_cal_v1_hypothesis_id_map.npy
tables/c1_cal_v1_predictions.csv
tables/c1_cal_v1_pixel_memberships.csv
visuals/01_c1_cal_v1_prediction_overlay.png
visuals/02_c1_cal_v1_audit_summary.png
summary.json
contract_audit.json
```

## Required Invariants

```text
promoted_pixels_subset_of_c1_candidate_support == true
keep_context_subset_of_c1_candidate_support == true
reserved_non_geometry_subset_of_c1_candidate_support == true
output_classes_mutually_exclusive == true
every_output_pixel_has_hypothesis_trace == true
runtime_truth_labels_not_used == true
does_not_create_final_geometry == true
does_not_modify_c1_outputs == true
does_not_modify_v3_4_2 == true
```

## X3 Integration

X3 may consume C1-CAL V1 outputs as an active trainable layer.

X3 may add `c1_cal_v1_promoted_residual_geometry_map.npy` to evidence-level
line-study support, but this remains evidence. It is not final geometry.

X3 must preserve source-bit traceability for every promoted C1-CAL pixel.

## Acceptance

C1-CAL V1 is accepted only when:

```text
dataset traceability rate == 1.0
splits are sample-id disjoint
all three target classes are present
hard-negative ratio >= 0.25
holdout accuracy is reported
readable runtime assets exist
runtime apply does not use truth labels
visual audit exists
```

