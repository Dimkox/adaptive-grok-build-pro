# architecture model path-shape preflight with located diagnostics

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260925-architecture-model-path-shape-preflight-with-loc-636406`
Created: 2026-09-25T00:07:14+00:00
Risk: medium
Complexity: high-risk
Domains: api

## Problem

architecture/system.yaml: report unsafe repository_paths shape errors once at load time with file:line instead of a 32-test cascade

Reproduced on `origin/main` = `cb9af407` in a private scratch copy: one added line
`"factory/runtime/",` (line 2263) made `python3 -m unittest discover -s tests` report
`Ran 924 tests in 453.136s` / `FAILED (failures=1, errors=40)` — 40 errors in eight modules
(`test_architecture_model` 11, `test_governance` 9, `test_architecture_fitness` 8,
`test_change_receipts` 5, `test_landing_architecture_boundaries` 3, `test_verification_doctor` 2,
`test_structure` 1, `test_demo` 1) plus one `test_demo_http` assertion failure, every copy carrying
the identical text
`node NODE-FACTORY-LANDING-LIVE-EXECUTORS repository path: unsafe repository-relative path
'factory/runtime/'` — no file, no line, no reason. `test_governance` re-raised it as
`RuntimeError: governance validation failed: ...` and `test_architecture_fitness` masked it as
`KeyError: 'head_kind'`.

## Outcome

A contributor or the pre-merge gate learns the exact document, line, owning node and reason for
an architecture path-shape defect from one seconds-scale command
(`python3 scripts/grok_doctor.py` → `architecture-model` item, or
`preflight_architecture(root)`), and every consumer copy of the loader error names the same
location. The model still refuses to load with a bad declared path.

## Scope

### In scope

- `preflight_architecture()` in `.grok-stack/adaptive_grok/architecture.py`: load-time
  validation that returns located findings instead of raising.
- Reason classification for rejected repository-relative paths
  (`_path_shape_problem`) and `document`/`line` carried on `ArchitectureError`.
- Location resolution against the canonical authority text for `repository_paths`, rule path
  fields and contract paths.
- `architecture-model` item in `.grok-stack/adaptive_grok/doctor.py`.
- New test module `tests/test_architecture_model_preflight.py`.

### Out of scope

- Accepting or normalizing a trailing separator (the path rule stays as filed).
- Any change to `architecture/system.yaml`, `architecture/rules.yaml`, the architecture schemas
  or `architecture/generated/` views.
- Editing the contended consumer suites that raise their own copy of the loader error; their
  messages improve automatically because they surface `str(exc)`.
- `scripts/grok_verify.py`, `verification.py`, `receipts.py` and other contour-owned files.

## Constraints

- Backward compatibility: rejection set is byte-for-byte the same set of values; added
  `ArchitectureError` keyword arguments and a new public function only.
- Data/privacy: no runtime or secret data involved; the check reads two tracked documents.
- Performance: preflight is a single load (seconds); no per-test filesystem walk added.
- Operational: `grok_doctor.py` exits 1 when the model cannot load, and skips with `info` where
  architecture documents are absent (harness copies), so no existing doctor suite changes status.
