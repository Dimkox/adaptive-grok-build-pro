# Documentation and compatibility analysis — issue #95

## Current documented contract

- `scripts/grok_verify.py` is the public local verification entry point (`README.md` Map; `factory/README.md` has domain-specific verification commands). Its accepted modes are `fast`, `pr` (default), and `release`; it calls the imported `adaptive_grok.verification.verify` with `find_root()` (`scripts/grok_verify.py`).
- The mandatory repository preflight is `python3 scripts/grok_verify.py --mode pr` (`AGENTS.md`, “Local verification and completion”). The README describes this as local preflight, not merge authority; exact-SHA App-owned Trust CI remains authoritative (`README.md` “How work runs” and `START_HERE.md` “Live Trust CI orientation”).
- Fresh-clone documentation requires reading START_HERE, PROJECT_STATE, AGENTS, decisions, mistakes, roadmap, README, then fetching refs and following route/PR-only rules (`START_HERE.md`).

## Relevant tests and compatibility considerations

- Verifier internals are exercised mainly from `tests/test_change_receipts.py` and `tests/test_python_test_runner.py`; repository CLI behavior is launched by script paths elsewhere. The reported regression should be a subprocess integration test using two distinct temporary git worktrees (or equivalent independent roots), placing an external copy of `scripts/grok_verify.py` in one while the active repository is the other. Assert failure before checks/receipt writes and a clear repository/verifier identity diagnostic. Also retain a positive invocation from the repository's own script path.
- Compatibility must preserve normal invocations from the repository's own checkout, all three documented modes, `--profile` repetition, `--no-record`, and `--json`; package/installed copies should be tested according to the intended trust boundary. Be careful that `scripts/grok_verify.py` intentionally inserts its own checkout's `.grok-stack` path on `sys.path` before imports, while `find_root()` independently identifies the working repository. A guard must compare the intended verifier source identity and repository identity without breaking legitimate launches from a relocated complete checkout or symlink policy unless explicitly specified.
- Verification computes its initial and final `tree_fingerprint` and records only if the route exists, governance passes, and the source stayed stable (`.grok-stack/adaptive_grok/verification.py::verify`). Identity rejection must happen before this routine can execute checks or record a receipt, so an external verifier cannot leave misleading evidence in the target worktree.
- Existing repository startup docs distinguish local verification receipts from external Trust CI. The fix must not describe a local path/source check as merge authorization or proof of an externally checked SHA. No README release-state refresh is indicated by this source-level bugfix alone; if release publication becomes in scope, AGENTS.md requires updating README's version/current-state and architecture links against the exact final tree.

## Documentation impact

No user-facing documentation change is inherently needed if CLI names and invocation semantics remain unchanged. If the fix intentionally rejects some formerly accepted invocation (for example, symlinked/external script paths), document that boundary in the CLI help or the existing verification section and include a direct regression test. Do not update the published identity/current state in README or START_HERE for a local candidate; those files describe the observed published tree and dated state.
