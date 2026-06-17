# CONTRACT G1.0-CAL V1 - TRAINABLE DEFERRED FAMILY CALIBRATOR

Version: `MODULE_G1_0_CAL_V1_TRAINABLE_DEFERRED_FAMILY_CALIBRATOR`

Date: 2026-06-14

## 1. Purpose

G1.0-CAL V1 is a trainable calibrator for the DG1.0 deferred-only problem:

```text
deferred component + candidate line family -> promote / keep deferred / reserve
```

It exists to calibrate the decision boundary left by G1.0, especially hard
negative linear symbols that can look like traceable line support.

## 2. Non-Negotiable Rule

```text
No module may gain interpretation by losing geometric traceability.
```

Every prediction must preserve:

```text
sample_id
split
sample_type
component_id
family_candidate_id
orientation
bbox
component_pixel_count
features_used
predicted_target
predicted_promote
calibrated probabilities
```

## 3. Scope

G1.0-CAL V1 is a dataset-trained calibrator. It does not replace V3, U, L, or
G modules, and it does not alter existing runtime outputs.

Allowed:

```text
train a model on DG1.0 train split
choose thresholds using DG1.0 validation split
evaluate on train/validation/holdout
save weights, scaler, thresholds, predictions, metrics, and visuals
```

Forbidden:

```text
modify V3.4.1
modify V3.4.2
modify G1.0 runtime code or outputs
use holdout labels for training or threshold selection
use truth labels as runtime inputs
use sample-specific manual coordinates
use OCR or clinical semantics
create final geometry, final line objects, tables, cells, rows, columns, or axes
```

## 4. Training Unit

The training unit is:

```text
component_id + family_candidate_id inside one sample_id
```

not a raw image crop and not a whole-mask label.

## 5. Permitted Inputs

Runtime-style inputs are restricted to traceable geometric features from
`component_features.csv` and deterministic derived features:

```text
component_pixel_count
family_distance
anchor_score
family_strength_score
component_colinearity_score
component_run_score
microstructure_score
mixed_contact_score
conflict_contact_score
bbox width / height / area
major length / minor length
fill ratio
aspect ratio
orientation one-hot
G1.0-compatible association score
```

The following may be used only for training/evaluation grouping, not as model
features:

```text
sample_id
sample_type
split
association_target
component_truth_label
pixel_truth_label
```

## 6. Targets

Allowed targets:

```text
promote_to_probable_line
keep_deferred
reserve_for_future_non_line
```

The calibrated binary promotion decision is:

```text
predicted_promote = predicted_target == promote_to_probable_line
```

## 7. Split Discipline

Training must use only `splits/train.txt`.

Threshold selection may use only `splits/validation.txt`.

Holdout must remain untouched until final evaluation.

Splits are sample-level splits, never component-level random splits.

## 8. Required Script

Create:

```text
outputs/module_g1_0_cal_v1_trainable_deferred_family_calibrator.py
```

Minimum CLI:

```bash
python outputs/module_g1_0_cal_v1_trainable_deferred_family_calibrator.py \
  --dataset-root outputs/dg1_0_deferred_only_line_family_dataset_v1 \
  --out outputs/g1_0_cal_v1_trainable_deferred_family_calibrator_dg1_0 \
  --seed 3420
```

## 9. Required Outputs

The output directory must include:

```text
summary.json
model/model_config.json
model/feature_scaler.json
model/coefficients.csv
predictions.csv
evaluation_metrics.csv
confusion_matrix.csv
threshold_search.csv
visuals/prediction_contact_sheet.png
visuals/error_contact_sheet.png
visuals/samples/<sample_id>_calibration_audit.png
```

## 10. Metrics

Minimum metrics:

```text
component_count
pixel_count
tp
fp
tn
fn
precision
recall
specificity
f1
binary_accuracy
target_accuracy
false_promotion_count
missed_structural_count
symbol_linear_false_positive_count
```

Metrics must be reported for:

```text
all
train
validation
holdout
each sample_type
```

## 11. Acceptance

Acceptance on DG1.0 requires:

```text
traceability_pass == true
split_discipline_pass == true
holdout_not_used_for_training == true
holdout_recall >= 0.99
holdout_false_promotion_count <= G1.0 baseline holdout false_promotion_count
all_false_promotion_count <= G1.0 baseline all false_promotion_count
```

For this dataset run, the G1.0 evaluation baseline is:

```text
baseline_all_false_promotion_count = 12
baseline_holdout_false_promotion_count = 4
baseline_all_recall = 1.0
baseline_holdout_recall = 1.0
```

## 12. Interpretation Rule

G1.0-CAL V1 may produce calibrated probabilities and decisions for audit or
future integration planning.

It must not be presented as a final runtime replacement until it is separately
audited against real pipeline outputs and the no-loss-of-traceability rule.

