# CONTRACT X2.0 - Geometric Evidence Fusion Single Script

Version: `MODULE_X2_0_GEOMETRIC_EVIDENCE_FUSION_SINGLE_SCRIPT`

Date: 2026-06-16

## Purpose

X2.0 replaces the X1.0 operational wrapper idea with a true single-script fusion step.

It does not extract embedded modules and does not call subprocesses. It consumes existing upstream evidence maps and performs one integrated geometric decision that includes deferred simple-line evidence.

## Critical Rule

```text
No module may gain interpretation by losing geometric traceability.
```

## Inputs

Required upstream evidence directories:

```text
--u1-1-dir
--l1-0-dir
--l1-1-dir
--l1-2-dir
--l1-2-cal-dir
--g1-0-dir
--g1-0-cal-v1-dir
```

X2.0 may use U1.1 as purity/traceability evidence, but it must not expand the observed-support universe beyond the L1 observed-domain support.

## Fusion Logic

X2.0 must:

```text
load all required maps directly
verify all input maps have the same shape
derive observed support from L1.0 observed-domain maps
derive core line-study support from G1.0-CAL V1
derive future/non-line pool from G1.0-CAL V1
scan remaining deferred support internally for simple horizontal/vertical lineality
classify D1 lineality internally into tentative roles
add only D1 grid-line candidates to line-study support
reserve D1 text/border/curve/ambiguous candidates for future/non-line pool
write source-bit traceability maps
write visual audit maps
```

## Forbidden

X2.0 must not:

```text
modify V3.4.1
modify V3.4.2
modify upstream outputs
call external module scripts
extract embedded modules
include datasets or historical result folders
create final virtualized geometry
create final line objects, tables, cells, OCR, or clinical semantics
allow U1.1 to create new observed support
promote D1 observed-line evidence without source traceability
```

## Invariants

```text
all_input_maps_same_shape == true
fused_line_subset_of_observed == true
fused_future_subset_of_observed == true
fused_line_and_future_disjoint == true
d1_candidate_subset_of_deferred == true
d1_grid_candidate_subset_of_d1_candidate == true
source_trace_for_all_fused_line_pixels == true
u1_1_valid_and_excluded_disjoint == true
does_not_create_final_geometry == true
does_not_modify_upstream_outputs == true
```

## Acceptance On Current Tests

`test3.3`:

```text
observed_support_pixels: 33090
core_line_study_support_pixels: 20940
d1_grid_line_added_pixels: 112
fused_line_study_support_pixels: 21052
fused_future_module_pool_pixels: 11308
unaccounted_observed_support_pixels: 730
all invariants: true
```

`test3.2`:

```text
observed_support_pixels: 24388
core_line_study_support_pixels: 20631
d1_grid_line_added_pixels: 9
fused_line_study_support_pixels: 20640
fused_future_module_pool_pixels: 3604
unaccounted_observed_support_pixels: 144
all invariants: true
```

## Status

X2.0 is experimental. It is a true single-script fusion module, not a runtime bundle.

It remains conservative: D1 evidence can enrich line-study support, but cannot become final virtualized geometry.
