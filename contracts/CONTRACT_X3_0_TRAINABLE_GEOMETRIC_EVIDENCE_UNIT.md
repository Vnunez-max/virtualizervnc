# CONTRACT X3.0 - Trainable Geometric Evidence Unit

Version: `MODULE_X3_0_TRAINABLE_GEOMETRIC_EVIDENCE_UNIT`

Date: 2026-06-18

## Purpose

X3.0 is the first complete runtime surface for the Geometric Evidence Unit that
explicitly supports trainable modules without turning the full unit into a
black-box model.

X3.0 consumes:

```text
unit full-model outputs
C1.0/C1.1 residual geometry evidence when supplied
G1.0-CAL V1 trainable outputs
D1.0 deferred simple-linearity outputs
D1.1 deferred linear role outputs
readable trained model assets
```

It produces:

```text
fused line-study support
future-module pool
trainable influence maps
source-bit traceability maps
visual audit outputs
```

X3.0 is not a final virtualizer.

## Critical Rule

```text
No module may gain interpretation by losing geometric traceability.
```

## Architectural Position

X3.0 comes after the current modular unit and after X2.0.

Conceptually:

```text
V3.4.2 -> C1.x -> U1.x -> L1.x -> G1.x -> D1.x -> UNIT/X2 -> X3.0
```

X3.0 is a trainable-aware fusion layer. It must not replace the upstream
modules, datasets, contracts, or runtime maps.

## Trainability Policy

The full X3.0 unit is not trainable as a monolith.

Active trainable runtime layer:

```text
G1.0-CAL V1
```

Active calibrable upstream layers:

```text
U1.1-CAL
L1.1
L1.2-CAL
```

Inactive future trainable/calibrable slots:

```text
D1-CAL
C1-CAL
U/L threshold calibrators beyond current contracts
```

C1 and D1 themselves are active functional layers. Only their future trainable
CAL variants are reserved until they have their own contracts, datasets,
evaluation reports, readable runtime assets, and visual audits.

## Required Inputs

CLI:

```bash
python modules/x3/module_x3_0_trainable_geometric_evidence_unit.py \
  --unit-dir /path/to/unit_out \
  --g1-cal-dir /path/to/g1_0_cal_v1_out \
  --d1-0-dir /path/to/d1_0_out \
  --d1-1-dir /path/to/d1_1_out \
  --model-dir models/g1_0_cal_v1_deferred_family \
  --out /path/to/x3_out \
  --sample-id sample_id \
  --c1-0-dir /optional/path/to/c1_0_out \
  --c1-1-dir /optional/path/to/c1_1_out
```

Optional C1 inputs are active functional evidence when supplied. They are
optional because earlier promoted smoke runs did not always materialize C1
folders, and X3 must remain portable over the current functional unit.

Required unit maps:

```text
unit_observed_support_map.npy
unit_final_line_study_support_map.npy
unit_final_future_module_pool_map.npy
unit_unaccounted_observed_support_map.npy
unit_stage_contribution_map.npy
```

Required G1.0-CAL V1 maps:

```text
g1_0_cal_v1_action_map.npy
g1_0_cal_v1_promoted_to_line_map.npy
g1_0_cal_v1_non_promoted_candidate_map.npy
g1_0_cal_v1_calibrated_future_module_pool_map.npy
g1_0_cal_v1_calibrated_deferred_domain_support_map.npy
```

Required D1.0 maps:

```text
simple_linearity_candidate_map.npy
linearity_hypothesis_id_map.npy
```

Required D1.1 maps:

```text
d1_1_role_class_map.npy
d1_1_role_confidence_map.npy
grid_line_candidate_map.npy
text_or_digit_stroke_map.npy
tick_or_scale_mark_map.npy
page_border_or_layout_box_map.npy
curve_or_data_trace_map.npy
ambiguous_linear_map.npy
```

Optional C1.0 maps:

```text
validated_hypothesis_observed_support_map.npy
```

Optional C1.1 maps:

```text
collective_validated_observed_support_map.npy
```

Required readable model assets:

```text
model_config.json
feature_scaler.json
coefficients.csv
```

## Required Outputs

Maps:

```text
x3_observed_support_map.npy
x3_unit_line_study_support_map.npy
x3_trainable_g1_0_cal_v1_influence_map.npy
x3_trainable_changed_decision_map.npy
x3_d1_grid_line_added_map.npy
x3_fused_line_study_support_map.npy
x3_fused_future_module_pool_map.npy
x3_unaccounted_observed_support_map.npy
x3_fused_class_map.npy
x3_source_bit_map.npy
x3_d1_role_class_map.npy
x3_d1_role_confidence_map.npy
x3_d1_hypothesis_id_map.npy
x3_c1_functional_evidence_map.npy
```

Tables:

```text
x3_fused_class_summary.csv
x3_trainable_action_summary.csv
x3_trainable_layers.csv
x3_functional_layers.csv
x3_source_traceability_summary.csv
```

Visuals:

```text
01_x3_fused_class_overlay.png
02_x3_fused_line_study.png
03_x3_future_module_pool.png
04_x3_trainable_g1_influence.png
05_x3_d1_grid_added.png
06_x3_c1_functional_evidence.png
07_x3_trainable_influence_codes.png
08_x3_audit_summary.png
```

Reports:

```text
summary.json
contract_audit.json
```

## Fusion Logic

X3.0 must:

```text
load all required maps directly
verify all input maps share one shape
verify G1.0-CAL V1 readable model assets exist
derive observed support only from the unit observed map
start line-study support from the unit line-study map
register C1.0/C1.1 as active residual functional evidence when supplied
derive trainable influence from G1.0-CAL V1 candidates/actions
add D1.1 grid-line candidates only as line-study evidence
reserve D1.1 non-grid linear roles for future-module pool
preserve unaccounted observed support explicitly
write source-bit traceability for fused line and future pixels
```

## Forbidden

X3.0 must not:

```text
train at runtime
use dataset truth labels at runtime
use manual sample-specific coordinates
use OCR or clinical semantics
modify V3.4.1
modify V3.4.2
modify upstream outputs
call upstream modules as subprocesses
create final line/table/cell/OCR objects
turn X3 into a black-box segmentation model
hide which trainable layer influenced a pixel
```

## Invariants

```text
all_input_maps_same_shape == true
x3_line_subset_of_observed == true
x3_future_subset_of_observed == true
x3_line_and_future_disjoint == true
d1_grid_added_subset_of_d1_candidate == true
trainable_influence_subset_of_g1_candidate == true
trainable_changed_subset_of_g1_candidate == true
source_trace_for_all_x3_line_pixels == true
source_trace_for_all_x3_future_pixels == true
c1_functional_evidence_subset_of_observed == true
g1_trainable_model_assets_readable == true
runtime_truth_labels_not_used == true
does_not_create_final_geometry == true
does_not_modify_upstream_outputs == true
does_not_modify_v3_4_2 == true
```

## Acceptance

X3.0 is accepted only if:

```text
all invariants pass
visual audit outputs exist
trainable layers table exists
source traceability table exists
no datasets or historical outputs are added to repo
V3.4.2 remains frozen
```

## Status

X3.0 is the trainable-aware complete Geometric Evidence Unit runtime surface.

It is complete in the sense that it integrates the current functional unit,
current trainable layer, and D1 deferred complement. It is not complete in the
sense of final document virtualization.
