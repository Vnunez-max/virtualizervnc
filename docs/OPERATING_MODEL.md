# Operating Model - Modular Geometric Virtualizer

This repository stores the clean, transportable engineering surface of the geometric virtualizer project.

## Current Source Of Truth

Primary working evidence remains in the local Codex workspace until artifacts are promoted here:

```text
/Users/admin/Documents/Codex/2026-06-13/v3-4-2-residual-evidence-handoff
```

## System Roles

```text
Linear  = planning, contracts, technical audits, acceptance criteria
GitHub  = source code, contracts, manifests, clean runtime artifacts
Slack   = short operational updates only
```

Slack is not a technical source of truth.

## Critical Rule

```text
No module may gain interpretation by losing geometric traceability.
```

## What Belongs In This Repo

```text
modules/*.py
contracts/*.md
docs/*.md
manifests/*.md
requirements.txt
small smoke-test fixtures when explicitly approved
```

## What Does Not Belong Here

```text
clinical images
large datasets
historical output folders
uncurated experiment dumps
V3.4.1 or V3.4.2 modifications
```

## Current Experimental Unit

X2.0 is the current real single-script fusion layer. It is not a replacement for the full upstream modular pipeline; it consumes upstream evidence maps and fuses decision support.

```text
X1.0 = operational wrapper/runtime bundle
X2.0 = real single-script evidence fusion layer
```
