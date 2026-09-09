# Architect — factory live path auto-assembles the complete L5 landing artifact

Route: `c2837bf9d4a4`
Change: `20260906-factory-live-path-automatically-assembles-the-co-c2837b`
Authority SHA: `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9` (published 2.0.15 product source)
This checkout: stale `2.0.12` on `fix/path-aware-shell-policy-circuit-breaker`. Do not implement from it.
Role: read-only design. No implementation in this report.

## 1. Ruling

Ship the smallest **default-off live composition** over existing L5 seams on `fd51dcf`:

When an **injected** live executor succeeds, the factory **automatically** runs the existing coordinator + packager and returns a complete local `SiteArtifactV1` (20-member ZIP + sidecar). Tests fake the executor. The repository still ships **no** live Codex process, **no** network publisher, **no** landing-repo mutation, and `live_url` remains JSON `null`.

Do **not** retarget the implemented source pin from frozen `6990103` to observed `80d6215` in this slice. A SHA-only swap would package newer analytics/privacy bytes through a 6990103-era renderer and inventory. The live binding **must** name SHA + tree + renderer identity + inventory digest, and construction must fail closed unless that tuple equals the **currently implemented** renderer pin.

Empty/unavailable remains the shipped default. Success of a fake executor in tests is not a live model turn and does not advance the design-partner pilot.

## 2. What origin/main already owns

L5 landing **source** is already on `main` via PR #24 (`v2.0.14`) plus the unreleased Stage 3/5 local runtime that landed before `fd51dcf`. That is repository product, not an enabled live path.

| Layer | Location on `fd51dcf` | Current bound |
| --- | --- | --- |
| Exact source pin | `landing_renderer.py` `TARGET_BASE_SHA` / `TARGET_BASE_TREE` | `699010380f4f90a0193a9c22090c35e6aded7d2c` / `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4` |
| Writes | `LANDING_WRITE_PATHS` | exactly `{index.html, content.css}`; source-owned `index.css` protected |
| Inventory | `landing_artifact.py` `DEPLOY_MEMBERS` | closed 20-member deploy set |
| Coordinator | `landing_coordinator.py` | ≤3 attempts; writer ≠ evaluator; `candidate_ready` or `needs_human` |
| Packager | `LandingArtifactPackager` | private `--no-local` clone, source guard, no origin write |
| Builder | `CoordinatedLandingArtifactBuilder` | coordinator → packager → `RetainedLandingArtifact` |
| Service | `LandingApplicationService._process` | if spec normalized **and** `artifact_builder` present → `artifact_ready`; if builder is `None` → `needs_human` / `artifact_builder_unavailable` |
| Default provider | `server.py` `build_app` | `UnavailableLandingProvider`, **no** `artifact_builder` |
| Codex seam | `CodexLandingNormalizer` + `CodexLandingExecutor` | “repository ships no live executor”; default `unavailable_codex_landing_profile()` |
| Publisher | `delivery/.../landing_publisher.py` | `UnavailableLandingPublisher.publish` always raises; `live_url` OpenAPI type `null` |
| Result contract | `landing-dogfood.v1.json` Result | frozen `live_url: {const: null}`; SHA256 `4aa733b43c6f2fca…` |
| Observed drift | `PROJECT_STATE.json` `observed_target_drift` | landing `main` `80d621545938e24c296420d7f685f2d0b2b5785e` / tree `a1c2eff37ec808a53b2aeec089a5f6d7cb72bd55`, `blocked_before_model_attempt` |

Existing tests already prove **pieces**, not the live composition:

- `test_landing_normalizer.py`: fake `RecordingExecutor` → `StaticLandingSpecV1` only. No coordinator, no packager, no ZIP.
- `test_landing_runtime.py`: `BoundProvider` (not Codex) + manual `CoordinatedLandingArtifactBuilder` → complete artifact + SQLite replay.
- `test_landing_api.py`: `BoundArtifactBuilder` returns a synthetic `SiteArtifactV1` without Git/packager.
- `test_server.py`: quarantine composition is unavailable provider, no builder.

The gap is one constructor: injecting a succeeding executor currently does **not** force coordinator+packager. Callers can get `needs_human` / `artifact_builder_unavailable` after a “successful” live normalize.

## 3. What this slice must not do

Preserve, do not reopen:

- Default `UnavailableLandingProvider` / unavailable Codex profile. Zero process, zero blob read, zero packager on the shipped server path.
- `live_url is None` on every result, including `artifact_ready`. Frozen OpenAPI Result stays byte-identical (`4aa733b43c6f2fca9ec6f40d442ebd5c585fc96d489006b0c05054963da55dd3`).
- `UnavailableLandingPublisher` as the only publisher. No cPanel/FTP/SFTP/HTTPS adapter, DNS/TLS, credentials, or M9 `DryRunController` reuse.
- Landing-repo mutation. Packager already clones privately and raises `source_mutation` if the source HEAD/tree/worktree changes. Do not `git add` / commit / push in `ai-dark-factory-landing`.
- Renderer pin swap to `80d6215`. Do not change `TARGET_BASE_SHA`, `TARGET_BASE_TREE`, `DEPLOY_MEMBERS`, `LANDING_WRITE_PATHS`, or `RENDERER_VERSION` in this slice.
- OpenAPI `ExactBaseSha` const (still predecessor `176efca…` by freeze). Runtime `source_identity` 409 remains the authority; do not “fix” the frozen snapshot here.
- Factory PostgreSQL migrations `001`–`018`, M8/M9 activation, GitHub Actions, VERSION/ZIP/tag, Trust CI policy/holdout, human keys, `.env`.
- Design-partner `pilot/` issue-to-PR cycle, real Codex start, GitHub issue snapshot, or PR publication. That track is separately blocked on `80d6215`.
- `FACTORY_LANDING_LIVE=true` (or any env flag) that enables a real executor. Live is constructor-injected only.

## 4. Smallest coherent vertical

Additive factory **library composition** on `origin/main`. No new HTTP route, no new service, no new datastore, no publisher.

```text
submit (existing four routes)
        │
        ▼
CodexLandingNormalizer(profile, injected executor | unavailable)
        │  fake executor in tests; none shipped
        ▼
normalized StaticLandingSpecV1
        │  automatic, not optional, when live executor was injected
        ▼
CoordinatedLandingArtifactBuilder
   LandingCoordinator (workspace + renderer + evaluator)
        → LandingArtifactPackager.seal
        → RetainedLandingArtifact
        │
        ▼
artifact_ready, artifact_digest=<hex64>, live_url=null
```

Default (no injection):

```text
UnavailableLandingProvider  →  provider_unavailable
artifact_builder = None
live_url = null
zero executor / git / packager effects
```

### 4.1 Live composition object

Add a closed constructor on the existing runtime module (prefer `landing_runtime.py` over a new package). Suggested shape:

```text
LandingLiveBindingV1
  schema_version = 1
  repository_id
  exact_base_sha          # hex40
  exact_base_tree         # hex40
  renderer_version        # must equal RENDERER_VERSION
  deploy_members          # exact tuple equal to DEPLOY_MEMBERS
  write_paths             # exact frozenset equal to LANDING_WRITE_PATHS
  enabled                 # bool; shipped default False
  binding_digest          # landing_digest("live-binding", facts)

compose_landing_live(...) -> LandingApplicationService
compose_unavailable_landing(...) -> LandingApplicationService   # current server path
```

`compose_landing_live` requires **all** of:

1. `binding.enabled is True` (tests only; shipped default never constructs this).
2. `binding.exact_base_sha == landing_renderer.TARGET_BASE_SHA`
3. `binding.exact_base_tree == landing_renderer.TARGET_BASE_TREE`
4. `binding.repository_id == TARGET_REPOSITORY_ID`
5. `binding.renderer_version == RENDERER_VERSION`
6. `binding.deploy_members == DEPLOY_MEMBERS` and `binding.write_paths == LANDING_WRITE_PATHS`
7. `CodexLandingProfile.available is True`
8. a `CodexLandingExecutor` instance (tests: `RecordingExecutor` or equivalent)
9. absolute source repository, scratch root, output directory (mode 0700, outside the control repo)

On success it wires:

- provider = `CodexLandingNormalizer(profile, executor)`
- `artifact_builder` = `CoordinatedLandingArtifactBuilder(coordinator, packager, output_directory)` **unconditionally**

Callers cannot inject an executor without the packager. That is the whole product change.

On any binding mismatch: raise a closed `LandingRuntimeError` (`source_binding_unimplemented` or `profile_source_mismatch`) **before** executor or Git. A binding that names `80d6215` while the renderer still pins `6990103` cannot start.

`compose_unavailable_landing` stays the server default: unavailable provider, no executor, no builder. Do not pass a landing Git path. Do not read `FACTORY_LANDING_QUARANTINE_PATH` as a live switch.

### 4.2 SHA ruling: profile-bound, not swapped

| SHA | Role | This slice |
| --- | --- | --- |
| `699010380f4f90a0193a9c22090c35e6aded7d2c` / `f7dbbd80…` | Implemented renderer + service pin; frozen live-binding default | **Keep.** Live binding must name this exact tuple (or the test-patched `TARGET_BASE_*` from `sealed_target()`). |
| `80d621545938e24c296420d7f685f2d0b2b5785e` / `a1c2eff3…` | Observed landing `main` with newer analytics/privacy and archive coherence | **Do not pin.** Document as unimplemented source. Construction with this SHA fails closed. |
| OpenAPI const `176efca…` / `f2bdcecc…` | Frozen predecessor contract snapshot | **Do not edit.** Runtime 409 already rejects it. |

Why not SHA-only swap to `80d6215`:

- Renderer identity, protected `index.css` blob, 20-member inventory, and write-path tests are 6990103-era facts.
- `80d6215` is documented as analytics/privacy plus source-to-deployment-archive work. Substituting the hex would either drop those semantics from policy or silently pack them without a reviewed renderer/inventory/identity bump.
- Pilot/runbook already forbids “merely substitute a SHA or overwrite newer work.”

Why the target SHA **must** become profile-bound (sibling of the Codex executor profile, not a mutated module constant):

- `CodexLandingProfile` today has no SHA/tree. Submit headers are checked against `TARGET_BASE_SHA` in `LandingApplicationService`, but a live executor could still be composed while an operator believes they are targeting observed `80d6215`.
- A later reviewed refresh to `80d6215` is a **new** binding digest: new renderer identity, possibly new inventory/analytics policy, new tests. It must not look like the 6990103 live profile with one field overwritten.
- Keep `CodexLandingProfile` as executor/capability identity (CLI version, executable digest, prompt/schema). Add `LandingLiveBindingV1` as source/renderer/inventory identity. Both digests are required to enable live assembly. Mutating either digest is a new empty live epoch, never a mixed artifact.

Tests that use `sealed_target()` already patch `TARGET_BASE_SHA` to a disposable fixture commit. The live binding must equal **the implemented pin at construction time**, not a second hardcoded `6990103` that would fail those fixtures. Production construction uses the module constants (`6990103`). Observed `80d6215` is never an alternate pin in this slice.

Do **not** add `exact_base_sha` onto `CodexLandingProfile` in this slice unless a test proves the executor request itself must carry it. Source identity belongs on the live binding; `LandingInputV1` already carries SHA/tree into normalize/build.

### 4.3 Automatic assembly on executor success

Reuse `LandingApplicationService._process` as-is. After `outcome.state == "normalized"`:

1. Validate spec/evidence binding (existing).
2. Call `artifact_builder.build(source, spec, evidence)` (existing). Because live composition always supplies `CoordinatedLandingArtifactBuilder`, this is the complete L5 artifact, not a stub `SiteArtifactV1`.
3. Persist `artifact_ready` + `sealed_artifact`. `result_view()["live_url"]` stays `None`.

Preserve existing fail-closed branches:

| Executor / media outcome | Builder called? | Terminal |
| --- | --- | --- |
| unavailable profile | no | `provider_unavailable` / `profile_unavailable` |
| profile drift | no | `provider_unavailable` / `profile_drift` |
| pdf / audio | no | `needs_human` / extractor reasons |
| invalid text | no | `rejected` |
| malformed model JSON | no | `needs_human` / `invalid_model_output` |
| valid draft (fake executor) | **yes, coordinator+packager** | `artifact_ready`, `live_url=null` |
| coordinator `needs_human` | builder ran, failed closed | `needs_human` (service maps builder exception to internal/needs_human; do not invent a publisher) |
| default server composition | no | `provider_unavailable` |

PDF/audio must still stop **before** executor and **before** packager.

### 4.4 No landing-repo mutation, no publisher

Packager `ExactGitLandingArtifactSource.materialize` already:

- clones with `--no-local --no-hardlinks` into a private workspace;
- checks out the snapshot source SHA detached;
- removes `origin`;
- writes only `index.html` / `content.css` inside the clone;
- compares `source_guard` after cleanup; source HEAD/tree/worktree change → `source_mutation`.

Live tests must use `sealed_target()` (or an equally disposable clone). They must not point the packager at a developer checkout of `ai-dark-factory-landing`.

Do not import or compose `LandingPublisher`. Do not add a `live_url` assignment anywhere except the existing `None`.

## 5. Files

Implementer works from a **new branch off `origin/main` `fd51dcf`**, not this worktree and not PR #12/#28.

**Add**

| Path | Why |
| --- | --- |
| `factory/src/adaptive_factory/landing_live.py` **or** functions at the bottom of `landing_runtime.py` | `LandingLiveBindingV1`, `compose_landing_live`, `compose_unavailable_landing`. Prefer extending `landing_runtime.py` if the file stays small; split only if binding+compose would bury the existing builder. |
| `factory/tests/test_landing_live.py` | Default-off, fake-executor success → complete artifact, mismatch SHA, no publisher, no source mutation |

**Optional add**

| Path | Why |
| --- | --- |
| `factory/contracts/jsonschema/landing-live-binding.v1.schema.json` | Only if the binding is serialized. If it is a constructor-only dataclass, skip the schema and do **not** expand the frozen six-schema inventory in `test_landing_contracts.py`. |

**Touch (minimal)**

| Path | Why |
| --- | --- |
| `factory/src/adaptive_factory/server.py` | Keep default unavailable + no builder. Optionally accept a prebuilt `landing_service` (already does). Do **not** auto-compose live from env. Add a one-line comment or assertion that live composition is injected, not default. |
| `factory/tests/test_server.py` | Default quarantine composition still has no executor and no `artifact_builder`. |
| `factory/src/adaptive_factory/landing_runtime.py` | If compose lives here: export binding checks next to `CoordinatedLandingArtifactBuilder`. |
| `factory/README.md` | One truthful sentence **after** tests are green: default-off live composition auto-seals the L5 artifact when an injected executor succeeds; `live_url` remains null; source pin unchanged. |

**Do not change in this slice**

- `landing_renderer.py` `TARGET_BASE_*`, `RENDERER_VERSION`, write paths
- `landing_artifact.py` `DEPLOY_MEMBERS` / packager Git guards
- `landing_publisher.py`, OpenAPI `landing-dogfood.v1.json`, Result `live_url`
- `landing_provider.py` unavailable default
- `CodexLandingProfile` field set (unless a red test proves SHA must ride the executor profile; default ruling: no)
- `resources/001_*.sql`–`018_*.sql`, `store.py`, factory Postgres
- `pilot/**` (separate `80d6215` blocker)
- `trust-ci/**`, `.github/**`, packages/ZIP/VERSION
- Real landing clone under `/home/pall/grok-projects/ai-dark-factory-landing`

**Docs (only after behavior exists)**

One sentence on the product PR. Do not pre-claim live hosting or a model turn. Do not load this into PR #28.

## 6. Tests

P0 (must fail before implementation, then pass). Put them in `factory/tests/test_landing_live.py`. Fake the executor; never start Codex.

1. **Default-off.** `compose_unavailable_landing` (or server quarantine path) on text submit → `provider_unavailable`; executor `run` call count `0`; no ZIP directory entries; `result.live_url is None`; `subprocess.Popen` not used.
2. **Injected fake executor success auto-assembles the complete artifact.** `compose_landing_live` with `RecordingExecutor` (valid draft JSON) + `sealed_target()` → job `artifact_ready`; `sealed_artifact.member_names == tuple(sorted(DEPLOY_MEMBERS))`; ZIP and sidecar exist; `artifact.source_sha` equals the **fixture** SHA (patched pin), not `80d6215`; `live_url is None`; coordinator disposition `candidate_ready`; builder is the real `CoordinatedLandingArtifactBuilder`, not `BoundArtifactBuilder`.
3. **Executor failure does not pack.** Malformed stdout → `needs_human` / `invalid_model_output`; output directory empty; live_url null.
4. **PDF/audio never reach executor or packager.** Same reasons as `test_landing_normalizer.py`.
5. **`80d6215` binding is unimplemented.** Constructing `LandingLiveBindingV1` with observed SHA/tree while `TARGET_BASE_SHA` is 6990103 (or fixture SHA) raises before executor. No Git clone, no ZIP.
6. **SHA-only swapped binding with matching hex but wrong renderer/inventory is rejected.** A binding that copies `TARGET_BASE_SHA` but lies about `renderer_version` or `deploy_members` fails closed (`binding_identity`). Prevents “pin the new SHA, keep old inventory.”
7. **Source mutation is detected, not written through.** After `sealed_target()` commit, append a file to the fixture repo and/or move HEAD; packager/build fails `source_identity` or `source_mutation`; original fixture commit still on its HEAD (test asserts no new commit from the factory).
8. **No publisher import/effect.** Live composition module does not import `adaptive_delivery.landing_publisher`. `artifact_ready` result JSON still has `"live_url": null` only.

P1:

- Idempotent submit replay does not call executor or packager again (reuse SQLite pattern from `test_landing_runtime.py` if the live compose uses SQLite; in-memory is acceptable for the success-path unit test if restart coverage stays in the existing runtime test).
- Existing `test_landing_normalizer.py`, `test_landing_runtime.py`, `test_landing_api.py`, `test_landing_contracts.py` OpenAPI digest, and `test_server.py` stay green.
- `tests/test_project_state.py` `CURRENT_LANDING_SHA` remains `6990103…`. Do not retarget it to `80d6215`.

Do **not** add a test that performs a real Codex exec, opens a network socket, or writes to the real landing repository.

Focused commands after implementation (write owner):

```bash
# from a branch of fd51dcf, inside factory/
python3 -m unittest factory.tests.test_landing_live factory.tests.test_landing_runtime factory.tests.test_landing_normalizer factory.tests.test_landing_api factory.tests.test_server -v
python3 scripts/grok_verify.py --mode pr
```

## 7. Rollout and rollback

**Rollout**

1. Leave this 2.0.12 checkout. New branch from `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9`.
2. Characterization tests first (default unavailable; fake executor does not yet auto-pack — that red test is the slice).
3. Implement `LandingLiveBindingV1` + `compose_landing_live` that always attaches coordinator+packager.
4. Local verify + route reviews (`code_reviewer`, `test_reviewer`).
5. Open a **new** PR to `main`. Wait for App-owned `adaptive-trust-ci/verified@06ecf1c875bc` on the exact head SHA.
6. Do not merge, tag, release, deploy, enable a live Codex binary, or refresh the landing pin to `80d6215`. No delegated grant in this package.

No feature flag. Absence of an injected executor **is** the flag. Server composition stays unavailable.

**Rollback**

Revert the successor commit. There is no migration, no production env, no committed landing artifact, no publisher state. Default on `fd51dcf` remains `UnavailableLandingProvider` without a builder. Disposable `sealed_target()` repos and test output dirs vanish with the process.

**Forward recovery**

If a later slice reviews `80d6215` analytics/privacy/archive policy: update renderer identity, inventory/tests, then mint a **new** `LandingLiveBindingV1` digest that names `80d6215` **and** the new renderer/inventory. Do not edit the 6990103 binding in place. A live executor for that epoch is still a separate injection, still default-off, still `live_url=null` until a separately granted publisher exists.

## 8. Residual risk

| Risk | Mitigation |
| --- | --- |
| Implementer SHA-swaps `TARGET_BASE_SHA` to `80d6215` “so live matches origin” | Forbidden. Binding check + P0 test 5–6. Renderer/inventory stay 6990103. |
| Implementer adds `live_url` or a transport fake reachable from server | Forbidden. Frozen OpenAPI digest. No publisher import. |
| Fake executor success without packager (stub `SiteArtifactV1`) | Forbidden. Live compose must type-check `CoordinatedLandingArtifactBuilder` and assert 20 members. |
| Env flag enables a host Codex binary | Forbidden. Constructor injection only. |
| Tests write the real landing clone | Forbidden. `sealed_target()` only. Source-guard test. |
| Mixing this slice into the design-partner pilot / issue #1 | Out of scope. Pilot remains blocked on a reviewed `80d6215` policy refresh. |
| Claiming “factory is live” because tests packed a ZIP | Tests are fixtures. Shipped default is still unavailable. README sentence must say default-off. |
| Changing frozen OpenAPI SHA consts to 6990103 or 80d6215 | Out of scope. Runtime 409 already enforces the implemented pin. |

## 9. Write-owner sequence

1. Branch from `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9`.
2. Fill change-package requirements/architecture/test-plan from this report (default-off live compose; fake executor; auto coordinator+packager; no publisher; pin stays 6990103; binding is profile-like and rejects 80d6215).
3. Red tests → compose + binding → green focused tests.
4. Do not open production, do not merge, do not edit PR #12/#28, do not touch the landing repository.
5. After behavior exists, a small README hunk on the **same** PR may record default-off auto-assembly and unchanged `live_url`/source pin.

This slice moves L5 from “coordinator and packager exist, but a succeeding executor does not automatically seal the landing” to “injected live executor success always produces the complete local L5 artifact; default remains unavailable; observed `80d6215` is still a future source-policy refresh, not a hex swap.” That is the whole slice.
