# Architect analysis — issues #186 and #36

Analysis scope: historical/base evidence intentionally audited origin/main at
130ce4a42d9f9bbd1b56772d40b19ae530283205. Candidate package identity and the
post-evidence tree are bound separately by owner-mapping.md, the review reports,
and the final verifier receipt.

## Basis and commands

Audited the fetched `origin/main` at `130ce4a42d9f9bbd1b56772d40b19ae530283205`.
The issue statements were checked at [#186](https://github.com/Dimkox/adaptive-grok-build-pro/issues/186) and [#36](https://github.com/Dimkox/adaptive-grok-build-pro/issues/36).

Commands used:

```text
git fetch --all --prune
git rev-parse origin/main
rg --files origin/main | rg '(^|/)(verify|receipt|run|exit|status|execution|command|trust)'
git grep -n -i -E 'exit.?status|status.?file|record.*status|record.*exit|returncode|CalledProcessError' origin/main -- ':!engineering/changes/**' ':!PROJECT_STATE.json' ':!mistakes.md'
git log --all --oneline --decorate --grep='issue #186\|#186\|issue #36\|#36' -i -- . ':!engineering/changes/**'
```

## Findings

- #36's reported owner is a shell function using `if ! "$@" >"$log" 2>&1; then code=$?; fi`. The repository-wide search finds no tracked implementation of that shape, no shell `rec`/`rec2` equivalent, and no command that owns the described recorder.
- The current executable paths are different: `origin/main:.grok-stack/adaptive_grok/python_test_runner.py:181,285-325`, `origin/main:.grok-stack/adaptive_grok/verification.py:357-358,973-974`, and `origin/main:trust-ci/src/adaptive_trust_ci/sandbox.py:180` consume or preserve process return codes directly. These are not evidence that the #36 shell defect exists in this repository.
- The repository has no `package.json`, `verify:deploy`, or tracked multi-file shell gate corresponding to the adjacent #35 finding. The same absence is material for #36: there is no repository-owned shell command to repair.
- `git log` found no repository history entry whose implementation or test owns #36. The issue metadata also reports no assignee, branch, or pull request. #186 itself records the same owner-mapping result for #36.
- Trust CI is a separate deployed authority. Its source references above do not make the external shell report repository-owned, and this disposition must not claim to repair deployed Trust CI behavior.

## Architecture/disposition

Adding a helper would be speculative: it would create a new recorder rather than fix the reported one. Adding a regression test would likewise be speculative because there is no existing repository command whose behavior the test could bind. Adding general documentation would not establish an owner or correct #36; only a durable disposition is justified.

The smallest honest repository-owned change for #186 is this evidence report, bound to the exact audited `origin/main` SHA. It records #36 as external/misrouted pending an upstream owner path and reproduction that runs against this repository. No product source, test, contract, route, or authority file should change in this wave.

## Recommendation

Close or disposition #186 only after attaching this report as its binding evidence and explicitly linking #36 as external/misrouted. Keep #36 open with an external-owner request: provide the repository and exact file/command that contains the shell recorder, plus a reproduction against that owner. If such an owner is later proven inside this repository, route a separate bugfix that first adds a failing regression test and then applies the minimal `"$@" ... || code=$?` repair with execution evidence. Until then, implement nothing beyond this report.
