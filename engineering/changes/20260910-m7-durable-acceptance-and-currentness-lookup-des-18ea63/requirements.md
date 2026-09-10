# Requirements for the proposed implementation

1. Persist canonical M7 bundle/outcome bodies and bind repository/task/run/result-head/profile identities to durable M4/M5/M6 facts. A completed task may clear current_run_id; use immutable completed-run provenance.
2. Separate external acceptance from currentness. A historic successful check remains history when head/base/policy/holdout change; currentness requires a fresh trusted observation.
3. Exact duplicate writes are idempotent. Conflicting identity reuse, cross-repository swaps, body mutation, stale epochs and out-of-order observations fail closed.
4. Recover the same observation-only preflight facts after process and PostgreSQL restart. Missing, corrupt or inaccessible data yields explicit unavailable/rejected reasons.
5. Preserve existing V1 schemas/digests, M8 activation/recommendation behavior and M9 restrictions. Future qualification uses a separately versioned consumer.
6. Retain original human outcome provenance and invalidation history. A merge actor, local digest or imported history report cannot originate acceptance.
7. Readers/runtime cannot originate trusted external observations; writes are capability-scoped. Production rollout is outside this source proposal.

These are acceptance targets, not claims of implemented or tested behavior.
