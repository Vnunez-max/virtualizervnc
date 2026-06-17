# virtualizervnc

Clean repository surface for the synergic geometric virtualizer.

The project is organized as a cumulative geometric evidence chain:

```text
V3.4.2 -> C1.x -> U1.x -> L1.x -> G1.x -> D1.x -> X2.0
```

Current repository roles:

```text
modules/    clean runnable module code
contracts/  module and traceability contracts
manifests/  registry, graph and promotion records
models/     small runtime calibrator assets only
docs/       architecture and operating notes
tools/      verification helpers
```

Datasets, generated outputs, masks, visual audits and historical experiment
folders are intentionally excluded from GitHub.

## Trainability Boundary

The full system is not a single black-box trainable model. It is a modular
geometric evidence pipeline with selected trainable/calibrable layers.

Current strict trainable module:

```text
G1.0-CAL V1
```

Current calibrable modules:

```text
U1.1-CAL
L1.1
L1.2-CAL
```

Frozen/non-trainable by default:

```text
V3.4.2
C1.x
U1.1
L1.0
L1.2
G1.0 base resolver
D1.0
unit orchestrator
X2.0
```

See:

- `manifests/TRAINABLE_MODULES.md`
- `contracts/TRAINABILITY_CONTRACT.md`

Critical rule:

```text
No module may gain interpretation by losing geometric traceability.
```
