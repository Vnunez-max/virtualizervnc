# CONTRACT L1.0 - OBSERVED SUPPORT DOMAIN STRATIFIER V1

Version: `MODULE_L1_0_V1_OBSERVED_SUPPORT_DOMAIN_STRATIFIER`

Date: 2026-06-14

## 1. Purpose

L1.0 separates traceable observed support into functional domains after U1.1.

The immediate need is to protect line analysis from contamination by text,
digits, symbols, short marks, annotations, or other non-line support.

L1.0 answers only:

```text
Given traceable observed support after U1.1, which pixels/regions belong to
the line-study domain, which do not belong to the line-study domain, and which
must be deferred or marked mixed?
```

L1.0 must not answer:

```text
What does the text say?
What number is this?
What clinical symbol is this?
What is the final table/grid/cell structure?
What lines should be repaired or created?
```

Core principle:

```text
Excluding support from the line study does not remove it from the system.
```

## 2. Non-Negotiable Rule

```text
No module may gain interpretation by losing geometric traceability.
```

Every pixel classified by L1.0 must remain traceable to observed upstream
support and must remain available to future modules unless an explicit contract
prohibits it.

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
-> later C2.0 negative gap hypothesis over line domain only, if any
-> later T1.0 text/digit module over future-module pool, if any
-> later S1.0 symbol/mark module over future-module pool, if any
-> later integration module, if any
```

L1.0 is not a final line extractor and not a semantic recognizer.

## 4. Fundamental Ontology

### 4.1 Observed Support

Observed support is support that exists in upstream observed maps and
memberships.

L1.0 may classify observed support. It must not synthesize support.

### 4.2 Line-Study Domain

Line-study domain support is observed support that may be used by later modules
that study structural lines, line continuity, line gaps, families, borders, or
grids.

Line-study domain support is not final geometry.

### 4.3 Non-Line Domain

Non-line domain support is observed support that should not contaminate line
analysis but remains available for future modules.

Non-line domain support is not rejected support.

Allowed examples:

```text
text_like
digit_like
symbol_like
annotation_like
tick_like_nonstructural
noise_like
shape_like
unknown_non_line
```

These are morphology/domain labels only. They must not claim semantic meaning.

### 4.4 Mixed Domain

Mixed domain support contains line-like and non-line-like evidence that cannot
be safely separated at L1.0 granularity.

Mixed support must remain traceable and must not be silently counted as clean
line-study support.

### 4.5 Deferred Domain

Deferred domain support is traceable observed support with insufficient context
for domain assignment.

Deferred support remains available for future modules.

## 5. Allowed Domain Classes

L1.0 may emit only:

```text
line_domain
probable_line_domain
non_line_domain
probable_non_line_domain
mixed_domain
deferred_domain
```

Optional `domain_subclass` values:

```text
structural_line
line_fragment
border_like
grid_line_like
tick_like_structural
text_like
digit_like
symbol_like
annotation_like
tick_like_nonstructural
noise_like
shape_like
unknown_non_line
mixed_line_text_contact
ambiguous_domain
```

Prohibited domain classes:

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

Required U1.1 files:

```text
summary.json
contract_audit.json
u1_1_subobject_regions.csv
u1_1_subobject_memberships.csv
u1_1_subobject_validation.csv
maps/grid_consistent_subsupport_map.npy
maps/suspicious_subsupport_map.npy
maps/blocking_like_subsupport_map.npy
maps/ambiguous_subsupport_map.npy
maps/deferred_subsupport_map.npy
maps/excluded_subsupport_map.npy
maps/u1_1_subobject_region_id_map.npy
maps/u1_1_subobject_gate_state_map.npy
maps/refined_unified_valid_observed_support_map.npy
```

Required V3.3 files:

```text
summary.json
geometry_objects.csv
pixel_geometry_memberships.csv
maps/combined_geometry_support_count_map.npy
```

Required optional-context files when available:

```text
V3.4.2 summary.json
V3.4.2 maps/diagnostic_residual_support_count_map.npy
C1.0 maps/rejected_residual_support_map.npy
C1.1 maps/collective_blocking_evidence_map.npy
```

GRID_AUDIT truth, if used, may be used only for benchmark/audit metrics. It
must not be used as runtime input.

## 7. Required Outputs

L1.0 must write:

```text
l1_0_domain_regions.csv
l1_0_domain_memberships.csv
l1_0_domain_validation.csv
l1_0_line_study_support.csv
l1_0_future_module_pool.csv
l1_0_mixed_domain_regions.csv
l1_0_deferred_domain_regions.csv
summary.json
contract_audit.json
```

Required maps:

```text
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

Required visuals:

```text
visuals/01_u1_1_input_support.png
visuals/02_line_domain_support.png
visuals/03_non_line_domain_reserved_support.png
visuals/04_mixed_and_deferred_domain_support.png
visuals/05_line_study_support_clean.png
visuals/06_future_module_pool.png
visuals/07_domain_stratification_summary.png
```

## 8. Required CSV Schemas

### 8.1 `l1_0_domain_regions.csv`

Required fields:

```text
domain_region_id
source_u1_1_region_id
source_geometry_object_id
source_u1_1_gate_state
domain_class
domain_subclass
domain_confidence
excluded_from_line_study
available_for_future_modules
region_pixel_count
orientation
elongation_score
longitudinal_continuity_score
width_stability_score
parallel_family_score
grid_context_score
text_like_score
symbol_like_score
curvature_or_complexity_score
short_mark_score
mixed_contact_score
domain_reason
```

### 8.2 `l1_0_domain_memberships.csv`

Required fields:

```text
domain_region_id
source_u1_1_region_id
source_geometry_object_id
x
y
source_layer
source_u1_1_gate_state
domain_class
domain_subclass
excluded_from_line_study
available_for_future_modules
membership_weight
```

### 8.3 `l1_0_domain_validation.csv`

Required fields:

```text
domain_region_id
source_u1_1_region_id
domain_class
support_subset_of_observed_support
line_study_support_subset_of_u1_1_refined_valid_support
non_line_support_not_counted_as_line_study
future_pool_preserves_non_line_support
mixed_domain_not_silently_counted_as_clean_line
deferred_domain_not_silently_counted_as_clean_line
does_not_create_geometry
does_not_delete_support
does_not_modify_upstream
validation_reason
rejection_or_deferral_reason
```

## 9. Runtime Feature Families

L1.0 may use only traceable geometric/domain features.

Required features:

```text
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
curvature_or_complexity_score
closed_shape_score
text_like_microstructure_score
digit_like_microstructure_score
symbol_like_microstructure_score
short_mark_score
mixed_contact_score
source_u1_1_gate_state
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
```

## 10. Domain Decision Rules

### 10.1 Strong Line Domain

Support may be `line_domain` when:

```text
support is traceable observed support
source U1.1 state is grid_consistent or otherwise explicitly allowed
elongation is high
orientation is stable
longitudinal continuity is sufficient
width is locally stable
line has parallel/grid/border/crossing context OR sufficient colinearity
text_like / symbol_like / curvature scores are low
```

### 10.2 Probable Line Domain

Support may be `probable_line_domain` when:

```text
line-like evidence is present but incomplete
fragment is short but colinear with nearby line support
support is part of a grid family but locally degraded
context is enough for line study but not enough for strong line classification
```

### 10.3 Non-Line Domain

Support may be `non_line_domain` when:

```text
microstructure is character-like, digit-like, symbol-like, annotation-like,
shape-like, or noise-like
elongation is low or unstable
orientation changes frequently
support forms compact clusters, curves, loops, dots, or dense marks
support lacks line family/grid/border context
```

Non-line support must be excluded from line study and preserved in
future-module pool.

### 10.4 Probable Non-Line Domain

Support may be `probable_non_line_domain` when:

```text
non-line evidence is likely but not decisive
support is short and isolated
support resembles text/digit/symbol morphology but could be a tick or fragment
```

### 10.5 Mixed Domain

Support must be `mixed_domain` when:

```text
line and non-line evidence are physically touching
support includes both colinear line structure and character-like local clusters
separation would require semantic interpretation or destructive splitting
```

Mixed domain support must be preserved and not silently included in clean line
study support.

### 10.6 Deferred Domain

Support must be `deferred_domain` when:

```text
context is insufficient
features conflict without enough evidence
region is too small to classify safely
```

## 11. Line Study Support Policy

The line-study support map may include:

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

Line-study support is not final geometry. It is a clean input pool for later
line modules.

## 12. Future Module Pool Policy

The future-module pool must include:

```text
non_line_domain
probable_non_line_domain
mixed_domain
deferred_domain
```

It may optionally include line-domain support as context, but only if flagged
as context and not as target evidence.

Every future-pool pixel must preserve:

```text
x
y
source_u1_1_region_id
source_geometry_object_id
domain_class
domain_subclass
available_for_future_modules
excluded_from_line_study
```

## 13. Metrics

Required summary metrics:

```text
observed_support_pixels_seen
line_domain_pixels
probable_line_domain_pixels
non_line_domain_pixels
probable_non_line_domain_pixels
mixed_domain_pixels
deferred_domain_pixels
line_study_support_pixels
future_module_pool_pixels
line_exclusion_ratio
future_pool_traceability_rate
mixed_domain_ratio
deferred_domain_ratio
```

Optional benchmark metrics when truth exists:

```text
line_domain_retention_rate
non_line_contamination_rate_in_line_study
line_false_exclusion_rate
future_pool_non_line_recall
mixed_domain_precision
```

## 14. Invariants

Mandatory invariants:

```text
line_domain_support subset_of observed support
probable_line_domain_support subset_of observed support
non_line_domain_support subset_of observed support
probable_non_line_domain_support subset_of observed support
mixed_domain_support subset_of observed support
deferred_domain_support subset_of observed support
all L1.0 domain maps are mutually exclusive
line_study_support excludes non_line/probable_non_line/mixed/deferred
future_module_pool includes non_line/probable_non_line/mixed/deferred
future_module_pool preserves traceability
non_line support is not deleted
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
```

If any invariant fails, status must be:

```text
failed_contract
```

## 15. Visualization Rules

Required colors:

```text
blue = line_domain
cyan = probable_line_domain
red = non_line_domain
orange = probable_non_line_domain
purple = mixed_domain
gray = deferred_domain
green = line_study_support
magenta = future_module_pool
black = U1.1 input support
```

Visuals must clearly separate:

```text
input observed support
line-domain support
non-line support reserved for future modules
mixed/deferred support
line-study support
future-module pool
```

No visual may imply that non-line support was deleted.

## 16. Prohibitions

L1.0 must not create or declare:

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

L1.0 must not:

```text
erase non-line support
hide non-line support
use non-line classification as deletion
use OCR or semantic recognition as runtime evidence
use GRID_AUDIT truth as runtime evidence
repair gaps
convert inferred spans into observed support
```

## 17. Acceptance Criteria

L1.0 is accepted only if:

```text
all invariants true
required outputs complete
line-study support is visibly cleaner than U1.1 final support
structural table/grid/border lines are mostly retained
text-like/noise-like support is mostly moved out of line-study support
future-module pool preserves excluded non-line/deferred/mixed support
membership traceability is complete
```

Quantitative acceptance targets may be dataset-specific. In absence of a
line-domain ground truth dataset, visual audit is mandatory.

## 18. Contract Verdict

L1.0 is valid only if it is a domain stratifier over observed support.

It becomes invalid if it converts:

```text
non-line -> deleted support
domain class -> semantic recognition
line-domain support -> final LineObject
mixed support -> silently accepted clean line
deferred support -> silently accepted clean line
truth labels -> runtime decision
```

Final rule:

```text
L1.0 may exclude support from the line study.
L1.0 may not remove that support from the modular evidence system.
```
