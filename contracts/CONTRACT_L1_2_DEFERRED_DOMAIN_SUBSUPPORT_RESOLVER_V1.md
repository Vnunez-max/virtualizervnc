# CONTRACT L1.2 - DEFERRED DOMAIN SUBSUPPORT RESOLVER V1

Version: `MODULE_L1_2_V1_DEFERRED_DOMAIN_SUBSUPPORT_RESOLVER`

Date: 2026-06-14

## 1. Purpose

L1.2 resolves part of the `deferred_domain` produced by L1.1.

L1.2 exists because `deferred_domain` is not a single visual or geometric
phenomenon. It may contain:

```text
line-like observed support that is still too weak for L1.1 promotion
mixed support where line-like and non-line-like evidence touch
probable non-line support without enough confidence
tiny evidence with too few pixels
true unknown support
```

L1.2 answers only:

```text
Given observed support still marked as deferred after L1.1, can any part of
that support be assigned to a more specific functional domain without losing
traceability?
```

L1.2 must not answer:

```text
What is the final line?
What text, number, symbol, axis, table, row, column, or cell is this?
What geometry should be created, repaired, or inferred?
```

Core principle:

```text
Explaining deferred is allowed.
Forcing deferred to disappear is not allowed.
```

## 2. Non-Negotiable Rule

```text
No module may gain interpretation by losing geometric traceability.
```

Every L1.2 resolution must preserve:

```text
x
y
source_l1_1_calibrated_domain_region_id
source_l1_0_domain_region_id
source_u1_1_region_id
source_geometry_object_id
source_l1_1_domain_class
resolved_l1_2_domain_class
deferred_subclass
resolution_reason
resolution_confidence
```

L1.2 may resolve deferred support. It must not delete, hide, collapse, or
overwrite the upstream trace.

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
-> later C2.0 negative gap hypothesis over resolved line-study support, if any
-> later T1.0 text/digit module over resolved future-module pool, if any
-> later S1.0 symbol/mark module over resolved future-module pool, if any
-> later integration module, if any
```

L1.2 is not a new geometry extractor.

L1.2 is not a line recovery module.

L1.2 is not a semantic recognizer.

L1.2 is not required to eliminate all deferred support.

## 4. Fundamental Ontology

### 4.1 Observed Support

L1.2 operates only on observed support already present in L1.1 outputs.

It must not synthesize pixels, spans, gaps, crossings, axes, lines, cells, or
tables.

### 4.2 Deferred Source Support

The source support of L1.2 is:

```text
L1.1 calibrated_deferred_domain_support_map
```

L1.2 may use surrounding non-deferred L1.1 support as context, but it may only
change domain assignment for source deferred support.

### 4.3 Deferred Subclass

L1.2 must first subclass deferred support before resolving it.

Allowed `deferred_subclass` values:

```text
deferred_line_rescue_candidate
deferred_mixed_candidate
deferred_probable_non_line_candidate
deferred_tiny_low_evidence
deferred_true_unknown
```

These are diagnostic morphology/domain subclasses. They are not semantic
recognition labels.

### 4.4 Resolved Domain

L1.2 may emit only the same functional domain classes as L1.0/L1.1:

```text
line_domain
probable_line_domain
non_line_domain
probable_non_line_domain
mixed_domain
deferred_domain
```

For source deferred support, allowed resolutions are:

```text
deferred_domain -> probable_line_domain
deferred_domain -> probable_non_line_domain
deferred_domain -> mixed_domain
deferred_domain -> deferred_domain
```

L1.2 must not promote source deferred support directly to:

```text
line_domain
```

unless a future contract explicitly permits it with stronger evidence.

## 5. Required Inputs

Required L1.1 files:

```text
summary.json
contract_audit.json
l1_1_calibrated_domain_regions.csv
l1_1_calibrated_domain_memberships.csv
l1_1_domain_transitions.csv
l1_1_domain_validation.csv
l1_1_calibrated_line_study_support.csv
l1_1_calibrated_future_module_pool.csv
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

L1.2 must write:

```text
l1_2_deferred_subclasses.csv
l1_2_resolved_domain_regions.csv
l1_2_resolved_domain_memberships.csv
l1_2_deferred_resolutions.csv
l1_2_domain_validation.csv
l1_2_resolved_line_study_support.csv
l1_2_resolved_future_module_pool.csv
l1_2_promoted_from_deferred_to_line.csv
l1_2_resolved_from_deferred_to_non_line.csv
l1_2_kept_deferred.csv
summary.json
contract_audit.json
```

Required maps:

```text
maps/deferred_line_rescue_candidate_map.npy
maps/deferred_mixed_candidate_map.npy
maps/deferred_probable_non_line_candidate_map.npy
maps/deferred_tiny_low_evidence_map.npy
maps/deferred_true_unknown_map.npy
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

Required visuals:

```text
visuals/01_l1_1_deferred_input.png
visuals/02_deferred_subclasses.png
visuals/03_promoted_from_deferred_to_line.png
visuals/04_resolved_from_deferred_to_non_line.png
visuals/05_kept_deferred.png
visuals/06_resolved_line_study_support.png
visuals/07_resolved_future_module_pool.png
visuals/08_l1_1_vs_l1_2_comparison.png
visuals/09_l1_2_audit_summary.png
```

## 7. Required CSV Schemas

### 7.1 `l1_2_deferred_subclasses.csv`

Required fields:

```text
deferred_subclass_region_id
source_l1_1_calibrated_domain_region_id
source_l1_0_domain_region_id
source_u1_1_region_id
source_geometry_object_id
deferred_subclass
subclass_confidence
region_pixel_count
orientation
line_context_score
microstructure_score
mixed_contact_score
colinearity_score
width_stability_score
local_connectivity_score
subclass_reason
```

### 7.2 `l1_2_resolved_domain_regions.csv`

Required fields:

```text
resolved_domain_region_id
source_l1_1_calibrated_domain_region_id
source_l1_0_domain_region_id
source_u1_1_region_id
source_geometry_object_id
source_l1_1_domain_class
deferred_subclass
resolved_l1_2_domain_class
resolution_kind
resolution_confidence
excluded_from_resolved_line_study
available_for_future_modules
region_pixel_count
orientation
line_context_score
microstructure_score
mixed_contact_score
colinearity_score
width_stability_score
local_connectivity_score
resolution_reason
```

### 7.3 `l1_2_resolved_domain_memberships.csv`

Required fields:

```text
resolved_domain_region_id
source_l1_1_calibrated_domain_region_id
source_l1_0_domain_region_id
source_u1_1_region_id
source_geometry_object_id
x
y
source_l1_1_domain_class
deferred_subclass
resolved_l1_2_domain_class
resolution_kind
resolution_confidence
excluded_from_resolved_line_study
available_for_future_modules
membership_weight
```

### 7.4 `l1_2_deferred_resolutions.csv`

Required fields:

```text
resolution_id
resolved_domain_region_id
source_l1_1_calibrated_domain_region_id
source_l1_1_domain_class
deferred_subclass
resolved_l1_2_domain_class
resolution_kind
resolution_confidence
pixel_count
support_subset_of_l1_1_deferred_support
line_study_resolution_allowed
future_pool_resolution_allowed
resolution_reason
```

### 7.5 `l1_2_domain_validation.csv`

Required fields:

```text
resolved_domain_region_id
source_l1_1_calibrated_domain_region_id
source_l1_1_domain_class
deferred_subclass
resolved_l1_2_domain_class
support_subset_of_l1_1_observed_support
changed_support_subset_of_l1_1_deferred_support
resolved_line_study_excludes_non_line_mixed_deferred
resolved_future_pool_preserves_non_line_mixed_deferred
resolution_preserves_source_traceability
no_semantic_recognition_used
does_not_create_geometry
does_not_delete_support
does_not_modify_upstream
validation_reason
rejection_or_deferral_reason
```

## 8. Runtime Feature Families

L1.2 may use only traceable geometric/domain features.

Allowed features:

```text
source_l1_1_domain_class
source_l1_1_transition_confidence
source_l1_0_domain_class
source_u1_1_gate_state
region_pixel_count
bounding_box_width
bounding_box_height
orientation_stability_score
longitudinal_run_length
longitudinal_continuity_score
width_stability_score
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
local_connectivity_score
component_separability_score
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

## 9. Deferred Subclassification Rules

### 9.1 Deferred Line Rescue Candidate

Support may be `deferred_line_rescue_candidate` when:

```text
support is traceable L1.1 deferred support
line context is strong
colinearity with existing line-study or V3.3 support is strong
orientation is stable
width is locally stable
microstructure/non-line score is low
diagnostic/blocking contact is low
```

### 9.2 Deferred Mixed Candidate

Support must be `deferred_mixed_candidate` when:

```text
line evidence and microstructure/non-line evidence are both strong
support touches line-study and future-pool context
support contains compact marks, curves, ticks, or dense local structure near
line-like support
safe separation is not yet established
```

### 9.3 Deferred Probable Non-Line Candidate

Support may be `deferred_probable_non_line_candidate` when:

```text
microstructure/non-line evidence is strong
line context is weak
support is compact, curved, dotted, or character-like
diagnostic/blocking contact supports future-pool reservation
```

### 9.4 Deferred Tiny Low Evidence

Support must be `deferred_tiny_low_evidence` when:

```text
the observed support has too few pixels for safe domain assignment
```

### 9.5 Deferred True Unknown

Support must remain `deferred_true_unknown` when:

```text
evidence is balanced
context is insufficient
classification would require semantic interpretation
classification would require synthesized geometry
```

## 10. Resolution Rules

### 10.1 Promotion From Deferred To Line Study

L1.2 may move:

```text
deferred_domain -> probable_line_domain
```

only when:

```text
deferred_subclass is deferred_line_rescue_candidate
support is traceable L1.1 deferred support
orientation is stable
longitudinal continuity is sufficient for local fragment scale
width is locally stable
fragment is colinear with nearby line-study or V3.3 support
line family/grid/border context is present
microstructure score is low
diagnostic/blocking contact does not dominate
```

L1.2 must not move source deferred support directly to `line_domain`.

### 10.2 Resolution From Deferred To Probable Non-Line

L1.2 may move:

```text
deferred_domain -> probable_non_line_domain
```

only when:

```text
deferred_subclass is deferred_probable_non_line_candidate
microstructure/non-line evidence is strong
line context is weak or contradicted
support remains traceable and available for future modules
```

### 10.3 Resolution From Deferred To Mixed

L1.2 may move:

```text
deferred_domain -> mixed_domain
```

when:

```text
deferred_subclass is deferred_mixed_candidate
line and non-line evidence both remain strong
safe subcomponent separation is not available
```

Mixed support must not be counted as clean line-study support.

### 10.4 Kept Deferred

L1.2 must keep support as:

```text
deferred_domain
```

when:

```text
deferred_subclass is deferred_true_unknown
deferred_subclass is deferred_tiny_low_evidence
evidence is insufficient
classification would require semantic interpretation
classification would require creating or repairing geometry
```

## 11. Optional Subsupport Separation

L1.2 may split a deferred L1.1 region into multiple L1.2 resolved regions only
if the split is based on observed connected support or existing upstream
memberships.

Allowed splitting evidence:

```text
connected components within observed deferred support
existing L1.1 membership groups
existing L1.0 membership groups
existing U1.1 subobject groups
```

Forbidden splitting evidence:

```text
OCR text interpretation
semantic symbol interpretation
manual coordinate selection
inferred spans
synthetic bridge pixels
visual appearance alone without traceable support
```

If safe split is not available, the support must remain deferred or mixed.

## 12. Resolved Line-Study Support Policy

The resolved line-study support map may include:

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

Resolved line-study support is not final geometry.

It is a cleaner input pool for later line modules.

## 13. Resolved Future Module Pool Policy

The resolved future-module pool must include:

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
source_l1_1_calibrated_domain_region_id
source_l1_0_domain_region_id
source_u1_1_region_id
source_geometry_object_id
deferred_subclass
resolved_l1_2_domain_class
available_for_future_modules
excluded_from_resolved_line_study
```

## 14. Metrics

Required summary metrics:

```text
l1_1_deferred_pixels_seen
deferred_line_rescue_candidate_pixels
deferred_mixed_candidate_pixels
deferred_probable_non_line_candidate_pixels
deferred_tiny_low_evidence_pixels
deferred_true_unknown_pixels
promoted_from_deferred_to_line_pixels
resolved_from_deferred_to_non_line_pixels
resolved_from_deferred_to_mixed_pixels
kept_deferred_pixels
resolved_line_study_support_pixels
resolved_future_module_pool_pixels
deferred_reduction_ratio_vs_l1_1
line_study_delta_ratio_vs_l1_1
future_pool_traceability_rate
resolution_traceability_rate
```

Optional benchmark metrics when truth exists:

```text
deferred_line_rescue_precision
deferred_non_line_resolution_precision
line_contamination_delta
future_pool_non_line_recall
```

## 15. Invariants

Mandatory invariants:

```text
all changed support subset_of L1.1 deferred support
all unchanged non-deferred L1.1 support preserved
resolved_line_domain_support equals L1.1 line_domain support
resolved_probable_line_domain_support subset_of L1.1 observed support
resolved_non_line_domain_support subset_of L1.1 observed support
resolved_probable_non_line_domain_support subset_of L1.1 observed support
resolved_mixed_domain_support subset_of L1.1 observed support
resolved_deferred_domain_support subset_of L1.1 observed support
all L1.2 resolved domain maps are mutually exclusive
resolved_line_study_support excludes non_line/probable_non_line/mixed/deferred
resolved_future_module_pool includes non_line/probable_non_line/mixed/deferred
resolved_future_module_pool preserves traceability
all resolutions preserve source L1.1 class
all resolutions preserve source L1.0 region id when available
all resolutions preserve source U1.1 region id when available
all resolutions preserve source geometry object id when available
promoted_from_deferred support remains traceable to L1.1 deferred support
resolved_to_non_line support is not deleted
resolved_to_mixed support is not silently counted as clean line
kept_deferred support is not silently counted as clean line
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
```

If any invariant fails, status must be:

```text
failed_contract
```

## 16. Visualization Rules

Required colors:

```text
green = unchanged/resolved line-study support
yellow = promoted_from_deferred_to_line
orange = resolved_from_deferred_to_probable_non_line
purple = resolved_from_deferred_to_mixed
gray = kept_deferred
light green = deferred_line_rescue_candidate
light orange = deferred_probable_non_line_candidate
light purple = deferred_mixed_candidate
dark gray = deferred_true_unknown
black = L1.1 deferred input support
```

Visuals must clearly separate:

```text
L1.1 deferred input
deferred subclasses
promotions to line-study
resolutions to future-pool
kept deferred support
resolved line-study support
resolved future-module pool
```

No visual may imply that deferred support was deleted.

No visual may imply that resolved line-study support is final geometry.

## 17. Prohibitions

L1.2 must not create or declare:

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

L1.2 must not:

```text
erase deferred support
hide deferred support
force deferred support into a non-deferred class
use OCR or semantic recognition as runtime evidence
use GRID_AUDIT truth as runtime evidence
repair gaps
convert inferred spans into observed support
promote deferred support to line-study without traceable geometric evidence
resolve deferred support to non-line without traceable geometric evidence
optimize visual appearance by losing source memberships
```

## 18. Acceptance Criteria

L1.2 is accepted only if:

```text
all invariants true
required outputs complete
deferred subclasses are complete and traceable
resolved line-study support is not visibly more contaminated than L1.1
structural table/grid/border lines are retained or modestly improved
only high-confidence deferred line rescue candidates are promoted
mixed deferred support is not silently counted as clean line
true unknown deferred support remains available for future modules
future-module pool preserves excluded non-line/deferred/mixed support
membership traceability is complete
resolution audit is complete
```

Target direction for `test3_3`, without making it a hard contract:

```text
promote only a small high-confidence subset of deferred support first
expected initial promotion may be about 200-600 px
do not attempt to eliminate all 8305 px of L1.1 deferred support
future_pool_traceability must remain 100%
```

Quantitative acceptance targets must be dataset-specific. In absence of a
line-domain ground truth dataset, visual audit is mandatory.

## 19. Contract Verdict

L1.2 is valid only if it is a deferred-domain subsupport resolver over observed
support.

It becomes invalid if it converts:

```text
deferred resolution -> final geometry
deferred support -> deleted support
deferred subclass -> semantic recognition
probable_line_domain -> final LineObject
mixed support -> silently accepted clean line
true unknown support -> forced classification
truth labels -> runtime decision
```

Final rule:

```text
L1.2 may resolve some deferred observed support.
L1.2 may not make deferred disappear by force.
L1.2 may not remove unresolved support from the modular evidence system.
L1.2 may not call resolved line-study support final geometry.
```
