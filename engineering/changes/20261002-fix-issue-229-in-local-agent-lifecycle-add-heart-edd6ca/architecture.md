# Architecture — local lifecycle observations

Typed authority: [change-spec.yaml](change-spec.yaml).

state.py preserves start/stop callers and delegates to agent_lifecycle.py. Active records gain route/task/workspace identity, generation, lifecycle, distinct heartbeat/progress/activity times, closed activity/checkpoint classes and request envelopes. The active/history shape and 200-entry retention remain. Legacy records are uninstrumented and stoppable.

Every mutation uses a stable POSIX kernel guard, the existing agents lock and atomic dump. Duplicate start cannot reset an instance; writer acquisition checks all active owners while locked. The spawn policy blocks same-role duplicates too. POSIX flock is provided by the supported Linux profile.

grok_agent.py provides start, heartbeat, progress, activity, status-request/ack, interrupt-request/ack, resume, terminated, report, watchdog and finite watch. Watchdog is read-only; grok_status.py adds diagnostics. Pre/PostToolUse only observe explicit known child IDs and generations. SubagentStart exposes the generated identity. SubagentStop keeps empty output; an unversioned stop cannot clear a resumed generation.

Native control boundary: interrupt-request stores intent. The controller separately invokes native interruption and records interrupt-ack after actual interruption is observed. Resume rotates local generation before same-agent native followup. Ownership remains reserved through interruption; terminated records actual final termination. The local CLI never invokes the native collaboration harness or infers a stall from subprocess absence. Local generation fences are workflow checks, not OS enforcement against old executors.

Activity bounds are at most 3600s; they cannot suppress overdue heartbeat or ACK. Legacy initial-generation stops stay compatible. No migration, background service or new provider dependency is needed.
