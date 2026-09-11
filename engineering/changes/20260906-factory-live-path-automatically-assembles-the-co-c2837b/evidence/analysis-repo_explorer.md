# Repo explorer: why factory L5 does not automatically produce a complete live landing

Inspected **origin/main `fd51dcfed6b33f4a8707c0db602328146df17cc9` only**. Working tree HEAD was not used as product truth. No implementation.

## Live-run failure chain (current main)

A live factory process that uses `server.build_app()` never reaches a sealed site. The path stops at **provider composition**, then again at **artifact builder absence**, then again at **publication**. Even a successful offline seal still reports **no URL**.

### 1. `LandingApplicationService._process` is a local, one-shot pipeline

File: `factory/src/adaptive_factory/landing_service.py`.

`submit()` gates `exact_base_sha` / `exact_base_tree` against hardcoded renderer constants, accepts a blob, persists `accepted`, then **synchronously** calls `_process()` under a process lock. `_process`:

1. Transitions `accepted` → `normalizing`.
2. Calls `self._provider.normalize(...)`.
3. If `outcome.state != "normalized"` or `spec is None`, **returns that terminal state immediately** (`provider_unavailable`, `needs_human`, `rejected`). No renderer, no ZIP.
4. If spec is present **but `self._artifact_builder is None`**, returns `needs_human` / `artifact_builder_unavailable`.
5. Else `generating` → `artifact_builder.build` → `artifact_ready`.

There is no queue, no live Codex spawn, no hosting step. Unexpected exceptions become `needs_human` / `internal_failure`.

`result_view()` **always** serializes `"live_url": None`. There is no field, setter, or publisher hook that can populate a URL.

### 2. Default live composition: unavailable provider, no builder

File: `factory/src/adaptive_factory/server.py` (`build_app`).

When `landing_service is None` and quarantine is configured, the process wires:

- `unavailable_landing_profile()`
- `UnavailableLandingProvider(profile)`
- `LandingApplicationService(..., profile_digest=...,)` with **default `artifact_builder=None`**
- **No** `CodexLandingNormalizer`, **no** `CoordinatedLandingArtifactBuilder`

`UnavailableLandingProvider.normalize` (`landing_provider.py`) **never reads the blob**. It returns `state="provider_unavailable"`, `reason_code="profile_unavailable"`, `spec=None`. `_process` therefore never generates HTML.

`FixedCommandLandingProvider` exists for **explicit fixtures** only; it is not the server default.

### 3. `CodexLandingNormalizer` is a seam, not a live executor

File: `factory/src/adaptive_factory/landing_normalizer.py`.

Class docstring: *“Native-Codex request seam; the repository ships no live executor.”*

- Default profile helper `unavailable_codex_landing_profile()` sets `available=False`, `executable=None`, `tool_policy_digest` of `b"no-live-executor-capability"`.
- `normalize()` with `available=False` returns `provider_unavailable` / `profile_unavailable` **before** blob read or `executor.run`.
- Even with `available=True`, it requires a caller-injected `CodexLandingExecutor`. The repository does not ship a subprocess/CLI implementation used by `server.py`.
- PDF → `needs_human` / `pdf_extractor_unavailable`; audio → `needs_human` / `audio_transcriber_unavailable`; both **before** blob/executor.
- Text / image / DOCX can decode a **closed draft JSON** into `StaticLandingSpecV1` only if an executor returns valid stdout. That is test-only today (`RecordingExecutor` in `factory/tests/test_landing_normalizer.py`).

The normalizer never writes git, never clones Dimkox, never hosts.

### 4. Hardcoded `TARGET_BASE_SHA` / `TARGET_BASE_TREE`

File: `factory/src/adaptive_factory/landing_renderer.py`:

- `TARGET_REPOSITORY_ID = "github.com/Dimkox/ai-dark-factory-landing"`
- `TARGET_BASE_SHA = "699010380f4f90a0193a9c22090c35e6aded7d2c"`
- `TARGET_BASE_TREE = "f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4"`
- Writes only `index.html` and `content.css` (`LANDING_WRITE_PATHS`)
- Workspace checkout is **detached** at that SHA; head/tree mismatch raises `source_identity`

`landing_service.submit` rejects any other SHA/tree with HTTP 409 `source_identity`. A live clone that moved past this commit cannot assemble. Tests that succeed (`test_landing_runtime.py`) **patch** these constants onto a **local `sealed_target()` fixture**, not the operator’s Dimkox checkout.

### 5. `live_url` is unrepresentable as non-null

- `LandingJobRecord.result_view()` hardcodes `live_url: None`.
- Delivery port `delivery/src/adaptive_delivery/landing_publisher.py`: `UnavailableLandingPublisher.publish` always raises; tests prove it inspects neither artifact nor sockets.
- `CoordinatedLandingArtifactBuilder` docstring: compose render/evaluate/seal **without publishing**.

A complete local ZIP is still not a live landing.

### 6. `CoordinatedLandingArtifactBuilder` is local seal only

File: `factory/src/adaptive_factory/landing_runtime.py`.

It requires a `LandingCoordinator` + `LandingArtifactPackager` + absolute output dir. `build()`:

1. `coordinator.run(spec)` must yield `candidate_ready` with attempts/evaluations.
2. Packager seals ZIP + sidecar into the output directory.
3. `RetainedLandingArtifact.capture` stores metadata.

Renderer uses `ExactGitLandingWorkspace` against a **read-only exact-SHA clone copy**. It does not push, merge, or mutate the operator’s landing repo. Server never constructs this builder, so live `_process` hits `artifact_builder_unavailable` even if a provider were swapped in without a builder.

## What “automatic full-site assembly” would mean vs this tree

| Stage | Live default (`build_app`) | Offline test that already works | Gap for “live automates the landing” |
| --- | --- | --- | --- |
| Intake | Yes (if quarantine configured) | Yes | — |
| Normalize | `UnavailableLandingProvider` | Fake/fixed provider or `RecordingExecutor` | Default-off; no live Codex |
| Render/eval/seal | Skipped (`artifact_builder is None`) | `CoordinatedLandingArtifactBuilder` + `sealed_target()` | Not wired in server |
| PDF/audio | Never reached | Explicit `needs_human` | No extractors |
| Host / URL | Impossible | `live_url` still null | Publisher deny-by-design |
| Dimkox mutation | Forbidden / unused | Fixture clone only | Must stay grant-gated |

## How a FAKE live-executor test can prove assembly without Codex or Dimkox writes

**Goal:** prove the **service path** can go `submit` → normalize → generate → `artifact_ready` with a full sealed member set, **without** calling a real Codex binary, network, or the real `ai-dark-factory-landing` working tree.

**Do not:** spawn Codex CLI, open sockets, `git push`, checkout the operator clone in-place, or set a non-null `live_url`.

**Suggested shape** (characterization, in-process):

1. **Fake executor** implementing `CodexLandingExecutor.run`: record the `CodexExecutionRequest`; return `CodexExecutionResult` with closed draft JSON (same shape as `factory/tests/test_landing_normalizer.py` `draft()`), `exit_code=0`. Optionally assert argv starts with a **temp fixture file** labeled “codex”, not a real install.
2. **Available `CodexLandingProfile`** pointing at that fixture file’s SHA (as existing tests). Wrap `CodexLandingNormalizer(profile, fake_executor)` as the `LandingProvider`.
3. **Isolated git fixture** via existing `sealed_target()` (or equivalent): a **copy** whose HEAD is whatever SHA/tree the test patches onto `landing_service.TARGET_BASE_SHA` / `TARGET_BASE_TREE` (and renderer if the coordinator reads them). Never the live Dimkox path.
4. **`CoordinatedLandingArtifactBuilder`** with `ExactGitLandingWorkspace(fixture)`, `DeterministicLandingRenderer`, `DeterministicLandingEvaluator`, `LandingArtifactPackager`, temp output dir.
5. **`LandingApplicationService`** with in-memory or SQLite store, private blob dir, the fake normalizer, **explicit** `artifact_builder=builder`.
6. **Submit** `text/plain` (and optionally image/docx) as the operator would.
7. **Assert:**
   - job `state == "artifact_ready"`
   - sealed ZIP exists; member names match `DEPLOY_MEMBERS` (20-member inventory on this SHA)
   - `result_view()["live_url"] is None`
   - fake executor `run` called **once** for text/docx/image; **zero** OS process launches if the fake is pure Python
   - fixture remote/working tree unchanged (no extra commits on the source clone; writes only in workspace scratch + output dir)
   - PDF/audio still `needs_human` with the existing reason codes (documents remaining human gates)
8. **Negative:** same service **without** builder still `needs_human` / `artifact_builder_unavailable`; `UnavailableLandingProvider` still `provider_unavailable` — proving default live remains off.

That test is the proof of **automatic full-site assembly of the local artifact**. It is **not** proof of hosting, indexing, merge, or production Codex. Those remain grant-gated and out of default composition on `fd51dcf`.

## Impact surface for a later implementer (read-only note)

- Must change **composition** (`server.build_app`) to opt-in live path; default should stay unavailable unless an explicit live flag/grant exists.
- `_process` already supports a builder; wiring is the live gap, not a missing state machine.
- Do not relax `live_url` or publisher without a separate grant-gated delivery change.
- Do not retarget SHA/tree without binding the exact clone used in tests.
- Do not add a real Codex subprocess in unit tests; keep `CodexLandingExecutor` fake.

## Unverified on this inspect

- Whether any operator host already injects a custom `landing_service=` into `main()` outside this repo.
- Current HEAD of the real Dimkox landing repository vs `6990103…`.
