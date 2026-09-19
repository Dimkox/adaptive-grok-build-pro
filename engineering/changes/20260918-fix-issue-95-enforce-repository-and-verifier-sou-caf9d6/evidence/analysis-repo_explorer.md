# Repository explorer analysis — issue #95

## Finding

`scripts/grok_verify.py` binds imports to the verifier copy but binds the checked repository to the process working directory. At module load it computes `ROOT = Path(__file__).resolve().parents[1]` and prepends that checkout's `.grok-stack` to `sys.path`; however, after parsing arguments it calls `verify(find_root(), ...)`, and `find_root()` starts from `os.getcwd()` (see `.grok-stack/adaptive_grok/util.py:21-40`). `ROOT` is never passed to `verify` and the CLI has no `--root` option. Consequently, launching a copied/stale verifier script from another checkout executes code imported from the copy while collecting files, route, change package, runtime evidence and (unless `--no-record`) writing the receipt under the cwd checkout.

## Reproduction

I loaded the actual repository `find_root()` implementation from a temporary external copy and called it with a separate temporary checkout as the process cwd/start directory. It returned the target checkout, not the external script root. The CLI wiring confirms this returned path is passed directly as `verify`'s root. This reproduces the root-selection mismatch without running the expensive verification profiles or writing repository evidence.

Data flow: `scripts/grok_verify.py` → `ROOT` for Python imports → `find_root()` (cwd/ancestor `.grok-stack`, then `git rev-parse`) → `verification.verify(root, ...)` → check inventory, active route/change, tree fingerprint, and receipt all rooted at the `find_root()` result. Existing tests exercise `find_root` consumers indirectly, but I found no CLI-level regression test that runs `grok_verify.py` from one worktree while its script path points at another.

## Affected callers / expectations

- User and repository contract invoke `python3 scripts/grok_verify.py --mode pr`; ordinary in-repository execution has matching script and cwd roots and is unaffected.
- `.grok-stack/adaptive_grok/workflow_artifacts.py:547-548,611` emits verification commands using the canonical relative script path; this does not pass a separate root and assumes execution inside the relevant checkout.
- `tests/test_python_test_runner.py:166` documents the verifier's Python checks but does not test entrypoint root selection.
- Existing explicit-root CLIs `scripts/grok_architecture.py` and `scripts/grok_governance.py` expose `--root`, but this verifier CLI currently does not.

## Tests / implications

The regression should invoke the copied/external script from a distinct target worktree (or an equivalent isolated subprocess) and assert it fails closed before running checks/recording if script source root and selected repository root differ. Also preserve a same-checkout invocation test. Test which root is used for both module imports and `verify`, rather than merely testing `find_root()` in isolation. The mismatch is material even with `--no-record`: reported checks are still produced by a verifier code tree different from the repository being checked; with recording enabled, a receipt can be attached to that target tree by foreign verifier code.

No product code or tests were modified in this analysis.
