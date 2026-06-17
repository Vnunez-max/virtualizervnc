# Module Registry - Synergic Geometric Virtualizer

Status: experimental registry
Date: 2026-06-18

## Purpose

This registry organizes the modules as a cumulative geometric evidence unit, not as independent scripts.

Critical rule:

```text
No module may gain interpretation by losing geometric traceability.
```

## Global Chain

```text
V3.4.2 -> C1.x -> U1.x -> L1.x -> G1.x -> D1.x -> X2.0
```

## Module Families

| Family | Role | Main contribution | Output status |
| --- | --- | --- | --- |
| V3.4.2 | residual evidence stratifier | Separates residual evidence while preserving geometric traceability | frozen upstream |
| C1.x | residual geometry validators | Tests whether residual evidence has local or collective geometric coherence | complement |
| U1.x | purity gates | Filters support toward clean grid-compatible geometric evidence | calibration layer |
| L1.x | observed support stratification | Separates line-study, non-line/future pool, mixed and deferred support | core modular unit |
| G1.x | deferred family association | Associates deferred components with candidate line families and calibrated promotion decisions | trainable/calibrated layer |
| D1.x | deferred lineality complement | Rechecks deferred support for simple observed lineality without creating final geometry | complementary auditor |
| X2.0 | single-script fusion | Fuses upstream maps and D1 evidence into auditable line-study and future-pool support | experimental transport unit |

## Individual Modules

### V3.4.2

- Name: residual evidence stratifier.
- Status: frozen; must not be modified.
- Role: source of residual evidence after prior geometry processing.
- Traceability requirement: every interpretation must remain tied to observed pixels and source maps.

### C1.0

- Name: individual residual evidence hypothesis validator.
- Role: tests isolated residual candidates.
- Synergy: provides candidate-level context before purity and domain stratification.
- Forbidden: final line/table/cell creation.

### C1.1

- Name: collective residual evidence hypothesis validator.
- Role: examines where residual evidence acts collectively.
- Synergy: prepares residual evidence for downstream purity and stratification.
- Forbidden: replacing observed geometry with inferred geometry.

### U1.0

- Name: clean grid geometry purity gate.
- Role: validates cleaner geometric support.
- Synergy: constrains later L1/G1 decisions to cleaner evidence.

### U1.1

- Name: subobject clean grid geometry purity gate.
- Role: acts on sub-support, not whole-mask semantics.
- Synergy: improves purity before deferred resolution.

### U1.1-CAL

- Name: geometric hysteresis/calibration support.
- Role: stabilizes purity thresholds.
- Synergy: prevents brittle threshold decisions from contaminating L1/G1.

### L1.0

- Name: observed support domain stratifier.
- Role: creates first line-study/future/deferred partition.
- Synergy: defines the observed-support universe for later modules.

### L1.1

- Name: observed support domain calibration layer.
- Role: improves L1.0 domain assignments.
- Synergy: reduces accidental promotion and prepares L1.2.

### L1.2

- Name: deferred domain subsupport resolver.
- Role: resolves part of deferred support.
- Synergy: gives G1 and D1 a narrower, more meaningful deferred domain.

### L1.2-CAL

- Name: deferred line-like fragment calibrator.
- Role: calibrates line-like fragments inside deferred support.
- Synergy: reduces unresolved line support before G1/D1.

### G1.0

- Name: deferred line family resolver.
- Role: evaluates deferred component plus candidate family.
- Synergy: starts trainable family association without runtime truth labels.

### G1.0-CAL V1

- Name: trainable deferred family calibrator.
- Role: calibrates G1 decisions using deferred-only dataset evidence.
- Synergy: improves promote/keep/reserve decisions while preserving component-family traceability.

### D1.0

- Name: simple deferred lineality auditor.
- Role: checks clear horizontal/vertical observed lineality that G1/L1 may leave deferred.
- Synergy: complements G1 by applying simple reality-first line criteria.

### D1.1

- Name: deferred linear role classifier.
- Role: separates line-like deferred evidence into tentative roles.
- Synergy: prevents all linearity from being interpreted as structural line.

### X2.0

- Name: geometric evidence fusion single script.
- Role: transportable experimental fusion of upstream evidence plus D1-style deferred lineality.
- Synergy: produces fused line-study support and future-module pool, not final geometry.

## Promotion Rules

A module output can be promoted only if all are true:

```text
observed support is preserved
source map or source bit is preserved
pixel-level traceability is preserved
component/family traceability is preserved when applicable
no final virtualized geometry is created prematurely
```

## Rejection Rules

Reject or reserve output if any are true:

```text
interpretation increases while traceability decreases
runtime uses dataset truth labels
module creates final lines/tables/cells/OCR
module expands observed support without explicit contract
module modifies V3.4.1 or V3.4.2
```
