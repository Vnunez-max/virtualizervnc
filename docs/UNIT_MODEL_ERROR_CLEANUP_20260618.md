# Unit Model Error Cleanup

Status: applied
Date: 2026-06-18

## Scope

This cleanup keeps the current unit model architecture intact and removes
operational errors from the promoted runtime surface.

No geometric logic was redesigned.

No V3.4.1 or V3.4.2 logic was modified.

## Fixed Errors

### Test-specific entrypoint names

The promoted runtime had two general-purpose entrypoints whose filenames still
referred to `test3_3`.

Renamed:

```text
modules/g1/module_g1_0_cal_v1_apply_trainable_calibrator_to_test3_3_unit.py
  -> modules/g1/module_g1_0_cal_v1_apply_trainable_calibrator.py

modules/unit/module_unit_full_model_v1_apply_to_test3_3.py
  -> modules/unit/module_unit_full_model_v1_apply.py
```

### Historical default paths

Some runtime scripts contained default paths to historical `test3_3` output
folders. D1.0 and D1.1 also pointed to an older unit output directory name.

The affected scripts now require explicit input/output paths:

```text
modules/unit/module_unit_full_model_v1_apply.py
modules/d1/module_d1_0_deferred_simple_linearity_auditor.py
modules/d1/module_d1_1_deferred_linear_role_classifier.py
```

### Fixed sample label in visual output

G1.0-CAL V1 had a visual title that still said `test3.3`. The title now uses
the provided `sample_id`.

### VM documentation paths

VM usage docs pointed to flat `modules/module_*.py` paths that do not match
the promoted module directory structure. The docs now point to the actual
family directories.

### VM manifest drift

The VM manifest had stale module/contract counts and stated that V3.4.2 was
excluded. The manifest now reflects the promoted package:

```text
modules: 15
contracts: 15
docs: 8
```

V3.4.2 may be present as a frozen upstream module. V3.4.2 modifications remain
forbidden.

## Verifier Upgrade

`tools/verify_vm_runtime.py` now checks:

```text
all expected modules compile
G1.0-CAL V1 runtime model assets are readable
no datasets/samples/historical outputs are packaged
current docs do not reference obsolete test-specific entrypoints
MANIFEST_VM_RUNTIME counts match actual files
```

## Smoke Result

The cleaned runtime surface was smoke-tested on local `test3.3` inputs with
outputs written outside the repository:

```text
/tmp/virtualizervnc-cleanup-smoke-r2/test3_3
```

Observed smoke metrics:

```text
G1.0-CAL V1:
  association_count: 613
  cal_v1_promoted_pixels: 2705
  line_study_delta_pixels: 399
  invariants_pass: true

UNIT:
  final_line_study_support_pixels: 20940
  final_future_module_pool_pixels: 11420
  observed_support_pixels: 33090
  accounted_ratio_of_observed: 0.9779389543668782
  invariants_pass: true

D1.0:
  input_deferred_pixels: 1885
  simple_linearity_candidate_pixels: 1041
  accepted_hypothesis_count: 51
  invariants_pass: true

D1.1:
  d1_0_candidate_pixels: 1041
  grid_line_candidate_pixels: 518
  page_border_or_layout_box_pixels: 138
  text_or_digit_stroke_pixels: 58
  curve_or_data_trace_pixels: 327
  invariants_pass: true
```

## Boundary

This cleanup fixes operational/runtime hygiene. It does not claim that all
visual or algorithmic errors are solved.

Remaining visual/model errors should be handled as separate audited changes,
with the same rule:

```text
No module may gain interpretation by losing geometric traceability.
```
