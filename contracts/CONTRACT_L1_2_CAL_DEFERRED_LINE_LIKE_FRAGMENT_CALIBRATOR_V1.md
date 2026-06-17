# CONTRACT L1.2-CAL - DEFERRED LINE-LIKE FRAGMENT CALIBRATOR V1

Version: `MODULE_L1_2_CAL_V1_DEFERRED_LINE_LIKE_FRAGMENT_CALIBRATOR`

Date: 2026-06-14

## 1. Purpose

L1.2-CAL calibrates L1.2 specifically for deferred support that is visually and
geometrically line-like, but was not promoted because width or local stability
was unreliable.

L1.2-CAL exists because L1.2 is deliberately conservative. In `test3_3`, a
substantial part of `kept_deferred` still has strong line context:

```text
line_like_potential
line_like_but_width_unstable
moderate_line_context
```

L1.2-CAL answers only:

```text
Given support that L1.2 kept as deferred, can a high-confidence line-like
fragment be promoted to probable_line_domain even when width stability is not
reliable?
```

L1.2-CAL must not answer:

```text
What is the final line?
What text, digit, symbol, axis, table, row, column, or cell is this?
What geometry should be created, bridged, inferred, or repaired?
```

Core principle:

```text
Unreliable width is not by itself negative evidence.
Unreliable width is not by itself positive evidence.
Promotion requires stronger external line context.
```

## 2. Non-Negotiable Rule

```text
No module may gain interpretation by losing geometric traceability.
```

Every L1.2-CAL promotion must preserve:

```text
x
y
source_l1_2_resolved_domain_region_id
source_l1_1_calibrated_domain_region_id
source_l1_0_domain_region_id
source_u1_1_region_id
source_geometry_object_id
source_l1_2_domain_class
source_l1_2_deferred_subclass
calibrated_l1_2_cal_domain_class
calibration_reason
calibration_confidence
```

L1.2-CAL may promote only traceable observed support. It must not create,
delete, hide, collapse, or overwrite upstream trace.

## 3. Pipeline Position

Required conceptual order:

```text
B1 V3.3 geometry extraction
-> B1 V3.4.2 residual evidence stratification
-> C1.0 individual residual hypothesis validation
-> C1.1 collective residual hypothesis validation
-> U1.0 clean-grid geometry purity gate
-> U1.1 subobject clean-grid geometry purity gate
-> L1.0 observed support domain stratifier
-> L1.1 observed support domain calibration layer
-> L1.2 deferred domain subsupport resolver
-> L1.2-CAL deferred line-like fragment calibrator
-> later C2.0 negative gap hypothesis over calibrated line-study support, if any
-> later T1.0 text/digit module over calibrated future-module pool, if any
-> later S1.0 symbol/mark module over calibrated future-module pool, if any
```

L1.2-CAL is not a final line extractor.

L1.2-CAL is not a line recovery module.

L1.2-CAL is not a semantic recognizer.

L1.2-CAL is not allowed to eliminate all deferred support.

## 4. Fundamental Ontology

### 4.1 Observed Support

L1.2-CAL operates only on observed support already present in L1.2 outputs.

It must not synthesize pixels, spans, gaps, crossings, axes, lines, cells, or
tables.

### 4.2 Candidate Source Support

The only support L1.2-CAL may change is:

```text
L1.2 resolved_deferred_domain_support_map
```

All non-deferred L1.2 support must be preserved.

### 4.3 New Diagnostic Subclass

L1.2-CAL may add this diagnostic subclass:

```text
deferred_line_like_width_unstable_candidate
```

Meaning:

```text
observed support with strong external line context and colinearity, where local
width stability is unreliable or low, but no strong microstructure/diagnostic
evidence contradicts line-study use.
```

This is not a final line label.

### 4.4 Calibrated Domain

L1.2-CAL may emit only the same domain classes as L1.0/L1.1/L1.2:

```text
line_domain
probable_line_domain
non_line_domain
probable_non_line_domain
mixed_domain
deferred_domain
```

Allowed change:

```text
deferred_domain -> probable_line_domain
```

Forbidden changes:

```text
deferred_domain -> line_domain
non-deferred support -> any other class
mixed_domain -> line_domain
mixed_domain -> probable_line_domain
non_line_domain -> line_domain
probable_non_line_domain -> line_domain
```

## 5. Required Inputs

Required L1.2 files:

```text
summary.json
contract_audit.json
l1_2_deferred_subclasses.csv
l1_2_resolved_domain_regions.csv
l1_2_resolved_domain_memberships.csv
l1_2_deferred_resolutions.csv
l1_2_domain_validation.csv
l1_2_resolved_line_study_support.csv
l1_2_resolved_future_module_pool.csv
maps/resolved_line_domain_support_map.npy
maps/resolved_probable_line_domain_support_map.npy
maps/resolved_non_line_domain_support_map.npy
maps/resolved_probable_non_line_domain_support_map.npy
maps/resolved_mixed_domain_support_map.npy
maps/resolved_deferred_domain_support_map.npy
maps/resolved_line_study_support_map.npy
maps/resolved_future_module_pool_map.npy
maps/l1_2_resolved_domain_region_id_map.npy
maps/l1_2_resolved_domain_class_map.npy
maps/l1_2_deferred_subclass_map.npy
maps/l1_2_resolution_kind_map.npy
maps/l1_2_resolution_confidence_map.npy
```

Required L1.1 files:

```text
summary.json
l1_1_calibrated_domain_regions.csv
l1_1_calibrated_domain_memberships.csv
maps/l1_1_calibrated_domain_region_id_map.npy
maps/l1_1_calibrated_domain_class_map.npy
maps/calibrated_line_study_support_map.npy
```

Required L1.0 files:

```text
summary.json
l1_0_domain_regions.csv
l1_0_domain_memberships.csv
maps/l1_0_domain_region_id_map.npy
maps/l1_0_domain_class_map.npy
```

Required U1.1 files:

```text
summary.json
u1_1_subobject_regions.csv
u1_1_subobject_memberships.csv
maps/u1_1_subobject_region_id_map.npy
maps/refined_unified_valid_observed_support_map.npy
```

Required V3.3 context files:

```text
summary.json
geometry_objects.csv
pixel_geometry_memberships.csv
maps/combined_geometry_support_count_map.npy
```

Required optional-context files when available:

```text
V3.4.2 maps/diagnostic_residual_support_count_map.npy
C1.0 maps/rejected_residual_support_map.npy
C1.1 maps/collective_blocking_evidence_map.npy
U1.0 summary.json
```

GRID_AUDIT truth, if used, may be used only for benchmark/audit metrics. It
must not be used as runtime input.

## 6. Required Outputs

L1.2-CAL must write:

```text
l1_2_cal_calibrated_domain_regions.csv
l1_2_cal_calibrated_domain_memberships.csv
l1_2_cal_width_unstable_candidates.csv
l1_2_cal_promoted_to_line.csv
l1_2_cal_kept_deferred.csv
l1_2_cal_domain_validation.csv
l1_2_cal_line_study_support.csv
l1_2_cal_future_module_pool.csv
summary.json
contract_audit.json
```

Required maps:

```text
maps/width_unstable_line_like_candidate_map.npy
maps/width_unstable_promoted_to_line_map.npy
maps/width_unstable_kept_deferred_map.npy
maps/calibrated_line_domain_support_map.npy
maps/calibrated_probable_line_domain_support_map.npy
maps/calibrated_non_line_domain_support_map.npy
maps/calibrated_probable_non_line_domain_support_map.npy
maps/calibrated_mixed_domain_support_map.npy
maps/calibrated_deferred_domain_support_map.npy
maps/calibrated_line_study_support_map.npy
maps/calibrated_future_module_pool_map.npy
maps/l1_2_cal_domain_region_id_map.npy
maps/l1_2_cal_domain_class_map.npy
maps/l1_2_cal_calibration_kind_map.npy
maps/l1_2_cal_calibration_confidence_map.npy
```

Required visuals:

```text
visuals/01_l1_2_input_domains.png
visuals/02_width_unstable_line_like_candidates.png
visuals/03_promoted_to_line.png
visuals/04_kept_deferred_after_calibration.png
visuals/05_calibrated_line_study_support.png
visuals/06_calibrated_future_module_pool.png
visuals/07_l1_2_vs_l1_2_cal_comparison.png
visuals/08_l1_2_cal_audit_summary.png
```

## 7. Required CSV Schemas

### 7.1 `l1_2_cal_calibrated_domain_regions.csv`

Required fields:

```text
calibrated_region_id
source_l1_2_resolved_domain_region_id
source_l1_1_calibrated_domain_region_id
source_l1_0_domain_region_id
source_u1_1_region_id
source_geometry_object_id
source_l1_2_domain_class
source_l1_2_deferred_subclass
calibrated_l1_2_cal_domain_class
calibration_subclass
calibration_kind
calibration_confidence
excluded_from_calibrated_line_study
available_for_future_modules
region_pixel_count
orientation
line_context_score
colinearity_score
width_stability_score
width_reliability_score
microstructure_score
mixed_contact_score
diagnostic_contact_score
blocking_contact_score
external_line_context_score
calibration_reason
```

### 7.2 `l1_2_cal_calibrated_domain_memberships.csv`

Required fields:

```text
calibrated_region_id
source_l1_2_resolved_domain_region_id
source_l1_1_calibrated_domain_region_id
source_l1_0_domain_region_id
source_u1_1_region_id
source_geometry_object_id
x
y
source_l1_2_domain_class
source_l1_2_deferred_subclass
calibrated_l1_2_cal_domain_class
calibration_subclass
calibration_kind
calibration_confidence
excluded_from_calibrated_line_study
available_for_future_modules
membership_weight
```

### 7.3 `l1_2_cal_width_unstable_candidates.csv`

Required fields:

```text
candidate_id
calibrated_region_id
source_l1_2_resolved_domain_region_id
source_l1_2_deferred_subclass
candidate_pixel_count
line_context_score
colinearity_score
width_stability_score
width_reliability_score
microstructure_score
mixed_contact_score
diagnostic_contact_score
blocking_contact_score
external_line_context_score
candidate_reason
```

### 7.4 `l1_2_cal_domain_validation.csv`

Required fields:

```text
calibrated_region_id
source_l1_2_resolved_domain_region_id
source_l1_2_domain_class
source_l1_2_deferred_subclass
calibrated_l1_2_cal_domain_class
changed_support_subset_of_l1_2_deferred_support
non_deferred_support_preserved
line_domain_not_created_from_deferred
calibrated_line_study_excludes_non_line_mixed_deferred
calibrated_future_pool_preserves_non_line_mixed_deferred
calibration_preserves_source_traceability
no_semantic_recognition_used
does_not_create_geometry
does_not_delete_support
does_not_modify_upstream
validation_reason
rejection_or_deferral_reason
```

## 8. Runtime Feature Families

L1.2-CAL may use only traceable geometric/domain features.

Allowed features:

```text
source_l1_2_domain_class
source_l1_2_deferred_subclass
source_l1_2_resolution_confidence
source_l1_1_domain_class
source_l1_0_domain_class
region_pixel_count
bounding_box_width
bounding_box_height
orientation_stability_score
longitudinal_run_length
longitudinal_continuity_score
width_stability_score
width_reliability_score
parallel_family_score
grid_context_score
neighbor_line_support_score
fragment_colinearity_score
local_line_study_neighbor_ratio
external_line_context_score
microstructure_score
compact_mark_score
curvature_or_complexity_score
mixed_contact_score
diagnostic_residual_contact_score
blocking_residual_contact_score
local_connectivity_score
```

Forbidden runtime features:

```text
OCR text recognition
digit recognition as semantic value
clinical symbol recognition
human-readable label meaning
GRID_AUDIT truth labels
untraceable neural embeddings as sole decision source
sample-specific manual coordinates
final line-object identity
```

## 9. Candidate Rule

Support may be labeled:

```text
deferred_line_like_width_unstable_candidate
```

only when:

```text
source_l1_2_domain_class is deferred_domain
support is traceable observed support
line_context_score is very high
fragment_colinearity_score is very high
external_line_context_score is high
microstructure_score is low or moderate-low
mixed_contact_score is not high
diagnostic/blocking contact is low
width_stability_score is low OR width_reliability_score is low
```

This subclass must not be assigned when:

```text
microstructure_score is high
mixed_contact_score is high
diagnostic/blocking contact is high
support is not traceable to L1.2 deferred support
```

## 10. Promotion Rule

L1.2-CAL may move:

```text
deferred_domain -> probable_line_domain
```

only when:

```text
calibration_subclass is deferred_line_like_width_unstable_candidate
support is traceable L1.2 deferred support
line_context_score >= strict threshold
fragment_colinearity_score >= strict threshold
external_line_context_score >= strict threshold
microstructure_score <= safe threshold
mixed_contact_score <= safe threshold
diagnostic/blocking contact <= safe threshold
```

L1.2-CAL must not move source deferred support directly to:

```text
line_domain
```

Default target:

```text
probable_line_domain
```

## 11. Keep Deferred Rule

L1.2-CAL must keep support as:

```text
deferred_domain
```

when:

```text
candidate thresholds are not met
microstructure or mixed evidence is strong
diagnostic/blocking contact is strong
classification would require semantic interpretation
classification would require creating or repairing geometry
```

## 12. Calibrated Line-Study Support Policy

The calibrated line-study support map may include:

```text
line_domain
probable_line_domain
```

It must not include:

```text
non_line_domain
probable_non_line_domain
mixed_domain
deferred_domain
inferred spans
diagnostic residual
ambiguous residual
GRID_AUDIT truth labels
```

Calibrated line-study support is not final geometry.

## 13. Calibrated Future Module Pool Policy

The calibrated future-module pool must include:

```text
non_line_domain
probable_non_line_domain
mixed_domain
deferred_domain
```

Every future-pool pixel must preserve:

```text
x
y
source_l1_2_resolved_domain_region_id
source_l1_1_calibrated_domain_region_id
source_l1_0_domain_region_id
source_u1_1_region_id
source_geometry_object_id
source_l1_2_deferred_subclass
calibrated_l1_2_cal_domain_class
available_for_future_modules
excluded_from_calibrated_line_study
```

## 14. Metrics

Required summary metrics:

```text
l1_2_deferred_pixels_seen
width_unstable_line_like_candidate_pixels
width_unstable_promoted_to_line_pixels
width_unstable_kept_deferred_pixels
calibrated_line_study_support_pixels
calibrated_future_module_pool_pixels
line_study_delta_ratio_vs_l1_2
deferred_reduction_ratio_vs_l1_2
future_pool_traceability_rate
calibration_traceability_rate
```

Optional benchmark metrics when truth exists:

```text
width_unstable_promotion_precision
line_contamination_delta
future_pool_non_line_recall
```

## 15. Invariants

Mandatory invariants:

```text
all changed support subset_of L1.2 deferred support
all unchanged non-deferred L1.2 support preserved
calibrated_line_domain_support equals L1.2 line_domain support
calibrated_probable_line_domain_support subset_of L1.2 observed support
calibrated_non_line_domain_support equals L1.2 non_line_domain support
calibrated_probable_non_line_domain_support equals L1.2 probable_non_line_domain support
calibrated_mixed_domain_support equals L1.2 mixed_domain support
calibrated_deferred_domain_support subset_of L1.2 observed support
all L1.2-CAL domain maps are mutually exclusive
calibrated_line_study_support excludes non_line/probable_non_line/mixed/deferred
calibrated_future_module_pool includes non_line/probable_non_line/mixed/deferred
calibrated_future_module_pool preserves traceability
all calibrations preserve source L1.2 class
all calibrations preserve source L1.1 region id when available
all calibrations preserve source L1.0 region id when available
all calibrations preserve source U1.1 region id when available
all calibrations preserve source geometry object id when available
promoted support remains traceable to L1.2 deferred support
kept deferred support is not silently counted as clean line
inferred spans are not converted to observed support
diagnostic residual is not converted to line-study support
ambiguous residual is not converted to line-study support
does not create geometry
does not create final LineObjects
does not create AxisDescriptors
does not create crossings
does not modify V3.3 outputs
does not modify V3.4.2 outputs
does not modify C1.0 outputs
does not modify C1.1 outputs
does not modify U1.0 outputs
does not modify U1.1 outputs
does not modify L1.0 outputs
does not modify L1.1 outputs
does not modify L1.2 outputs
```

If any invariant fails, status must be:

```text
failed_contract
```

## 16. Visualization Rules

Required colors:

```text
green = calibrated line-study support
yellow = width_unstable_promoted_to_line
light yellow = width_unstable_line_like_candidate
gray = width_unstable_kept_deferred
magenta = calibrated future-module pool
black = L1.2 deferred input support
```

Visuals must clearly separate:

```text
L1.2 input domains
width-unstable line-like candidates
promotions to line-study
kept deferred support
calibrated line-study support
calibrated future-module pool
```

No visual may imply that deferred support was deleted.

No visual may imply that calibrated line-study support is final geometry.

## 17. Prohibitions

L1.2-CAL must not create or declare:

```text
final LineObjects
final text
recognized OCR strings
recognized digit values
clinical labels
AxisDescriptors
crossings
crossing graphs
axis families as final geometry
topology graphs
grids
tables
rows
columns
cells
coordinate systems
final virtualization
```

L1.2-CAL must not:

```text
erase deferred support
hide deferred support
force deferred support into a non-deferred class
use OCR or semantic recognition as runtime evidence
use GRID_AUDIT truth as runtime evidence
repair gaps
bridge gaps
convert inferred spans into observed support
promote deferred support to line-study without strict traceable geometric evidence
optimize visual appearance by losing source memberships
```

## 18. Acceptance Criteria

L1.2-CAL is accepted only if:

```text
all invariants true
required outputs complete
only L1.2 deferred support changes class
non-deferred L1.2 support is preserved
promoted support is visibly line-like and not visibly text/mixed dominant
calibrated line-study support is not visibly more contaminated than L1.2
future-module pool preserves excluded non-line/deferred/mixed support
membership traceability is complete
calibration audit is complete
```

Target direction for `test3_3`, without making it a hard contract:

```text
rescue part of the 4432 px line_like_potential kept deferred by L1.2
initial promotion target may be about 800-2000 px
do not promote line_like_but_microstructured support wholesale
future_pool_traceability must remain 100%
```

Quantitative acceptance targets must be dataset-specific. In absence of a
line-domain ground truth dataset, visual audit is mandatory.

## 19. Contract Verdict

L1.2-CAL is valid only if it is a conservative calibrator over L1.2 deferred
support.

It becomes invalid if it converts:

```text
width-unstable candidate -> final geometry
deferred support -> deleted support
candidate subclass -> semantic recognition
probable_line_domain -> final LineObject
mixed support -> silently accepted clean line
truth labels -> runtime decision
```

Final rule:

```text
L1.2-CAL may promote a strict subset of L1.2 deferred observed support.
L1.2-CAL may not promote non-deferred support.
L1.2-CAL may not remove unresolved support from the modular evidence system.
L1.2-CAL may not call calibrated line-study support final geometry.
```
