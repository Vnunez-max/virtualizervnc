# CONTRACT D1.0 - DEFERRED SIMPLE LINEARITY AUDITOR V1

Version: `MODULE_D1_0_V1_DEFERRED_SIMPLE_LINEARITY_AUDITOR`

Date: 2026-06-14

## 1. Purpose

D1.0 is a complementary auditor for the deferred support left after the unit
model. It searches simple horizontal and vertical lineality in deferred pixels
only.

It answers:

```text
which deferred observed pixels form simple line-like alignments?
```

## 2. Non-Negotiable Rule

```text
No module may gain interpretation by losing geometric traceability.
```

D1.0 may propose line hypotheses, but every marked pixel must remain an
observed deferred pixel with traceability to:

```text
sample_id
x
y
linearity_hypothesis_id
orientation
baseline
source_deferred_map
```

## 3. Scope

Allowed:

```text
read deferred support from G1.0-CAL V1 or an equivalent unit-stage deferred map
read unit line-study/observed maps for visual context only
scan deferred pixels with simple horizontal/vertical projection criteria
write candidate maps, hypothesis tables, membership tables, metrics, and visuals
```

Forbidden:

```text
modify V3.4.1
modify V3.4.2
modify U/L/G/G1.0/G1.0-CAL outputs
create final geometry
create LineObjects
create AxisDescriptors
create crossings
create OCR or clinical semantics
fill missing gaps as accepted pixels
use manual sample-specific coordinates
use truth labels
classify non-deferred pixels as D1.0 candidates
```

## 4. Criteria

A lineality hypothesis is based only on observed deferred pixels.

Allowed simple criteria:

```text
orientation: horizontal or vertical
band radius around a candidate baseline
gap-tolerant longitudinal grouping
minimum span
minimum observed deferred pixels
minimum density or longest run
simple lineality score from span, density, run length, and pixel count
```

The module may write a corridor/hypothesis map for audit, but the accepted
candidate map must contain only original deferred pixels.

## 5. Required Outputs

```text
summary.json
contract_audit.json
d1_0_linearity_hypotheses.csv
d1_0_candidate_memberships.csv
d1_0_rejected_windows.csv
maps/input_deferred_map.npy
maps/simple_linearity_candidate_map.npy
maps/horizontal_linearity_candidate_map.npy
maps/vertical_linearity_candidate_map.npy
maps/linearity_hypothesis_id_map.npy
maps/linearity_corridor_map.npy
visuals/01_input_deferred_context.png
visuals/02_simple_linearity_candidates.png
visuals/03_linearity_corridors.png
visuals/04_d1_0_audit_summary.png
```

## 6. Acceptance

```text
candidate_subset_of_deferred == true
candidate_pixels_have_hypothesis_id == true
membership_pixels_subset_of_deferred == true
hypothesis_ids_present_for_all_memberships == true
does_not_create_final_geometry == true
does_not_modify_upstream_outputs == true
```

## 7. Interpretation

D1.0 is not a line finalizer. It is an evidence auditor that exposes visually
clear line-like deferred support with simple, traceable criteria.
