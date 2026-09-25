# Issue #227 documentation and policy audit

## Scope and evidence boundary

This is a read-only analysis for route `177f5dc1d5cf` at local HEAD
`cb9af4073ba6c3d515145164d771c75ebdfa3224`. Local `origin/main` resolved to
the same commit when the audit was performed on 2026-09-25 UTC. The route
forbids network access, so this audit did not fetch, push, or make any GitHub
write. Issue metadata below is the issue snapshot already captured by the
controller earlier on 2026-09-25; it was not refreshed during this audit.

Primary references:

- [Issue #227](https://github.com/Dimkox/adaptive-grok-build-pro/issues/227)
- [Current `util.py` at the audited commit](https://github.com/Dimkox/adaptive-grok-build-pro/blob/cb9af4073ba6c3d515145164d771c75ebdfa3224/.grok-stack/adaptive_grok/util.py)
- [Current `state.py` at the audited commit](https://github.com/Dimkox/adaptive-grok-build-pro/blob/cb9af4073ba6c3d515145164d771c75ebdfa3224/.grok-stack/adaptive_grok/state.py)
- [Current legacy policy evaluator at the audited commit](https://github.com/Dimkox/adaptive-grok-build-pro/blob/cb9af4073ba6c3d515145164d771c75ebdfa3224/.grok-stack/adaptive_grok/_policy_legacy.py)
- [Current hook root resolver at the audited commit](https://github.com/Dimkox/adaptive-grok-build-pro/blob/cb9af4073ba6c3d515145164d771c75ebdfa3224/.grok/hooks/_lib.py)
- [Prior-art commit `69f68704`](https://github.com/Dimkox/adaptive-grok-build-pro/commit/69f68704e62a9a2ee11fde570cd717ba84aab165)

## Issue claim and current-main result

The captured issue was open, unassigned, without a milestone or comments,
and labeled `bug` and `priority:medium`. It says that inherited `GIT_DIR` or
`GIT_WORK_TREE` can redirect the Git probes used for local grant identity and
asks for an explicit denial that names the environment override instead of a
generic missing-grant response. Its expected test uses a foreign repository
and asserts both denial and the reason.

The claim is confirmed and is stronger than a misleading generic denial. An
offline simulation created an intended repository and a foreign clone with the
same fetch identity, HEAD, and tree, but a different `remote.origin.pushurl`.
It then created a valid intended-root `git-push-branch` grant, set the process
environment to the foreign clone's `GIT_DIR` and `GIT_WORK_TREE`, and evaluated
the command string `git push origin feature`. It did **not** execute a push.
The observed result was:

```text
grant_repository Dimkox/adaptive-grok-build-pro
probe_repository Dimkox/adaptive-grok-build-pro
grant_head ab0603fa...
probe_head ab0603fa...
grant_digest_matches True
approval_valid True
policy_allowed True
policy_reason None
effective_pushurl git@github.com:example/foreign.git
```

This establishes an authorization bypass: approval validation can accept the
grant while Git's eventual repository selection resolves the push target from
the foreign repository. The test was entirely local and inspected the
effective push URL with `git remote get-url --push`; no network operation or
push occurred.

Empty values are also repository-selection overrides for this contract. These
local checks both exited 128:

```text
env GIT_DIR= git rev-parse --git-dir
env GIT_WORK_TREE= git rev-parse --show-toplevel
```

Therefore the safe predicate is environment-variable **presence**, not a
truthy or non-empty value.

## Why current main permits it

- `.grok-stack/adaptive_grok/util.py:78-105` copies all of `os.environ` into
  every command executed by `run()`. `git_output()` and `git_head()` use this
  path, so their `cwd=root` does not neutralize inherited Git selectors.
- `util.py:162-218` runs Git directly in `_git_paths()` and
  `_git_name_status()`, also inheriting the process environment. These paths
  contribute index, diff, and untracked-file data to the tree fingerprint.
- `.grok-stack/adaptive_grok/state.py:173-178,237-255,268-333` derives the
  repository, HEAD, and tree digest through those probes when issuing and
  validating grants. The repository identity uses the fetch URL, not the
  effective push URL.
- `.grok-stack/adaptive_grok/_policy_legacy.py:578-598` classifies a push,
  checks its human gate and then `has_valid_approval()`. It permits the action
  when that redirected validation returns true; it never checks inherited Git
  selectors. When validation merely fails it emits the generic message
  `Production action {action} requires an exact delegated local grant bound to
  the current SHA.`
- `.grok/hooks/_lib.py:246-302,305-350` recognizes command-local assignments,
  `git -C`, `--git-dir`, `--work-tree`, and tool/session working-directory
  aliases. It cannot see inherited `GIT_DIR` or `GIT_WORK_TREE` because those
  values are absent from the command payload.
- Existing hook and policy tests cover command-local root selection and valid
  grants, but not inherited process-level Git selectors.

## Prior-art assessment

Commit `69f68704e62a9a2ee11fde570cd717ba84aab165` is present locally on
`fix/next-green-batch-20260921`, but `git merge-base --is-ancestor 69f68704
origin/main` exited 1. It is not in the audited main lineage.

The commit removes inherited `GIT_*` variables inside `util.run()` only when
the executable is exactly `git` and the caller did not pass any explicit
`env`. Its one test proves that `git_head()` ignores a bare-repository redirect.
That is useful prior art but is not a complete or safe fix for #227:

- `_git_paths()` and `_git_name_status()` bypass `run()` and remain ambient-env
  dependent, so the complete grant fingerprint is not root-bound.
- Passing even an unrelated explicit `env` preserves every inherited Git
  variable.
- It removes all `GIT_*` names rather than defining the repository-selection
  variables and the intended compatibility boundary.
- Most importantly, sanitizing only the internal approval probes can validate
  the intended repository while the actual shell `git push` still inherits
  selectors and targets the foreign repository. Probe isolation without an
  authorization-time denial would therefore preserve the dangerous split.

Existing safer patterns are
`.grok-stack/adaptive_grok/architecture_diff.py:_git_environment()` and
`scripts/package_stack.py:_git_invocation()`: both deliberately construct a
Git invocation environment instead of assuming that `cwd` defeats Git's
repository-selection variables.

## Required two-part contract

1. Root-bind every internal Git probe used to issue or validate a grant. A
   dedicated probe helper should remove inherited repository-selection
   metadata and explicitly bind the resolved repository root. It must cover
   repository URL, HEAD, tracked/staged/unstaged state, and untracked inventory,
   including direct subprocess paths; changing `git_output()` alone is
   insufficient.
2. Before checking a human gate or delegated grant for `git-push-branch` or
   `git-push-tag`, fail closed when either `GIT_DIR` or `GIT_WORK_TREE` is
   present in the hook process environment. This is required even if the value
   is empty and even if a valid grant exists. Do not inspect, interpolate, log,
   or otherwise disclose the values.

The exact user-facing first-denial contract should be frozen as:

```text
Production action {action} denied: inherited Git repository selection is overridden by {names}. Unset the named variable(s) and retry from the intended repository root; no delegated grant is valid for a Git push while an override is present.
```

Contract details:

- `{action}` is the already-classified `git-push-branch` or `git-push-tag`.
- `{names}` is the deterministic, sorted, comma-separated subset of
  `GIT_DIR`, `GIT_WORK_TREE` that is present.
- Presence includes an empty string.
- The message names variables only. It must not contain variable values,
  command text, remote URLs, or push URLs.
- `pre_tool_use.py` should surface this policy reason in both the top-level
  `reason` and `hookSpecificOutput.permissionDecisionReason`. The existing
  circuit breaker may prepend its repeat-denial guidance later, while retaining
  the underlying reason.
- The denial ledger may retain its generic production-action reason and hashes,
  but must not add raw environment values.

Minimum regression coverage is: each variable alone, both variables, and each
present with an empty value; a valid intended-root grant; a same-identity
foreign clone with a different push URL; exact denial text; and proof of the
would-be target using a read-only URL query. No test should execute `git push`.
Separate probe tests should demonstrate that repository identity, HEAD, and the
full tree fingerprint still describe the explicit intended root under ambient
redirects. Existing command-local override and benign/read-only behavior tests
should remain unchanged.

## External-action boundary

The route's `scope_and_design_approval` is pending. It is the gate for
implementation scope; it does not authorize any external operation. Under the
repository contract and active route:

- No network access, GitHub comment, issue close, pull-request creation/update,
  push, merge, tag, release, deployment, or other external write is authorized
  by this audit.
- A later branch push requires explicit user delegation materialized as an
  exact `git-push-branch` local grant for the current repository, route, change,
  HEAD, tree fingerprint, and resource.
- A merge separately requires an exact `pull-request-merge` delegation plus
  the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on the exact
  PR head and all applicable external signed approvals. A local grant cannot
  substitute for those controls.
- Commenting on or closing issue #227 is a distinct GitHub write and requires
  explicit delegation; neither the scope/design approval nor a push grant
  covers it.
- Implementation must receive the route-required independent security, code,
  test, and release-readiness reviews and fingerprint-bound verification. No
  agent may create, request, read, or simulate human private-key approval
  material.

## Commands used

All commands were local and read-only except creation of disposable temporary
repositories and this evidence file:

```text
git rev-parse HEAD
git rev-parse origin/main
git merge-base --is-ancestor 69f68704e62a9a2ee11fde570cd717ba84aab165 origin/main
git show --stat --oneline 69f68704e62a9a2ee11fde570cd717ba84aab165
git show --format=fuller --no-ext-diff --unified=25 69f68704e62a9a2ee11fde570cd717ba84aab165 -- .grok-stack/adaptive_grok/util.py tests/test_util_fingerprint.py
rg -n "GIT_DIR|GIT_WORK_TREE|git-push|has_valid_approval|remote.origin.url" .grok-stack scripts tests AGENTS.md README.md
env GIT_DIR= git rev-parse --git-dir
env GIT_WORK_TREE= git rev-parse --show-toplevel
```

The offline reproduction used `tests._support.project_copy(git=True)`, local
`git clone --no-local`, `state.add_approval()`, `state.has_valid_approval()`,
and `policy.evaluate_pre_tool()` with a push command string. It did not invoke
the push command. No `git fetch`, GitHub API call, or other network command was
run because the active route expressly forbids network access.
