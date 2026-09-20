# Write-owner spawn blocker

Route write_agent is `general_implementer`. Spawn was denied:

`Another write agent is already active: ['frontend_implementer']`

`.grok-stack/runtime/agent-state.json` still lists `01a0354f-f0ab-7990-a697-0aeb7faf20df` as `frontend_implementer` started `2026-08-24T19:47:06+00:00`. That id is not a live task in this session; `kill_command_or_subagent` returned not found. `frontend_implementer` is not in this route’s `allowed_agents`.

Bounded ruling (same class as change `20260815-break-subagentstop-hook-retry-loop-14464b`): the parent performs the product write. One write owner. Do not spawn a second write role. Do not edit the stale runtime lock as a product change.
