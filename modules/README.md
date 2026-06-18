# Modules

This directory stores the clean, versioned module surface of the current
Geometric Evidence Unit inside the larger synergic geometric virtualizer.

These modules organize observed mask support into traceable geometric evidence
domains. They are not the complete virtualizer and do not construct final
tables, cells, OCR, symbols, page semantics, or virtualized output objects.

The modules are organized by family:

```text
v3_4_2/  frozen residual evidence stratifier
c1/      residual evidence hypothesis validators
u1/      geometric purity gates and calibration
l1/      observed support stratification and deferred resolution
g1/      deferred line-family association and calibration
d1/      complementary deferred simple-line analysis
unit/    unit-level orchestrator entrypoints
x3/      trainable-aware complete evidence-unit fusion
```

The experimental X2.0 single-script fusion layer is also kept at:

```text
modules/module_x2_0_geometric_evidence_fusion_single_script.py
```

The X3.0 trainable-aware evidence unit is kept at:

```text
modules/x3/module_x3_0_trainable_geometric_evidence_unit.py
```

Active trainable/calibration entrypoints are:

```text
modules/g1/module_g1_0_cal_v1_apply_trainable_calibrator.py
modules/c1/module_c1_cal_v1_apply_residual_hypothesis_calibrator.py
modules/d1/module_d1_cal_v1_apply_deferred_linear_role_calibrator.py
```

Dataset/training generators are included as code, but generated datasets and
training outputs remain outside GitHub unless promoted as small readable model
assets.

Critical rule:

```text
No module may gain interpretation by losing geometric traceability.
```

This repository intentionally excludes datasets, generated outputs, images,
large masks and historical experiment folders.
