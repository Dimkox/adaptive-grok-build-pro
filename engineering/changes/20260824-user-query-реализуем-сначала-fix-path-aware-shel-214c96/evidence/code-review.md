# Code review — PR #6 follow-up (path-aware shell policy + circuit breaker)

Reviewer: `code_reviewer` (read-only).  
HEAD: `6ebb219190574940bed350907323aa0d56604295` on `fix/path-aware-shell-policy-circuit-breaker`.  
Compared: `git diff origin/main` and uncommitted `git diff HEAD`.  
No merge, push, or product-code edits.

## Scope vs change package

Package `20260824-user-query-реализуем-сначала-fix-path-aware-shel-214c96` wants PR #6 verified and only fixed if tests fail; merge stays out of scope.

Committed delta vs `origin/main` (8 files): path-aware shell targeting (`shell_targets.py` + `policy.py` split), PreToolUse denial circuit breaker, AGENTS/SKILL circuit-breaker docs, tests.

Uncommitted vs HEAD (intended follow-up, not extra product surface):

- Restore `_CONTROL_PLANE_BATCH_GUIDANCE` / `grok_protected_write.py` on control-plane shell denials while keeping the circuit breaker.
- `# nosec B105` on `'-'`, `'--'`, `'-i'` literals.
- Extra argv mutation deny cases in `tests/test_policy_shell_targets.py`.

Untracked `engineering/changes/**` trees are session paperwork, not PR #6 product.

## Regression checks

| Check | Result |
| --- | --- |
| `docker cp …:/tmp/…` and `curl -o /tmp/trust-ci-live.body` allowed | Pass. Targets resolve outside the repo (`safe_relative_path` is `None`); substring `trust-ci` no longer trips the guard. Covered by `test_names_outside_repo_do_not_trigger_control_plane`. |
| `AGENTS.md` shell mutation denied | Pass. Redirect and argv paths that stay in-repo and match control-plane patterns are denied. |
| Named targets in the reason | Pass in implementation: `Blocked control-plane shell mutation targeting {targets}`. Redirect test asserts `AGENTS.md` in the reason. Uncommitted argv cases only assert `allowed is False` (do not assert the name string). |
| Batch guidance | Pass on working tree: `_actionable_reason` appends `grok_protected_write.py --manifest` unless already present. Circuit-breaker prefixes still wrap that message on repeat denials. |
| Secrets / credentials | Pass. No `.env`, keys, or dumps. Secret-read patterns unchanged in legacy defaults. |
| Merge / deploy | Not performed. |

## Implementation notes (non-blocking)

- `evaluate_pre_tool` uses a process-wide monkeypatch of `_legacy._is_control_plane_shell_mutation` under a lock. Correct for in-process tests; do not call it concurrently from multiple processes without the lock.
- Opaque fallback still requires both unresolved mutation *and* a control-plane prefix in the command; docker/tmp false positives should stay off that path.
- `# nosec B105` is a bandit false-positive suppression on flag tokens, not a secret.

## Verdict

Working tree matches the path-aware deny/allow contract, restores batch grant guidance, keeps the circuit breaker, and does not introduce secrets or merge. Minor test gap: argv cases should also `assertIn` the protected path in `reason` (test_reviewer).

PASS
