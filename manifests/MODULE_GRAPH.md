# Module Graph - Synergic Geometric Virtualizer

Status: experimental graph
Date: 2026-06-18

## Concept

The system is cumulative. Each layer receives geometric evidence from previous layers and may refine interpretation only under traceability constraints.

This graph represents the current `Geometric Evidence Unit`, a subsystem of
the larger virtualizer. It is the evidence-preparation and line/deferred
reasoning surface, not the whole virtualizer.

```text
V3.4.2
  -> C1.0
  -> C1.1
  -> U1.0
  -> U1.1
  -> U1.1-CAL
  -> L1.0
  -> L1.1
  -> L1.2
  -> L1.2-CAL
  -> G1.0
  -> G1.0-CAL V1
  -> D1.0
  -> D1.1
  -> C1-CAL V1 / D1-CAL V1
  -> X2.0
  -> X3.0
```

## Dependency Levels

### Level 0: observed pixels

All support must remain tied to observed pixels.

Required trace:

```text
sample_id
x, y
source_map
component_id where applicable
family_candidate_id where applicable
```

### Level 1: residual evidence

Modules:

```text
V3.4.2, C1.0, C1.1
```

Role:

```text
extract and validate residual geometric evidence
```

Status in X3:

```text
C1.0 and C1.1 are active functional evidence layers.
C1-CAL V1 is an active trainable output layer for C1.0/C1.1 hypotheses.
```

Rule:

```text
residual evidence cannot become final structure by itself
```

### Level 2: purity and support cleaning

Modules:

```text
U1.0, U1.1, U1.1-CAL
```

Role:

```text
clean observed support and stabilize geometric gates
```

Rule:

```text
purity gates can reject or reserve support, but cannot invent support
```

### Level 3: domain stratification

Modules:

```text
L1.0, L1.1, L1.2, L1.2-CAL
```

Role:

```text
partition observed support into line-study, future/non-line, mixed and deferred domains
```

Rule:

```text
deferred is not failure; deferred is reserved traceable evidence
```

### Level 4: deferred family reasoning

Modules:

```text
G1.0, G1.0-CAL V1
```

Role:

```text
score component-family associations and calibrate deferred promotion
```

Rule:

```text
training truth can calibrate the model, but cannot be runtime input
```

### Level 5: simple observed lineality complement

Modules:

```text
D1.0, D1.1
```

Role:

```text
find clear observed lineality still left in deferred support
```

Status in X3:

```text
D1.0 and D1.1 are active functional evidence layers.
D1-CAL V1 is an active trainable output layer for D1.0/D1.1 roles.
```

Rule:

```text
simple lineality can add line-study evidence, but not final geometry
```

### Level 6: fusion transport layer

Module:

```text
X2.0
```

Role:

```text
combine upstream maps into a runnable, auditable single-script experimental unit
```

Rule:

```text
X2.0 is a fusion layer, not a replacement for upstream evidence generation
```

### Level 7: trainable-aware complete evidence unit

Module:

```text
X3.0
```

Role:

```text
combine the functional unit, active C1/D1 functional evidence, active
trainable G1.0-CAL/C1-CAL/D1-CAL evidence, trainable influence maps and source-bit
traceability
```

Rule:

```text
X3.0 can consume trained/calibrated outputs, but cannot become a trainable
monolith or create final virtualized geometry
```

## Data Flow Contract

```text
upstream maps -> observed universe -> stratified domains -> calibrated residual/deferred decisions -> fused study support -> trainable-aware X3 evidence
```

This data flow ends at auditable support maps. It does not create final
tables, cells, OCR labels, symbols, clinical semantics, or exported virtual
objects.

No module may bypass:

```text
observed universe
source traceability
contracted output maps
visual audit surface
```

## Operational Ownership

```text
GitHub: code, contracts, module registry, module graph
Linear: planning, issues, acceptance, technical audit
Slack: short status updates only
Local workspace: datasets, heavy outputs, visual experiments
```
