# M5 Implementation Ledger

- [x] Establish route-bound durable package and approved exact-M4 scope.
- [x] Freeze M5 design and implementation plan; self-review and commit.
- [x] TDD immutable schemas, packet/manifest contracts, protocol parser, and adapter fixtures.
- [x] TDD proposal brokers, workspace/Git abstractions, host capability probe, and fake-runtime adversarial cases.
- [x] Deliver the early contracts/protocol/adapters/brokers and persistence/API successors as bounded historical stack inputs.
- [x] Materialize successor slice-02 migration `014`, persistence and explicit execution claims/stages/proposals on exact slice-01 predecessor `34dd618`; preserve immutable M4 migration `013` and legacy compatibility.
- [x] Require an injected exact trusted adapter/profile registry, deny reader write capabilities, clean failed post-claim leases, and bind grant role to the durable run.
- [x] Add and directly validate the separate execution OpenAPI fragment, preserving byte-identical M4 control v1 plus disjoint routes/operation IDs and installer parity.
- [x] In successor 04, add bounded fail-closed rich-contract comparison and register five byte-identical execution-v1 artifacts. Exact predecessor `8a7be8a` → `27b0ae6` fitness, model 60/60, fitness 88/88 and independent comparator/security review pass; cumulative M4 → successor-04 exceeds the change budget and therefore must remain stacked.
- [x] Enforce monotonic bounded proposal streams, no post-terminal effects, structured redaction, and allowed-path/trusted artifact evidence; the runtime SQL capability independently binds durable role/live grant, exact replay and indexed sequence/terminal checks.
- [x] Bind start/finalize SQL to canonical cross-fields, derive M4 outcome from factual terminal result, and fail closed on result corruption.
- [x] Preserve provisional migrations `014`-`016`; add unpublished migration `017` for PostgreSQL-17 recovery/atomic metrics without backfill. Integrated M6 must start at `018` after restack and fresh checksum/upgrade/restart evidence.
- [x] In successor 05 source, wire the control-plane-owned terminal proposal → trusted snapshot → finalize saga for enrolled v1 and additive v2 routes; workers never supply snapshots, failures resume idempotently, and recovery fabricates neither proposals nor results.
- [x] Add M5-aware orphan/cancel/supersede recovery and close/inventory execution request/response contracts. Focused pure and selected PostgreSQL tests pass; final exact-head verification remains open.
- [ ] Replace the legacy M4-only restart probe with a two-restart M5 runtime/attestor/recovery drill on disposable PostgreSQL 17.
- [ ] Add exactly four inert hardened systemd source units plus parser tests; never install, enable or activate them.
- [ ] Finish architecture, installer, README, provider eligibility and operations parity in bounded successor 06 if successor 05 would exceed the immediate-predecessor budget.
- [ ] Run every locally feasible focused suite and root preflight; record OS isolation exit `BLOCKED`.
- [ ] Parent dispatches independent reviewers/receipts and owns any later PR/external action.

Implementation owner updates this ledger in each coherent product commit. Current branch `milestone/m5-successor-05-runtime-recovery` is provisional work on frozen predecessor `27b0ae6`; preservation commit is `3f56b6a`, with later worktree changes not yet assigned a final SHA. No live provider call, secret access, external write, unit activation, package, PR, acceptance, delivery or M5-exit claim is part of this checkpoint. Operational M5 remains blocked on a trusted rootless broker and live credential/egress isolation.

The two independent reviews of historical aggregate source SHA `61db79f07904ae5facb244c34b26c8383504dd88` remain FAIL evidence, not completion authority or PASS receipts. Their bounded remediation matrix is preserved in `evidence/remediation-review-findings-61db79f.md`; this successor must prove the applicable repairs against its own exact predecessor and head.
