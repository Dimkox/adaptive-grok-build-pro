# Analysis — task_analyst

Change: `20260906-factory-live-path-automatically-assembles-the-co-c2837b`
Route: `c2837bf9d4a4` · intent=`feature` · risk=`low` · complexity=`standard` · domains=`generic`
Write owner: `general_implementer`
Analysis wave: `repo_explorer` / `task_analyst` / `architect` / `docs_researcher`
Reviews after implementation: `code_reviewer` + `test_reviewer`
Evidence kinds: `verification`, `code_review`, `test_review`
Human gates on this route: **none**
Skills loaded: `/adaptive-delivery`, `feature-workflow` (analysis only)

Narrow question: convert “делай фабрику до live и в live фабрики собирай лендос полностью автоматом” into a bounded, testable outcome this route **can** ship on `fd51dcf`. Smallest coherent vertical. Explicit non-goals (real model turn, `gh` push, cPanel, PR #12, M8 activation). What remains human-blocked.

Read-only except this evidence report. No application-code edits. No `.env`. No push / tag / merge / deploy from this agent.

Companion fact reports (same change): `evidence/analysis-repo_explorer.md`, `evidence/analysis-docs_researcher.md`. This note converts those facts into scope and AC.

---

## Ruling (one screen)

User ask: *«делай фабрику до live и в live фабрики собирай лендос полностью автоматом естесна»*.

“Factory live” for **this** route is **not** a hosted site, a real Codex turn, a landing-repo write, cPanel, or M8 activation. Those are either already grant-gated on `main` (pilot `--live` CLI) or forbidden without a named grant this route does not have.

For this route, “live factory automatically assembles the landing” means:

> Ship a **default-off live landing path** on published `origin/main` `fd51dcf` that, **when a live executor and available profile are injected**, runs **one** `submit` through **normalize → render → evaluate → seal** and yields a **complete 20-member `SiteArtifactV1`**. Tests prove that path with a **fake executor**. `live_url` stays **null**. The landing clone stays **read-only**. M8 stays **inactive**.

After this slice, the factory is **live-capable, default-off**. It is not operational, hosted, or autonomous.

| Layer | Meaning |
| --- | --- |
| Product base | `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9` (`VERSION` `2.0.15`). Do not implement on this 2.0.12 checkout. |
| Already on main | L5 intake + unavailable default (PR #24); Codex seam + SQLite + coordinator-to-packager builder (PR #26); disabled pilot CLI (PR #27). |
| Actual gap | Default `server.build_app()` wires `UnavailableLandingProvider` and **`artifact_builder=None`**. Pieces exist; **one injected live composition does not**. |
| Automatic assembly | Local ZIP + sidecar + 20 `DEPLOY_MEMBERS`. Not a URL, push, or host. |
| Tests | Fake `CodexLandingExecutor` (`RecordingExecutor` pattern). No real Codex binary, no network, no Dimkox working-tree write. |
| Frozen | `live_url` JSON-null; OpenAPI Result schema `live_url: {type: null}`; migrations `001`–`018`; published `v2.0.14` ZIP bytes; `TARGET_BASE_SHA` `6990103…`. |
| Do not pick | Real model turn, `gh` push, cPanel, PR #12, M8 activation, landing-profile refresh to `80d6215`. |

Route `human_gates: []` means the implementer may proceed after this bounded design. It does **not** authorize merge, model use, GitHub write, hosting, or human approval keys.

---

## Verified facts (against origin/main, not this 2.0.12 checkout)

Checked 2026-09-06 from git objects on `origin/main`. Do not treat the dirty local tree as product.

| Item | Verified value | Source |
| --- | --- | --- |
| `origin/main` | `fd51dcfed6b33f4a8707c0db602328146df17cc9` — `feat(pilot): bounded Codex issue-to-draft-PR capability (2.0.15 candidate) (#27)` | git |
| `origin/main` `VERSION` | `2.0.15` | `origin/main:VERSION` |
| Local HEAD | `7c61e3b` on `fix/path-aware-shell-policy-circuit-breaker`, VERSION `2.0.12` | git status |
| L5 dogfood | PR #24 / `v2.0.14` merge `1751b585` | CHANGELOG / PROJECT_STATE |
| Stage 3/5 runtime | PR #26 merge `6f3b6ed` — Codex seam, SQLite, `CoordinatedLandingArtifactBuilder` | git log |
| Pilot | PR #27 on `fd51dcf` — default-off `--live` CLI; `live_model_invoked: false` | PROJECT_STATE / `pilot/` |
| Default server landing | `UnavailableLandingProvider` + `artifact_builder=None` | `factory/src/adaptive_factory/server.py` |
| Service pipeline | `submit` → `_process`: normalize; if no spec → terminal; if no builder → `needs_human` / `artifact_builder_unavailable`; else `generating` → `build` → `artifact_ready` | `landing_service.py` |
| `live_url` | Hardcoded `None` in `result_view()`; OpenAPI `live_url: {type: null}` | `landing_service.py`, `landing-dogfood.v1.json` |
| Codex seam | `CodexLandingNormalizer`; docstring “repository ships no live executor”; default `unavailable_codex_landing_profile()` `available=False` | `landing_normalizer.py` |
| Fake executor tests | `RecordingExecutor` in `test_landing_normalizer.py` only — **does not** call coordinator/packager | tests |
| Builder tests | `test_landing_runtime.py` uses `BoundProvider` fixture, **not** `CodexLandingNormalizer` | tests |
| Source pin | `github.com/Dimkox/ai-dark-factory-landing@699010380f4f90a0193a9c22090c35e6aded7d2c` / tree `f7dbbd80…` | `landing_renderer.py` |
| Writes | Only `index.html` and `content.css`; `index.css` protected | renderer / 65b201 |
| Artifact inventory | `DEPLOY_MEMBERS` is **20** paths (README current-state still says 19; code/repair packages win) | `landing_artifact.py` |
| Publisher | `delivery/src/adaptive_delivery/landing_publisher.py` `UnavailableLandingPublisher.publish` always raises | delivery |
| PDF/audio | `needs_human` before blob/executor | `landing_normalizer.py` |
| Observed landing drift | `80d6215` blocks **pilot** live model; this factory slice does not retarget SHA | PROJECT_STATE / START_HERE |
| M8 | Evaluation delivered; factual cohort 0; activation absent | ROADMAP / prior D5 analysis |
| PR #12 | OPEN, unique lazy CLI imports; **do not pick** | PROJECT_STATE |
| Route | `c2837bf9d4a4`, `write_agent=general_implementer`, `required_evidence=verification+code_review+test_review`, `human_gates=[]` | `route.json` / `active-route.json` |

The state machine already supports automatic assembly. The missing product is **composition of the live seam with the builder**, plus a test that one `submit` with a fake executor produces the complete sealed site.

---

## What “factory live / auto-assemble landing” is not (this route)

1. **Not a real model turn.** `CodexLandingNormalizer` is a seam. Tests inject a fake executor. Spawning Codex CLI, ChatGPT auth, or `gpt-6-astra` is out of scope (that is the separate `pilot/` `--live prepare` path, still blocked on `80d6215`).
2. **Not `gh` push / draft PR.** Pilot `publish-branch` / `publish-proposal` stay grant-gated and untouched. Factory live path does not call GitHub.
3. **Not cPanel / hosting / indexing.** Publisher remains unavailable. `live_url` cannot become a string.
4. **Not a landing-repo write.** Workspace is a disposable exact-SHA clone; source clone stays read-only; renderer writes only inside scratch (`index.html` / `content.css`).
5. **Not M8 activation.** Do not touch `autonomy.py`, cohort accounting, or `external_action_authorized`.
6. **Not PR #12.** Lazy Trust CI CLI imports are a different unique successor.
7. **Not retargeting `6990103` → `80d6215`.** SHA/tree pin stays. Refresh is a separately authorized landing-profile change.
8. **Not default-on.** `server.build_app()` without an injected live executor/profile must still return `provider_unavailable` and must not construct a real executor.
9. **Not automatic replay of interrupted work.** Existing SQLite recovery to `needs_human` stays.
10. **Not a VERSION / ZIP / tag bump.** Identity remains 2.0.15 source on `fd51dcf`; published `v2.0.14` bytes stay immutable.

If a later route holds an exact live-Codex grant plus a landing-profile refresh plus a hosting grant, that is a **new** change. It is not this PR.

---

## Outcome (observable, this route)

An operator or test, working from a reviewed `origin/main`-based checkout, can inject an **available** `CodexLandingProfile` plus a `CodexLandingExecutor` plus the existing coordinator/packager builder into the landing application service. One authenticated `text/plain` (and equivalently image / safe DOCX) submit then **automatically** produces:

- job `state == "artifact_ready"`;
- a sealed ZIP + sidecar whose members are exactly `DEPLOY_MEMBERS` (20);
- bound `SiteArtifactV1` (source SHA/tree, input/spec/profile digests, final attempt + evaluation);
- `result_view()["live_url"] is None`;
- exactly one fake-executor `run` for those media kinds;
- zero mutation of the fixture source clone (no extra commits, no push).

Without that injection, the same process stays `provider_unavailable` / `profile_unavailable` and never reads the blob or calls an executor.

Observable user result: **in the live factory path, the лендос is assembled fully automatically as a complete local site artifact.** Hosting, model, and GitHub remain off.

---

## Smallest coherent vertical

One library composition on **`fd51dcf`**, not a new service, not PostgreSQL `019`, not a publisher.

1. **Leave the stale 2.0.12 checkout.** New branch / worktree from `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9`. Recreate this change package there. Do not parent on PR #12 / #13 / #15 / #28 or `fix/path-aware-shell-policy-circuit-breaker`.
2. **Characterization first (keep green):**
   - default `UnavailableLandingProvider` + no builder → `provider_unavailable`, zero blob/executor;
   - existing `BoundProvider` + `CoordinatedLandingArtifactBuilder` → `artifact_ready` (`test_landing_runtime.py`);
   - `CodexLandingNormalizer` + `RecordingExecutor` still normalizes text/image/docx only (`test_landing_normalizer.py`);
   - `result_view()["live_url"] is None`.
3. **Add a default-off live-path composer** (architect may name it; likely `landing_runtime.py` or a small `landing_live.py`) that wires:
   - `CodexLandingNormalizer(profile, executor)` as provider;
   - `CoordinatedLandingArtifactBuilder(coordinator, packager, output_dir)` as builder;
   - `LandingApplicationService(..., artifact_builder=builder)`.
   Default helper / `server.build_app()` remains unavailable unless those objects are **explicitly injected**.
4. **Add failing tests** that one `submit` through that composer with a **fake executor** and `sealed_target()` fixture reaches `artifact_ready` with the complete 20-member seal; negatives for default-off, missing builder, PDF/audio, invalid stdout, profile drift.
5. **Do not** add a subprocess Codex executor, env-based auto-enable that points at a real binary, OpenAPI change, `live_url` type change, or publisher transport.
6. Local `python3 scripts/grok_verify.py --mode pr`, then independent `code_reviewer` + `test_reviewer`. Open a **new** PR to `main`. Stop.

Recommended split (architect may refine names):

| Surface | Owner | Job |
| --- | --- | --- |
| Live-path composer | `factory` next to `landing_runtime.py` | Inject profile+executor+workspace+packager; refuse to build if profile `available=False` or executor missing |
| Default composition | `server.build_app` | Stay `UnavailableLandingProvider`, `artifact_builder=None` |
| Tests | `factory/tests/test_landing_live_path.py` (new) | Fake executor end-to-end + default-off + fail-closed |

Reuse existing `LandingCoordinator`, `DeterministicLandingRenderer`, `DeterministicLandingEvaluator`, `LandingArtifactPackager`, `DEPLOY_MEMBERS`. Do not reimplement them.

---

## In scope

- New isolated branch from `origin/main` `fd51dcf`.
- Default-off live landing composition: available `CodexLandingProfile` + injected `CodexLandingExecutor` + existing coordinator/packager → one `submit` runs normalize → render → evaluate → seal.
- Tests using a **fake** executor (no OS process, no network):
  - text (required), image and safe DOCX (at least one additional kind);
  - complete 20-member ZIP + sidecar + `SiteArtifactV1` bindings;
  - `live_url is None`;
  - source fixture unchanged;
  - executor called once on success;
  - default-off and missing-builder negatives;
  - PDF/audio still `needs_human` before executor;
  - invalid model JSON / profile drift fail closed **before** render/seal.
- Optional: `server.build_app(..., landing_service=)` already accepts injection; may document that the live composer is the injected object. Do not change the no-arg default.
- Focused factory tests + later `grok_verify --mode pr` and route reviews.
- Short `decisions.md` fact only if the next subtask needs the composer name / default-off ruling.
- Rollback: revert the successor commit / close the successor PR. No migration.

---

## Out of scope / explicit non-goals

- Implementing on `fix/path-aware-shell-policy-circuit-breaker` @ `7c61e3b`.
- Real Codex / ChatGPT / `gpt-6-astra` turn; reading host auth; spawning the real CLI in tests.
- `gh` push, draft PR, merge, tag, GitHub Release.
- cPanel, LiteSpeed, DNS, TLS, indexing, any non-null `live_url`.
- Writing `Dimkox/ai-dark-factory-landing` (push, commit on the operator clone, retarget to `80d6215`).
- M8 cohort/activation, M9 production, factory migrations `019+`.
- PR #12 / #13 / #15 / #28 as parent or mixed scope.
- Pilot CLI (`pilot/live.py`) changes; that `--live` flag is a different grant-gated product.
- PDF extraction, audio transcription, OCR, automatic retry, background workers.
- Changing frozen OpenAPI `landing-dogfood.v1.json`, published `v2.0.14` ZIP/sidecar, renderer write paths, `TARGET_BASE_SHA`/`TREE`.
- VERSION bump, package rebuild, README “current-state” rewrite beyond a factual live-path sentence if the architect requires it (prefer not; this is not a release).
- GitHub Actions, force-push, merge to `main`, deploy, production mutation.
- Second write agent. Security/data/release reviews are **not** selected; do not fake them.

---

## Frozen boundaries (must not change)

From L5 dogfood / Stage 3/5 / AGENTS.md; still valid on `fd51dcf`:

- `live_url` is JSON `null` only (OpenAPI + `result_view()`)
- Landing OpenAPI v1 snapshot bytes
- Migrations `001`–`018`
- Published `v2.0.14` ZIP SHA-256 `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`
- `TARGET_REPOSITORY_ID` / `TARGET_BASE_SHA` `699010380f4f90a0193a9c22090c35e6aded7d2c` / `TARGET_BASE_TREE` `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`
- Renderer writes only `index.html` and `content.css`; `index.css` is source-owned
- `DEPLOY_MEMBERS` 20-path inventory
- Default provider and publisher unavailable
- M8 `separate_activation_required=True`, `external_action_authorized=False`
- Human private keys, deployed Trust CI policy/holdout, GitHub App key, branch protection

---

## Testable acceptance criteria

Close **this** change only when all of these are true on the **same** successor tree, branched from `fd51dcf`, not from `7c61e3b`.

### A. Base and delivery hygiene

- [ ] **AC-A1:** Given the implementer starts work, when `git merge-base --is-ancestor fd51dcfed6b33f4a8707c0db602328146df17cc9 HEAD` is checked, then the successor contains `fd51dcf` as ancestor and is **not** `fix/path-aware-shell-policy-circuit-breaker`.
- [ ] **AC-A2:** Given the successor diff vs `origin/main`, when files are listed, then product edits stay under `factory/src/adaptive_factory/` (composer / optional server injection docs in comments only), `factory/tests/` (new live-path tests), this change package / evidence, and at most a short `decisions.md`/`mistakes.md` fact. No `pilot/`, no `trust-ci/`, no `delivery/` publisher transport, no `VERSION`, no `packages/` ZIP, no `.github/workflows/`, no SQL `019`.
- [ ] **AC-A3:** Given AGENTS.md last-mile rules, when this route closes, then no merge, tag, deploy, live API write, model invocation, or human-key use has occurred.
- [ ] **AC-A4:** Given sibling routes for PR #12 / M8 accounting / offline L5-only, when this successor is published, then it is a **new** PR to `main` and does not mix those scopes.

### B. Default-off (factory is not live unless injected)

- [ ] **AC-B1:** Given `server.build_app()` with quarantine configured and **no** injected live executor/profile/builder, when a landing submit is processed, then the job is `provider_unavailable` / `profile_unavailable`, the blob is not read for normalization, and no `CodexLandingExecutor.run` occurs.
- [ ] **AC-B2:** Given `unavailable_codex_landing_profile()` even if a fake executor is present, when `normalize` runs, then state is `provider_unavailable` / `profile_unavailable` and `executor.requests == []`.
- [ ] **AC-B3:** Given an available profile and fake executor **without** an artifact builder, when `LandingApplicationService.submit` succeeds at normalize, then the job is `needs_human` / `artifact_builder_unavailable` and no ZIP is written.
- [ ] **AC-B4:** Given the live-path composer, when constructed with `available=False` or a missing executor, then it refuses to represent a live path (raises or returns the unavailable composition); it must not silently fall back to a fixture provider.

### C. Injected live path automatically assembles the complete site

- [ ] **AC-C1:** Given the live composer with an available fixture profile, fake executor returning closed draft JSON, `sealed_target()` clone, and `CoordinatedLandingArtifactBuilder`, when an authenticated operator submits `text/plain` once, then `created.job.state == "artifact_ready"` with no extra operator step between submit and seal.
- [ ] **AC-C2:** Given that ready job, when the sealed artifact is inspected, then `member_names == tuple(sorted(DEPLOY_MEMBERS))` (20 members including `index.html`, `content.css`, protected `index.css`), ZIP and sidecar exist as mode-private files, and `SiteArtifactV1` binds `source_sha`/`source_tree` to the patched fixture identity, `input_digest`, `spec_digest`, and `profile_digest`.
- [ ] **AC-C3:** Given the same run, when coordinator output is inspected, then `run.disposition == "candidate_ready"`, there is at least one attempt and one evaluation, attempt count is in `1..3`, and the writer id is not the evaluator id.
- [ ] **AC-C4:** Given image and/or safe DOCX fixtures already used by `test_landing_normalizer.py`, when submitted through the same live composer, then they also reach `artifact_ready` with one executor call each (image bytes on the request for image; extracted text in stdin for DOCX).
- [ ] **AC-C5:** Given a successful live-path submit, when the fake executor is inspected, then `run` was called **exactly once** and argv does not contain the raw source payload; no `subprocess` / real Codex binary is launched.
- [ ] **AC-C6:** Given the fixture source clone after a successful run, when `git status` / HEAD / tree are checked, then the source identity is unchanged (no extra commit, no pushed ref); generated files exist only in workspace scratch and the packager output directory.

### D. `live_url`, publication, and fail-closed edges

- [ ] **AC-D1:** Given every terminal result from default and live-path tests, when `result_view()` / JSON Result is read, then `live_url is None`. No test assigns a URL string.
- [ ] **AC-D2:** Given PDF and audio fixtures, when submitted on the live composer, then state is `needs_human` with `pdf_extractor_unavailable` / `audio_transcriber_unavailable`, `executor.requests == []`, and no ZIP.
- [ ] **AC-D3:** Given invalid model stdout (duplicate JSON keys / missing draft fields), when submitted on the live composer, then state is `needs_human` / `invalid_model_output` (or the existing normalizer terminal), and the builder is **not** invoked.
- [ ] **AC-D4:** Given executable bytes drifted from `executable_sha256`, when submitted, then `provider_unavailable` / `profile_drift` before blob read and before render.
- [ ] **AC-D5:** Given OpenAPI `landing-dogfood.v1.json` and migrations `001`–`018` vs `origin/main`, when the successor diff is taken, then those files are byte-identical.

### E. Verification and review (this route)

- [ ] **AC-E1:** Given the final successor tree, when `python3 scripts/grok_verify.py --mode pr` runs, then it PASSes.
- [ ] **AC-E2:** Given that PASS, when `code_reviewer` and `test_reviewer` inspect the actual diff, then both reports are stored under this change package and `grok_review.py` receipts bind the **same** tree fingerprint.
- [ ] **AC-E3:** Given `required_evidence` is `verification` + `code_review` + `test_review`, when `python3 scripts/grok_status.py` runs after receipts, then evidence gaps for this route are empty. Local receipts are not merge authority.

### F. Explicit non-claims (must remain true)

- [ ] **AC-F1:** No real model turn, ChatGPT auth read, or Codex CLI subprocess in tests or default composition.
- [ ] **AC-F2:** No `gh` / git push to `ai-dark-factory-landing` or any GitHub PR create/merge.
- [ ] **AC-F3:** No cPanel/host transport; `UnavailableLandingPublisher` still the only shipped publisher.
- [ ] **AC-F4:** No M8 activation, no `external_action_authorized=True`, no factual-cohort fabrication.
- [ ] **AC-F5:** No PR #12 CLI import relocation in this diff.
- [ ] **AC-F6:** Published `v2.0.14` ZIP/sidecar bytes unchanged; no retag.

---

## Risk-based test plan (for implementer / test_reviewer)

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Default `build_app` / unavailable profile: `provider_unavailable`, zero executor | new live-path test + existing API tests |
| P0 | Injected fake executor + builder: text `submit` → `artifact_ready` + 20 members + `live_url is None` | `factory/tests/test_landing_live_path.py` |
| P0 | Source fixture HEAD/tree unchanged | same |
| P0 | Missing builder after successful normalize → `artifact_builder_unavailable` | same |
| P0 | PDF/audio `needs_human` before executor | same / existing normalizer tests |
| P1 | Image and/or DOCX through the **same** composer | same |
| P1 | Invalid stdout / profile drift fail closed before seal | same |
| P1 | Existing `test_landing_runtime.py` BoundProvider path stays green | characterization |
| P2 | SQLite replay of a live-path `artifact_ready` row does not re-call executor | optional; reuse runtime restart test pattern |

Do not add live PostgreSQL, Docker, or GitHub tests for this slice.

---

## Failure and edge cases the live path must keep

- Unavailable / drifted profile: no blob, no executor, no ZIP.
- PDF/audio: `needs_human` before executor.
- Malformed draft JSON: `needs_human`, builder not called.
- SHA/tree other than the (test-patched) target: `source_identity` 409.
- Fourth coordinator attempt: impossible (`MAX_LANDING_ATTEMPTS = 3`).
- Publisher / URL: unrepresentable.
- Restart of in-flight generating/evaluating: existing `needs_human` recovery, no automatic replay.

---

## Non-functional

- **Security:** caller cannot select executable, model, repository, SHA, output path, credential, or transport. Fake executor confers no network authority. Raw source is not stored in durable evidence beyond existing digest/quarantine rules.
- **Reliability:** one-shot `_process`; no hidden retry; WAL/FULL SQLite behavior unchanged if used.
- **Performance:** one executor call on success; ≤3 render/eval attempts; no new workers.
- **Observability:** existing job `state` / `reason_code` / digests; `live_url` remains the honest null signal.

---

## What remains human-blocked after this slice

| Blocker | Why this route cannot clear it |
| --- | --- |
| Real Codex / model attempt | No grant; landing profile stale vs observed `80d6215`; tests must stay fake |
| Landing-repo push / draft PR | Pilot `--live` + exact `grok_approve.py` resource grants; not this composition |
| cPanel / HTTPS / indexing | Publisher has no transport; `live_url` frozen null |
| M8 activation / auto-merge | Zero factual cohort; evaluation forbids external action |
| Merge of this PR | App-owned `adaptive-trust-ci/verified@06ecf1c875bc` + human merge |
| PR #12 successor | Separate unique CLI work |

Honest close statement: **live path exists and is default-off; automatic local assembly is proven with a fake executor; the site is not live.**

---

## Conflicts and rulings (do not stop)

1. **Root README still says 19-member artifact; code has 20.** Ruling: AC uses `DEPLOY_MEMBERS` (20). Do not “fix” README as this change unless a one-line current-state correction is required to keep the stack graph honest; prefer not to expand into docs-sync (PR #28).
2. **CHANGELOG/START_HERE still call 2.0.15 unreleased while this checkout’s `origin/main` already is the #27 candidate.** Ruling: do not retag or rebuild ZIP. Work from `fd51dcf` as product source.
3. **“Live” in docs also means pilot `--live`.** Ruling: this route’s “live factory” is the **injected factory landing composer**, not `pilot/live.py`. Do not change the pilot CLI.
4. **Job state `evaluating` is in the machine but `_process` jumps `generating` → `artifact_ready`.** Ruling: AC requires coordinator evaluation evidence on the sealed result, not a visible `evaluating` job row. Do not add a worker just to emit that state.
5. **Sibling change `1d68a8` is “offline L5 complete / live later”.** Ruling: this route **is** that “live later” for **assembly only**. Do not duplicate offline-gate work; do not wait on that package.

---

## Implementer recipe (order)

1. Worktree / branch from `fd51dcf`. Copy this change package.
2. Add `factory/tests/test_landing_live_path.py` that **fails** because no composer wires normalizer+builder (or the composer does not exist).
3. Implement the smallest composer + keep `server.build_app` default-off.
4. Run focused `python3 -m unittest factory.tests.test_landing_live_path factory.tests.test_landing_normalizer factory.tests.test_landing_runtime factory.tests.test_landing_api`.
5. `python3 scripts/grok_verify.py --mode pr`.
6. Independent reviews; fingerprint-bound receipts.
7. Open PR to `main`. Stop. Do not merge, push landing, host, or activate M8.

---

## Rollback

Revert the successor commit or close the successor PR. No data migration. Default composition on `fd51dcf` already fails closed (`provider_unavailable`). Residual risk if the composer were default-on: unintended executor construction — mitigated by AC-B1/B4 requiring explicit injection.
