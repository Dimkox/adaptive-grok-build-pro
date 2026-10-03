# Requirements — local lifecycle watchdog

Typed authority: [change-spec.yaml](change-spec.yaml).

AC-001: deterministic stalled-running observations produce heartbeat/progress warnings without modifying ownership. Heartbeat, polling and status ACK cannot renew progress. Defaults: heartbeat 180s, progress 600s, ACK 60s. Bounded legitimate activity explains progress age only.

AC-002: ACK matches request ID and generation. Resume requires observed interruption, rotates generation and preserves the same agent, task, workspace and uncommitted bytes. Stale executors cannot update, stop or resume successors.

AC-003: policy and locked acquisition reject every second writer, including the same role. Duplicate start is idempotent. Warning and interruption retain the slot; observed final termination releases it.

AC-004: installed CLI and explicit child hooks retain empty/idempotent stop compatibility. Missing child ID or generation cannot update child activity. Missing terminal reports are distinct from running stalls; late closed result classification is supported.

Atomic writes use the existing runtime lock plus bounded stable kernel serialization. Runtime observations and lock files are excluded from installer payloads and fingerprints. Only fixed classes, identity tokens and timestamps are persisted; no arbitrary prompts, tool payloads or provider blobs. Governance and merge trust are unchanged.
