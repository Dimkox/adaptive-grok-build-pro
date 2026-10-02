# Architecture analysis

V2 belongs to the proposal broker; the HTTP contract belongs to the local API, not the control node. With persistence excluded, POST/GET must be absent or explicit `503 result_admission_unavailable`, never mock-only 201 or AttributeError/500. All channels remain unavailable/non-consuming and no outbox, transport, model call or live interception is introduced.

The Factory test budget has only 55 bytes of headroom, so any adjustment must be explicit and measured; moving tests outside the governed prefix is forbidden. Rollback removes the V2/API registration and leaves V1 intact.
