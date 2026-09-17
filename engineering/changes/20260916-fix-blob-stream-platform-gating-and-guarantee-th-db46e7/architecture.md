# Architecture

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

`.grok-stack/adaptive_grok/architecture_diff.py`: `_stream_git_blob` gains a setup try/except Exception → ArchitectureError(code='io') (message 'streamed blob setup failed') and a terminal guard `if process.poll() is None: _stop_process(process)` in the finally; `_profile_worktree_blob`'s finally nests descriptor-close under directory-close. Untouched: `_run_capped`, `_stop_process`, cap/deadline/digest logic. Tests: three arms in `tests/test_architecture_fitness.py` (BoomSelector, SelectBoom, spy-based close-order).
