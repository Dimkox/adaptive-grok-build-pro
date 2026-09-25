# Architecture — Select PR verification scope from the changed-path inventory (issue 205)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`grok_verify --mode pr` and `--mode release` measure the same thing for every pull request: ruff,
bandit, secret scan, contracts, SQL safety, spec, architecture, governance and workflow artifacts,
then the whole `tests/` tree under coverage (629 s measured serial on this checkout) plus the
bounded factory PostgreSQL exit run. A release documentation/state successor — prose,
`PROJECT_STATE.json`, `VERSION`, tracked `packages/**` bytes and the modules that re-derive them —
pays that cost even though no executed product statement can move.

## Proposed behavior

The changed-path inventory is classified before the Python lane is chosen. `.grok-stack/`
`adaptive_grok/verification_scope.py` decides, purely and fail-closed, between the
`docs-state-focused` profile and `full-pr-suite`. Selection is **by content role, not by
directory**: a path is admitted only when its bytes are prose/state that nothing executes and a
module this lane itself runs re-derives them. Focused runs replace full discovery with the five
admitted modules and disclose the three checks they do not measure.

## Components and boundaries

- `adaptive_grok/verification_scope.py` (new, pure): `select_docs_state_scope()`,
  `focused_command()`, `is_valid_inventory_path()`, `_classify_path()` and the admitted-role
  constants (`DOCUMENT_ROOT_FILES`, `DOCUMENT_FILES`, directory-shaped `DOCUMENT_PREFIXES`,
  `SHIPPED_EXECUTED_FILES`, `STATE_ROOT_FILES`, `ARTIFACT_PREFIXES`, `FOCUSED_TEST_TARGETS`,
  `FOCUSED_SKIPPED_CHECKS`, `SAFE_FILE_STATUSES`). No subprocess, no filesystem, no imports from
  the verifier — so it is testable without a repository and cannot widen itself.
- `adaptive_grok/verification.py`: `_docs_state_status_inventory()` (status-preserving side
  channel), `_docs_state_scope_check()` (the reported check), `verify()` (single constructor of the
  scope), `_python()`/`_focused_python()` (the only place the classification changes what runs).
- `adaptive_grok/util.py`: `changed_file_statuses(..., rename_detection=True)` — one shared
  name-status reader for both focused lanes; the previous near-copy in `verification.py` and its
  private-import of `util._git_name_status` are gone.
- `scripts/grok_verify.py`: exit code still comes from `report['status']`; `--full-scope` sets the
  environment override.
- Out of boundary: the static-SEO-landing selector keeps its own `verification_scope` report key
  and its own mode; nothing in `trust-ci/` reads either profile.

## Data flow

`get_active_route` + `_git_range_selection` → `_changed_file_inventory` (names, `--no-renames`) →
`_docs_state_status_inventory` (statuses, rename/copy detection off, untracked included so the
veto channel spans exactly the inventory domain) → `select_docs_state_scope` (mode, override,
route presence, path validity, range findings, range base count, statuses, per-path role,
admitted-module availability) → scope dict → `_docs_state_scope_check` (always reported) and
`_python` (only branch on `scope['eligible'] is True`) → report `docs_state_scope` →
fingerprint-bound receipt.

## API and event contracts

No HTTP API, no queue, no event schema. The durable contract is the report/receipt block:

```
docs_state_scope: {schema-shaped fields} eligible, profile, mode, reason, reason_code,
  documentation_files, state_files, artifact_files, changed_lockstep_tests, focused_tests,
  rejected_files, skipped_checks, changed_paths_digest, evidence_kind, rejection
```

`evidence_kind` is `verification:docs-state-focused` or `verification:full-pr-suite`, the same
string the route's evidence matcher consumes. Fields are additive; no existing key changed meaning.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none asserted by this change; the governance and architecture checks still
  run inside the focused profile, so a documentation successor cannot bypass them.
- Applicable canonical example IDs/versions: none.
- Open or overdue debt IDs: none created here.
- Expected governance handoff or receipt impact: the receipt gains `docs_state_scope`; the
  verification evidence kind changes only for an inventory that is entirely admitted.

## Bitrix-specific impact

- Modules/events/agents/components affected: none in the factory itself. The relation is an
  admission decision: `docs/bitrix-local-AGENTS.md` is installed verbatim as `local/AGENTS.md`
  into every consumer Bitrix install (`scripts/install_into.py`), so it is rejected from the lane
  by role (`shipped-executed-content`) even though it lives in `docs/`.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: none; the installer ships this module as part of the
  stack copy and no install step reads the profile.
- Core modification: forbidden unless explicitly approved. None performed.

## Decisions

1. Admit by content role, not by path prefix. A `docs/` prefix admits `docs/bitrix-local-AGENTS.md`
   (executed product in a consumer install) and an `engineering/changes/` prefix admits
   `evidence/historical-*` (bytes `tests/test_history.py` pins literally). Both classes are now
   refused with their own reason codes, and prefix lists are directory-shaped only.
2. A path is admitted only when a module that this lane runs re-derives it. README's
   Workflow-sources table and a delivered package's route record are admitted content, so
   `tests/test_workflow_sources.py` and `tests/test_repo_router.py` joined the admitted set
   (4 s combined) instead of being declared as skipped bindings.
3. Rename/copy detection stays off for the docs/state side channel, on for the landing lane, via
   one parameter on the shared `util.changed_file_statuses`. Justification and the residual
   property are pinned by tests, not comments.
4. The classifier's own modules are outside its allowlist, so the shortcut can never certify its
   own modification; the App-owned Trust CI check still runs the whole suite on the exact head.

## Risks and mitigations

- Risk: an admitted test module is edited to silence its own binding. Mitigation: the admitted set
  is five named modules, all of which re-derive admitted content; any other `tests/` change reports
  `test-suite-change` and keeps the full suite, and that reason code is pinned by a test.
- Risk: a renamed or deleted source hides behind a documentation name. Mitigation: the status
  channel is required (absent, untrusted, or any `D`/`R`/`C`/`U` record vetoes), and three arms
  prove each of those paths end-to-end on a real repository.
- Risk: the receipt advertises a profile the run did not act on. Mitigation: `verify()` arms assert
  on the report *and* on a marker file that only full discovery can write.
- Risk: the coverage floor silently stops applying. Mitigation: `coverage` appears with status
  `skip` plus the reason, and `FOCUSED_SKIPPED_CHECKS` names the replaced discovery runner too.
