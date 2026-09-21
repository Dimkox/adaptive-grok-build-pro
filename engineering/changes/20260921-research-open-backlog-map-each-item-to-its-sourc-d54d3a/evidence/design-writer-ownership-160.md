# #160 — atomic writer ownership and recoverable leases

Research route `d54d3afd1c92`; execution packet, not implementation or verification evidence. The active delivery controller must select one write owner on a separate routed branch; do not mutate this research route. Requirements below preserve exact-SHA Trust CI and all existing external approval boundaries.

## Outcome and required invariants

A terminated writer cannot block a future task forever, and two writers of the same or different role cannot simultaneously obtain ownership of one worktree. Route role authorizes eligibility; a concrete agent/session identity authorizes ownership. A different worktree may have its own owner.

Current anchors: `state.py:131-165`, `_policy_legacy.py:628-639`, `subagent_start.py`, `subagent_stop.py`, `pre_tool_use.py:228-247`. `_lib.agent_id` currently defaults to `unknown`; `_lib.session_id` defaults to `manual`. Those fallback strings cannot serve as unique lease identities.

## Recommended design and bounded sequence

1. Pin supported hook payloads and lifecycle with sanitized fixtures: stable agent ID, parent session ID, canonical worktree identity, route ID, and start/stop correlation. Missing identity must produce an actionable denial for writer ownership, never collapse all writers into `unknown`. Do not infer agent liveness from the short-lived hook process PID.
2. Add one atomic admission operation using an ownership record with schema version, owner identity, route/worktree, issued/renewed/expiry times, generation token and state (`reserved`, `active`, terminal history). Admit the same event idempotently; reject every distinct contender including the same role. PreTool reservation/start conversion must use a real shared correlation key; if the harness cannot supply it, explicitly prove a synchronous start admission plus per-write ownership check before claiming complete enforcement.
3. Add bounded renewal at actual owner activity and reconciliation of expired/dead owners. A replaced generation may not renew or perform another write. A running child without fresh hook traffic is not proven dead: require a dependable harness liveness signal or keep it held with a named operator diagnosis until safe release is established. Unversioned legacy records become `legacy_unresolved`, listed for explicit reconciliation; do not silently discard unknown live work.
4. Add `scripts/grok_agent_state.py list|release <agent-id>` scoped to one worktree and record terminal `abandoned`/`released` history. Refuse positively live owners and ambiguous identity; expose the exact safe recovery condition. No production-consumer runtime repair during source tests.
5. Make policy import/root errors explicit and consistently fail closed for sensitive actions; classification and enforcement use the same resolved root. Preserve read-only degraded diagnostics where classification can be safely determined independently. Do not blanket-allow after import failure or loosen the denial circuit breaker.

## Acceptance and focused validation

- Two synchronized processes attempting same-role admission yield exactly one owner; repeat with different roles and duplicate delivery.
- Expired demonstrably dead owner moves to history, legitimate successor succeeds; active renewed owner is never stolen; resumed stale generation is refused.
- PID reuse, unknown IDs, clock regression, malformed state, missing stop, expired reservation and duplicate stop do not create dual ownership.
- `list` is nonmutating; `release` cannot release a confirmed live writer; tests use temporary runtime directories.
- Import failure plus sensitive command denies loudly; unresolved roots use consistent classification/enforcement; original circuit-breaker tests retain behavior.
- Concurrency tests cover `runtime_lock` acquisition itself: its current create-then-write PID protocol treats an empty file as stale, so a contender may unlink a just-created live lock. Fix or avoid that acquisition race within this ownership slice before claiming atomicity.

Files: `.grok-stack/adaptive_grok/state.py`, `_policy_legacy.py` (or a small focused ownership module), `.grok/hooks/{_lib,pre_tool_use,subagent_start,subagent_stop,post_tool_use}.py`, new operator script; `tests/test_runtime_state.py`, `tests/test_hooks.py`, policy tests and synthetic lifecycle/concurrency fixtures. Do not perform unrelated lock/state refactors.

## Gates, recovery, and alternatives

This is a security-sensitive source change: obtain the route's named design/security reviews and exact external check/approval scopes before merge. No deployed Trust CI change is needed. Releasing existing consumer owners is a separate exact-runtime-file operation; this packet grants none. If harness identity/liveness cannot be established, finish explicit diagnostics and keep unsafe takeover blocked rather than inventing authority.

Recovery: preserve old records and terminal history, roll back hook installation as a coherent version, and refuse incompatible active record versions with a clear operator message. Reverting to the old same-role bypass is not a safe live recovery while writers are active.

Optional alternatives, not requirements: persistent supervisor-backed ownership, OS advisory locks held by the actual long-lived writer, or a heartbeat service. A configurable TTL is optional; atomic admission, trustworthy identity and no live takeover are required. TTL-only deletion and a global allow-on-error mode are rejected.
