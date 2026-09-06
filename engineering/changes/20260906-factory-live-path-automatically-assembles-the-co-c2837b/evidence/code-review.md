# Code review — factory live auto-landing

**Reviewer:** code_reviewer (read-only)
**Repository:** `/home/pall/grok-projects/adaptive-grok-build-pro-l5-live`
**Branch:** `feat/factory-live-auto-landing`
**Base:** `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9`
**Change:** `engineering/changes/20260906-factory-live-path-automatically-assembles-the-co-c2837b`
**Inspected tree:** uncommitted working tree (no commits on branch vs `origin/main`)
**Verdict:** **PASS**

## Scope inspected

Working-tree diff vs `origin/main` (not yet committed):

- `factory/src/adaptive_factory/landing_runtime.py` — `LandingLiveBindingV1`, `implemented_live_binding`, `compose_unavailable_landing`, `compose_landing_live`
- `factory/src/adaptive_factory/server.py` — comment + still `UnavailableLandingProvider`
- `factory/README.md` — default-off live composition note
- `factory/tests/test_landing_live.py` — new untracked tests
- `decisions.md`, `mistakes.md` — append-only facts
- change package `change-spec.yaml` (ACs/forbiddens); `brief.md` / `requirements.md` / `architecture.md` / `tasks.md` / `test-plan.md` remain template stubs

No `.github/workflows/` added. No product `.env` read.

## Contract check vs `change-spec.yaml`

| ID | Statement | Finding |
| --- | --- | --- |
| AC-001 | Default unavailable never calls executor; no artifact builder; `live_url` null | **Met.** `compose_unavailable_landing` wires `UnavailableLandingProvider` without `artifact_builder`. Test asserts `provider_unavailable`, empty executor log, `service._artifact_builder is None`. |
| AC-002 | Injected live executor + enabled binding seals 20-member artifact, `live_url` null | **Met.** `compose_landing_live` attaches coordinator+packager+`CodexLandingNormalizer`. Test asserts `artifact_ready`, `DEPLOY_MEMBERS` names, zip file, `live_url is None`. |
| AC-003 | Binding SHA `80d6215…` fails closed before executor | **Met.** Compose compares `binding.exact_base_sha/tree` to shipped `landing_pins.TARGET_*` and raises `source_binding_unimplemented`. Test uses `OBSERVED_SHA = 80d621545938e24c296420d7f685f2d0b2b5785e`. |
| AC-004 | PDF intake on live composition → `needs_human`, no executor | **Met.** |
| AC-005 | Disabled binding cannot compose | **Met.** `enabled=False` → `live_disabled`. |
| FORBID-001 | No default-on executor, env flag, or network publisher | **Met.** Server path still `UnavailableLandingProvider`. `implemented_live_binding(enabled=False)` default. No new `os.environ` / `FACTORY_LANDING_LIVE` flag. Publisher not introduced. |
| FORBID-002 | Non-null `live_url` or landing-repo mutation | **Met.** `LandingJobRecord.result_view` still hard-codes `"live_url": None`. Live workspace is `ExactGitLandingWorkspace(source, scratch_root=scratch)` plus packager output dir — source is a test fixture clone, not a live landing-repo write path. |
| FORBID-003 | SHA-only retarget 6990103 → 80d6215 | **Met.** Pin remains `699010380f4f90a0193a9c22090c35e6aded7d2c` / tree `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4` in README and `implemented_live_binding`. |
| INV-001 | Shipped server landing path remains unavailable without artifact builder | **Met.** `server.py` L183–195. |
| INV-002 | Live composition constructor-injected; always coordinator + packager | **Met.** |

## Confirmations requested by the review brief

- **Default remains unavailable:** yes (`compose_unavailable_landing` + server).
- **`live_url` stays null:** yes (job view + tests).
- **No landing-repo mutation:** yes (scratch workspace + output directory; no git write API).
- **`80d6215` fails closed:** yes, before executor.
- **Fake executor auto-seals 20-member artifact:** yes (`RecordingExecutor(draft())` → `member_names == sorted(DEPLOY_MEMBERS)`).
- **No env flag:** yes.
- **No GitHub Actions:** no `.github` in this tree; diff does not add workflows.

## Findings

### Blocking

None.

### Non-blocking

1. **Change-package prose is still template** (`brief.md` outcome/scope empty, `requirements.md` unchecked placeholders, `test-plan.md` empty table). `change-spec.yaml` and tests carry the contract. Does not contradict product behavior.
2. **`if executor is None` is a weak type guard** for `CodexLandingExecutor`; a non-callable object would fail later. Tests inject `RecordingExecutor`. Acceptable for this seam.
3. **`LandingLiveBindingV1.__post_init__` does not pin SHA/tree**; fail-closed for `80d6215` is only in `compose_landing_live`. That matches the test and keeps construction of a drifted binding possible for the closed-path assertion.

## Product-code edits

None (reviewer is read-only).
