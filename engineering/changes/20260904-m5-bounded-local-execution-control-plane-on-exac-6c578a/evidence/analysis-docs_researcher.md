# Documentation and state analysis — M5 bounded local execution

## Result

The minimal truthful documentation closure is: complete the active change package, rebind the repository's current-state surfaces to the new M5 lineage, update the assertions that make those facts executable, and leave historical M4/M5 evidence untouched. The M5 checkpoint may be described as a serious, enterprise-ready **repository-local control-plane source checkpoint**, but not as accepted, delivered, provider-running, deployable, or production-authorized.

Do not copy the 2026-09-01 M5 package or its root-state prose verbatim. Its contract and recovery semantics are useful implementation inputs, while its M4 predecessor, route, stacked-successor topology, host observations, deadlines, package identity, and completion status are historical.

## Inspected identities and provenance

- Worktree: `integration/m5-m4-final-20260904` at exact M4 predecessor `67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4`, tree `399c65e7c65626f3d5236cae1bce009c5d3a9714`.
- Active route: `6c578a9933b3`; active package: `engineering/changes/20260904-m5-bounded-local-execution-control-plane-on-exac-6c578a/`.
- The route's `base_commit` `78ad2f679d38dc3244e716c586332417e610089c` is the router-selected delivery comparison base. The exact integration predecessor is independently fixed by the task text and branch HEAD at `67dc4dd...`. Record both meanings in the package; do not hand-edit machine-local route state or mislabel `78ad2f6` as the M5 source predecessor.
- The superseded untracked package `engineering/changes/20260904-m5-indie-mvp-execution-on-exact-m4-67dc4dd-9cbda1/` must not enter the commit.
- The tracked `2.0.13` archive was last changed by artifact commit `60404baae2a76b6455ff0964c7539872b3ada25b`; its sidecar digest is `723395c0ab3e30af90f86e6602f47d775eab967948e9dfb7bdceac2fce065612`. Current M4 predecessor `67dc4dd` contains later policy changes, and M5 will add further tracked source. Therefore the archive is historical M4 output, not an exact package of the M5 tree. Do not weaken the exact-package parity check or claim current parity.
- The reusable canonical M5 runtime checkpoint is `3940267ac5754ad07a047894102015d33eb759b1`, tree `4646582a7c5ff6f08ee7e8462687da400459b08d`. It is based on obsolete M4 lineage and supplies no verification, review, acceptance, or delivery evidence for the new tree.

## Canonical M5 material to reuse semantically

The useful ordered source facts through `3940267` are:

1. `8fbbcab` — bounded design/change-package baseline.
2. `acb8c36` and `40f7d72` — closed schemas/contracts plus offline exact-version adapter fixtures.
3. `5cbda5b`, `7311432`, and `3171854` — broker/workspace boundaries and authenticated architecture ownership.
4. `0a3485a`, `355e78d`, and `0e5f0ef` — fenced lifecycle, factual workspace-result bridge, trusted selection, and durable role binding.
5. `f9dcb4f`, `c70950d`, and `0537fe9` — execution API, canonical persistence in migrations `014`-`016`, and fail-closed startup capability checks.
6. `36ab807` plus `27b0ae6` — contract enrollment and bounded comparator semantics.
7. `3f56b6a`, `5073fc0`, and `3940267` — migration `017`, recovery/metrics, additive v2, and the two-restart PostgreSQL 17 proof.

Port those behaviors onto `67dc4dd`; do not port historical branch/status text such as `9727bc3`, route `37b05f579320`, successors 04/05/06, the 2026-09-08 deadline, or an assertion that rootless-host evidence is already current.

## Minimal tracked documentation/state set

### 1. Active change package — required before implementation

Complete only the generated package for route `6c578a9933b3`:

- `change-spec.yaml`: replace `UNKNOWN`/empty arrays with stable IDs for the bounded objective, criteria, invariants, contracts, observability, forbidden outcomes, and approval scopes. Bind exact integration predecessor `67dc4dd...`, migrations `014`-`017`, four JSON Schemas, execution OpenAPI v1/v2, M4 compatibility, tenant isolation, and the no-live-provider/no-operational-action boundary.
- `brief.md`: state the observable outcome, in-scope slice, non-goals, and the distinction between delivery comparison base `78ad2f6` and exact M5 predecessor `67dc4dd`.
- `requirements.md`: mirror the typed criterion IDs; do not introduce additional acceptance scope in prose.
- `architecture.md`: describe M4 control -> immutable packet/manifest -> trusted offline adapter/proposal boundary -> fenced store/recovery -> factual result. Explicitly keep provider selection, authorization, tenant, run, owner, fence, allocation, deadline, and budget authority server-side.
- `tasks.md`: one bounded semantic-port sequence and focused verification ledger. Do not recreate the historical successor-04/05/06 ceremony.
- `test-plan.md`: P0 coverage for M4 compatibility, migration/checksum/order, closed contracts, authorization/tenant isolation, fail-closed provider selection, atomic terminal finalization, restart recovery, and no fabricated result/evidence. P1 hardening is backlog, not a completion loop.
- `release.md`: repository-local source checkpoint only. No deploy, provider invocation, migration application, PR, tag, release, or external write is authorized. Eventual activation still requires qualified isolation, credentials/egress controls, exact-head evidence, and explicit operational authority.
- `rollback.md`: before deployment, revert the unmerged source lineage; after any future accepted migration, quiesce claims, preserve evidence, and forward-fix with the next migration rather than down-migrating or rewriting `013`-`017`.
- `state.json`: use `grok_change.py` transitions after the scope/design decision is recorded. A provisional source checkpoint without final route evidence remains `implementing`; `ready` would be false until the required exact-fingerprint verification and reviews exist.
- `evidence/README.md`: index only reports and commands actually produced for this route. Historical results from `3940267` are background, never current receipts.

No second standalone Superpowers design/plan is needed: the active package's `architecture.md`, typed spec, and `tasks.md` satisfy the durable design/plan requirement with less duplication. Preserve the old design and package in Git history as historical inputs.

### 2. Current repository handoff — required when M5 product source lands

Update these factual surfaces together:

- `START_HERE.md`: make route `6c578a9933b3` and the M5 branch the continuation point; identify `67dc4dd` as the exact M4 source predecessor; state the final M5 product checkpoint/tree only after it exists; make M6 the next integration step. Preserve the no-delivery/no-external-authority facts.
- `PROJECT_STATE.json`: set `active_delivery` to the current M5 branch/package/route; add separate M4 predecessor and M5 implementation/review/delivery dimensions; update M5 and work-inventory entries to the new exact checkpoint. Keep all five axes separate and leave PR, external check, merge, tag, release, deployment, and live activation absent.
- `README.md`: update Current state, the `factory/` map entry, and the M5 role description to match the actual source. The existing K22/231-edge graph already contains `M5Execution`; do not add nodes or regenerate the clique unless topology genuinely changes.
- `DARK_FACTORY_ROADMAP.md`: replace the obsolete `141e51e`/migration-013-conflict M5 status with the exact new local lineage and bounded acceptance state. Mark only implemented/evidenced work items; keep M5 -> M6 digest/SHA handoff and later milestone dependency order intact.
- `factory/README.md`: document migrations `014`-`017`, immutable packet and manifest identities, v1/v2 execution surfaces, offline adapter limitations, tenant/authorization/fence invariants, terminal saga, recovery behavior, and PostgreSQL 17 requirement. It must continue to say that no live provider, external write, deployment, or Trust CI authority is present.
- `packages/README.md`: identify `2.0.13` as the retained M4 artifact at digest `723395c0...`, not a package of the current M5 source. State that no M5/final M9 archive exists yet. Do not rebuild or change `VERSION` merely to make this provisional checkpoint look released.
- `mistakes.md`: add the already-observed process root cause that exploratory review was allowed to expand acceptance without a finite severity boundary. Prevention should require one fixed acceptance/review wave and move non-critical discoveries to the optimization backlog while still blocking authority, tenant-isolation, data-loss/corruption, and core-flow failures.

`CHANGELOG.md`, `VERSION`, `QUICKSTART.md`, historical M4 packages/evidence, and old M5 change packages do not need a provisional-M5 edit. Add a release version/changelog and rebuild the archive only at the later final release-candidate boundary.

### 3. Executable truth assertions

- Update `tests/test_project_state.py` with the new route/branch/predecessor/checkpoint facts and the deliberately provisional statuses. Its current constants hard-code M4 checkpoint `47b1c0a`, M5 `141e51e`, and the obsolete active inventory.
- Update only directly affected assertions in `tests/test_structure.py` when the M5 contracts and `factory/README.md` land. Preserve the version and complete-graph assertions.
- Do not relax `tests/test_manifest_package.py` to tolerate a stale archive. Exact package parity is a final-candidate gate; the intermediate M5 checkpoint must simply avoid claiming it passed.

## Finite M5 acceptance boundary

The tracked criteria should block on these outcomes only:

1. M4 migration `013`, legacy control API, lease/capacity/budget/state behavior, and Trust CI separation remain intact.
2. Migrations `014`-`017` are ordered, checksum-bound, forward-only, tenant-safe, and proven on disposable PostgreSQL 17 without touching persistent/shared state.
3. Task packet and run manifest are immutable, separately domain-digested, and bound to exact M4 task/run/owner/fence/allocation plus trusted policy/profile/plan identities.
4. Execution v1 and additive v2 contracts are closed and provider-neutral; offline adapters have no subprocess/network/live fallback and fail closed on unknown or ineligible identities.
5. Every mutation enforces authentication, repository/tenant boundary, durable role, live lease/fence, idempotency, bounds, and redaction.
6. Terminal processing is server-owned and resumable: proposal -> trusted snapshot -> atomic finalization; workers cannot supply authoritative snapshots.
7. Restart/orphan recovery is bounded and idempotent, uses higher fences for cleanup, preserves history, and creates neither proposal nor result evidence.

Static systemd units, installer activation, a live rootless provider host, credential issuance, egress enablement, corporate workflow automation, M6 semantic adjudication, and any production operation are outside this repository-local checkpoint. They remain explicit later activation/delivery concerns; they are not silently waived.

## Claims that must disappear or remain explicitly historical

- Current M5 is `141e51e...` with `013_execution_plane` awaiting renumbering.
- Current M5 route is `37b05f579320`, or current work is successor 04/05/06 on `9727bc3`/`27b0ae6`.
- M4 continuation is still rebuild/review work from `47b1c0a`.
- The tracked `2.0.13` ZIP is an exact package of current HEAD.
- The `3940267` restart run or any old review is evidence for the new exact tree.
- M5 is accepted, delivered, externally verified, deployable, provider-running, or production-ready.
- Source-controlled migrations authorize applying them to any existing database.

The truthful checkpoint wording is: **M5 bounded local execution source is provisionally integrated on exact M4 `67dc4dd`; focused evidence may be recorded for the resulting product checkpoint, while package, exact final verification/reviews, external Trust CI, delivery, activation, and production authority remain separate later gates.**
