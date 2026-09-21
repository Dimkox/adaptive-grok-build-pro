# #50, #57, #54: read-only doctor and preflight diagnostics

## Shared boundary

The common user surface is `scripts/grok_doctor.py` / `.grok-stack/adaptive_grok/doctor.py`. These are three distinct probes: repository model validity, Python suite readiness, and local Git risk. Implement them as separate results with bounded runtimes and concrete remedies. A diagnostic never mutates Git, installs packages, changes architecture files, or declares a full verification pass. The historical issue counts (32 architecture errors, 39 fake test failures, 46 worktrees/350 unpushed commits) are examples, not current assertions.

## Slice A — #50 architecture preflight

When architecture adoption is configured, run a cheap `load_architecture(root)` before suite discovery; report one failure naming `architecture/system.yaml`, the offending node and bad repository path. Existing `_safe_relative_path` intentionally rejects trailing slashes; retain that rule. If source line is required, derive it from a bounded parser/source map rather than guessing from string search, since a repeated path may occur more than once. A single `doctor` failure must be visible before tests, and `grok_verify` should abort expensive dependent suites after the same malformed-model finding. Existing `scripts/grok_architecture.py validate` is another narrow preflight entrypoint. Tests: canonical model passes; one trailing-slash fixture yields one actionable diagnostic and no suite dispatch; absent consumer architecture remains legitimately optional. Likely files: `doctor.py`, `verification.py`, architecture error context, `tests/test_verification_doctor.py`/architecture tests.

## Slice B — #57 Python suite readiness

Before advertising optional factory, Trust CI, pilot or delivery test commands, inspect the matching `pyproject.toml` runtime dependencies in the current Python interpreter using import metadata or a bounded import probe. Report `ready`, `missing packages`, or `suite not present` separately; avoid calling unit-test discovery merely to infer missing modules. The doctor must name the selected interpreter, missing distributions, the correct project/environment installation command, and the corrected delivery `PYTHONPATH` (includes `factory/src`). Do not silently install dependencies and do not fail a consumer that does not ship a given optional suite. Tests mock missing `fastapi`/`psycopg` and a ready environment, and validate guide commands. Likely files: `doctor.py`, relevant README/runbooks, focused doctor tests.

## Slice C — #54 Git inventory audit

Add an optional `grok_doctor --git-audit` or `scripts/grok_git_audit.py` read-only probe. Obtain worktrees (`git worktree list --porcelain`), branch/upstream relation (`for-each-ref`), unique local commits relative to available remote refs, and stash count using `-z`/structured formats where supported. Bound output and subprocess time; report counts plus a sample of affected refs, explicitly say when remotes are absent or stale. Flag a feature branch tracking `origin/main`, a gone upstream, dirty worktrees and commits not reachable from fetched remote refs; never auto-push, prune, reset, apply stashes, or label all unpushed commits disposable. This checkout currently lists 143 worktrees, 19 branches tracking `origin/main`, and 5 stashes, illustrating why the original 46/4 counts cannot be reused as live state. Tests use a tiny temporary repository with one dirty linked worktree, wrong upstream, gone upstream and local-only commit. Likely files: new bounded Git-audit helper, `doctor.py` CLI wiring, focused tests, `AGENTS.md` only if the branch-upstream rule is adopted.

## Delivery order

Land A and B as independent diagnostic patches if desired. C can follow without sharing parsing logic; its operational follow-up is a separate decision per branch. Run focused tests first, then required routed verification and independent review for each product change. Rollback is removing each additive doctor result; no persistent data or Git state is changed by the probes.
