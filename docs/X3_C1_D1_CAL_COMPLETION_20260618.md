# X3 C1-CAL/D1-CAL Completion Smoke - 2026-06-18

## Scope

This note records the activation of C1-CAL V1 and D1-CAL V1 as trainable
runtime layers inside the Geometric Evidence Unit.

The datasets were generated outside the repository:

```text
/tmp/virtualizervnc-c1-cal-dataset-v1
/tmp/virtualizervnc-d1-cal-dataset-v1
```

Generated datasets are not committed to GitHub.

## C1-CAL Dataset

```text
sample_count: 96
hypothesis_count: 511
positive_hypothesis_count: 198
negative_hypothesis_count: 221
ambiguous_hypothesis_count: 92
hard_negative_ratio: 0.4324853228962818
pixel_hypothesis_traceability_rate: 1.0
hypothesis_feature_traceability_rate: 1.0
split_independence_pass: true
runtime_truth_labels_allowed: false
status: PASS
```

## D1-CAL Dataset

```text
sample_count: 112
hypothesis_count: 672
role_counts:
  grid_line_candidate: 106
  axis_line_candidate: 93
  tick_or_scale_mark: 97
  page_border_or_layout_box: 98
  text_or_digit_stroke: 94
  curve_or_data_trace: 94
  ambiguous_linear: 90
hard_negative_ratio: 0.8422619047619048
pixel_hypothesis_traceability_rate: 1.0
hypothesis_feature_traceability_rate: 1.0
split_independence_pass: true
runtime_truth_labels_allowed: false
status: PASS
```

## Training Outputs

Readable runtime assets were created:

```text
models/c1_cal_v1_residual_hypothesis/model_config.json
models/c1_cal_v1_residual_hypothesis/feature_scaler.json
models/c1_cal_v1_residual_hypothesis/coefficients.csv
models/d1_cal_v1_deferred_linear_role/model_config.json
models/d1_cal_v1_deferred_linear_role/feature_scaler.json
models/d1_cal_v1_deferred_linear_role/coefficients.csv
```

Training reports embedded in `model_config.json`:

```text
C1-CAL validation_accuracy: 1.0
C1-CAL holdout_accuracy: 1.0
D1-CAL validation_accuracy: 1.0
D1-CAL holdout_accuracy: 1.0
```

These scores are synthetic-dataset smoke metrics, not clinical or production
accuracy claims.

## Runtime Smoke

A synthetic runtime fixture was created outside the repo:

```text
/tmp/virtualizervnc-cal-smoke
```

C1-CAL apply:

```text
candidate_pixels: 982
promoted_residual_geometry_pixels: 982
changed_decision_pixels: 0
hypothesis_count: 7
invariants_pass: true
```

D1-CAL apply:

```text
candidate_pixels: 620
changed_decision_pixels: 0
hypothesis_count: 6
grid_line_candidate_pixels: 347
axis_line_candidate_pixels: 130
text_or_digit_stroke_pixels: 59
curve_or_data_trace_pixels: 76
ambiguous_linear_pixels: 8
invariants_pass: true
```

X3 with C1-CAL and D1-CAL supplied:

```text
observed_support_pixels: 1592
x3_fused_line_study_support_pixels: 1326
x3_fused_future_module_pool_pixels: 141
c1_functional_evidence_pixels: 982
c1_cal_v1_added_pixels: 982
d1_cal_v1_changed_decision_pixels: 0
x3_d1_grid_line_added_pixels: 344
invariants_pass: true
```

## Interpretation

C1-CAL V1 and D1-CAL V1 are now active trainable layers with explicit contracts,
dataset generators, training scripts, runtime apply scripts, readable assets,
and X3 integration.

X3 remains a trainable-aware fusion/orchestrator. It is not a trainable
monolith and does not create final geometry.

Critical rule preserved:

```text
No module may gain interpretation by losing geometric traceability.
```

