# Select PR verification scope from the changed-path inventory (issue 205)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260924-select-pr-verification-scope-from-the-changed-pa-c2e3b1`
Created: 2026-09-24T22:27:30+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Fix issue 205: select PR verification scope from the changed-path inventory so documentation/state-only successors run the focused lockstep profile instead of the full coverage suite

## Outcome

A release documentation/state successor — the inventory class that recurs every version bump
(prose, `PROJECT_STATE.json`, `VERSION`, tracked `packages/**` bytes, and the modules that bind
them) — finishes local verification in about 14 seconds instead of 629, and the receipt states in
the same breath which profile ran, why, which paths were admitted, and the three checks that were
not measured. Nothing else changes behaviour: every other inventory keeps the full PR suite, and
no local classification grants merge authority or relaxes the App-owned exact-SHA Trust CI check.

## Scope

### In scope

- `.grok-stack/adaptive_grok/verification_scope.py`: a pure classifier whose admission decision is
  the *role* a file's bytes play, never the directory it sits in.
- `verify()` and `_python()` in `.grok-stack/adaptive_grok/verification.py`: derive the inventory
  from a re-resolved, status-preserving Git read, thread the classification into the runner, and
  report it as the first-class `docs-state-scope` check stored in the receipt.
- `util.changed_file_statuses`: one `rename_detection` flag so the docs/state side channel can
  disable rename/copy scoring without duplicating the name-status plumbing the landing lane shares.
- `tests/test_verification_scope.py`: end-to-end arms that run `verify()` against a real temporary
  repository, plus role-admission, reason-code, status-domain and empty-target arms.
- README.md and AGENTS.md statements about which path classes the lane admits.

### Out of scope

- The static-SEO-landing focused mode (a separate explicit `--mode`), its `verification_scope`
  report key, and its product-inventory rules.
- Trust CI policy, holdout, deployed images, branch protection and any GitHub-side gate.
- Any relaxation of fingerprint binding, receipt writing, independent review, or the requirement
  that a change to this classifier itself runs the full suite.
- Widening the lane to test modules, generated architecture views, contracts or governance JSON.

## Constraints

- Backward compatibility: `verify()` keeps its signature and report shape, only adding
  `docs_state_scope`; `changed_file_statuses` keeps byte-identical behaviour for existing callers
  because the new flag defaults to the previous flags. `--mode pr` remains full PR verification
  unless every path in the final inventory is admitted.
- Data/privacy: no new I/O, no network, no provider call, no credential read. The classifier is a
  function of the changed-path inventory, its Git statuses, the route presence and the environment
  override.
- Performance: the focused lane runs five admitted modules (measured about 14 s serial) and skips
  the serial coverage run (measured 629 s) plus the bounded factory PostgreSQL exit run.
- Operational: one documented escape hatch at two levels — `--full-scope` for a single run and
  `GROK_VERIFY_FORCE_FULL=1` for a session — and both are tested on an identical inventory.
