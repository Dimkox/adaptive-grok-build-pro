# Requirements — issue #158 worker child reaping

> Typed authority: [`change-spec.yaml`](change-spec.yaml). Markdown explains; typed IDs win.

## Acceptance criteria

- [ ] AC-001 adopted orphan reaped at loop/lease boundaries, with the control arm proving a zombie survives without the boundary
- [ ] AC-002 no status theft: tracked child return code preserved, sweep declines while any spawn is in flight, naive sweep pinned to fail
- [ ] AC-003 classification unchanged: timeout→timeout, heartbeat failure still raises, missing runtime classification identical
- [ ] AC-004 every spawn site guarded; guarded set exactly the worker's helpers; decorator really wraps `subprocess.run`
- [ ] AC-005 no SIGCHLD disposition is taken over
- [ ] AC-006 real spawn through the decorated helper is reaped and the guard released
- [ ] AC-007 gate + three receipts on the delivered fingerprint *(receipts tick this)*

## Failure and edge cases

- Sweep racing a spawn → impossible by construction (one `RLock` shared by guard check and sweep).
- Long sandbox phase: `ContainerExecutor.run` holds the guard for the whole command, so drains are declined during it; growth is bounded at one sweep per job.
- Heartbeat thread excluded on purpose: it is not the main thread and must not reap.
- `_terminate_process` still accepts `zombie_only` without reaping — left as is (#103/#132 territory), listed as residual.
- `os.posix_spawn` / `os.system` / async subprocess would slip past the AST sweep — recorded, not silently assumed covered.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Rule IDs: none changed. No
policy, holdout, key or approval-scope file is touched; `reap_stats()` is deliberately not added to
`OperationalMetrics` (frozen payload, out of budget).

## Non-functional requirements

- Security: nothing new exposed; no credential, key or runtime state read.
- Reliability: removes a monotonic PID-table leak in a PID-1 service and prevents a reaping design that would
  silently turn a killed command into a passing one.
- Performance: one `waitpid(WNOHANG)` sweep per loop iteration, declined while spawning.
- Observability: `SIG-001` worker zombie count, measured per job.
