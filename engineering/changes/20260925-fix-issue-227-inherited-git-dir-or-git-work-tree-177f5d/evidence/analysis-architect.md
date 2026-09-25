# Architecture analysis — issue #227 grant/repository boundary

Route `177f5dc1d5cf`; base `origin/main` / `cb9af4073ba6c3d515145164d771c75ebdfa3224`; observed 2026-09-25 UTC. This report is read-only design evidence. No grant was created in the real worktree, no push command was executed, and no network or external write was attempted.

## Ruling

Implement #227 as one bounded, two-control security repair:

1. **Root-bind internal Git probes.** Repository identity, HEAD, changed-file inventory, and tree fingerprint must derive from the explicit `root` argument after removing inherited `GIT_DIR` and `GIT_WORK_TREE` from the child Git environment.
2. **Deny ambiguous execution.** Before a `git-push-branch` or `git-push-tag` action can consume a delegated grant, core policy must fail closed if either selector is present in the policy process environment.

Both controls are mandatory. Probe isolation alone can make `has_valid_approval(root, ...)` correctly validate repository A while the eventual shell push remains redirected to repository B; denial alone leaves direct grant creation/validation and other root-bound state computations dependent on ambient process state. Local commit `69f68704` is prior art only and must not be cherry-picked alone: it strips inherited Git variables for `util.run()` calls but does not cover direct `_git_paths` / `_git_name_status` subprocesses and does not deny the redirected execution.

The scope-and-design gate is pending. The write owner must not begin implementation until the parent records approval of this exact two-control scope.

## Confirmed root cause

The authorization decision currently derives both its trusted identity and the eventual command target from one mutable input, `os.environ`:

1. `.grok/hooks/pre_tool_use.py` resolves the payload/session root and calls `adaptive_grok.policy.evaluate_pre_tool(root, event)`.
2. `policy.py` delegates production actions to `_policy_legacy.evaluate_pre_tool`.
3. `_policy_legacy.py` classifies `git push`, checks the human gate, and asks `state.has_valid_approval(root, "production", action=...)`.
4. `state.py` binds and validates repository identity with `git_output`, HEAD with `git_head`, and worktree state with `tree_fingerprint`.
5. `util.run()` copies all of `os.environ`; `git_output` uses it. `_git_paths` and `_git_name_status` call `subprocess.run` directly and also inherit the full environment. Therefore `GIT_DIR` / `GIT_WORK_TREE` can redirect every binding input away from the passed root.
6. The eventual shell `git push` inherits the same selectors. If a foreign clone has the same GitHub fetch identity, HEAD, and clean-tree digest as the grant, the policy can validate the foreign state and return allow even when that clone's `remote.origin.pushurl` points elsewhere.

The security issue is not that the stored grant was forged. The grant remains a real schema-v2 local grant. The defect is that mutable execution context changes what repository the verifier believes the grant describes.

## Assets, actors, and trust boundaries

| Boundary | Asset / actor | Required property |
| --- | --- | --- |
| Human delegation | Exact named local production action | Must not expand through environment or repository-controlled redirects |
| Route and human gate | Local workflow constraint | Must still be evaluated; this fix does not create approval |
| Explicit `root` argument | Repository selected by the hook/tool payload | Sole repository input for grant identity, HEAD, and tree probes |
| `os.environ` | Mutable, inherited execution context | Untrusted for repository selection; selector names may be observed, values must not be logged |
| `approvals.json` | Local grant evidence | Schema, route/change, action/resource, TTL, HEAD, and digest semantics remain stable |
| `policy.evaluate_pre_tool` | Authorization boundary before execution | Must deny an ambiguous push before checking/consuming a matching grant |
| Git probe subprocesses | Read-only identity/fingerprint adapters | Must use canonical cwd plus a selector-scrubbed environment |
| Shell Git process | Eventual external writer | Must never be assumed to share probe identity when inherited selectors exist |
| Fetch URL / push URL | Repository label versus effective write destination | Fetch identity is not proof of write destination; #227 closes inherited-selector redirection only |
| External Trust CI | Merge authority | Unchanged and never substituted by this local repair |

Entry points are direct `evaluate_pre_tool` calls, the PreToolUse hook subprocess, `add_approval`, `has_valid_approval`, and any caller of `git_head` / `changed_files` / `tree_fingerprint` in the grant path.

## Proposed component design

### 1. Root-bound Git probe adapter in `util.py`

Create one private selector set containing exactly `GIT_DIR` and `GIT_WORK_TREE`, plus one private environment constructor that copies the current environment and removes those keys. Use that environment for every Git subprocess in `util.py` that participates in root or fingerprint resolution:

- the Git fallback inside `find_root`;
- `git_output` and therefore `git_head`, `git_default_base`, and `state._repository_identity`;
- `_git_paths`, used by `changed_files` and `tree_fingerprint`;
- `_git_name_status`, used by focused changed-file status selection.

Do not silently change arbitrary `run()` command behavior. Either add an explicit per-call unset/exact-environment option whose default preserves all existing callers, or use a private Git-only runner shared by the text and binary probe paths. Passing a dictionary with the selectors omitted to today's `run(env=...)` is insufficient because `run()` first copies `os.environ` and then overlays that dictionary.

The adapter must preserve existing semantics:

- canonical `cwd` remains the supplied root;
- text probes still return strings or `None` on failure;
- NUL-delimited inventory probes remain binary and preserve non-UTF-8 filesystem bytes;
- timeouts, missing Git, malformed NUL output, fingerprint noise rules, and no-HEAD fallback behavior remain unchanged;
- no Git command may perform a network operation or mutate repository state.

`state.py` requires no schema or signature change. Once its utility calls are root-bound, `add_approval` and `has_valid_approval` continue to bind the explicit root correctly.

### 2. Inherited-selector denial in `policy.py`

Enforce the execution check at the public core policy boundary, not only in the hook UI:

- classify the Bash command using the existing production-action classifier;
- for `git-push-branch` and `git-push-tag`, inspect selector **presence** in `os.environ` before delegating to grant validation;
- if either selector is present, return `(False, reason)` immediately;
- the reason must include the action and sorted selector name(s), say that the Git execution target is ambiguous, and direct the operator to unset them and retry from the delegated repository;
- never include selector values, paths, remote URLs, credentials, or grant contents.

Presence, including an empty value or a value that appears to point back to the same root, is denied deliberately. Proving that inline clearing, nested wrappers, or platform-specific Git behavior cancels an inherited selector would enlarge the parser and create another bypass surface. The safe recovery is a clean process environment.

Existing command-local defenses in `.grok/hooks/_lib.py` remain authoritative for literal `GIT_DIR=...`, `git --git-dir`, `--work-tree`, `git -C`, shell nesting, dynamic roots, and cross-repository working-directory aliases. This change does not weaken or replace them.

### 3. Keep the two outcomes intentionally different

After the repair, under hostile ambient selectors:

- `git_head(A)`, `changed_files(A)`, `tree_fingerprint(A)`, and `has_valid_approval(A, ...)` describe A consistently;
- `evaluate_pre_tool(A, git-push-event)` still denies because the actual execution environment is ambiguous.

This is not contradictory. Grant validity answers whether a grant matches an explicit repository state; policy answers whether the proposed command is safe to execute in the current context.

## Frozen contracts and compatibility

No HTTP, OpenAPI, event, database, or external API contract changes.

Preserve:

- `has_valid_approval(...) -> bool` and `add_approval(...) -> dict` signatures;
- grant schema version 2, `grant_binding_digest`, legacy `tree_fingerprint` read compatibility, route/change/action/resource/TTL checks, and existing expiry cleanup;
- production action names `git-push-branch` and `git-push-tag`;
- clean-environment behavior: a matching exact grant may allow its exact push action, while missing, stale, mismatched, or expired grants deny;
- non-Git and read-only command decisions;
- the hook denial-ledger schema and its generic non-secret reason field;
- separation between local grants and App-owned Trust CI/signed human approvals.

Intentional compatibility tightening: a granted push is denied whenever inherited `GIT_DIR` or `GIT_WORK_TREE` is present, even if the value resolves to the intended checkout. The remedy is to unset the variable, not to relax the authorization boundary.

Do not broaden this patch to every `GIT_*` variable without an inventory and dedicated tests. `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, object/namespace selectors, and Git config injection may deserve successor analysis, but #227's accepted scope is the two proven repository selectors. Likewise, root-local `remote.*.pushurl` mutation and the larger #58 destination-binding problem remain explicit residual risks; this patch must not claim all push-destination attacks are solved.

## Exact regression and acceptance tests

All fixtures are local temporary repositories. Tests must never invoke `git push`, a remote transport, or any network client.

### P0 — authorization bypass is killed

In `tests/test_policy.py`:

1. Create repository A with the expected GitHub-shaped `remote.origin.url`, active route, and a real `git-push-branch` local grant.
2. Clone/copy A locally into B so HEAD and clean-tree digest match.
3. In B set the same `remote.origin.url` and a foreign `remote.origin.pushurl`; read the push URL only as fixture evidence.
4. Patch the process environment with `GIT_DIR=B/.git` and `GIT_WORK_TREE=B`.
5. Evaluate, but never execute, `git push origin feature`.
6. Assert `allowed is False`; the reason contains `GIT_DIR` and `GIT_WORK_TREE`, contains the action/ambiguity, and contains neither B's path nor either remote URL.

Repeat the denial with `GIT_DIR` only, `GIT_WORK_TREE` only, each key present with an empty value, and `git-push-tag`. These cases pin presence-based fail-closed behavior.

Mutation expectations:

- removing the policy denial must make the same-identity fixture allow;
- restoring ambient Git inheritance to all probe paths must fail root-binding tests;
- sanitizing probes while removing denial must be caught as the unsafe split-brain mutant.

### P0 — probes remain bound to A

In `tests/test_util_fingerprint.py`, create a different-HEAD B and make A dirty with a tracked edit plus an untracked included file. Record clean-environment values for:

- `git_head(A)`;
- `find_root(A)` and `git_output(A, "rev-parse", "--show-toplevel")`;
- `changed_files(A)`;
- `changed_file_statuses(A)`;
- `tree_fingerprint(A)`.

Under `GIT_DIR=B/.git`, `GIT_WORK_TREE=B`, and both together, assert every A result remains equal to its clean-environment baseline. The dirty A arm is required: HEAD-only tests do not execute the direct `_git_paths` / `_git_name_status` seams.

In `tests/test_policy.py`, create a grant for A, then use a mismatching B under inherited selectors and assert `has_valid_approval(A, ...)` has the same result as in the clean environment. Policy denial must be attributable to execution ambiguity, not to silently reading B.

### P0 — real hook boundary denies

In `tests/test_hooks.py`, run the actual `pre_tool_use.py` subprocess with payload cwd A and inherited foreign selectors. `patch.dict(os.environ, ...)` around the existing `run_hook` helper is sufficient because the subprocess inherits the parent environment; avoid changing the shared helper unless a test needs an explicit environment API.

Assert:

- decision and `permissionDecision` are `deny`;
- the reason names selectors but not their values;
- the denial ledger is written under A, not B;
- no refs, remotes, worktree files, or HEADs in either fixture changed.

### P1 — compatibility controls

- Clean environment plus exact branch-push grant remains allowed.
- Exact branch grant does not authorize tag push; existing action-mismatch behavior remains.
- Tree change, new commit, expired grant, foreign repository identity, and conflicting current/legacy digest fields remain denied.
- A benign non-production command and read-only Git status remain unaffected by inherited selectors; this repair is not a process-wide Git ban.
- `add_approval(A, ...)` under inherited selectors stores A's repository, HEAD, and binding digest, never B's.
- Non-UTF-8 filenames, NUL-delimited inventory validation, ignored scratch paths, staged deletion/rename/copy status, missing Git, and timeout/error behavior retain current tests.
- Source/static assertion: no denial output formats or logs interpolate `os.environ[selector]` values.

Focused preflight should run at least:

```bash
python3 -m unittest tests.test_policy tests.test_util_fingerprint tests.test_hooks
```

Then run the route-required full preflight on the committed candidate:

```bash
python3 scripts/grok_verify.py --mode pr
```

Independent code, test, security, and release reviews must inspect the same final tree. Security review must reproduce the same-identity foreign-clone case without a push and verify both single-control mutants are killed.

## Rollout and observable signals

1. Record this design and the typed acceptance criteria, then stop for `scope_and_design_approval`.
2. The sole `general_implementer` adds failing characterizations before implementation.
3. Implement only the Git-probe adapter, push-selector denial, and focused tests listed above.
4. Commit before final fingerprint-bound verification; any later repository change invalidates receipts.
5. Run focused tests, full PR verification, then all four independent reviews and fresh receipts.
6. Do not push or open/update a PR from this task without separate exact delegation. Because the current hook is the vulnerable boundary, publication must come from an operator-controlled clean environment with destination independently verified.
7. Merge only after the App-owned `adaptive-trust-ci/verified@06ecf1c875bc` succeeds on the exact up-to-date head and all required signed scopes are present.

Success signals:

- adversarial policy and hook fixtures deny before execution;
- denial text identifies selector names without leaking values;
- root-bound probes return A's exact results under hostile selectors;
- clean exact-grant behavior remains green;
- no push/network invocation occurs in tests;
- full verification and independent security review pass on one fingerprint.

## Rollback and recovery

Forward-fix is preferred because reverting reopens an authorization bypass. Trigger rollback consideration only for a demonstrated regression in clean-environment root probes or ordinary exact-grant decisions that cannot be safely forward-fixed before delivery.

If the commit must be reverted:

1. revert the exact change commit; there is no data migration or grant-schema conversion;
2. immediately prohibit agent-executed delegated Git pushes/tags/merges/releases through this policy path;
3. invalidate/recreate any local receipts or grants whose repository tree changed;
4. reproduce the bypass and the compatibility regression against the reverted/current state;
5. ship a corrected two-control forward fix through the same security gate.

Rollback is containment failure, not restoration of normal service. Never work around the denial by clearing policy checks, trusting `remote.origin.url` alone, or accepting a grant validated against ambient Git state.

## Out of scope

- #226 timeout serialization, #95 verifier source/target binding, #58's complete push destination/ancestry policy, #217 route-gate validity, and any broader cleanup wave;
- changing production-grant resource requirements or grant schema;
- editing deployed Trust CI policy/holdout/trust stores or branch protection;
- any real push, merge, tag, release, deployment, remote lookup, or network test;
- denying all Git environment variables without a separately reviewed closed-list threat model.
