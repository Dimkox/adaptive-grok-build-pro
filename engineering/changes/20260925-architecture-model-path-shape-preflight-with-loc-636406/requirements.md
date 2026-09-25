# Requirements — architecture model path-shape preflight with located diagnostics

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001 — Given a `repository_paths` entry `"factory/runtime/"` in a minimal valid model, when `preflight_architecture(root)` runs, then exactly one finding is returned and its message contains `architecture/system.yaml:<line>`, the owning node id, the quoted value and the reason `trailing separator`.
- [x] AC-002 — Given the same injected defect, when `load_architecture(root)` runs, then it still raises `ArchitectureError` with `code == "path"`; the value is never normalized or accepted.
- [x] AC-003 — Given the identical model with the trailing separator removed, when the preflight runs, then it returns no findings and the model loads (the contradictory control that keeps AC-001 from passing vacuously).
- [x] AC-004 — Given `../escape`, `/etc/passwd`, `a//b`, `./relative`, `windows\path` and `factory/runtime/`, when each is declared, then each gets its own reason text and no other case's reason text appears in that message.
- [x] AC-005 — Given a trailing separator in a rules-document `source_prefixes` entry, when the preflight runs, then the finding names `architecture/rules.yaml:<line>` and the rule id.
- [x] AC-006 — Given the shipped model with the defect injected in a harness copy, when `run_doctor(root)` runs, then the single `architecture-model` item is `fail` and its message contains the located diagnostic once; the unmodified copy yields `pass`.
- [x] AC-007 — Given the repaired tree, when the architecture, governance, receipt, structure and doctor suites run, then all stay green and the generated views stay re-derivable.

## Failure and edge cases

- Document without the offending scalar on its own line (a hand-edited non-canonical document):
  the canonical-source byte check already rejects the document first; if a located line cannot be
  resolved, the message falls back to naming the document, and `preflight_architecture()` adds
  `(see <document>)`.
- Same bad entry declared by two nodes: one finding, with the occurrence count in the message
  (the ownership-tie rule cannot compare unnormalizable values).
- Non-string and empty entries: caught by the schema before the shape rule; the preflight still
  returns exactly one finding naming the document rather than raising.
- Project copies without `architecture/` (harness `project_copy()`): the doctor item reports
  `info` "not present; skipped" instead of a failure, so the preflight gate cannot break
  unrelated doctor tests.
- Root cause of the cascade (every consumer raising its own copy) is deliberately not silenced:
  an invalid model must stay loud; each copy now names the same file:line.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none added or changed; `governance/` documents are untouched by this contour.
- Canonical-example deviations and evidence: none — the change is diagnosis-only.
- Intentional debt created, repaid, or accepted: repays the reporting debt filed as issue #50;
  no new debt. The schema-level shape rule (`$defs/path` has no `pattern`) stays as-is so the
  frozen M2 architecture digests do not move.

## Non-functional requirements

- Security: path rejection semantics unchanged — absolute, backslash, dot-segment, empty-segment,
  non-NFC and control-character values remain refused. No new path is trusted because it is now
  explained.
- Reliability: `preflight_architecture()` never raises for a model defect; the doctor gate degrades
  to a finding, not a traceback.
- Performance: one located report in ~2.8 s wall for the whole `grok_doctor.py` run (preflight alone
  is sub-second), versus 453 s of suite runtime to observe the same defect before this change.
- Observability: `SIG-001` (doctor `architecture-model` status and located message) and `SIG-002`
  (preflight finding count, 1 for the injected and 0 for the repaired model).
