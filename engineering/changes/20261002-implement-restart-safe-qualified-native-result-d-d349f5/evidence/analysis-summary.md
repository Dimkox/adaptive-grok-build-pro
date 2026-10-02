# PR3d route-selected analysis summary

Six read-only analyses compared source trio `aefbde3ed → c5fe8f397 → 8ffd66982` with PR235. Direct cherry-pick is unsafe because the source is based on the older combined `e0be7cb`; adapt the final semantics only.

- Preserve the final source hardening: no trigger/backfill, all seven channels unavailable, dedicated dispatcher capability, exact UDS identity, response bounds, sending-before-POST, observation-only recovery and blocked unresolved outcomes.
- Fix source gaps during adaptation: bind outbox identity compositionally to its result source; reject or quarantine any unexpected pre-025 rows; validate current run/fence/packet/open attempt at claim time; require lease to exceed timeout plus processing margin.
- UDS is the complete destination allowlist. No TCP, DNS, proxy, redirect, provider/model SDK or live interception is allowed. The wire is a local durable handoff/observation boundary, not proof of a model call.
- Exact delivered/proved-failed state requires a closed JSON response and exact operation/request/envelope/postcondition binding. Transport ACK, auth errors, 5xx and malformed/duplicate/oversized responses remain ambiguous.
- PR235 admission remains outbox-empty. Tests seed admitted rows only as fixtures. This is a dormant U3d foundation, not U3/U6/U7 completion; BB/FPF/VibeVM remain default-off and U4/macOS remains owner-excluded.
