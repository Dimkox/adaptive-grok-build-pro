# Implementation RED/GREEN evidence — issue #229

Writer: general_implementer, route edd6ca692480. Worktree: .worktrees/issue229-watchdog; branch fix/issue-229-heartbeat-watchdog; initial HEAD/base e5856acfd4bc7a186f40a740b54ec86459462db5. This records focused local behavior only; the controller owns final full verification, manifest generation, independent reviews and release delivery.

## RED

Before product implementation, ran:

`python3 -m unittest tests.test_agent_lifecycle tests.test_policy.PolicyTests.test_blocks_second_same_role_writer`

Exit 1: 14 tests; 2 failures and 12 errors. The concurrent acquisition fixture produced [0, 0], leaving two owners, instead of one accepted/one rejected child. Same-role writer policy incorrectly returned allowed. Other tests found absent new APIs (now argument, lifecycle module, CLI). The clock is a fixed synthetic UTC fixture, not a real stalled native agent.

Additional RED after initial implementation:

`python3 -m unittest tests.test_agent_lifecycle.AgentLifecycleTests.test_reused_child_id_cannot_be_stopped_by_unversioned_old_executor`

Exit 1: the unversioned prior executor could remove a new execution after the same ID was reused. Acquisition now retains recorded generation lineage; the regression is included in the final GREEN run.

## GREEN

`python3 -m unittest tests.test_agent_lifecycle tests.test_runtime_state tests.test_policy tests.test_hooks tests.test_installer`

Exit 0: 109 tests in 53.324 seconds. Includes exact request ACK ordering, same-agent CLI recovery/terminal report, retained writer during interruption, preserved uncommitted bytes, stale generation rejection, closed/redacted diagnostics, heartbeat versus progress, bounded activity versus ACK deadlines, finite watch and installed CLI/runtime exclusion. The concurrency fixture uses at most two child processes; the test runner is serial.

`python3 -m ruff check .grok-stack/adaptive_grok/agent_lifecycle.py .grok-stack/adaptive_grok/state.py .grok-stack/adaptive_grok/_policy_legacy.py .grok/hooks scripts/grok_agent.py scripts/grok_status.py scripts/install_into.py tests/test_agent_lifecycle.py tests/test_policy.py tests/test_installer.py`

Exit 0: All checks passed. After the final lineage repair, a narrower ruff check of changed module/CLI/tests also passed.

`git diff --check`: exit 0, no whitespace errors.

`python3 scripts/grok_spec.py validate --gate --json`: exit 0; ok true, 7/7 typed criteria mapped, no errors.

`python3 scripts/grok_agent.py watchdog`: exit 0; schema_version 1, control local-observation-only, default 180/600 budgets, empty live/terminal lists on the source worktree.

## Russian task identity compatibility repair

The merged-base source is e30751f17ac0b7c9f12058922033b0e8aba8c215, including actual origin/main 63799f8760d3a55028d83ab5ff0116ececf8f7d1. Read-only investigation reproduced normal Russian startup failure in a private 0700 temporary fixture: slugify deliberately preserves Cyrillic, but lifecycle startup validated route.change_id as an ASCII diagnostic token. The fixture returned invalid-identity and wrote no agent state; the reviewed candidate remained unchanged during the controller's running verifier.

Controller-reported first full-verifier session 23856 was stopped after exact owned PID/cwd confirmation and exited 143. That run is incomplete, never a pass; a fresh full run is required after this repair.

RED command:

`python3 -m unittest tests.test_agent_lifecycle.AgentLifecycleTests.test_russian_change_identity_supports_heartbeat_ack_and_same_task_resume tests.test_agent_lifecycle.AgentLifecycleTests.test_ascii_task_identity_remains_unchanged_and_unicode_session_fallback_is_supported tests.test_agent_lifecycle.AgentLifecycleTests.test_malformed_and_oversized_task_source_refuse_without_agent_state`

Exit 1: three tests, two errors for Cyrillic change/session startup and three subtest failures because empty/null/list change IDs silently fell back. The fix validates a 1–128-character source identifier, preserves valid ASCII task tokens and hashes non-ASCII UTF-8 source bytes into an opaque task token. Other stable API fields remain unchanged. The Russian fixture verifies heartbeat, status ACK, interrupt ACK and same-task resume without storing the original source text.

GREEN command:

`python3 -m unittest tests.test_agent_lifecycle tests.test_runtime_state tests.test_policy tests.test_hooks tests.test_installer`

Exit 0: 112 tests in 55.798 seconds. `python3 -m ruff check .grok-stack/adaptive_grok/agent_lifecycle.py tests/test_agent_lifecycle.py` and `git diff --check` also passed.

## Delivery boundaries

Native #229 hang cause and actual native message delivery/interruption remain unproven. Interrupt-ack is a controller observation supplied after its separate native operation; no local CLI command invokes that native harness. Generation fences protect local state, not executor OS access. POSIX flock is required by the supported Linux profile. Terminal diagnostics retain only the existing 200-event history. Full PR verification and external App-owned exact-head Trust CI are still required; no broader 2.1.1 publication or qualification is claimed.
