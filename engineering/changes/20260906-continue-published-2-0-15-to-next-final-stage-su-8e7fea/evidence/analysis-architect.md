# Architecture analysis — extract PR #12 lazy Trust CI CLI imports onto origin/main

Route: `8e7fea3efac6`
Role: `architect` (read-only; no implementation)
Change: `20260906-continue-published-2-0-15-to-next-final-stage-su-8e7fea`
Reasoned from remotes, not the stale local checkout.

## Verdict

Build a **new successor branch from `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9` (published v2.0.15)**. Reconstruct only PR #12's unique product slice: command-local imports in `trust-ci/src/adaptive_trust_ci/cli.py`, a key-free import-isolation test module, and source-checkout operator documentation in `trust-ci/README.md`.

Do **not**:

- continue the stale local branch `fix/path-aware-shell-policy-circuit-breaker` (`7c61e3b`, VERSION `2.0.12`);
- merge, rebase, or cherry-pick `origin/fix/human-approval-cli` `0f7f508945ccce7dc4f1bffc463247633e9e8f58` wholesale;
- carry the old change package `engineering/changes/20260828-fix-trust-ci-human-approval-cli-approval-create-1810a9/`;
- stack this successor on PR #28;
- touch later main path/policy/holdout/attestation/workspace/runner hardening;
- add GitHub Actions or root packaging markers;
- generate, read, or submit human or operational approval keys, including in tests;
- merge, deploy, or activate M8/M9/pilot.

`cli.py` on origin/main is **byte-identical** to PR #12's merge-base `1c06299894279a88b881defa3f19b004fa742223`. The unique CLI patch therefore applies cleanly. The merge is dirty only because later main appended `decisions.md` / `mistakes.md`, and because PR #12 also carried superseded evidence churn.

## Observed identities

| Object | SHA / state |
| --- | --- |
| `origin/main` / tag `v2.0.15` | `fd51dcfed6b33f4a8707c0db602328146df17cc9` |
| PR #12 head `origin/fix/human-approval-cli` | `0f7f508945ccce7dc4f1bffc463247633e9e8f58` (open, `mergeable_state: dirty`, base still `1c06299`) |
| PR #12 merge-base with current main | `1c06299894279a88b881defa3f19b004fa742223` |
| PR #28 head `origin/docs/v2.0.15-published-handoff` | `ef7c8faeb5d339c5b4343de61162ea611c130c4d` (open, `mergeable_state: clean`) |
| Local HEAD (stale, leave it) | `7c61e3b647924e5667d171d8b286e5d79b8a4efe` on `fix/path-aware-shell-policy-circuit-breaker`, VERSION `2.0.12`, dirty `compose.yaml` plus untracked change packages |
| Trust CI package version on main | `2.1.0` (`cryptography==46.0.4` remains the only human-path dependency) |

Owner comment on PR #12 (2026-09-02) already classified it as **stale head; do not merge wholesale; clean successor required**. PR #28's runbook `engineering/runbooks/20260905-open-pr-reconciliation.md` names this extraction as the first remaining unique work.

## Current behavior (origin/main)

`trust-ci/src/adaptive_trust_ci/cli.py` still imports the full server graph at module import time:

`api`, `backup`, `github`, `github_app`, `holdout`, `migrations`, `models`, `policy`, `settings`, `signing`, `store`, `worker`.

A human-controlled host with only the pinned signing extra therefore fails at `from .api import create_app` → `ModuleNotFoundError: fastapi` before argparse, `--help`, `approval-create`, or `approval-submit`. That is the same defect PR #12 already proved against `1c06299`. Later main never touched `cli.py`.

Human-safe dependency chains already exist and are unchanged:

| Command | Required after dispatch |
| --- | --- |
| `approval-create` | `Policy`, `ApprovalPayload`, `Signer`, `sign_approval` → stdlib + `cryptography` |
| `approval-submit` | stdlib `urllib` / `pathlib` only |
| `--help` / parser | stdlib only |

`policy.py` and `models.py` still do not import API/worker/store/PostgreSQL. `adaptive_trust_ci/__init__.py` only sets `__version__ = "2.1.0"`.

## Later main hardening that must be preserved

Since PR #12's merge-base, origin/main changed Trust CI **around** the CLI, not the CLI itself. The successor must not regress:

| Area | Later main change | Successor rule |
| --- | --- | --- |
| Path-aware policy | `policy.py` `_validated_repo_relative`; exact globs/changed paths; reject absolute, drive, empty, `.`, `..`, control chars; no `lstrip('./')` rewrite | Do not edit `policy.py`. Keep later tests `test_required_scopes_preserve_exact_unusual_git_paths`, `test_approval_globs_preserve_exact_repo_relative_identity`, `test_approval_globs_reject_unsafe_patterns_without_rewriting`, `test_policy_file_with_invalid_utf8_fails_closed`. |
| Holdout | `holdout.example/validate.py` now calls `change_spec_validate`; new `change_spec_validate.py`; `policy.example.json` holdout digest `e2de0333…`; `tests/test_change_spec_holdout.py` | Do not edit holdout bundle, example policy digest, or holdout tests. `holdout-digest` / `doctor` keep current `bundle_digest` / `verify_bundle` call sites. |
| Attestation metadata | `models.py` optional `spec_digest` + `criterion_coverage`; `signing.py` verifies the original signed payload bytes | Do not edit `models.py` or `signing.py`. Approval envelope schema v1 is unchanged. |
| Workspace / runner | large path-confinement and execution-lifecycle work | Do not edit `workspace.py` or `runner.py`. |
| `_support.policy_data()` | later exact unusual git-path globs | New CLI tests may import current helpers; they must not rewrite them. |

`cli.py` does not call `Policy.required_scopes()`. Human commands are unaffected by path validation, but the doctor/holdout/policy-digest branches must keep later semantics.

## Proposed vertical slice

Keep the original PR #12 implementation shape: **stdlib-only module scope, product imports inside the selected command branch and `_doctor()`**. Do not split a second `operator_cli.py`. Do not add packaging extras, Docker, or install-path changes.

Required command boundaries after dispatch (same 19 commands as origin/main; inventory is frozen):

| Family | Imports allowed |
| --- | --- |
| parser / `--help` / `approval-submit` | stdlib only |
| `approval-create` | `Policy`, `ApprovalPayload`, `Signer`, `sign_approval` |
| `approval-verify`, `attestation-verify`, `keygen`, `trust-store-validate` | models / policy / signing as already used |
| `api` | `uvicorn`, `create_app`, `ApiSettings` |
| `worker` | `Worker`, `install_signal_handlers`, `WorkerSettings` |
| `migrate`, `migration-status` | `PostgresMigrator`, `CommonSettings` |
| `policy-digest` | `Policy`, `CommonSettings` |
| `holdout-digest` | `bundle_digest` only |
| `branch-protect` | `GitHubClient`, `Policy` |
| backup / restore / prune | `backup` (+ `CommonSettings` where already used) |
| `kill-switch` | `utc_now`, `CommonSettings` |
| `doctor` / `_doctor()` | current doctor graph (settings, policy, holdout, store, migrations, signing, github_app) |

Command names, flags, JSON output, overwrite-refusal, `0600` envelope mode, `/approvals` POST, and User-Agent `adaptive-trust-ci-human/2.1.0` stay frozen.

Do not reclassify `trust-ci/pyproject.toml`. The operator path remains:

```bash
python3 -m venv "$TRUST_CI_OPERATOR_VENV"
"$TRUST_CI_OPERATOR_VENV/bin/python" -m pip install 'cryptography==46.0.4'
PYTHONPATH="$TRUST_CI_CHECKOUT/trust-ci/src" \
  "$TRUST_CI_OPERATOR_VENV/bin/python" -m adaptive_trust_ci.cli approval-create --help
```

## Files likely to change

### Must change (product)

1. `trust-ci/src/adaptive_trust_ci/cli.py` — delete module-level product imports; add the same command-local imports PR #12 already has. No control-flow or output changes.
2. `trust-ci/tests/test_cli.py` — **new file**, adapted from PR #12 rather than copied blindly (see test plan).
3. `trust-ci/README.md` — replace the `adaptive-trust-ci approval-create` global-install recipe with the source-checkout operator flow. Current main README is unchanged since `1c06299`, so PR #12's README patch applies without losing later docs.

README field-list correction is in scope: origin/main still documents `pull_request` while `ApprovalPayload` has always used `pr_number`, plus `schema_version`, `approval_id`, and `reason`. That is documentation alignment with the frozen envelope, not a schema change.

### Should change (append-only logs, current package)

4. `decisions.md` — append a **new dated** entry on current main's tail (do not transplant the 2026-08-28 paragraph into the old insertion point). Pattern: multi-role CLIs import after command dispatch.
5. `mistakes.md` — append only the human-approval CLI server-graph root cause. Drop PR #12's whitespace-commit-gate note; it is process noise, not this product defect.
6. This change package (`engineering/changes/20260906-continue-published-2-0-15-to-next-final-stage-su-8e7fea/`) — fill brief/requirements/architecture/test-plan from this report. Do **not** copy `1810a9`.

### Must not change

- `trust-ci/src/adaptive_trust_ci/{policy,models,signing,holdout,api,worker,store,runner,workspace,settings,github,github_app,migrations,backup}.py`
- `trust-ci/holdout.example/**`, `trust-ci/config/policy.example.json`
- `trust-ci/tests/{test_policy,test_change_spec_holdout,test_workspace,test_runner,test_signing,test_api,_support}.py` except as unmodified regression targets
- root `pyproject.toml` / `setup.py` / `package.json` (none exist on origin/main; do not add them)
- `.github/workflows/` (none exist; do not add)
- `VERSION` (stay `2.0.15` unless a later named release is explicitly scoped)
- `trust-ci/pyproject.toml` version `2.1.0` and dependency pins
- `pilot/**`, M8/M9 activation, deployed policy/holdout/images/keys
- PR #13 repository profiles, PR #15 investor demo
- local `fix/path-aware-shell-policy-circuit-breaker` hook/policy work

## Compatibility constraints

Classification: **internal implementation-only**. No producer/consumer migration.

- `ApprovalPayload` / `ApprovalEnvelope` schema version 1 unchanged (`schema_version`, `approval_id`, `nonce`, `actor`, `key_id`, `repository`, `pr_number`, `base_sha`, `head_sha`, `policy_digest`, `scope`, `reason`, `issued_at`, `expires_at`, `signature`).
- Canonical JSON, Ed25519, policy digest, TTL, replay, and `POST /approvals` unchanged.
- Later attestation metadata (`spec_digest`, `criterion_coverage`, original signed-payload verify) unchanged and unused by this CLI slice.
- Path-validation and holdout-digest contracts unchanged.
- No SQL, migrations, trust-store, branch-protection, or deployed-policy edit.
- Private keys remain human-host-only via `Signer.from_private_file()` inside `approval-create`. `approval-submit` continues to POST opaque envelope bytes and never loads signing code.
- Local CLI success is not merge authority. App-owned `adaptive-trust-ci/verified@<policy-sha12>` on the exact PR head remains the merge gate.
- This successor must not approve itself.

## Test plan sketch

Do **not** copy PR #12's `test_approval_create_runs_without_server_imports_and_preserves_envelope_contract` as-is. That method calls `Signer.generate()`, writes a PEM, and reads it. AGENTS.md plus the PR #28 reconciliation runbook forbid generating/reading/submitting human approval keys; this successor treats **any** key material in new CLI tests as out of bounds. Existing `trust-ci/tests/test_signing.py` already covers ephemeral-signer envelope contracts; leave that suite unmodified and do not duplicate it.

P0 — import boundary (fresh subprocess, `sitecustomize` meta-path guard):

1. `--help`, `approval-create --help`, `approval-submit --help` succeed while blocking `adaptive_trust_ci.{api,backup,github,github_app,holdout,migrations,settings,store,worker}`, `fastapi`, `psycopg`, `uvicorn`, and `cryptography`.
2. `approval-submit` against a loopback stdlib HTTP server posts exact fixture bytes to `/approvals` with `Content-Type: application/json` and User-Agent `adaptive-trust-ci-human/2.1.0`, still blocking the server graph **and** `cryptography`. Fixture JSON is not a signed operational envelope and is not submitted to a deployed URL.

P0 — in-process command-slice smoke (fake modules, no PEM, no network except the loopback submit test above):

3. Freeze the parser's subcommand set to the current 19 names so a later command cannot appear without a lazy-import case.
4. Port PR #12's 17 non-human branch cases (`api` through `kill-switch`) asserting each branch imports only its slice and reaches a mocked safe effect. Keep the `keygen` case mocked so `write_keypair` records an effect and **no** PEM is written.
5. Add an `approval-create` fake-module case: mocked `Policy.load` / `Signer.from_private_file` / `sign_approval` / `_write_new_json`. Assert the signing/policy/models slice is imported, server modules are not, and no key file is created or read.

P1 — later hardening must stay green and unmodified:

6. `trust-ci/tests/test_policy.py` path/glob/UTF-8 cases.
7. `trust-ci/tests/test_change_spec_holdout.py` plus example holdout digest pairing.
8. Existing `test_signing.py` / API approval-requeue / replay tests (envelope contract; no new key fixtures).
9. `test_workspace.py` / `test_runner.py` as non-regression if the route verifier already includes them.

P1 — docs/operator:

10. README uses `python -m adaptive_trust_ci.cli`, placeholder paths only, no real key/policy/host values, and does **not** tell operators to generate keys or run a key-creating unittest. Policy digest is canonical `Policy.load(...).digest` compared to `/health/ready`, not raw `sha256sum`.

Static: route `base` profile via `python3 scripts/grok_verify.py --mode pr`. No GitHub Actions.

Characterization: on the successor tree, the historical `PYTHONPATH=trust-ci/src python3 -m adaptive_trust_ci.cli --help` reproduction must exit 0 without FastAPI installed in that interpreter.

## PR #28 stacking decision: leave independent

PR #28 is a **documentation-only** post-publication handoff against the same `origin/main`. Unique files: `README.md`, `START_HERE.md`, `CHANGELOG.md`, `PROJECT_STATE.json`, `DARK_FACTORY_ROADMAP.md`, `packages/README.md`, publication assertion tests, and its own change package/runbooks.

Overlap with PR #12 / this successor: **only** `decisions.md` and `mistakes.md` (append-only tails). No Trust CI product file overlap.

Leave it independent because:

1. Mixing publication paperwork with a Trust CI operator-path repair couples unrelated review, check, and rollback surfaces.
2. PR #28 is already `mergeable_state: clean` on `fd51dcf`. Stacking would make the CLI successor wait on docs checks and would revert CLI work if the docs PR is abandoned.
3. EOF log conflicts are ordinary: whichever PR merges second rebases a short append. That is cheaper than a stacked parent.
4. The successor PR body should **link** PR #28 as parallel docs work and link PR #12 as the superseded source, not use either as git parent.

Do not import PR #28's `PROJECT_STATE.json` / root README edits into this slice. Do not bump published-release assertions here.

After this successor exists, PR #12 should be closed as superseded (owner comment). Closing is an explicit later operation, not part of implementation.

## Rollout and rollback

Rollout is source-only:

1. New branch from `origin/main` `fd51dcf…`, not from the stale path-aware checkout.
2. Reconstruct the three product files + log appends + this change package.
3. Local `grok_verify --mode pr` and route reviews (`code_reviewer`, `test_reviewer`).
4. Open a new PR to `main`. Merge only after App-owned `adaptive-trust-ci/verified@<policy-sha12>` on the exact head SHA plus required human-signed scopes.
5. Humans may then use the reviewed source checkout with `cryptography==46.0.4`. Existing API/worker images keep running; a later normal image rebuild picks up server-command lazy imports.

No database migration, policy epoch, holdout digest, trust-store, or branch-protection change. No VERSION bump and no GitHub Release in this slice.

Bootstrap: a human may use the currently deployed full-dependency CLI, or personally review this source repair, to sign **other** PRs. This PR cannot carry its own human private key.

Rollback: revert the successor commit. No data recovery. Old envelopes remain verifiable. Roll back if any server command fails to import after dispatch, if envelope bytes/schema diverge, or if later path/policy/holdout tests regress.

## Residual risk

| Risk | Mitigation |
| --- | --- |
| Wholesale cherry-pick of `0f7f508` conflicts on logs and restores stale `1810a9` evidence | Reconstruct the unique slice; do not cherry-pick the commit |
| Lazy import omitted for a server command | Frozen 19-command inventory + 17 fake-module cases + existing API/worker/backup tests |
| New CLI tests generate or read keys | Key-free test design; no `Signer.generate()`, no runtime PEM paths, no deployed submit |
| README auto-merge looks like a schema change | Field-list edit is docs alignment with unchanged `ApprovalPayload`; attestation metadata docs stay untouched |
| Path/policy/holdout regress by accident | Those files are out of scope; later tests stay unmodified and must pass |
| Stacking onto PR #28 or continuing 2.0.12 path-aware HEAD | New branch from `fd51dcf`; leave both the docs PR and the local path-aware branch alone |
| Treating local receipts as merge authority | External exact-SHA App check remains mandatory |
| Scope creep into PR #13 profiles or PR #15 demo | Explicit non-goals |

## Acceptance for the write owner

Implement only when the successor tree on top of `fd51dcf` shows:

1. `python -m adaptive_trust_ci.cli --help` works without FastAPI/psycopg/uvicorn.
2. Human help and `approval-submit` pass the server-import (and cryptography) guard without touching keys.
3. Fake-module coverage exists for every current non-help command, including mocked `approval-create` and `keygen` with no PEM files.
4. Unmodified later `test_policy`, holdout, signing, workspace, and runner tests still pass.
5. No policy, models, signing, holdout bundle, SQL, GHA, or root packaging file changed.
6. Operator docs are source-checkout + pinned `cryptography==46.0.4`, with placeholder paths only.
7. PR #28 remains an independent docs PR; PR #12 is referenced as superseded source, not merged.

Write owner: route `general_implementer`. This report is design only.
