# M1 security re-review 7

## Verdict

**PASS** for exact HEAD `98649e4e1e6a971fb802bc934eb5680de529e18a` against prior reviewed HEAD `9a6e27c193ec944a149e452ff7591fbc7493238c`.

The constructor-allocation remediation closes the partial-workspace resource leak reported by the prior code/test review-6 reports. Checkout and trusted-config allocation now form one guarded transaction, all known partial allocations receive best-effort cleanup before the original exception is re-raised, and attributes are published only after complete initialization. No weakening or regression was found in trusted Git configuration isolation, bounded subprocess handling, process-group cleanup, exact path approvals, or earlier M1 parser/provenance boundaries.

## Exact-HEAD evidence

- Initial `git rev-parse HEAD` — `98649e4e1e6a971fb802bc934eb5680de529e18a`; initial `git status --short` was clean.
- Focused Trust CI security suites (`test_workspace`, `test_policy`, `test_runner`, holdout, signing, PostgreSQL) — **100 total, 90 passed, 10 skipped**. The skips are the disclosed conditional PostgreSQL tests because `TRUST_CI_TEST_DATABASE_URL` is not configured.
- Full root discovery — **223 passed**.
- Full Trust CI discovery — **200 total, 190 passed, 10 skipped**.
- `git diff --check 9a6e27c193ec944a149e452ff7591fbc7493238c..HEAD` — passed.
- Holdout bundle remained exactly `change_spec_validate.py` and `validate.py` after testing.

## Constructor lifecycle review

- `_remove_tree_quietly()` accepts only an allocated `Path`, performs best-effort recursive removal, and deliberately cannot replace the triggering exception (`trust-ci/src/adaptive_trust_ci/workspace.py:35-43`).
- `GitWorkspace.__init__()` initializes `checkout_path` and `config_home` to `None` before entering the transaction. Checkout `mkdtemp`/chmod, config-home `mkdtemp`/chmod, and XDG mkdir are all inside the same guard (`workspace.py:241-260`).
- On any `BaseException`, cleanup runs in reverse allocation order for both non-null paths and the original exception is re-raised. `self.path` and `self.config_home` are assigned only after every operation succeeds (`workspace.py:255-262`). An incompletely initialized object therefore cannot publish a partial trusted path.
- Normal `cleanup()` remains idempotent and removes both successful allocations (`workspace.py:354-356`).

The fault-injection tests cover every meaningful constructor boundary:

- checkout chmod failure;
- second/config `mkdtemp` failure;
- config-home chmod failure;
- XDG mkdir failure;
- successful lifecycle followed by cleanup twice.

Each failure test asserts the exact original `OSError` object is preserved and the workspace base is empty afterward (`trust-ci/tests/test_workspace.py:17-94`). All five lifecycle tests pass.

## Prior security protections remain intact

- Trusted Git HOME/XDG remain outside the checkout, global/system config and system attributes remain disabled, hooks/fsmonitor remain neutralized, and the authenticated header remains fetch-only. The committed executable `.gitconfig` regression passes without marker execution.
- Original process-group identity remains independent of leader lifetime. Overflow and timeout cleanup still applies TERM grace, escalates surviving same-group descendants to KILL, verifies group disappearance, reaps the leader, and refuses the worker's own group. All resistant-descendant tests pass.
- Stdout/stderr streaming and NUL record parsing retain pre-allocation aggregate byte, path-byte, path-count, and timeout bounds.
- Exact `.grok-stack/**`, `.grok/**`, `.github/**`, `.coveragerc`, literal-backslash, Unicode, LF, and tab approval scope/provenance tests remain passing.
- Strict local/holdout/trusted parsing, surrogate/control rejection, recursion limits, schema preflight, descriptor-relative no-follow reads, ancestor-symlink rejection, malformed raw provenance, spec-local criterion identity, signed zero-coverage failure, tamper detection, and public-only golden replay remain covered and passing.

## Security conclusion

No blocking security finding remains in the reviewed constructor remediation. The source is locally security-review ready at exact HEAD `98649e4e1e6a971fb802bc934eb5680de529e18a`. This report is advisory repository evidence only: it does not deploy Trust CI, provide a human approval, or replace the App-owned policy-epoch exact-SHA check and required external signed approvals.
