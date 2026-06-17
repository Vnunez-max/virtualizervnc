# Trainability Contract

Status: active experimental contract
Date: 2026-06-18

## Purpose

This contract defines when a module in the geometric virtualizer may be called trainable or calibrable.

The system is not a single black-box trainable model. It is a modular geometric evidence pipeline with selected trainable/calibrable decision layers.

## Critical Rule

```text
No module may gain interpretation by losing geometric traceability.
```

## Allowed Categories

### Frozen

Frozen modules cannot be modified, trained, or recalibrated in this project line.

Current frozen module:

```text
V3.4.2 residual evidence stratifier
```

### Fixed-Rule

Fixed-rule modules use deterministic geometric logic. They may be audited and tested but are not trainable unless a future contract changes their status.

Examples:

```text
C1.0
C1.1
U1.1
L1.0
L1.2
G1.0 base resolver
D1.0
```

### Calibrable

Calibrable modules may tune thresholds, hysteresis, weights, or decision cutoffs using traceable datasets.

Current calibrable modules:

```text
U1.1-CAL
L1.1
L1.2-CAL
```

### Trainable

Trainable modules may learn a small explicit model from traceable features.

Current trainable module:

```text
G1.0-CAL V1
```

### Fusion/Orchestrator

Fusion/orchestrator modules combine module outputs and should not become black-box learners.

Current fusion/orchestrator modules:

```text
unit full model
X2.0
X3.0
```

X3.0 is trainable-aware because it consumes active trainable/calibrable module
outputs and writes trainable influence maps. It is not trainable as a monolith.

## Runtime Ban

No runtime module may consume:

```text
dataset truth labels
manual sample-specific coordinates
OCR/clinical semantics
post-hoc visual decisions as hidden input
```

## Training Data Boundary

Datasets may exist for training, calibration, and audit only. They must remain outside the normal runtime repo unless explicitly approved as tiny smoke fixtures.

Datasets must preserve traceability:

```text
sample_id
x, y
component_id where applicable
family_candidate_id where applicable
source map/source bit
label provenance
```

## Runtime Assets

A trained/calibrated module may ship only small, readable runtime assets:

```text
model_config.json
feature_scaler.json
coefficients.csv
calibrated_thresholds.json
```

Opaque model blobs are rejected unless a future contract explicitly allows them and preserves auditability.

## Acceptance Checklist

A module can be marked trainable only when all are true:

```text
training contract exists
features are traceable
labels are dataset-only
evaluation exists
runtime does not use truth labels
saved model assets are readable
decision output preserves pixel/component/family traceability
visual audit output exists
```

A module can be marked calibrable only when all are true:

```text
calibration parameters are explicit
calibration does not create geometry
runtime parameters are readable
before/after audit exists
traceability does not decrease
```

## Rejection Criteria

Reject any training/calibration if it:

```text
improves apparent accuracy by hiding provenance
uses truth labels at runtime
collapses component/family identity
creates final geometry prematurely
modifies frozen V3.4.2
turns X2.0 or X3.0 into an untraceable black box
```
