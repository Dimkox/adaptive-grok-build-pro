# Architecture — Fix issue 227: inherited GIT_DIR or GIT_WORK_TREE can redirect repository identity and let a valid local grant authorize git push to a foreign pushurl. Add root-bound Git probes and explicit fail-closed denial. Never execute git push or access the network.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`state.add_approval` and `state.has_valid_approval` derive repository identity,
HEAD and tree fingerprint through Git helpers that inherit `os.environ`. The
eventual shell push inherits the same selectors. A crafted foreign checkout can
therefore satisfy the stored grant binding while its push URL targets another
repository, and policy returns allow.

## Proposed behavior

Introduce one internal root-bound Git environment helper that removes
`GIT_DIR`/`GIT_WORK_TREE` from read-only control-plane probes. Independently,
reject production Git pushes in the public policy path whenever either selector
is inherited. Both controls are mandatory: probe isolation protects grant
identity, while the denial protects the actual command execution boundary.

## Components and boundaries

- `.grok-stack/adaptive_grok/util.py`: sanitized environment for `git_output`,
  `_git_paths` and `_git_name_status`.
- `.grok-stack/adaptive_grok/_policy_legacy.py`: early, secret-safe denial before
  grant lookup for branch/tag push actions.
- `tests/test_util_fingerprint.py`: root-bound identity/fingerprint behavior.
- `tests/test_policy.py` and `tests/test_hooks.py`: core and hook-level denial,
  bypass regression and clean-environment compatibility.

## Data flow

`tool payload root -> policy root -> sanitized read-only Git probes -> grant
binding`; separately, `ambient selector presence -> push policy denial`. No
external command is executed by the regression tests.

## API and event contracts

No HTTP, OpenAPI or event contract changes. `has_valid_approval` remains boolean,
grant schema stays v2, and policy continues returning `(allowed, reason)`.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: active route/human-gate and delegated-grant rules.
- Applicable canonical example IDs/versions: none.
- Open or overdue debt IDs: issue #58/root-local push destination validation is
  adjacent but intentionally outside this patch.
- Expected governance handoff or receipt impact: existing fingerprint-bound
  receipt semantics remain unchanged.

## Bitrix-specific impact

- Modules/events/agents/components affected: none.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: none.
- Core modification: forbidden unless explicitly approved.

## Decisions

- Variable presence, not truthiness, triggers denial.
- Denial text exposes names only, never values.
- Prior-art commit `69f68704` is not reused alone because probe scrubbing without
  execution denial is unsafe.
- Root-local `pushurl` mutation is documented residual scope, not silently added.

## Risks and mitigations

- Operational tightening may reject intentionally inherited selectors; recovery
  is explicit unset-and-retry, which is safer than guessing intent.
- A missed Git probe could retain split identity; tests cover HEAD, changed files
  and fingerprint, and review must inspect every direct Git subprocess.
- A rollback would reopen an authorization bypass, so use forward-fix rollback
  and keep delegated agent push actions disabled until repaired.
