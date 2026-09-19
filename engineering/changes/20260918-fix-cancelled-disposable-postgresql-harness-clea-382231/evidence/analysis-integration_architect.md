# Integration architecture analysis — issue #128

Route 3822310b0593; read-only.

- Path: `grok_verify.py` → `verification.verify/_command_check` → `.grok-stack/adaptive_grok/util.run` → `subprocess.run` → disposable harness. The parent does not own a cancellable process group; the harness's `finally` is not enough when SIGTERM hits the verifier.
- Outer 600s expiry is flattened to `exit=124`; inner 480s test timeout escapes as traceback/exit 1. Preserve fail status but expose phase/elapsed/budget and distinguish timeout from assertion failure.
- Prefer a focused owned process supervisor for the factory check instead of changing generic `util.run` semantics. On cancel/timeout send bounded TERM, wait, then KILL/reap before harness cleanup; handle repeated signals.
- Keep aggregate inner budget below the 600s outer deadline with cleanup margin. Preserve explicit repository-sandbox capability skip.
- Integration tests should signal a subprocess running the actual harness with fake Docker and a blocking child, then prove child stop/reap precedes exact resource removal; test escalation and timeout classification.
