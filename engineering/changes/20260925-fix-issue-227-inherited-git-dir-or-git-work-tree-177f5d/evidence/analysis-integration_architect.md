# Integration architecture analysis — issue #227 Git environment/grant boundary

Route `177f5dc1d5cf`; source HEAD and local `origin/main` `cb9af4073ba6c3d515145164d771c75ebdfa3224`; observed 2026-09-25 UTC. The explicit no-network instruction superseded the repository's normal fetch step, so no fetch or other network access was attempted. This analysis created grants only inside disposable temporary repositories. It did not create a grant in the candidate worktree and never executed `git push`.

## Outcome and recommendation

Issue #227 is a confirmed authorization-boundary defect on current main. With a legitimate grant for repository A, a same-HEAD/same-tree repository B selected through inherited `GIT_DIR`/`GIT_WORK_TREE` can make `has_valid_approval(A, ...)` return true and `evaluate_pre_tool(A, "git push ...")` return allow. Repository B can carry a different `remote.origin.pushurl`, so the policy-approved resource and Git's execution resource diverge.

Proceed only with a paired repair:

1. grant identity/fingerprint probes must be rooted exclusively in their explicit `root` argument; and
2. a production Git action must fail closed when inherited repository-selection overrides are present, even if they resolve to the same root or happen to reproduce every stored grant field.

Either half alone is unsafe. In particular, cleaning policy probes while letting the eventual shell inherit a redirect can turn a previously false-negative grant check into an authorization bypass.

## Assets, actors, entry points, and trust boundaries

| Item | Role | Required boundary |
| --- | --- | --- |
| Human delegation | Authorizes an exact local operation | Cannot be widened by process environment or repository-controlled configuration |
| Payload `cwd` / command working-directory evidence | Selects the intended repository | Canonical input to policy root resolution |
| `os.environ` | Mutable execution context | Untrusted as a source of grant/repository identity |
| `.grok-stack/runtime/approvals.json` | Local delegated-grant evidence | Repository/route/change/HEAD/tree/action/TTL remain exact; not merge authority |
| Pre-tool policy | Decides whether a sensitive command may execute | Must deny when execution repository is ambiguous before consulting/consuming a grant |
| Git probe subprocesses | Derive remote identity, HEAD, changed paths, and tree digest | Must use the explicit canonical root, not ambient `GIT_DIR`/`GIT_WORK_TREE` |
| Git command subprocess | Would perform the external write | Inherits environment; must never run when environment can redirect the repository |
| `remote.origin.url` | Current grant repository label | Not equivalent to the actual push destination when `pushurl` is configured |
| `remote.origin.pushurl` | Actual target used by `git push origin ...` | Must not be reachable through an environment-selected foreign repository under a grant for A |
| External Trust CI | Authoritative exact-SHA merge check | Unchanged; local grants and this policy repair do not replace it |

Actors are the human delegator, the agent/tool caller, the pre-tool hook/policy, the local grant store, Git, and the external Git remote. The hostile input in this defect is inherited process environment, not the issue text or the local approval record.

## Confirmed root cause and call chain

The first incorrect state is not the generic missing-grant message. It is use of ambient Git repository selectors in control-plane probes whose API already accepts an explicit repository root.

1. `.grok/hooks/_lib.py:305-397` resolves a payload/session root. Its command parser detects literal `GIT_DIR=...`, `GIT_WORK_TREE=...`, `git -C`, and `--git-dir` at lines 176-302, but inherited values are not present in `RootContext`.
2. `.grok/hooks/pre_tool_use.py:240-262` passes the resolved root to the public policy.
3. `.grok-stack/adaptive_grok/policy.py:53-88` performs its shell-target checks, then delegates production policy to `_policy_legacy.evaluate_pre_tool`.
4. `.grok-stack/adaptive_grok/_policy_legacy.py:588-599` classifies `git push`, checks the human gate, and calls `has_valid_approval`.
5. `.grok-stack/adaptive_grok/state.py:173-178,237-255,268-333` derives repository, HEAD, and binding digest with `_repository_identity`, `git_head`, and `tree_fingerprint`.
6. `.grok-stack/adaptive_grok/util.py:78-134` copies all of `os.environ` into `run()` and therefore into `git_output`. `_git_paths` and `_git_name_status` at lines 162-218 invoke Git directly with the same ambient environment. `changed_files`/`tree_fingerprint` at lines 282-346 inherit the redirect too.
7. A mismatching foreign checkout produces a false-negative grant check and the wrong generic reason. A matching foreign checkout reproduces the binding and is authorized; the eventual shell command remains redirected to that checkout.

Existing hardened reference patterns are local and should guide, not be imported as private dependencies:

- `.grok-stack/adaptive_grok/architecture_diff.py:159-171,174-228` uses a minimal Git environment, explicit canonical `cwd`, and safe Git options.
- `scripts/package_stack.py:515-566` removes inherited `GIT_*`, pins `-C`/`core.worktree`, and has adversarial coverage in `tests/test_manifest_package.py:411-450` for multiple repository/config redirects.

Local-only historical commit `69f68704` is not safe to transplant alone: it cleaned `util.run()` Git calls but did not cover direct `_git_paths` probes or deny the eventual environment-inheriting push.

## Safe deterministic reproduction on this route

The reproduction used `tests._support.project_copy(git=True)` for repository A and a local filesystem clone for B. No network-capable command was invoked.

1. Add `remote.origin.url=git@github.com:Dimkox/adaptive-grok-build-pro.git` to A, install a temporary route in A, and call `add_approval(A, 'production', ..., actions=['git-push-branch'])`.
2. Clone A locally to B, preserving the same clean HEAD/tree.
3. Keep B's fetch URL equal to the authorized repository and set B's push URL to the inert test value `git@github.com:attacker/other.git`.
4. Under `patch.dict(os.environ, {'GIT_DIR': B/'.git', 'GIT_WORK_TREE': B})`, call `has_valid_approval(A, ...)` and `evaluate_pre_tool(A, {'tool_name':'Bash','tool_input':{'command':'git push origin feature'}})` only.
5. Read B's push URL with `git remote get-url --push origin`; never execute the push.

Observed on current main:

```text
grant_head              = 7fadf64e5751e9981bb046c81f9cbbebf9963c53  # disposable fixture
git_head_seen_for_root  = 7fadf64e5751e9981bb046c81f9cbbebf9963c53
changed_files_seen      = []
binding_matches         = True
approval_valid          = True
policy                  = (True, None)
foreign_pushurl         = git@github.com:attacker/other.git
```

The fixture SHA is not durable evidence; the security assertions are equality of A/B bindings, the foreign push destination, and the unexpected allow result.

The nearby baseline is green before implementation:

```text
python3 -m unittest tests.test_policy tests.test_hooks tests.test_util_fingerprint
Ran 75 tests in 38.551s
OK
```

## Exact implementation seams

### 1. Root-bound Git probes

Primary product seam: `.grok-stack/adaptive_grok/util.py`.

- Introduce one repository-probe environment/runner used by `git_output`, `_git_paths`, and `_git_name_status`; `git_head`, `changed_files`, and `tree_fingerprint` then inherit one rule.
- Bind Git explicitly to `Path(root).resolve(...)` and remove the repository-selection variables covered by the policy denial from the probe environment.
- Preserve binary/NUL behavior and conservative failure behavior of `_git_paths`/`_git_name_status`.
- Do not silently change arbitrary non-probe command execution. `run()` is used beyond repository identity, so a global environment rewrite requires wider caller proof.

The set of variables ignored by control-plane probes and the set that causes a production Git denial must be the same shared closed set. The required minimum is `GIT_DIR` and `GIT_WORK_TREE`. If implementation strips additional selectors/config injectors such as `GIT_COMMON_DIR`, `GIT_INDEX_FILE`, or `GIT_CONFIG_*`, those variables must also trigger execution denial; otherwise policy and the eventual Git command observe different repositories/configuration.

### 2. Explicit production-action denial

Primary product seam: public `.grok-stack/adaptive_grok/policy.py`, before delegation to the legacy grant check. Keeping the precondition in the public wrapper covers normal hook and direct policy callers without changing the established grant matcher.

- Apply the precondition only when the classified production action is Git-backed (`git-push-branch` or `git-push-tag`). Do not block unrelated reads or non-Git external/protected actions merely because an ambient Git variable exists.
- Any presence of a covered variable is ambiguous, including an empty value or a value that resolves to A itself. Fail closed; do not normalize and allow.
- Reason text must name the variable(s), the action, and the recovery (`unset and retry`) but must not include values/paths.
- Evaluate this condition before `has_valid_approval`; a matching grant cannot override repository ambiguity.

The equivalent precondition may be factored into a small shared helper if needed, but do not change `_policy_legacy.has_valid_approval` callers or the public boolean grant API as part of this fix.

### 3. Test seams

- `tests/test_util_fingerprint.py`: root-bound Git probe and dirty-tree coverage.
- `tests/test_policy.py`: direct policy/grant separation and denial reason.
- `tests/test_hooks.py`: end-to-end inherited-environment denial through the real pre-tool subprocess.
- `tests/_support.py`: only if `run_hook` needs an optional explicit environment argument; default behavior must remain identical.

No OpenAPI, HTTP, event, database, Trust CI, approval-envelope, or external integration contract requires a change.

## Proposed typed acceptance criteria

### AC-001 — probe identity is root-bound

Given two disposable repositories A and B with different HEAD or worktree state, when `GIT_DIR` and/or `GIT_WORK_TREE` point at B and repository probes are called with A, then `git_head(A)`, `changed_files(A)`, and `tree_fingerprint(A)` equal their clean-environment A values. The fixture must make A dirty so a test cannot pass by checking HEAD alone.

### AC-002 — grant creation/validation preserves explicit-root identity

Given a disposable A with a valid route/origin and inherited selectors pointing at B, when a temporary grant is created or validated for A, then its `repository`, `git_head`, and `grant_binding_digest` are derived from A. Grant schema version 2, `grant_binding_digest`, legacy `tree_fingerprint` read compatibility, action/resource/TTL checks, and `has_valid_approval(...) -> bool` remain unchanged.

### AC-003 — inherited repository selectors cannot authorize a push

Given a valid A grant and a same-HEAD/same-tree B whose fetch URL looks authorized but whose push URL is foreign, when policy evaluates a branch or tag push with inherited `GIT_DIR`, inherited `GIT_WORK_TREE`, or both, then policy denies before grant matching. The reason names each present variable and the Git action, says to unset/retry, and contains neither variable values nor foreign paths/URLs.

### AC-004 — real hook preserves the denial

Given the same fixture and a hook payload whose `cwd` is A, when `.grok/hooks/pre_tool_use.py` runs in a subprocess carrying the inherited override, then its structured response is `deny` with the same actionable reason. The test must not execute a push or perform network access.

### AC-005 — clean and existing fail-closed behavior remain compatible

With no covered ambient override, a matching branch-push grant remains allowed. Missing, expired, wrong-action, changed-HEAD/tree, conflicting legacy/current binding, and foreign-repository grants remain denied. Existing command-local `GIT_DIR=...`, `env GIT_DIR=...`, `git --git-dir`, `git -C`, nested-shell, and cross-root cases in `tests/test_hooks.py:270-330` stay denied or allowed exactly as currently specified.

### AC-006 — no side effect can hide in the regression

Tests use only policy evaluation, temporary local Git repositories, and read-only `git remote get-url --push`. A guard/mock fails the test if an argv containing Git's `push` subcommand reaches `subprocess`; no DNS, socket, remote fetch, push, grant in the candidate worktree, or external write is permitted.

## Compatibility and security review focus

- Preserve hook response shape (`decision`, `reason`, `hookSpecificOutput`) and grant schema/API. Reason wording is human-facing, so tests should assert stable facts rather than the entire sentence.
- A deliberate inherited override pointing to the same root will newly deny. This is intentional and recoverable by unsetting it; allowing equality would preserve ambiguity and race/config substitution risk.
- Denial ledger reason hashes will change for these invocations. That is expected; do not log override values.
- Root-bound probes are used beyond grants (routing, verification, receipts). Focused tests must cover clean, dirty, staged, untracked, non-Git, and Git-failure behavior so the fix does not weaken fingerprint invalidation.
- Filtering more Git variables in probes without denying them for the actual action is forbidden because it recreates the split-brain authorization condition.
- The reproduction exposes a broader residual: root-local Git config can define a divergent `pushurl`, and production grants are action-bound rather than remote/ref-resource-bound. This route must close the inherited-selector path. The scope gate should either add push-destination binding explicitly with dedicated acceptance or record a successor; it must not claim that all Git remote/ref substitution is solved by #227.
- Rollback is a source revert/forward-fix. No migration, backfill, external reconciliation, or production mutation is involved.

## Gate recommendation

Approve the narrow paired design only after AC-001 through AC-006 are copied into the typed change spec/test plan and the residual push-destination decision is recorded. Implementation should remain with the route's single `general_implementer`; afterward run focused tests, full `grok_verify --mode pr`, and independent code/test/security/release reviews. No local result authorizes push, merge, release, or deployment.

