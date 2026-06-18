# Trainable Modules Manifest

Status: active experimental manifest
Date: 2026-06-18

## Purpose

This manifest defines which modules in the synergic geometric virtualizer are trainable, calibrable, fixed, frozen, or only orchestration/fusion layers.

Critical rule:

```text
No module may gain interpretation by losing geometric traceability.
```

## Definitions

| Status | Meaning |
| --- | --- |
| frozen | Must not be modified or retrained in this project line. |
| fixed-rule | Deterministic geometric logic; may be audited, but not trained as a model. |
| calibrable | Thresholds/weights can be tuned using datasets while retaining explicit rules. |
| trainable | A small explicit model can be trained from traceable features and saved as readable runtime assets. |
| fusion/orchestrator | Combines module outputs; should not become a black-box model. |

## Module Trainability Matrix

| Module family | Module | Status | Training scope | Runtime truth labels allowed? | Notes |
| --- | --- | --- | --- | --- | --- |
| V3.4.2 | `module_b1_v3_4_2_residual_evidence_stratifier.py` | frozen | none | no | Frozen upstream residual evidence stratifier. Do not modify. |
| C1.x | `module_c1_0_residual_evidence_geometry_hypothesis_validator.py` | fixed-rule | calibrated by C1-CAL V1 output layer | no | Validates residual evidence hypotheses; functional source for C1-CAL. |
| C1.x | `module_c1_1_collective_residual_evidence_hypothesis_validator.py` | fixed-rule | calibrated by C1-CAL V1 output layer | no | Collective validator; must not invent geometry. |
| C1-CAL V1 | `module_c1_cal_v1_apply_residual_hypothesis_calibrator.py` | trainable | residual hypothesis classifier/calibrator | no | Active trainable layer; runtime uses saved readable assets only. |
| U1.x | `module_u1_1_subobject_clean_grid_geometry_purity_gate.py` | fixed-rule | none by default | no | Purity gate logic. Calibrated by U1.1-CAL, not trained directly. |
| U1.x | `module_u1_1_cal_geometric_hysteresis_calibrator.py` | calibrable | thresholds/hysteresis from traceable audit data | no | Calibrates geometric gates, not semantics. |
| L1.x | `module_l1_0_observed_support_domain_stratifier.py` | fixed-rule | none by default | no | Creates observed-domain partition; must preserve observed support. |
| L1.x | `module_l1_1_observed_support_domain_calibration_layer.py` | calibrable | thresholds/domain calibration | no | Calibration layer over L1.0 decisions. |
| L1.x | `module_l1_2_deferred_domain_subsupport_resolver.py` | fixed-rule | none by default | no | Resolves deferred support with explicit rules. |
| L1.x | `module_l1_2_cal_deferred_line_like_fragment_calibrator.py` | calibrable | line-like deferred thresholds | no | Calibrates deferred line-like fragments. |
| G1.x | `module_g1_0_deferred_line_family_resolver.py` | fixed-rule | feature generation/scoring audit | no | Creates component-family feature space; model is in G1.0-CAL. |
| G1.x | `module_g1_0_cal_v1_apply_trainable_calibrator.py` | trainable | component + family candidate classifier/calibrator | no | Main trainable module. Runtime uses saved model assets only. |
| D1.x | `module_d1_0_deferred_simple_linearity_auditor.py` | fixed-rule | calibrated by D1-CAL V1 output layer | no | Reality-first simple lineality auditor. |
| D1.x | `module_d1_1_deferred_linear_role_classifier.py` | fixed-rule | calibrated by D1-CAL V1 output layer | no | Functional role source for D1-CAL. |
| D1-CAL V1 | `module_d1_cal_v1_apply_deferred_linear_role_calibrator.py` | trainable | deferred linear role classifier/calibrator | no | Active trainable layer; runtime uses saved readable assets only. |
| Unit | `module_unit_full_model_v1_apply.py` | fusion/orchestrator | none | no | Applies module chain; must not become black-box training target. |
| X2.0 | `module_x2_0_geometric_evidence_fusion_single_script.py` | fusion/orchestrator | none by default | no | Experimental single-script fusion; consumes module evidence, not truth labels. |
| X3.0 | `module_x3_0_trainable_geometric_evidence_unit.py` | trainable-aware fusion/orchestrator | none as monolith | no | Consumes active trainable/calibrable outputs and writes trainable influence maps. |

## Current Trainable Set

Strictly trainable today:

```text
G1.0-CAL V1
C1-CAL V1
D1-CAL V1
```

Calibrable today:

```text
U1.1-CAL
L1.1
L1.2-CAL
```

Active functional layers that are not yet trained/calibrated by their own CAL
model:

```text
C1.0
C1.1
D1.0
D1.1
```

Dataset/training generators for active trainable modules exist but generated
datasets remain outside the repo:

```text
module_c1_cal_v1_residual_hypothesis_dataset.py
module_c1_cal_v1_train_residual_hypothesis_calibrator.py
module_d1_cal_v1_deferred_linear_role_dataset.py
module_d1_cal_v1_train_deferred_linear_role_calibrator.py
```

Frozen or non-trainable:

```text
V3.4.2
X2.0
unit orchestrator
```

Trainable-aware but not monolithic:

```text
X3.0
```

## Training Boundary

Training may use datasets only to produce explicit runtime assets such as:

```text
model_config.json
feature_scaler.json
coefficients.csv
calibrated_thresholds.json
```

Runtime modules must not use:

```text
ground-truth labels
manual sample-specific coordinates
OCR or clinical semantics
hidden visual inspection
```

## Acceptance For Any New Trainable Module

A new trainable/calibrable module requires:

```text
contract
feature table schema
training dataset boundary
evaluation report
saved readable model assets
visual audit surface
runtime path without truth labels
traceability to pixel/component/family where applicable
```

## Non-Negotiable Rule

```text
If training improves apparent accuracy but reduces geometric traceability, reject it.
```
