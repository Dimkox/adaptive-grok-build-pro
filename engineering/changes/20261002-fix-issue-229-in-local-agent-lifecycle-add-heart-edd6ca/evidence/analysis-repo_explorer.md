# Repository exploration

Route edd6ca692480; base e5856acfd4bc7a186f40a740b54ec86459462db5. Independent read-only repo_explorer report; no files changed, tests run or credentials read.

Local agent-state.json records only agent_type and started_at; history keeps 200 start/stop events. record_agent_start overwrites IDs; stop is idempotent. There is no heartbeat, progress, activity, interrupt acknowledgement or resume tracking. scripts/grok_agent_state.py is absent on this base. grok_status.py exposes raw state. This structural observability gap does not establish the cause of the external runtime hang in #229.

Canonical integrations: state.py, subagent_start.py, subagent_stop.py, pre_tool_use.py, post_tool_use.py and stop_gate.py under .grok/hooks. Root hook files are shims. Preserve empty SubagentStop payload and fingerprint invalidation. _lib.py maps explicit agent/subagent IDs and defaults absent IDs to unknown: do not attribute parent events to a child.

_policy_legacy.py allows a second same-role writer via `if active and agent_type not in active`; ownership needs instance identity and atomic start protection, retained through interruptions. New CLI must be listed in scripts/install_into.py MANAGED_FILES and config/managed.json. Modules/hooks install recursively; runtime remains excluded.

Regression targets: tests/test_hooks.py lifecycle/empty/idempotent stops and invalidation; tests/test_runtime_state.py state locking; tests/test_policy.py same-role duplicate; tests/test_installer.py and structure CLI registration. Cover legacy records, heartbeat/progress separation, bounded warnings, exact control requests/acknowledgements and safe resume. Findings are static, not passing acceptance evidence.
