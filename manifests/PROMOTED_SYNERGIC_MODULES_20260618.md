# Promoted Synergic Modules - 2026-06-18

## Purpose

This manifest records the clean promotion of the synergic module chain into
GitHub. It does not include datasets, generated results, images, masks or
historical output folders.

## Promoted Chain

```text
V3.4.2 -> C1.x -> U1.x -> L1.x -> G1.x -> D1.x -> X2.0
```

## Promoted Code

### V3.4.2

- `modules/v3_4_2/module_b1_v3_4_2_residual_evidence_stratifier.py`

### C1.x

- `modules/c1/module_c1_0_residual_evidence_geometry_hypothesis_validator.py`
- `modules/c1/module_c1_1_collective_residual_evidence_hypothesis_validator.py`

### U1.x

- `modules/u1/module_u1_1_subobject_clean_grid_geometry_purity_gate.py`
- `modules/u1/module_u1_1_cal_geometric_hysteresis_calibrator.py`

### L1.x

- `modules/l1/module_l1_0_observed_support_domain_stratifier.py`
- `modules/l1/module_l1_1_observed_support_domain_calibration_layer.py`
- `modules/l1/module_l1_2_deferred_domain_subsupport_resolver.py`
- `modules/l1/module_l1_2_cal_deferred_line_like_fragment_calibrator.py`

### G1.x

- `modules/g1/module_g1_0_deferred_line_family_resolver.py`
- `modules/g1/module_g1_0_cal_v1_apply_trainable_calibrator.py`

### D1.x

- `modules/d1/module_d1_0_deferred_simple_linearity_auditor.py`
- `modules/d1/module_d1_1_deferred_linear_role_classifier.py`

### Unit

- `modules/unit/module_unit_full_model_v1_apply.py`

### X2.0

- `modules/module_x2_0_geometric_evidence_fusion_single_script.py`

### X3.0

- `modules/x3/module_x3_0_trainable_geometric_evidence_unit.py`

## Promoted Contracts And Accessories

- V3.4.2 contract under `contracts/v3_4_2/`
- C1 contracts under `contracts/c1/`
- U1/L1/G1/D1 contracts under `contracts/`
- G1.0-CAL small runtime model under `models/g1_0_cal_v1_deferred_family/`
- VM runtime verifier under `tools/verify_vm_runtime.py`
- VM runtime manifest under `manifests/MANIFEST_VM_RUNTIME.json`

## Exclusions

The following remain outside GitHub:

```text
datasets/
outputs/
results/
visuals/
*.npy
*.npz
*.png
*.jpg
*.zip
```

## Traceability Rule

```text
No module may gain interpretation by losing geometric traceability.
```
