# X3 Trainable Geometric Evidence Unit Manifest

Status: active experimental manifest
Date: 2026-06-18

## Purpose

X3.0 defines the next complete runtime surface for the Geometric Evidence Unit:
functional, modular, trainable-aware, and still geometrically traceable.

Critical rule:

```text
No module may gain interpretation by losing geometric traceability.
```

## Why X3 Exists

X2.0 proved that a single fusion layer can combine modular geometric evidence.
However, X2.0 is not trainable by default.

X3.0 adds an explicit trainable boundary:

```text
trainable modules are allowed
the full unit is not a black-box learner
every trained decision must be traceable to pixels/components/families
```

## X3 Runtime Chain

```text
UNIT outputs
  + C1.0/C1.1 residual geometry evidence when supplied
  + C1-CAL V1 residual hypothesis calibration when supplied
  + G1.0-CAL V1 trainable outputs
  + D1.0 simple lineality
  + D1.1 role classification
  + D1-CAL V1 role calibration when supplied
  + readable trained assets
  -> X3.0 trainable-aware fusion
```

## Active Trainable Modules

| Layer | Status | Runtime role | Runtime truth labels |
| --- | --- | --- | --- |
| G1.0-CAL V1 | active trainable | component-family candidate calibration | forbidden |
| C1-CAL V1 | active trainable | residual hypothesis calibration | forbidden |
| D1-CAL V1 | active trainable | deferred linear role calibration | forbidden |

## Active Functional Modules

| Layer | Status | Runtime role | Runtime truth labels |
| --- | --- | --- | --- |
| C1.0 | active functional | individual residual geometry hypothesis validation | forbidden |
| C1.1 | active functional | collective residual geometry hypothesis validation | forbidden |
| D1.0 | active functional | deferred simple lineality | forbidden |
| D1.1 | active functional | deferred linear role classification | forbidden |

## Active Calibrable Inputs

| Layer | Status | Runtime role | Runtime truth labels |
| --- | --- | --- | --- |
| U1.1-CAL | upstream calibrable | purity/hysteresis support | forbidden |
| L1.1 | upstream calibrable | observed-domain calibration | forbidden |
| L1.2-CAL | upstream calibrable | deferred line-like calibration | forbidden |

## Reserved Trainable/Calibrable Slots

| Slot | Status | Required before runtime activation |
| --- | --- | --- |
| U/L extended calibrators | reserved, not runtime-active | contract, dataset boundary, runtime safety audit |

## X3 Module

```text
modules/x3/module_x3_0_trainable_geometric_evidence_unit.py
```

X3.0 consumes existing outputs. It must not call upstream module scripts.

## Required Contract

```text
contracts/CONTRACT_X3_0_TRAINABLE_GEOMETRIC_EVIDENCE_UNIT.md
```

## Required Runtime Assets

Current active trained assets:

```text
models/g1_0_cal_v1_deferred_family/model_config.json
models/g1_0_cal_v1_deferred_family/feature_scaler.json
models/g1_0_cal_v1_deferred_family/coefficients.csv
models/c1_cal_v1_residual_hypothesis/model_config.json
models/c1_cal_v1_residual_hypothesis/feature_scaler.json
models/c1_cal_v1_residual_hypothesis/coefficients.csv
models/d1_cal_v1_deferred_linear_role/model_config.json
models/d1_cal_v1_deferred_linear_role/feature_scaler.json
models/d1_cal_v1_deferred_linear_role/coefficients.csv
```

## Acceptance

X3.0 is accepted only when:

```text
all X3 invariants pass
G1.0-CAL, C1-CAL and D1-CAL assets are readable
trainable influence maps are written
source-bit maps are written
G1.0-CAL probable-line evidence is preserved as its own traced evidence layer
D1.0 simple observed-line evidence is preserved independently from D1 role labels
visual audit exists
no runtime truth labels are consumed
no final geometry is created
```

## Non-Goal

X3.0 does not create:

```text
final tables
final cells
OCR labels
clinical semantics
exported virtual objects
```
