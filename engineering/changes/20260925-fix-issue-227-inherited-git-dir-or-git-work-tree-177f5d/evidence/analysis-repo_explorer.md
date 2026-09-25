# Repository exploration — issue #227 inherited Git repository selectors

## Scope and source identity

Read-only inspection of the current `main` implementation for route `177f5dc1d5cf`. No push, network access, grant creation, or product-tree mutation was performed.

- worktree: `/home/pall/grok-projects/adaptive-grok-build-issue227`
- branch: `fix/issue-227-git-env-grant-boundary`
- `HEAD`: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- local `origin/main`: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- `HEAD^{tree}` and `origin/main^{tree}`: `881cb6f0ad65ecd131904adf701829e8146b60e3`
- route base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- product status before this report: clean; the active change package was untracked workflow evidence

The route and its typed change package are still drafts: `change-spec.yaml` has no acceptance criteria or forbidden outcomes, and the route's `scope_and_design_approval` gate is pending. This report therefore identifies code/test boundaries and a bounded repair; it does not supply or simulate approval.

## Finding

**Security defect confirmed by deterministic code trace.** The explicit `root: Path` supplied to approval creation and policy validation is not authoritative for their Git probes. Ambient `GIT_DIR` and `GIT_WORK_TREE` are inherited by every relevant Git subprocess. If the same redirected environment is present when a local grant is created and later checked, the grant's repository, HEAD, and binding digest can all be derived from the redirected repository. The pre-tool policy can then allow `git push`; the eventual Git command would inherit the same selectors and operate on the redirected repository/push URL.

The existing cross-root command parser does not close this path. It recognizes selectors written in command text, such as `GIT_DIR=/other/.git git push`, but inherited process variables are absent from the command string and tool input.

### Trust boundary

- Trusted authorization inputs: resolved repository root, active route/change, exact action, HEAD, and tree binding.
- Untrusted input currently crossing the boundary: the hook/CLI process environment, specifically repository-selection variables `GIT_DIR` and `GIT_WORK_TREE`.
- Protected asset: a production grant's exact repository/head/tree/action binding.
- Required invariant: internal Git probes must derive identity and state only from the canonical root; a production Git action must be denied explicitly while inherited repository selectors are present, even if a grant would otherwise validate.

## Exact call graph on current main

### Grant creation

1. `scripts/grok_approve.py:54-63` calls `add_approval(find_root(), ...)`.
2. `.grok-stack/adaptive_grok/util.py:22-41` resolves a root. A directory containing `.grok-stack` is found without Git, but its fallback `git rev-parse --show-toplevel` at lines 29-36 also inherits ambient Git variables.
3. `.grok-stack/adaptive_grok/state.py:187-265` creates the grant:
   - `git_head(root)` at line 237;
   - `_repository_identity(root)` at line 251;
   - `tree_fingerprint(root)` at line 255.
4. `_repository_identity` at `state.py:173-178` calls `git_output(root, 'config', '--get', 'remote.origin.url')`.
5. `git_head` at `util.py:133-134` calls `git_output(root, 'rev-parse', 'HEAD')`.
6. `git_output` at `util.py:124-130` calls `run(['git', ...], cwd=root)`. `run` begins from `os.environ.copy()` at lines 78-103, so `cwd=root` does not neutralize `GIT_DIR` or `GIT_WORK_TREE`.
7. `tree_fingerprint` at `util.py:330-346` binds the Git head plus `changed_files(root)`. `changed_files` at lines 282-319 calls both `git_head` and `_git_paths`.
8. `_git_paths` at `util.py:162-174` and `_git_name_status` at lines 177-218 invoke `subprocess.run(['git', ...], cwd=root)` without `env=`, so they inherit the same selectors independently of `run()`.
9. `state.py:242-258` persists the resulting `repository`, `git_head`, and `grant_binding_digest`. All three Git-derived fields can therefore share the same redirected source and appear internally consistent.

### Pre-tool authorization

1. `.grok/hooks/pre_tool_use.py:221-240` reads the event, computes `root_context`, and classifies the action with `sensitive_action`.
2. `.grok/hooks/_lib.py:248-327` extracts command-local `GIT_DIR`, `GIT_WORK_TREE`, `git -C`, `--git-dir`, and `--work-tree` selectors from text. It does not inspect inherited `GIT_DIR` or `GIT_WORK_TREE`. `_root_context` at lines 330-395 therefore retains the session/effective root for a plain `git push` even when the process environment redirects Git.
3. `.grok-stack/adaptive_grok/policy.py:24-50` classifies the command; `evaluate_pre_tool` at lines 53-88 delegates production policy to the legacy evaluator after the structured shell-mutation check.
4. `.grok-stack/adaptive_grok/_policy_legacy.py:516-528` analyzes authority. `_production_action` at lines 267-296 maps a push to `git-push-branch` or `git-push-tag`.
5. `_policy_legacy.evaluate_pre_tool` at lines 562-607 checks the action, then the human gate, then `has_valid_approval(root, 'production', action=action)` at line 597. There is no process-environment rejection.
6. `state.has_valid_approval` at lines 268-333 recomputes repository identity (line 285), HEAD (line 288), and tree digest (line 298) through the same ambient-sensitive functions used at grant creation. A grant minted and checked under the same redirection can match at lines 317-325.
7. The evaluator then returns allow. The hook emits allow at `pre_tool_use.py:257-265`; if the tool executes the original `git push`, Git will see the still-inherited repository selectors.

### Existing safeguards and the gap

- `_policy_legacy.py:267-285` correctly recognizes command-line `--git-dir`/`--work-tree` and push actions.
- `_lib.py:248-327` correctly makes command-local repository selectors part of root resolution; `tests/test_hooks.py:270-330` covers these cross-repository forms.
- `tests/test_policy.py:105-120` covers classification of `env GIT_DIR=... git push`.
- None of `tests/test_policy.py`, `tests/test_hooks.py`, or `tests/test_util_fingerprint.py` sets inherited `GIT_DIR`/`GIT_WORK_TREE` around grant creation or evaluation.
- `scripts/package_stack.py:515-553` is a useful repository-local precedent: its read-only Git invocation removes ambient `GIT_*`, fixes `-C` to a canonical root, disables replacement refs/config influence, and sets `GIT_OPTIONAL_LOCKS=0`. Its regression at `tests/test_manifest_package.py:411-450` includes a decoy repository and multiple ambient Git variables. That helper is private to packaging and is not used by `adaptive_grok.util`.

## Minimal repair boundary

### Required production files (2)

1. **`.grok-stack/adaptive_grok/util.py`**
   - Centralize an internal, read-only, root-bound Git invocation.
   - Resolve the supplied root canonically, invoke Git with that root (for example via `git -C <canonical-root>`), and pass an environment that cannot select a different repository/worktree. Clearing all inherited `GIT_*` for internal probes is the smallest robust analogue of the existing packaging boundary; restore only explicitly safe read-only settings such as `GIT_OPTIONAL_LOCKS=0`.
   - Route `git_output`, `_git_paths`, and `_git_name_status` through the same boundary. Also sanitize the `find_root` Git fallback, although marker-based resolution is the path used by this repository.
   - Do not globally change `run()` semantics for unrelated commands unless unavoidable; the vulnerability is the internal Git-probe boundary.

2. **`.grok-stack/adaptive_grok/_policy_legacy.py`**
   - For a recognized `git-push-branch` or `git-push-tag` action, check for inherited `GIT_DIR` and `GIT_WORK_TREE` before human-gate/grant validation.
   - Deny explicitly and name the present variable(s). Presence should fail closed even if a matching grant exists; sanitizing internal probes alone would otherwise allow a legitimate root-bound grant while the eventual `git push` remained redirected.
   - Keep the check limited to Git push production actions for this issue. The existing policy wrapper should continue delegating to this single production-authorization point.

No production edit is required in `state.py`, `policy.py`, `.grok/hooks/_lib.py`, `.grok/hooks/pre_tool_use.py`, or `scripts/grok_approve.py` if the two central boundaries above are repaired. Their callers then inherit root-bound probe behavior, while the authorization point supplies the explicit denial.

### Required regression files (2)

1. **`tests/test_policy.py`**
   - Build intended and decoy temporary Git repositories with different GitHub remotes/HEADs.
   - Under `patch.dict(os.environ, {'GIT_DIR': ..., 'GIT_WORK_TREE': ...})`, call `add_approval` for the intended root and assert its `repository`, `git_head`, and `grant_binding_digest` remain identical to clean intended-root values, not decoy values.
   - With an otherwise valid `git-push-branch` grant, evaluate (do not execute) `git push origin feature` under each inherited override independently and together. Assert denial and an explicit reason naming the offending selector.
   - This test kills both incomplete mutants: “sanitize probes but permit redirected push” and “deny redirected push but keep grant bindings ambient-sensitive.”

2. **`tests/test_hooks.py`**
   - Add one end-to-end hook regression. `run_hook()` already launches a subprocess that inherits the test process environment, so `patch.dict(os.environ, ...)` requires no change to `tests/_support.py`.
   - Create a valid grant in the intended temporary repository first, then run the pre-tool hook with inherited `GIT_DIR`/`GIT_WORK_TREE` pointing at a decoy and a plain `git push` payload. Assert `permissionDecision == 'deny'` and that the reason names the inherited selector.
   - The test must stop at hook evaluation. It must never invoke `git push` or use a network remote.

An additional direct test in `tests/test_util_fingerprint.py` would be useful defense in depth, but is not necessary for the minimal vertical regression if `tests/test_policy.py` verifies all three stored binding fields under a decoy environment.

## Acceptance behavior to freeze before implementation

1. Internal repository identity, HEAD, changed-file inventory, and binding digest are invariant under inherited `GIT_DIR` and `GIT_WORK_TREE`.
2. A plain Git push command is explicitly denied when either inherited selector is present, even with an otherwise valid exact-action grant.
3. Command-local cross-root selectors remain denied by the existing root-context logic.
4. A clean environment plus a valid exact-action grant retains current allow behavior.
5. Tests evaluate policy only; no push, remote contact, or real-worktree grant is permitted.

## Reproducible inspection and verification commands

These commands are read-only against the real worktree; the focused tests create only disposable repositories through `tests._support.project_copy`.

```bash
cd /home/pall/grok-projects/adaptive-grok-build-issue227
git rev-parse HEAD origin/main HEAD^{tree} origin/main^{tree}
git status --short
nl -ba .grok-stack/adaptive_grok/util.py | sed -n '22,218p;282,346p'
nl -ba .grok-stack/adaptive_grok/state.py | sed -n '169,333p'
nl -ba .grok-stack/adaptive_grok/_policy_legacy.py | sed -n '267,296p;516,607p'
nl -ba .grok/hooks/_lib.py | sed -n '248,395p'
nl -ba .grok/hooks/pre_tool_use.py | sed -n '221,300p'
python3 -m unittest tests.test_policy tests.test_hooks
```

After implementation, run the route-selected base/contracts verification in addition to the focused tests. This report did not run tests because the current task is read-only seam analysis and the failing regressions do not yet exist.
