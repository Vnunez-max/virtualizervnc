# Global Traceability Contract

Status: active experimental contract
Date: 2026-06-18

## Critical Rule

```text
No module may gain interpretation by losing geometric traceability.
```

## Scope

This contract applies to every module in the synergic geometric virtualizer chain:

```text
V3.4.2 -> C1.x -> U1.x -> L1.x -> G1.x -> D1.x -> X2.0 -> X3.0
```

## Required Traceability Units

### Pixel level

Every pixel used by a module must be traceable to:

```text
sample_id
x
y
observed_support membership
source map or source bit
```

### Component level

Every component-level decision must be traceable to:

```text
component_id
component pixel set
bbox
area
source domain
```

### Family-candidate level

Every deferred family decision must be traceable to:

```text
component_id
family_candidate_id
candidate corridor or support map
feature row
decision score or calibrated class
```

### Module level

Every module must produce:

```text
contract or documented acceptance criteria
machine-readable maps or tables when applicable
visual audit output when visual interpretation is involved
summary with counts and invariants
```

## Forbidden Runtime Inputs

Runtime modules must not use:

```text
ground-truth labels from datasets
manual sample-specific coordinates
OCR or clinical semantics
post-hoc visual interpretation as hidden input
```

Dataset truth is allowed only for:

```text
training
calibration
evaluation
audit reports
```

## Output Boundaries

Line-study support is not final geometry.

Future-module pool is not rejection.

Deferred support is not failure.

No current module may create final:

```text
virtualized lines
tables
cells
OCR
clinical labels
semantic structures
```

unless a future contract explicitly allows it and preserves traceability.

## Promotion Invariants

A promoted support pixel must satisfy:

```text
promoted_pixel subset_of observed_support
source_trace exists
module_source exists
class or role is explicit
visual audit can display the contribution
```

A component-family promotion must satisfy:

```text
component_id exists
family_candidate_id exists
feature row exists
decision row exists
truth label is absent at runtime
```

## Dataset Boundary

Datasets are not repository runtime artifacts.

They belong outside GitHub unless explicitly approved as small smoke fixtures.

The repo `.gitignore` must continue excluding:

```text
datasets/
data/
outputs/
results/
*.npy
*.npz
*.png
*.jpg
*.zip
```

## Acceptance

A module passes this contract only if:

```text
all outputs are subsets of observed support when they represent observed evidence
all promoted evidence has source traceability
all ambiguous evidence remains available for future modules
no frozen upstream module is modified
no final geometry is created by study-support modules
```
