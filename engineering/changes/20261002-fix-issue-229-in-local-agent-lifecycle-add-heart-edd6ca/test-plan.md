# Test plan — local lifecycle watchdog

Typed authority: [change-spec.yaml](change-spec.yaml).

Focused command: python3 -m unittest tests.test_agent_lifecycle tests.test_runtime_state tests.test_policy tests.test_hooks tests.test_installer. Run serially with at most two simultaneous acquisition fixture processes.

Fixed UTC timestamps exercise stalled-running observations without hanging any real agent. Cover fresh heartbeat/no useful progress, polling, bounded legitimate test activity, overdue status ACK, unavailable/future/malformed timestamps, matching request/generation and ACK ordering. Synthetic interruption proves local behavior only. Recovery preserves uncommitted bytes and rejects stale updates/stops. Concurrent processes and policy tests reject duplicate same-role writers.

Hook checks preserve empty/idempotent stop and ignore unknown/unversioned child activity. Installer checks execute the copied CLI and exclude runtime state. Terminal result loss and later failure classification are separate from running stalls. Finite-watch bounds and generic redacted argument errors are exercised.

RED on base: 14 tests; two observable failures (both concurrent starts succeed; same-role spawn allowed) and 12 errors for missing instrumentation. GREEN evidence is recorded in evidence/implementation-tests.md. Controller owns final full verification and independent mutation reviews.
