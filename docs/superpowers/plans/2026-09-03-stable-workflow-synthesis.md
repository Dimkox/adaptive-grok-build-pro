# Stable workflow synthesis implementation plan

Approved by the user (`утверждаю stable-синтез`), including weekly intake of newest stable releases and bounded post-pin change/bugfix candidates.

1. Freeze analyses, typed ACs, design, rollback and release boundary; transition the durable change to implementing and commit this checkpoint.
2. RED/GREEN closed pins, typed DAG/transitions/findings/convergence, snapshots, and journal CAS/corruption/resume/contention.
3. RED/GREEN fixed fake transport, release/tag/head/compare/cache/error matrix, atomic state, due/clock/locking behavior.
4. RED/GREEN CLI mutation boundary, inert units, architecture node/edge/ownership, and router bounded terms.
5. Update factual current docs; run focused, architecture, and full baseline checks. Leave `implementing` for parent-owned verification/reviews.

No step authorizes external/production actions or tracked automatic pin/source changes.
