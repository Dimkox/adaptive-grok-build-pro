# Test review — factory live auto-landing

**Status:** PASS
**Scope:** `factory/tests/test_landing_live.py` vs change-spec AC-001–AC-005 / FORBID-001–003.
**Tree:** uncommitted product + new test file on `feat/factory-live-auto-landing`. grok_verify `--mode pr` was already PASS on this tree; this review did not rewrite product code.

## Verdict

Characterization in `test_landing_live.py` is adequate for the named live-composition acceptance criteria. Tests stay offline: injected `RecordingExecutor` only, local `sealed_target()` git fixture, no subprocess Codex, no writes under Dimkox/`ai-dark-factory-landing`.

## AC mapping

| AC | Criterion | Coverage | Result |
| --- | --- | --- | --- |
| AC-001 | Unavailable default: no executor, no artifact builder, `live_url` null | `test_unavailable_composition_never_calls_executor_or_sets_live_url` — `compose_unavailable_landing`, state `provider_unavailable`, `executor.requests == []`, `_artifact_builder is None` | Covered |
| AC-002 | Injected executor + enabled binding → `artifact_ready`, 20 members, `live_url` null | `test_injected_executor_automatically_seals_complete_artifact` — one `RecordingExecutor` request, `artifact_ready`, `live_url is None`, `member_names == tuple(sorted(DEPLOY_MEMBERS))`, zip exists | Covered (`DEPLOY_MEMBERS` is 20 paths; no literal `assertEqual(20, …)` but equivalent) |
| AC-003 | Binding SHA `80d6215…` fail-closed before executor | `test_observed_landing_sha_fails_closed_before_executor` — `LandingRuntimeError("source_binding_unimplemented")`, empty `executor.requests` | Covered |
| AC-004 | PDF live intake → `needs_human` without executor | `test_pdf_stops_before_executor_on_live_composition` — `pdf_extractor_unavailable`, empty requests, `live_url` null | Covered |
| AC-005 | Disabled binding cannot compose | `test_disabled_binding_cannot_compose_live` — `live_disabled` | Covered |

## Isolation / forbidden outcomes

- **No real Codex:** `RecordingExecutor.run` records requests and returns fixture `draft()` stdout. The `codex` path in `setUp` is a local chmod-0700 byte fixture, never executed.
- **No landing-repo mutation:** `source_repository` is either a tempfile blob root (fail-closed cases) or `sealed_target()` under `tempfile.TemporaryDirectory`. No path to Dimkox or `ai-dark-factory-landing`.
- **FORBID-002:** `live_url` asserted None on unavailable, ready, and PDF paths. Ready path writes zip only under the test `artifacts/` temp dir.
- **FORBID-003:** Observed SHA `80d621545938e24c296420d7f685f2d0b2b5785e` is rejected before the executor; implemented binding SHA is taken from patched `TARGET_BASE_SHA` of the sealed fixture, not a SHA-only retarget of production `6990103`.

## Gaps (non-blocking)

1. **INV-001 / server default-off** is not asserted in this file. `server.py` still builds `UnavailableLandingProvider` without `artifact_builder` and comments that live is constructor-injected only. A dedicated server-wiring test would lock FORBID-001 (env flag / default-on executor) more tightly; current live tests cover the compose helpers, not `create_app` wiring.
2. **AC-002** does not assert `len(member_names) == 20` as a numeric constant; it ties completeness to `DEPLOY_MEMBERS`. That is the right contract if the packager list is the source of truth.
3. **AC-005** does not record executor requests (compose raises before use). Harmless.
4. **INV-002** (coordinator + packager attached) is implied by a successful seal, not inspected on the builder object.

## Recommendation

Keep the test file as the primary evidence for AC-001–AC-005. Optional follow-up: assert `len(created.job.sealed_artifact.member_names) == 20` and a server-construction check that `landing_service._artifact_builder is None`. Neither is required to pass this review.
