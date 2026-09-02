# M5 Implementation Ledger

- [x] Establish route-bound durable package and approved exact-M4 scope.
- [x] Freeze M5 design and implementation plan; self-review and commit.
- [x] TDD immutable schemas, packet/manifest contracts, protocol parser, and adapter fixtures.
- [x] TDD proposal brokers, workspace/Git abstractions, host capability probe, and fake-runtime adversarial cases.
- [x] Give every slice-01 source executable architecture ownership/rules/generated parity; exact fitness against final M4, architecture checks, 52 architecture tests and 25 focused factory tests pass at checkpoint `9ba284e`.
- [x] Materialize successor slice-02 migration `014`, persistence and explicit execution claims/stages/proposals on exact slice-01 predecessor `34dd618`; preserve immutable M4 migration `013` and legacy compatibility.
- [x] Require an injected exact trusted adapter/profile registry, deny reader write capabilities, clean failed post-claim leases, and bind grant role to the durable run.
- [x] Add and directly validate the separate execution OpenAPI fragment, preserving byte-identical M4 control v1 plus disjoint routes/operation IDs and installer parity.
- [ ] In slice 04, add conservative rich-contract baseline support and register all five M5 artifacts in architecture inventory; current `unsupported added-contract baseline semantics` must not be hidden by dropping contracts or weakening policy.
- [x] Enforce monotonic bounded proposal streams, no post-terminal effects, structured redaction, and allowed-path/trusted artifact evidence; the runtime SQL capability independently binds durable role/live grant, exact replay and indexed sequence/terminal checks.
- [x] Bind start/finalize SQL to canonical cross-fields, derive M4 outcome from factual terminal result, and fail closed on result corruption.
- [x] Preserve provisional migration `014` byte-identically; materialize non-destructive forward expand `015` canonical persistence and DROP-only contract `016`; lock proposals before results, prove compatible populated non-final `014` evidence upgrades, reject any legacy finalized row or unattested artifact atomically before DDL/data mutation, and prove an `016` failure rolls back `015`. Rollout must quiesce old finalizers; `014` was never accepted or published, so no universal production-upgrade claim is made and future integrated M6 migration starts at `017`.
- [ ] In slice 04, wire a control-plane-owned terminal-to-trusted-snapshot-to-finalize path for all six execution API routes (or a bounded supervisor/reconciler); workers must never supply snapshots and terminal proposal persistence alone is not AC-007 completion.
- [ ] Add M5-aware orphan/cancel recovery and close/inventory all execution schemas and OpenAPI request/response contracts.
- [ ] TDD restart/orphan recovery, bounded metrics, and predefined systemd source topology.
- [ ] Integrate architecture, installer, README, provider eligibility, and operations documentation.
- [ ] Run every locally feasible focused suite and root preflight; record OS isolation exit `BLOCKED`.
- [ ] Parent dispatches independent reviewers/receipts and owns any later PR/external action.

Implementation owner updates this ledger in each coherent product commit. Slice 03 is provisional source only: no subagent, reviewer receipt, provider call, secret access, external write, unit activation, package, PR, acceptance, delivery, or M5-exit claim is part of this checkpoint.

The two independent reviews of historical aggregate source SHA `61db79f07904ae5facb244c34b26c8383504dd88` remain FAIL evidence, not completion authority or PASS receipts. Their bounded remediation matrix is preserved in `evidence/remediation-review-findings-61db79f.md`; this successor must prove the applicable repairs against its own exact predecessor and head.
