# L5 Multimodal Landing Dogfood Implementation Plan

> **Execution rule:** Use the route-selected `ai_implementer` as the sole write owner for every task. This is the explicit SDD conflict ruling: repository `AGENTS.md` and adaptive routing require one writer and reviews only after verification, so generic fresh-writer-per-task and per-task-review clauses yield. Tasks remain sequential and handoff-safe through committed closed interfaces.

**Goal:** Deliver the approved offline multimodal-to-static-site vertical with a sealed provider fixture, unavailable defaults, at most three evaluated candidates, and an exact-SHA deterministic ZIP/sidecar without external effects.

**Design:** [`../specs/2026-09-04-l5-multimodal-landing-dogfood-design.md`](../specs/2026-09-04-l5-multimodal-landing-dogfood-design.md)

**Control baseline:** `ad6d23cc30c11e5ea51c388213f5ebdfe306fb56`; no stale-branch cherry-picks. **Dogfood target:** private `github.com/Dimkox/ai-dark-factory-landing` at exact SHA `176efcaab931c2482781ff163c621b10aa05dee9`, tree `f2bdcecc6dbe9ecc82007610d398ca12bd75e07f`; its local clone is read-only and candidate writes occur only in disposable workspaces. Existing showcase, migrations `001`-`018`, M0-M9 contracts, and published `v2.0.13` package bytes are frozen; Task 5 establishes unpublished source candidate `2.0.14` without creating its product ZIP.

**TDD rule:** For each task, add the named focused test first, run it to observe the specified RED, implement only that task, rerun the focused group once to GREEN, run Ruff only on modified Python files, run `git diff --check`, and commit. If GREEN fails, rerun only the failed method/group after repair.

### Task 1: Freeze closed contracts and bounded intake

**Create:** six L5 JSON schemas, `factory/contracts/openapi/landing-dogfood.v1.json`, `factory/src/adaptive_factory/landing_contracts.py`, `factory/src/adaptive_factory/landing_intake.py`, `factory/tests/test_landing_contracts.py`, `factory/tests/test_landing_intake.py`, bounded media fixtures.
**Modify:** only contract/runtime inventory surfaces required to register the additive contract.

- [ ] Write tests for canonical round-trip/digests, unknown/duplicate/non-finite rejection, exact five media kinds, MIME/signature/shape/limit enforcement, tenant/repository/idempotency conflicts, private mode, purge, and absence of raw bytes in records/logs.
- [ ] Run `python3 -m unittest factory.tests.test_landing_contracts factory.tests.test_landing_intake -v`; expected RED is missing L5 modules/contracts.
- [ ] Implement immutable records and domain-separated digests, raw-body streaming into a mode-`0600` tenant store outside Git, finite structural checks, and purge-on-terminal/cancel behavior. Do not add a migration or third-party decoder/provider dependency.
- [ ] Run the same two modules; expected GREEN proves `LandingInputV1` is the only downstream byte handle.
- [ ] Run targeted Ruff/diff check and commit `feat(factory): add landing intake contracts`.

**Handoff:** exact schema/contract digests plus one validated `LandingInputV1`; later tasks never read request metadata as authority and access bytes only through the tenant-bound read port.

### Task 2: Add fixed command normalization and unavailable default

**Create:** `factory/src/adaptive_factory/landing_provider.py`, sealed command fixture executable/data, `factory/tests/test_landing_provider.py`.
**Modify:** local settings/composition types only to declare immutable trusted profiles; default remains unavailable.

- [ ] Write tests for fixed executable/argv and canonical stdin, `shell=False`, scrubbed environment, sequence/terminal/size/time bounds, deterministic five-media fixture equivalence, strict `StaticLandingSpecV1`, hostile prompt/tool/path/URL/authority content, profile drift, and zero-call default behavior.
- [ ] Run `python3 -m unittest factory.tests.test_landing_provider -v`; expected RED is the absent provider port/profile implementations.
- [ ] Implement `LandingProvider` protocol, trusted fixed command launcher, checked fixture profile, and `UnavailableLandingProvider`. Bind profile/executable/protocol/model/prompt/tool/schema/decoder identities before blob access; permit no caller override or fallback.
- [ ] Validate one bounded canonical output into `StaticLandingSpecV1`; discard raw/native output and retain only `LandingProviderEvidenceV1` digests/counters/disposition.
- [ ] Run the focused module to GREEN, targeted Ruff/diff check, and commit `feat(factory): add sealed landing provider boundary`.

**Handoff:** one closed spec/evidence pair bound to Task 1 input and a proven default `provider_unavailable` path with no command/network activity.

### Task 3: Render and independently evaluate at most three exact-SHA candidates

**Create:** `factory/src/adaptive_factory/landing_renderer.py`, `landing_evaluation.py`, `landing_coordinator.py`, `factory/tests/test_landing_renderer.py`, `factory/tests/test_landing_coordinator.py`.
**Modify:** workspace broker only through additive landing-specific composition.

- [ ] Write tests for escaped deterministic HTML/CSS, static/no-remote/no-script output, the two-file target write allowlist, exact-base verification, fresh context/workspace, no credential/network capability, cleanup, distinct read-only evaluator, bounded repair projection, append-only prior digest, and hard ordinal `1..3` ceiling.
- [ ] Run `python3 -m unittest factory.tests.test_landing_renderer factory.tests.test_landing_coordinator -v`; expected RED is missing renderer/coordinator behavior.
- [ ] Implement a pure renderer and coordinator over fresh disposable workspaces of the exact target SHA/tree. Preserve the control-repository showcase and all target paths except root `index.html` and `content.css` by checked digest, including indexed URL topology, locale/legal pages, verification files, robots, sitemap, canonical, and hreflang facts; never mutate the read-only target clone.
- [ ] Implement the independent deterministic evaluator with fixed policy/rubric and closed `pass|repair|needs_human`; only verified reason codes reach a fresh next attempt. Attempt three non-pass and every fourth-attempt request terminate `needs_human`.
- [ ] Run the focused modules to GREEN, targeted Ruff/diff check, and commit `feat(factory): add bounded landing render loop`.

**Handoff:** one sealed exact candidate SHA/tree with a complete one-to-three-attempt chain, or a closed terminal disposition; mutable “best candidate” state does not exist.

### Task 4: Seal the exact candidate as deterministic site artifact

**Create:** `factory/src/adaptive_factory/landing_artifact.py`, `factory/tests/test_landing_artifact.py`; generated artifacts remain ignored/local.
**Modify:** no product packager or published ZIP.

- [ ] Write tests for exact candidate binding, complete sorted manifest, path/mode/hash validation, symlink/traversal/special-file/case-collision rejection, fixed ZIP metadata, atomic pair creation, replay identity, and product-package isolation.
- [ ] Run `python3 -m unittest factory.tests.test_landing_artifact -v`; expected RED is absent site artifact construction.
- [ ] Implement `SiteArtifactV1` and a site-only content-addressed packager that accepts exactly the Task 3 selected tree inventory, writes private temporary bytes, fsyncs, hashes, and atomically installs ZIP then sidecar without replacement.
- [ ] Build the same fixture candidate twice in separate temporary directories and assert identical ZIP SHA-256, sidecar content, manifest, and member inventory.
- [ ] Run the focused module to GREEN, targeted Ruff/diff check, and commit `feat(factory): seal deterministic landing artifact`.

**Handoff:** immutable exact-SHA site ZIP/sidecar identity distinct from `packages/adaptive-grok-build-pro-v2.0.13.zip`; it conveys no Trust CI, signing, or publication authority.

### Task 5: Integrate the additive API and disabled publication boundary

**Create:** `delivery/src/adaptive_delivery/landing_publisher.py`, `delivery/tests/test_landing_publisher.py`, `factory/tests/test_landing_api.py`.
**Modify:** `factory` API/server/settings/OpenAPI registration, architecture model/rules/diagrams, root/factory documentation, active package state/evidence only as required for the truthful final source.

- [ ] Write tests for authenticated submit/status/cancel/result parity, correlation/idempotency, default unavailable provider, local `artifact_ready`, publisher denial before transport, absence of live/indexed results, and frozen showcase/migration/M0-M9/package digests.
- [ ] Run `python3 -m unittest factory.tests.test_landing_api delivery.tests.test_landing_publisher -v`; expected RED is absent API/publisher integration.
- [ ] Wire the additive routes and local store through existing composition without migration. Implement only `LandingPublisher` plus `UnavailableLandingPublisher`; no HTTPS client, credential/config discovery, live adapter, or fake production-success path.
- [ ] Update architecture/docs to describe actual source and operational blockers. Run the Task 5 tests, `tests.test_structure`, architecture validate/drift/diagram checks, targeted Ruff, and diff check to GREEN.
- [ ] Commit source-freeze `F` as `feat: integrate offline landing dogfood` with state `verifying` and no `2.0.14` product ZIP. The parent finalization flow runs gate wave 1 on exact `F`, records bookkeeping-only ready child `R`, builds twice from exact `R`, adds only the `2.0.14` ZIP/sidecar as artifact child `A`, then runs gate wave 2 on exact `A`; repairs remain owned by this implementer and invalidate stale receipts.

**Handoff:** clean locally ready source with fingerprint-bound verifier/review evidence and no external effect. Push, PR, merge, release, provider transfer, signing, and deployment require new explicit authority and are not steps in this plan.
