# CONTRACT L1.1 - OBSERVED SUPPORT DOMAIN CALIBRATION LAYER V1

Version: `MODULE_L1_1_V1_OBSERVED_SUPPORT_DOMAIN_CALIBRATION_LAYER`

Date: 2026-06-14

## 1. Purpose

L1.1 calibrates the domain assignment produced by L1.0.

L1.1 exists because L1.0 is intentionally conservative:

```text
some line-like observed support remains in future_pool/deferred/mixed domains
some non-line-like observed support remains in line_study support
```

L1.1 answers only:

```text
Given traceable observed support already stratified by L1.0, should any support
change functional domain for downstream line-study or future-module use?
```

L1.1 must not answer:

```text
What final line object exists?
What text does this support encode?
What digit, symbol, label, axis, table, row, column, or cell is this?
What geometry should be created or repaired?
```

Core principle:

```text
Calibration is not recovery.
Calibration is not deletion.
Calibration is not semantic recognition.
```

## 2. Non-Negotiable Rule

```text
No module may gain interpretation by losing geometric traceability.
```

Every L1.1 transition must preserve:

```text
x
y
source_u1_1_region_id
source_geometry_object_id
source_l1_0_domain_region_id
source_l1_0_domain_class
calibrated_l1_1_domain_class
transition_reason
transition_confidence
```

L1.1 may change a functional domain label. It must not erase, hide, collapse,
or overwrite the upstream trace.

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
-> later C2.0 negative gap hypothesis over calibrated line-study support, if any
-> later T1.0 text/digit module over calibrated future-module pool, if any
-> later S1.0 symbol/mark module over calibrated future-module pool, if any
-> later integration module, if any
```

L1.1 is not a new geometry extractor.

L1.1 is not a line recovery module.

L1.1 is not a semantic recognizer.

## 4. Fundamental Ontology

### 4.1 Observed Support

L1.1 operates only on observed support already present in L1.0 inputs and
outputs.

It must not synthesize pixels, spans, gaps, crossings, axes, lines, cells, or
tables.

### 4.2 Source Domain

The source domain is the L1.0 domain class assigned before calibration:

```text
line_domain
probable_line_domain
non_line_domain
probable_non_line_domain
mixed_domain
deferred_domain
```

### 4.3 Calibrated Domain

The calibrated domain is the L1.1 domain class after applying traceable
geometric/domain evidence.

L1.1 may emit only the same domain classes as L1.0:

```text
line_domain
probable_line_domain
non_line_domain
probable_non_line_domain
mixed_domain
deferred_domain
```

L1.1 must not create a new semantic class.

### 4.4 Transition

A transition is a documented change:

```text
source_l1_0_domain_class -> calibrated_l1_1_domain_class
```

Allowed transition kinds:

```text
unchanged
promoted_to_line_study
demoted_from_line_study
reserved_for_future_module
resolved_from_deferred
resolved_from_mixed
kept_deferred
kept_mixed
```

Every transition must be reversible in audit terms: the original L1.0 class
must remain present in CSV outputs.

## 5. Allowed Domain Subclasses

Optional `calibrated_domain_subclass` values:

```text
structural_line
line_fragment
border_like
grid_line_like
tick_like_structural
character_like_microstructure
digit_like_microstructure
symbol_like_microstructure
annotation_like_microstructure
tick_like_nonstructural
noise_like
shape_like
unknown_non_line
mixed_line_microstructure_contact
ambiguous_domain
```

These are morphology/domain labels only.

Prohibited subclass values:

```text
recognized_text
recognized_digit
recognized_symbol_meaning
clinical_label
table_cell
row
column
final_line
axis
crossing
```

## 6. Required Inputs

Required L1.0 files:

```text
summary.json
contract_audit.json
l1_0_domain_regions.csv
l1_0_domain_memberships.csv
l1_0_domain_validation.csv
l1_0_line_study_support.csv
l1_0_future_module_pool.csv
maps/line_domain_support_map.npy
maps/probable_line_domain_support_map.npy
maps/non_line_domain_support_map.npy
maps/probable_non_line_domain_support_map.npy
maps/mixed_domain_support_map.npy
maps/deferred_domain_support_map.npy
maps/future_module_pool_map.npy
maps/line_study_support_map.npy
maps/l1_0_domain_region_id_map.npy
maps/l1_0_domain_class_map.npy
```

Required U1.1 files:

```text
summary.json
contract_audit.json
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

## 7. Required Outputs

L1.1 must write:

```text
l1_1_calibrated_domain_regions.csv
l1_1_calibrated_domain_memberships.csv
l1_1_domain_transitions.csv
l1_1_domain_validation.csv
l1_1_calibrated_line_study_support.csv
l1_1_calibrated_future_module_pool.csv
l1_1_promoted_to_line_study.csv
l1_1_demoted_from_line_study.csv
l1_1_kept_deferred_or_mixed.csv
summary.json
contract_audit.json
```

Required maps:

```text
maps/calibrated_line_domain_support_map.npy
maps/calibrated_probable_line_domain_support_map.npy
maps/calibrated_non_line_domain_support_map.npy
maps/calibrated_probable_non_line_domain_support_map.npy
maps/calibrated_mixed_domain_support_map.npy
maps/calibrated_deferred_domain_support_map.npy
maps/calibrated_line_study_support_map.npy
maps/calibrated_future_module_pool_map.npy
maps/l1_1_calibrated_domain_region_id_map.npy
maps/l1_1_calibrated_domain_class_map.npy
maps/l1_1_transition_kind_map.npy
maps/l1_1_transition_confidence_map.npy
```

Required visuals:

```text
visuals/01_l1_0_input_domain_summary.png
visuals/02_l1_1_calibrated_domains.png
visuals/03_promoted_to_line_study.png
visuals/04_demoted_from_line_study.png
visuals/05_calibrated_line_study_support.png
visuals/06_calibrated_future_module_pool.png
visuals/07_l1_0_vs_l1_1_comparison.png
visuals/08_l1_1_audit_summary.png
```

## 8. Required CSV Schemas

### 8.1 `l1_1_calibrated_domain_regions.csv`

Required fields:

```text
calibrated_domain_region_id
source_l1_0_domain_region_id
source_u1_1_region_id
source_geometry_object_id
source_l1_0_domain_class
calibrated_l1_1_domain_class
calibrated_domain_subclass
transition_kind
transition_confidence
excluded_from_calibrated_line_study
available_for_future_modules
region_pixel_count
orientation
elongation_score
longitudinal_continuity_score
width_stability_score
parallel_family_score
grid_context_score
colinearity_score
microstructure_score
line_context_score
non_line_context_score
mixed_contact_score
transition_reason
```

### 8.2 `l1_1_calibrated_domain_memberships.csv`

Required fields:

```text
calibrated_domain_region_id
source_l1_0_domain_region_id
source_u1_1_region_id
source_geometry_object_id
x
y
source_l1_0_domain_class
calibrated_l1_1_domain_class
calibrated_domain_subclass
transition_kind
transition_confidence
excluded_from_calibrated_line_study
available_for_future_modules
membership_weight
```

### 8.3 `l1_1_domain_transitions.csv`

Required fields:

```text
transition_id
calibrated_domain_region_id
source_l1_0_domain_region_id
source_l1_0_domain_class
calibrated_l1_1_domain_class
transition_kind
transition_confidence
pixel_count
support_subset_of_l1_0_observed_support
line_study_transition_allowed
future_pool_transition_allowed
transition_reason
```

### 8.4 `l1_1_domain_validation.csv`

Required fields:

```text
calibrated_domain_region_id
source_l1_0_domain_region_id
source_l1_0_domain_class
calibrated_l1_1_domain_class
support_subset_of_l1_0_observed_support
calibrated_line_study_excludes_non_line_mixed_deferred
calibrated_future_pool_preserves_non_line_mixed_deferred
transition_preserves_source_traceability
no_semantic_recognition_used
does_not_create_geometry
does_not_delete_support
does_not_modify_upstream
validation_reason
rejection_or_deferral_reason
```

## 9. Runtime Feature Families

L1.1 may use only traceable geometric/domain features.

Allowed features:

```text
source_l1_0_domain_class
source_l1_0_domain_subclass
source_u1_1_gate_state
region_pixel_count
bounding_box_width
bounding_box_height
elongation_score
orientation_stability_score
longitudinal_run_length
longitudinal_continuity_score
width_stability_score
axis_distance_p95_px
parallel_family_score
grid_context_score
crossing_context_score
neighbor_line_support_score
fragment_colinearity_score
local_line_study_neighbor_ratio
local_future_pool_neighbor_ratio
microstructure_score
compact_mark_score
curvature_or_complexity_score
mixed_contact_score
diagnostic_residual_contact_score
blocking_residual_contact_score
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

## 10. Calibration Decision Rules

### 10.1 Unchanged Line Domain

Support should remain `line_domain` or `probable_line_domain` when:

```text
it is traceable observed support
it is already in L1.0 line-study domain
line context is strong
microstructure/non-line evidence is weak
diagnostic/blocking contact is absent or negligible
```

### 10.2 Promotion To Line Study

Support may move:

```text
probable_non_line_domain -> probable_line_domain
mixed_domain -> probable_line_domain
deferred_domain -> probable_line_domain
```

only when:

```text
support is traceable observed support
orientation is stable
longitudinal continuity is sufficient for local fragment scale
width is locally stable
fragment is colinear with nearby line-study or V3.3 support
fragment belongs to a parallel/grid/border context
microstructure score is low enough
diagnostic/blocking contact does not dominate
```

Promotion must not create `line_domain` unless evidence is strong and the
source L1.0 class was already `probable_line_domain`.

Default promotion target should be:

```text
probable_line_domain
```

### 10.3 Demotion From Line Study

Support may move:

```text
line_domain -> probable_non_line_domain
line_domain -> mixed_domain
probable_line_domain -> probable_non_line_domain
probable_line_domain -> mixed_domain
probable_line_domain -> deferred_domain
```

only when:

```text
microstructure/non-line evidence is strong
line context is weak or local only
support is compact, curved, unstable, dotted, or character-like
support contacts diagnostic/blocking evidence
support lacks family/grid/border continuity
```

Demotion must preserve support in the future-module pool.

### 10.4 Mixed Resolution

Mixed support may be resolved only if separable by observed connected
subsupport or by existing L1.0/U1.1 memberships.

Allowed:

```text
mixed_domain subset -> probable_line_domain
mixed_domain subset -> probable_non_line_domain
mixed_domain subset -> mixed_domain
```

Forbidden:

```text
semantic splitting
OCR-based splitting
manual coordinate splitting
creating new pixels to separate a mixed region
```

If safe separation is not possible, support must remain `mixed_domain`.

### 10.5 Deferred Resolution

Deferred support may be resolved when context is sufficient.

Allowed:

```text
deferred_domain -> probable_line_domain
deferred_domain -> probable_non_line_domain
deferred_domain -> mixed_domain
deferred_domain -> deferred_domain
```

Deferred support must remain deferred if:

```text
line and non-line evidence remain balanced
local context is insufficient
classification would require semantic interpretation
```

## 11. Calibrated Line-Study Support Policy

The calibrated line-study support map may include only:

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

It is a cleaner input pool for later line modules.

## 12. Calibrated Future Module Pool Policy

The calibrated future-module pool must include:

```text
non_line_domain
probable_non_line_domain
mixed_domain
deferred_domain
```

It may include line-domain support only as explicit context. If used, each row
must be flagged:

```text
future_pool_role = context_only
```

If `future_pool_role` is not implemented, line-domain support must not be
listed in the future-module pool CSV.

Every future-pool pixel must preserve:

```text
x
y
source_u1_1_region_id
source_geometry_object_id
source_l1_0_domain_region_id
source_l1_0_domain_class
calibrated_l1_1_domain_class
available_for_future_modules
excluded_from_calibrated_line_study
```

## 13. Metrics

Required summary metrics:

```text
l1_0_observed_support_pixels_seen
calibrated_line_domain_pixels
calibrated_probable_line_domain_pixels
calibrated_non_line_domain_pixels
calibrated_probable_non_line_domain_pixels
calibrated_mixed_domain_pixels
calibrated_deferred_domain_pixels
calibrated_line_study_support_pixels
calibrated_future_module_pool_pixels
promoted_to_line_study_pixels
demoted_from_line_study_pixels
kept_deferred_pixels
kept_mixed_pixels
calibrated_line_exclusion_ratio
calibrated_future_pool_traceability_rate
deferred_reduction_ratio
mixed_reduction_ratio
line_study_delta_ratio_vs_l1_0
```

Optional benchmark metrics when truth exists:

```text
line_domain_retention_rate
non_line_contamination_rate_in_calibrated_line_study
line_false_exclusion_rate
future_pool_non_line_recall
promotion_precision
demotion_precision
```

## 14. Invariants

Mandatory invariants:

```text
calibrated_line_domain_support subset_of L1.0 observed support
calibrated_probable_line_domain_support subset_of L1.0 observed support
calibrated_non_line_domain_support subset_of L1.0 observed support
calibrated_probable_non_line_domain_support subset_of L1.0 observed support
calibrated_mixed_domain_support subset_of L1.0 observed support
calibrated_deferred_domain_support subset_of L1.0 observed support
all L1.1 calibrated domain maps are mutually exclusive
calibrated_line_study_support excludes non_line/probable_non_line/mixed/deferred
calibrated_future_module_pool includes non_line/probable_non_line/mixed/deferred
calibrated_future_module_pool preserves traceability
all transitions preserve source L1.0 class
all transitions preserve source U1.1 region id when available
all transitions preserve source geometry object id when available
demoted support is not deleted
promoted support remains traceable to L1.0 observed support
mixed support is not silently counted as clean line
deferred support is not silently counted as clean line
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
```

If any invariant fails, status must be:

```text
failed_contract
```

## 15. Visualization Rules

Required colors:

```text
blue = calibrated line_domain
cyan = calibrated probable_line_domain
red = calibrated non_line_domain
orange = calibrated probable_non_line_domain
purple = calibrated mixed_domain
gray = calibrated deferred_domain
green = calibrated line-study support
magenta = calibrated future-module pool
yellow = promoted_to_line_study
dark red = demoted_from_line_study
black = L1.0 input observed support
```

Visuals must clearly separate:

```text
L1.0 input domains
L1.1 calibrated domains
promotions to line-study
demotions from line-study
calibrated line-study support
calibrated future-module pool
```

No visual may imply that non-line support was deleted.

No visual may imply that calibrated line-study support is final geometry.

## 16. Prohibitions

L1.1 must not create or declare:

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

L1.1 must not:

```text
erase non-line support
hide non-line support
use non-line classification as deletion
use OCR or semantic recognition as runtime evidence
use GRID_AUDIT truth as runtime evidence
repair gaps
convert inferred spans into observed support
promote support to line-study without traceable geometric evidence
demote support from line-study without traceable geometric evidence
optimize visual appearance by losing source memberships
```

## 17. Acceptance Criteria

L1.1 is accepted only if:

```text
all invariants true
required outputs complete
calibrated line-study support is visibly cleaner than L1.0 line-study support
structural table/grid/border lines are retained or improved
text-like/noise-like support in line-study is reduced
line-like support stranded in future_pool/deferred is reduced
future-module pool preserves excluded non-line/deferred/mixed support
membership traceability is complete
transition audit is complete
```

Target direction for `test3_3`, without making it a hard contract:

```text
line_study_support should increase from the L1.0 47.27% only if visual
contamination does not increase.
deferred_domain should decrease from the L1.0 30.17% only if each resolved
pixel has traceable evidence.
future_pool_traceability must remain 100%.
```

Quantitative acceptance targets must be dataset-specific. In absence of a
line-domain ground truth dataset, visual audit is mandatory.

## 18. Contract Verdict

L1.1 is valid only if it is a calibration layer over observed support domains.

It becomes invalid if it converts:

```text
calibration -> final geometry
non-line -> deleted support
domain class -> semantic recognition
probable_line_domain -> final LineObject
mixed support -> silently accepted clean line
deferred support -> silently accepted clean line
truth labels -> runtime decision
```

Final rule:

```text
L1.1 may change the functional domain of observed support.
L1.1 may not remove that support from the modular evidence system.
L1.1 may not call calibrated line-study support final geometry.
```
