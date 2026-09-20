# Tasks — issue #158

- [x] Establish the real spawner from the **deployed** revision, not HEAD (image `pr7-c4d1ce7`, 2026-08-25, predates `start_new_session`), and the PID-1 adoption mechanism.
- [x] Rule out holdout-in-worker (only `verify_bundle`/`bundle_digest` runs in-process; commands run in the sandbox container).
- [x] Implement loop/lease-boundary `waitpid(-1, WNOHANG)` drain with a spawn counter and one shared `RLock`; no SIGCHLD handler.
- [x] 14 arms including the theft control and the AST coverage sweep; added `ContainerExecutor.run` coverage that did not exist.
- [x] Red-before-green on pristine `90078959` (behavioural `AssertionError: Lists differ: [715981] != []`), plus the real PID-1 pair.
- [x] 257 vs 243 suite, additions-only diff, ruff/compileall/diff-check clean.
- [ ] Independent reviews (code, test) and receipts on the final fingerprint.
- [ ] Push (branch already on origin), open PR, wait for the App-owned exact-SHA check. Restart of the live worker stays an operator action.
