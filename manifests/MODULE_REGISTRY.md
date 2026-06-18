# Module Registry - Synergic Geometric Virtualizer

Status: experimental registry
Date: 2026-06-18

## Purpose

This registry organizes the modules as a cumulative geometric evidence unit,
not as independent scripts.

The registered modules are a subsystem of the larger virtualizer. They form
the current `Geometric Evidence Unit`, whose job is to organize observed mask
support into traceable evidence domains. They are not the complete
virtualizer.

Critical rule:

```text
No module may gain interpretation by losing geometric traceability.
```

## Global Chain

```text
V3.4.2 -> C1.x -> U1.x -> L1.x -> G1.x -> D1.x -> X2.0 -> X3.0
```

## Product Boundary

This unit can promote, reserve, defer, or fuse observed support for geometric
study. It must not silently take responsibility for the full virtualizer.

Owned by this unit:

```text
residual evidence
purity-gated geometric support
line-study support
deferred support
future-module pool
component-family line association
deferred simple lineality evidence
traceable fused support maps
```

Reserved for other virtualizer subsystems:

```text
final line/table/cell objects
OCR/text recognition
symbol/annotation interpretation
page layout semantics
clinical/domain meaning
final export objects
```

Scope reference:

- `docs/GEOMETRIC_EVIDENCE_UNIT_SCOPE.md`

## Module Families

| Family | Role | Main contribution | Output status | Trainability status |
| --- | --- | --- | --- | --- |
| V3.4.2 | residual evidence stratifier | Separates residual evidence while preserving geometric traceability | frozen upstream | frozen |
| C1.x | residual geometry validators | Tests whether residual evidence has local or collective geometric coherence | active functional complement | C1.0/C1.1 fixed-rule; C1-CAL V1 trainable output layer |
| U1.x | purity gates | Filters support toward clean grid-compatible geometric evidence | calibration layer | U1.1 fixed-rule; U1.1-CAL calibrable |
| L1.x | observed support stratification | Separates line-study, non-line/future pool, mixed and deferred support | core modular unit | L1.1 and L1.2-CAL calibrable; L1.0/L1.2 fixed-rule |
| G1.x | deferred family association | Associates deferred components with candidate line families and calibrated promotion decisions | trainable/calibrated layer | G1.0-CAL V1 trainable; G1.0 fixed-rule feature/resolver layer |
| D1.x | deferred lineality complement | Rechecks deferred support for simple observed lineality without creating final geometry | active complementary auditor | D1.0/D1.1 active fixed-rule; D1-CAL V1 trainable output layer |
| X2.0 | single-script fusion | Fuses upstream maps and D1 evidence into auditable line-study and future-pool support | experimental transport unit | fusion/orchestrator, not trainable by default |
| X3.0 | trainable-aware evidence unit | Integrates the functional unit, G1.0-CAL trainable evidence and D1 role evidence with explicit trainable influence maps | complete evidence runtime | trainable-aware fusion/orchestrator, not a trainable monolith |

## Trainability Boundary

The full system is not a single black-box trainable model. It is a modular geometric evidence pipeline with selected trainable/calibrable layers.

Strictly trainable today:

```text
G1.0-CAL V1
C1-CAL V1
D1-CAL V1
```

Calibrable today:

```text
U1.1-CAL
L1.1
L1.2-CAL
```

Fixed/frozen/fusion modules are not trainable unless a future contract changes their status.

Authoritative references:

- `manifests/TRAINABLE_MODULES.md`
- `contracts/TRAINABILITY_CONTRACT.md`

## Individual Modules

### V3.4.2

- Name: residual evidence stratifier.
- Status: frozen; must not be modified.
- Trainability: frozen.
- Role: source of residual evidence after prior geometry processing.
- Traceability requirement: every interpretation must remain tied to observed pixels and source maps.

### C1.0

- Name: individual residual evidence hypothesis validator.
- Status: fixed-rule.
- Trainability: not trainable today.
- Role: tests isolated residual candidates.
- Synergy: provides candidate-level context before purity and domain stratification.
- Forbidden: final line/table/cell creation.

### C1.1

- Name: collective residual evidence hypothesis validator.
- Status: fixed-rule.
- Trainability: not trainable today.
- Role: examines where residual evidence acts collectively.
- Synergy: prepares residual evidence for downstream purity and stratification.
- Forbidden: replacing observed geometry with inferred geometry.

### C1-CAL V1

- Name: trainable residual hypothesis calibrator.
- Status: active trainable layer.
- Trainability: small readable softmax model over traceable C1 hypothesis features.
- Role: calibrates promote/keep/reserve decisions for observed residual hypotheses.
- Synergy: lets C1 evidence become active in X3 without hiding pixel/hypothesis provenance.
- Forbidden: dataset truth at runtime, inferred-span promotion as observed support, final geometry.

### U1.0

- Name: clean grid geometry purity gate.
- Status: fixed-rule.
- Trainability: not trainable today.
- Role: validates cleaner geometric support.
- Synergy: constrains later L1/G1 decisions to cleaner evidence.

### U1.1

- Name: subobject clean grid geometry purity gate.
- Status: fixed-rule.
- Trainability: not trainable directly; calibrated by U1.1-CAL.
- Role: acts on sub-support, not whole-mask semantics.
- Synergy: improves purity before deferred resolution.

### U1.1-CAL

- Name: geometric hysteresis/calibration support.
- Status: calibrable.
- Trainability: calibrable thresholds/hysteresis, not black-box training.
- Role: stabilizes purity thresholds.
- Synergy: prevents brittle threshold decisions from contaminating L1/G1.

### L1.0

- Name: observed support domain stratifier.
- Status: fixed-rule.
- Trainability: not trainable today.
- Role: creates first line-study/future/deferred partition.
- Synergy: defines the observed-support universe for later modules.

### L1.1

- Name: observed support domain calibration layer.
- Status: calibrable.
- Trainability: calibrable domain thresholds/parameters.
- Role: improves L1.0 domain assignments.
- Synergy: reduces accidental promotion and prepares L1.2.

### L1.2

- Name: deferred domain subsupport resolver.
- Status: fixed-rule.
- Trainability: not trainable today.
- Role: resolves part of deferred support.
- Synergy: gives G1 and D1 a narrower, more meaningful deferred domain.

### L1.2-CAL

- Name: deferred line-like fragment calibrator.
- Status: calibrable.
- Trainability: calibrable deferred line-like thresholds.
- Role: calibrates line-like fragments inside deferred support.
- Synergy: reduces unresolved line support before G1/D1.

### G1.0

- Name: deferred line family resolver.
- Status: fixed-rule feature/resolver layer.
- Trainability: not the learner itself; supplies traceable features for G1.0-CAL.
- Role: evaluates deferred component plus candidate family.
- Synergy: starts trainable family association without runtime truth labels.

### G1.0-CAL V1

- Name: trainable deferred family calibrator.
- Status: trainable.
- Trainability: current main trainable module.
- Role: calibrates G1 decisions using deferred-only dataset evidence.
- Synergy: improves promote/keep/reserve decisions while preserving component-family traceability.

### D1.0

- Name: simple deferred lineality auditor.
- Status: fixed-rule.
- Trainability: not trainable today.
- Role: checks clear horizontal/vertical observed lineality that G1/L1 may leave deferred.
- Synergy: complements G1 by applying simple reality-first line criteria.

### D1.1

- Name: deferred linear role classifier.
- Status: fixed-rule functional source.
- Trainability: calibrated by D1-CAL V1.
- Role: separates line-like deferred evidence into tentative roles.
- Synergy: prevents all linearity from being interpreted as structural line.

### D1-CAL V1

- Name: trainable deferred linear role calibrator.
- Status: active trainable layer.
- Trainability: small readable softmax model over traceable D1.1 role features.
- Role: calibrates D1 roles: grid, axis, tick, border, text, curve, ambiguous.
- Synergy: gives X3 a calibrated D1 role source while preserving D1.0 hypothesis traceability.
- Forbidden: truth labels at runtime, final geometry, OCR/semantic interpretation.

### Unit Full Model

- Name: unit orchestrator.
- Status: fusion/orchestrator.
- Trainability: not trainable.
- Role: applies module chain.
- Forbidden: becoming a black-box target.

### X2.0

- Name: geometric evidence fusion single script.
- Status: fusion/orchestrator.
- Trainability: not trainable by default.
- Role: transportable experimental fusion of upstream evidence plus D1-style deferred lineality.
- Synergy: produces fused line-study support and future-module pool, not final geometry.

### X3.0

- Name: trainable geometric evidence unit.
- Status: trainable-aware fusion/orchestrator.
- Trainability: consumes active trainable/calibrable module outputs but is not trainable as a monolith.
- Role: integrates UNIT, C1.x when supplied, G1.0-CAL V1, D1.0 and D1.1 into traceable X3 evidence maps.
- Synergy: makes trainable influence explicit while preserving the functional modular architecture.
- Active functional layers: C1.0, C1.1, D1.0, D1.1.
- Active trainable layers: G1.0-CAL V1, C1-CAL V1, D1-CAL V1.
- Forbidden: runtime training, truth labels, final geometry, hidden trainable decisions.

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
