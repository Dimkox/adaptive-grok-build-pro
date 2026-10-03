# Architecture analysis

Route edd6ca692480; base e5856acfd4bc7a186f40a740b54ec86459462db5. Independent read-only architect report; no files changed.

Preserve active/history JSON shape, runtime_lock agents, atomic persistence, bounded 200-event history and existing callers. Add route/task identity, execution generation, lifecycle, heartbeat/progress timestamps, bounded activity, matching status/interrupt requests and acknowledgements. Explicit diagnostic events must not include private payloads.

Heartbeat proves reported liveness; progress is a meaningful explicit checkpoint. Polling and acknowledgements are not progress. Expose CLI actions for heartbeat/progress, status request/ack, interrupt request/ack, resume and bounded watchdog polling. Exact generations and request IDs reject stale events. Suggested defaults: heartbeat 180s, progress 600s, acknowledgement 60s. Inject time in deterministic tests. Missing/future/malformed timestamps mean unavailable, not healthy.

Watchdog warns only, never releases or restarts ownership. Bounded legitimate activity may explain stale progress, never stale heartbeat or missed acknowledgement. Reject all second writers including same role under lock; retain ownership through interrupt request and acknowledgement. Resume preserves agent/task/workspace only after observed interruption. Generation-fenced events cannot revive another execution. Terminal missing-result classification is separate from suspected-running stalls.

Native harness control remains external. A local request is intent, not evidence of actual native interruption. Require observed interruption before recovery and document workflow-only isolation. No new service/dependency/provider calls.
