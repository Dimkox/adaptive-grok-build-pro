# Architecture — architecture model path-shape preflight with located diagnostics

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`architecture/system.yaml` and `architecture/rules.yaml` are canonical JSON authority documents.
`load_architecture()` parses them, checks canonical bytes, validates against the two schemas, then runs
`_validate_system_semantics()` / `_validate_rule_semantics()`, where every declared repository path goes
through `_safe_relative_path()`. That single check is reached by nine root test modules, so one bad
character produced 40 identically-worded suite errors in eight of them (plus a demo health assertion in
the ninth) and named neither file nor line. A trailing separator and a `../` escape were
indistinguishable.

## Proposed behavior

Same rejection, better report:

- `_path_shape_problem()` classifies why a value is not a repository-relative path (trailing separator,
  absolute, empty `//` segment, `.`/`..` segment, backslash, non-NFC, control text, empty, non-string).
  The rejection set is unchanged.
- `_checked_model_path()` attaches the authority location: because the loader has already proven the
  document bytes are canonical two-space JSON, each scalar occupies its own line, so the offending
  literal is resolved to `architecture/system.yaml:<line>` (or `architecture/rules.yaml:<line>`) and
  stored on `ArchitectureError.document` / `.line` as well as in the message.
- `preflight_architecture(root)` is the non-raising, seconds-scale form: it returns the first blocking
  located finding, or `()` when the model loads.
- `run_doctor()` gains an `architecture-model` item that fails with that one diagnostic, and reports
  `info` where architecture documents are absent (harness copies), so no unrelated doctor assertion
  changes status.

## Components and boundaries

`.grok-stack/adaptive_grok/architecture.py` owns path shape rules and location resolution;
`.grok-stack/adaptive_grok/doctor.py` only consumes the new finding tuple. No new service, queue, store
or dependency. Test consumers (`verification.py`, `receipts.py`, `governance.py`) keep calling
`load_architecture()` and now surface the located message through their existing `str(exc)` paths.

## Data flow

Document bytes → canonical/parse/schema checks → semantic checks → (on shape failure) line lookup in the
already-decoded canonical text → located `ArchitectureError` → one `ArchitectureFinding` from
`preflight_architecture()` → one doctor line. Filesystem resolution stays in
`validate_architecture()`; the preflight deliberately does not walk the repository.

## API and event contracts

No HTTP/event/schema contract changes. `ArchitectureError` gains two optional keyword attributes
(`document`, `line`) and `preflight_architecture()` is additive; `ArchitectureFinding` fields are
unchanged so existing `--json` payload shapes do not move.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none changed by this contour.
- Applicable canonical example IDs/versions: none.
- Open or overdue debt IDs: none created; issue #50 reporting debt is addressed by this change.
- Expected governance handoff or receipt impact: governance validation keeps the same verdicts; its
  failure text now carries the location (verified by `tests.test_governance` staying green).

## Bitrix-specific impact

- Modules/events/agents/components affected: none.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: none.
- Core modification: forbidden unless explicitly approved. Not applicable.

## Decisions

- Report the first blocking defect rather than every defect: `load_architecture()` is fail-fast by
  design, and the issue asks for one located report, not a lint sweep. A multi-defect sweep would need a
  parallel non-fail-fast validator and would duplicate the schema layer.
- Keep the path rule strict: a trailing separator stays rejected. The defect was the diagnosis, not the
  policy, and the frozen architecture digests must not move.
- Resolve lines from the canonical document text instead of adding a position-tracking parser: the
  existing `_require_canonical_source()` byte check already guarantees one scalar per line, so the
  mapping is exact and the diff stays small.
- Put the early gate in the doctor rather than in a git hook: hooks are host-local and not merge
  authority, while `scripts/grok_doctor.py` is the shipped health check the issue names.

## Risks and mitigations

- Risk: a message-shape dependency in a consumer. Mitigation: no test asserted the old wording
  (`grep` over `tests/`, `pilot/`, `factory/tests/` found none for `unsafe repository-relative` /
  `path must be a string`), and the neighbouring suites are green.
- Risk: line resolution mismatching a non-canonical document. Mitigation: the canonical byte check runs
  before semantic checks; if no line can be resolved the message degrades to naming the document only.
- Risk: doctor failing on partial harness copies. Mitigation: missing documents yield `info`, and
  `tests.test_verification_doctor`/`tests.test_toolchain` (which assert zero doctor failures) stay green.
