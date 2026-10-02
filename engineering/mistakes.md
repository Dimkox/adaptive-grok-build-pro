# Moved

Canonical log is /mistakes.md. Do not append here.
## 2026-10-02 — Explicit worktree path is required for apply_patch

Root cause: apply_patch resolves repository-relative paths from the controller checkout and
does not inherit an exec_command workdir. Two newly-created PR3d tests briefly landed in the
root checkout; they were immediately removed and recreated under the explicit worktree prefix.

## 2026-10-02 — Reused a known nonstandard help trap

Root cause: I assumed `run_disposable_exit.py --help` behaved like a conventional argparse
entrypoint instead of consulting the existing mistake record or reading its source; the script
ignores that argument and starts the full suite. Keep the one live run, never duplicate it, and
inspect source before probing repository harnesses whose CLI behavior was already learned.
