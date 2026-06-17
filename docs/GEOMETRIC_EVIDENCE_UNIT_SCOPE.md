# Geometric Evidence Unit Scope

Status: active conceptual boundary
Date: 2026-06-18

## Purpose

This document defines the current promoted module set as a geometric evidence
unit inside the larger virtualizer project.

The current unit is important and runnable, but it is not the whole
virtualizer.

## Core Concept

The promoted modules form an observed geometric evidence engine.

Its responsibility is to transform already observed mask support into
traceable evidence domains:

```text
observed mask support
  -> residual evidence
  -> purity-gated support
  -> line-study support
  -> deferred support
  -> future-module pool
  -> fused auditable support maps
```

This unit does not claim to understand the whole document, page, table,
clinical form, symbol system, or semantic meaning of the image.

It prepares geometric evidence so later virtualizer layers can work on a
cleaner, better audited substrate.

## Relation To The Full Virtualizer

The full virtualizer should be understood as a system of cooperating
subsystems.

Current promoted subsystem:

```text
Geometric Evidence Unit
```

Future or external subsystems may include:

```text
table/cell reconstruction
symbol and annotation handling
text/OCR-facing support separation
page layout reasoning
clinical or domain-specific interpretation
final virtual object construction
export/serialization of virtualized entities
```

The geometric evidence unit must not absorb those responsibilities by
accident. It may reserve support for them, but it must not silently interpret
their evidence as lines.

## What The Unit Is

The unit is:

```text
a traceable geometric evidence processor
a line-study and deferred-support organizer
a source of auditable pixel/component/family maps
a modular chain with selected calibrable/trainable layers
a runtime unit that can be copied and verified independently
```

It can answer questions such as:

```text
which observed pixels are safe for line study?
which pixels remain deferred?
which deferred components look line-like?
which component-family associations are plausible?
which pixels should be reserved for future non-line modules?
which module contributed to a fused decision?
```

## What The Unit Is Not

The unit is not:

```text
the complete virtualizer
a document understanding model
an OCR system
a clinical interpretation system
a final table/cell constructor
a symbol recognizer
a page-layout model
a black-box segmentation model
a generator of final geometry
```

If it creates final lines, final tables, final cells, OCR labels, or clinical
meaning, it has exceeded its current contract.

## Boundary Principle

The unit may refine classification of observed support, but it must not
convert uncertainty into hidden interpretation.

Correct behavior:

```text
observed support -> line-study support
observed support -> deferred support
observed support -> future-module pool
observed support -> ambiguous/reserved support
```

Incorrect behavior:

```text
uncertain support -> silent final line
text-like mark -> structural line because it is linear
symbol stroke -> line-study support without reserved trace
missing support -> invented geometry
dataset truth -> runtime decision input
```

## Why Non-Line Evidence Matters

Non-line evidence is not waste.

Support classified as non-line, mixed, deferred, ambiguous, or reserved remains
part of the virtualizer project because another subsystem may need it later.

The correct goal is not:

```text
maximize line pixels at all cost
```

The correct goal is:

```text
maximize useful geometric organization while preserving future optionality
and pixel-level provenance
```

## Trainability Inside This Concept

Trainability is allowed only at controlled decision layers.

The current strict trainable layer is:

```text
G1.0-CAL V1
```

Current calibrable layers are:

```text
U1.1-CAL
L1.1
L1.2-CAL
```

The unit as a whole is not a trainable monolith.

The fusion/orchestrator layers are not training targets by default:

```text
unit full model
X2.0
```

Training may improve local decisions, but it may not erase the map of why a
pixel was promoted, reserved, or rejected.

## Architectural Contract

Every module in this unit must preserve:

```text
observed pixel support
source map/source bit
sample identity
component identity where applicable
family candidate identity where applicable
module contribution identity
visual audit surface
```

The full virtualizer can build higher-level meaning only if this unit keeps
the lower-level geometric substrate inspectable.

## Practical Naming

Preferred name for this promoted module set:

```text
Geometric Evidence Unit
```

Acceptable descriptive names:

```text
observed support evidence unit
line/deferred evidence unit
traceable geometric support unit
```

Avoid calling it:

```text
the complete virtualizer
the final model
the OCR model
the table reconstruction model
the clinical model
```

## Non-Negotiable Rule

```text
No module may gain interpretation by losing geometric traceability.
```

