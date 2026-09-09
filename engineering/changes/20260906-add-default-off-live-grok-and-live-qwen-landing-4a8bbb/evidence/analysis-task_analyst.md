# Analysis — task_analyst

Change: `20260906-add-default-off-live-grok-and-live-qwen-landing-4a8bbb`
Route: `4a8bbb4fa8a6` · intent=`feature` · risk=`low` · complexity=`standard` · domains=`generic`
Write owner: `general_implementer`
Analysis wave: `repo_explorer` / `task_analyst` / `architect` / `docs_researcher`
Reviews after implementation: `code_reviewer` + `test_reviewer`
Evidence kinds: `verification`, `code_review`, `test_review`
Human gates on this route: **none**
Skills loaded: `/adaptive-delivery`, `feature-workflow` (analysis only)

Product root: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-live`
Workflow root: `/home/pall/grok-projects/adaptive-grok-build-pro`
This report is the only write from this agent.

Narrow question: convert “добавь туда живой грок и живой квен, четко пропиши требования системы на уровне питона и тд под текущую конфигурацию” into a bounded, testable outcome this route **can** ship on the l5-live tree. Smallest coherent vertical. Explicit non-goals (real xAI/DashScope calls, `.env` reads, landing-repo push, `live_url`, server auto-enable). What remains human-blocked.

Read-only except this evidence report. No application-code edits. No `.env`. No push / tag / merge / deploy from this agent.

Companion fact reports (same change): `evidence/analysis-repo_explorer.md`, `evidence/analysis-docs_researcher.md`, `evidence/analysis-architect.md`. This note converts those facts into scope and AC.

---

## Ruling (one screen)

User ask: *«добавь туда живой грок и живой квен, четко пропиши требования системы на уровне питона и тд под текущую конфигурацию»*.

“Live Grok and live Qwen” for **this** route is **not** a hosted site, a real provider turn, an env-file credential load, a landing-repo write, or a default-on server. Those are either already grant-gated (pilot `--live` Codex path) or forbidden without a named grant this route does not have.

For this route, “add live Grok and live Qwen and write the current host Python/system requirements” means:

> Ship **default-off** Grok and Qwen landing executors that implement `CodexLandingExecutor`, fail closed unless a caller **injects** a non-empty API key, and are proven only with `httpx.MockTransport`. Freeze a closed `LandingHostRequirementsV1` for this host: Python `3.12.3` at `/usr/bin/python3.12` (SHA-256 `a92f0f95…96223`) and factory `httpx==0.28.1`. `live_url` stays **null**. The shipped server stays unavailable. Tests never open a real socket, never read `.env`, and never push the landing clone.

After this slice, the factory is **live-Grok/Qwen-capable, default-off**. It is not operational, hosted, or credentialed.

| Layer | Meaning |
| --- | --- |
| Product tree | l5-live worktree, local HEAD `22c70c3` (ahead 1 of `origin/main` `fd51dcf`). Parent of this slice is the injected live-path composer already on that commit. |
| Already on this HEAD | `compose_landing_live` + `RecordingExecutor` auto-seals 20-member artifact; `server.build_app()` still `UnavailableLandingProvider`; `live_url` hardcoded `None`. |
| Actual gap | No shipped Grok/Qwen `CodexLandingExecutor`; no closed host-requirements record; tests have no MockTransport coverage for HTTPS chat-completions. |
| “Live” | Injected HTTP adapter returning draft JSON as executor stdout. Not a URL, push, or host. |
| Tests | `httpx.MockTransport` only. Injected literal keys (`test-grok` / `test-qwen`). No real API, no `.env`, no Dimkox write. |
| Frozen | `live_url` JSON-null; OpenAPI Result `live_url: {type: null}`; migrations `001`–`018`; published `v2.0.14` ZIP bytes; `TARGET_BASE_SHA` `6990103…`. |
| Do not pick | Real xAI/DashScope, dotenv, server auto-wire, landing push, `80d6215` retarget, M8, publisher transport. |

Route `human_gates: []` means the implementer may proceed after this bounded design. It does **not** authorize merge, model use, GitHub write, hosting, or human approval keys.

Uncommitted WIP already exists on the l5-live worktree (`landing_live_executors.py`, `test_landing_live_executors.py`, `compose_landing_live_grok`/`qwen`, README host table, `.env.example` placeholders, one `architecture/system.yaml` path). **WIP is not authority.** Reuse only if the AC below hold; do not treat dirty files as done.

---

## Verified facts (l5-live product, 2026-09-06)

| Item | Verified value | Source |
| --- | --- | --- |
| Worktree branch | `feat/factory-live-auto-landing` ahead 1 of `origin/main` | git |
| Local HEAD | `22c70c3` `feat(factory): auto-assemble L5 landing on injected live path` | git |
| Ancestor | `fd51dcfed6b33f4a8707c0db602328146df17cc9` (`#27`, VERSION `2.0.15`) | git |
| Host Python | `/usr/bin/python3.12` reports `Python 3.12.3` | `python3.12 --version` |
| Host Python SHA-256 | `a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223` | `sha256sum /usr/bin/python3.12`; same pin in `engineering/runbooks/design-partner-pilot-v2.0.15.md` |
| Toolchain built pin | Python `built: 3.12.3`, minimum `3.10`, fallback `3.12` | `.grok-stack/config/toolchain.json` |
| Factory Python | `requires-python = ">=3.11"` | `factory/pyproject.toml` |
| Factory httpx | `httpx==0.28.1` (lock + host import `httpx.__version__ == "0.28.1"`) | `factory/pyproject.toml`, `factory/uv.lock`, `/usr/bin/python3.12 -c` |
| Codex seam | `CodexLandingExecutor` protocol: `run(CodexExecutionRequest) -> CodexExecutionResult` | `landing_normalizer.py` |
| Default profile | `unavailable_codex_landing_profile()` `available=False` | same |
| Available profile | still Codex-CLI shaped: `cli_version == "0.153.4"` + absolute executable + SHA | `CodexLandingProfile.from_facts` |
| Live composer | `compose_landing_live` requires enabled binding + available profile + executor | `landing_runtime.py` |
| Server default | `UnavailableLandingProvider`; comment: live composition constructor-injected only | `server.py` |
| Result contract | `result_view()["live_url"]` is always `None`; OpenAPI `live_url: {type: null}` | `landing_service.py`, `landing-dogfood.v1.json` |
| Publisher | `UnavailableLandingPublisher.publish` always raises | `delivery/` |
| httpx today | factory CLI uses `HTTPTransport(uds=...)` only; landing dogfood boundary **forbids** `httpx` in listed `landing_*.py` **except** a new file not on that list | `cli.py`, `FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY` |
| Dogfood node | `NODE-FACTORY-LANDING-DOGFOOD` `runtime.network: none` | `architecture/system.yaml` |
| Existing live tests | `factory/tests/test_landing_live.py` uses `RecordingExecutor`, no HTTP | tests |
| This route | `4a8bbb4fa8a6`, `write_agent=general_implementer`, evidence `verification+code_review+test_review`, `human_gates=[]` | `route.json` / `active-route.json` |

Host observation for the closed requirements record (this machine, not a CI guarantee):

| Pin | Value |
| --- | --- |
| Python executable | `/usr/bin/python3.12` |
| Python version prefix | `3.12.3` |
| Python SHA-256 | `a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223` |
| Factory `requires-python` | `>=3.11` |
| Factory / host `httpx` | `0.28.1` |

---

## What “live Grok / live Qwen” is not (this route)

1. **Not a real API call.** Tests inject `httpx.MockTransport`. No DNS, TLS, or socket to `api.x.ai` or DashScope. No pytest-httpx live mode. No recorded production responses.
2. **Not a `.env` read.** Do not open `.env`, credential stores, or host key files. Constructor takes an injected `api_key`. Optional `api_key_from_environ(name, mapping)` may read a **passed mapping** (tests pass `{}` / `{NAME: "secret"}`); it must not be called from `server.build_app()` or module import.
3. **Not landing-repo mutation / push.** Workspace remains a disposable exact-SHA clone; source clone stays read-only; no `git push`, no `gh`, no Dimkox write.
4. **Not a non-null `live_url`.** Publisher stays unavailable. OpenAPI Result stays `live_url: {type: null}`.
5. **Not default-on.** `server.build_app()` must not import or construct Grok/Qwen executors, must not read `FACTORY_LANDING_*_API_KEY`, and must still return `provider_unavailable` without injection.
6. **Not a Codex CLI subprocess.** Grok/Qwen adapters implement `CodexLandingExecutor.run` over HTTPS chat-completions. They ignore argv. Do not spawn `codex` or the Grok CLI.
7. **Not a `CodexLandingProfile` redesign.** Available profiles remain CLI-shaped (dummy executable + SHA for `_profile_is_current`). HTTP identity lives on the executor + closed host-requirements record.
8. **Not M8, publisher, cPanel, PR #12, or `80d6215` retarget.**
9. **Not a VERSION / ZIP / tag bump.** Identity remains 2.0.15 source; published `v2.0.14` bytes stay immutable.
10. **Not an architecture claim that the dogfood node has live network.** Default runtime stays `network: none`. Live HTTPS is an injected capability, proven mocked.

If a later route holds an exact live-provider grant plus a landing-profile refresh plus a hosting grant, that is a **new** change. It is not this PR.

---

## Outcome (observable, this route)

An operator or test, working from this l5-live checkout, can inject:

- enabled `LandingLiveBindingV1` (existing `implemented_live_binding(enabled=True)`);
- an available `CodexLandingProfile` (existing dummy-executable fixture);
- `grok_landing_executor(api_key=..., transport=MockTransport)` **or** `qwen_landing_executor(...)`;

into the existing `compose_landing_live` (or a thin named wrapper that only builds that executor and delegates). One authenticated `text/plain` submit then produces:

- job `state == "artifact_ready"`;
- sealed ZIP + sidecar whose members are exactly `DEPLOY_MEMBERS` (20);
- `result_view()["live_url"] is None`;
- exactly one mocked HTTPS `POST .../chat/completions` with the frozen model id;
- zero real sockets, zero `.env` reads, zero mutation of the fixture source clone.

Without an injected non-empty API key, executor construction raises `LandingProviderError("credential_unavailable")` and no HTTP client is used.

Without that injection, `server.build_app()` stays `provider_unavailable` and never constructs these executors.

Observable user result: **live Grok and live Qwen exist as default-off landing executors; current host Python/httpx pins are written as a closed record; the site is not live.**

---

## Smallest coherent vertical

One library slice on the current l5-live HEAD, not a new service, not PostgreSQL `019`, not a publisher, not a profile schema change.

1. **Characterization first (keep green):** existing `test_landing_live.py`, `test_landing_normalizer.py`, `test_landing_api.py` stay green. Default server path unchanged.
2. **Closed host requirements** (`LandingHostRequirementsV1` / `CURRENT_LANDING_HOST_REQUIREMENTS`) with **exact** current pins (table above) plus frozen Grok/Qwen HTTPS base URLs, model ids, and env **names** (not values).
3. **Two factories** `grok_landing_executor` / `qwen_landing_executor` returning an object that structurally implements `CodexLandingExecutor`. Constructor **requires** non-empty `api_key`. Optional `transport: httpx.BaseTransport | None`. HTTPS base only (`https://`).
4. **Chat Completions adapter:** `POST {base}/chat/completions`, `Authorization: Bearer <injected>`, `model` from host requirements, assistant `message.content` becomes `CodexExecutionResult.stdout` (UTF-8). Fail closed on HTTP error, non-200, missing/empty content, oversize stdout.
5. **Tests in `factory/tests/test_landing_live_executors.py`:** MockTransport only; missing/blank key; host-requirements constants; Grok and Qwen text submit through live composer → `artifact_ready` + 20 members + `live_url is None`.
6. **Keep `FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY`:** do **not** import `httpx` in `landing_runtime.py`. If named composers exist, they lazy-import the executor module. Prefer putting HTTP in `landing_live_executors.py` only.
7. **Docs:** one factory README table of the closed pins; `.env.example` may list **placeholder** env names. Server must not load them.
8. **Do not** change OpenAPI, publisher, migrations, `TARGET_BASE_SHA`, renderer writes, `VERSION`, packages, `pilot/`, `trust-ci/`.

Thin `compose_landing_live_grok` / `compose_landing_live_qwen` wrappers are allowed if they only inject the executor and still require `api_key` + optional `transport`. They are not required if tests call `compose_landing_live(..., executor=grok_landing_executor(...))` directly.

---

## Closed host requirements (product text the implementer must freeze)

These are **this host’s** pins, not a promise that CI is the same binary. Tests assert the **record** equals these strings and that `factory/pyproject.toml` `httpx==0.28.1` matches `httpx_version`. Tests must **not** fail CI by hashing `/usr/bin/python3.12` at runtime.

| Field | Frozen value |
| --- | --- |
| `python_executable` | `/usr/bin/python3.12` |
| `python_version_prefix` | `3.12.3` |
| `python_sha256` | `a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223` |
| `factory_requires_python` | `>=3.11` |
| `httpx_version` | `0.28.1` |
| `grok_base_url` | `https://api.x.ai/v1` |
| `grok_model_id` | `grok-4` |
| `grok_api_key_env` | `FACTORY_LANDING_GROK_API_KEY` |
| `qwen_base_url` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `qwen_model_id` | `qwen-plus` |
| `qwen_api_key_env` | `FACTORY_LANDING_QWEN_API_KEY` |

Ruling on model ids: freeze `grok-4` and `qwen-plus` as the closed record for this slice. That is a **documented default**, not a claim that a live turn was executed. Changing models later is a new change.

---

## Out of scope / explicit non-goals

- Real HTTPS to xAI or DashScope; any test without `MockTransport`.
- Reading `.env`, `os.environ` inside executor constructors, token files, or host auth stores.
- `server.build_app()` auto-enable, dotenv load, or default transport that dials the network.
- `gh` push, draft PR, merge, tag, GitHub Release, landing-repo commit.
- cPanel, LiteSpeed, DNS, TLS, indexing, any non-null `live_url`.
- Retarget `6990103` → `80d6215`; renderer/inventory refresh.
- Redesign `CodexLandingProfile` / drop dummy Codex executable.
- PDF extraction, audio transcription, OCR, image bytes on the HTTP body (image/DOCX stay on the existing RecordingExecutor path).
- M8 cohort/activation, M9 production, factory migrations `019+`.
- PR #12 / #13 / #15 / #28 as parent or mixed scope.
- Pilot CLI (`pilot/`) changes.
- VERSION bump, package rebuild, root README 19→20 member rewrite.
- GitHub Actions, force-push, merge to `main`, deploy, production mutation.
- Second write agent. Security/data/release reviews are **not** selected; do not fake them.

---

## Frozen boundaries (must not change)

- `live_url` is JSON `null` only (OpenAPI + `result_view()`)
- Landing OpenAPI v1 snapshot bytes
- Migrations `001`–`018`
- Published `v2.0.14` ZIP SHA-256 `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`
- `TARGET_REPOSITORY_ID` / `TARGET_BASE_SHA` `699010380f4f90a0193a9c22090c35e6aded7d2c` / `TARGET_BASE_TREE` `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`
- Renderer writes only `index.html` and `content.css`; `index.css` is source-owned
- `DEPLOY_MEMBERS` 20-path inventory
- Default provider and publisher unavailable
- `FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY` still forbids `httpx` in the listed landing core modules
- Factory dependency pin `httpx==0.28.1` (do not bump)
- Human private keys, deployed Trust CI policy/holdout, GitHub App key, branch protection

---

## Testable acceptance criteria

Close **this** change only when all of these are true on the **same** successor tree in the l5-live worktree.

### A. Base and delivery hygiene

- [ ] **AC-A1:** Given the implementer starts work, when `git merge-base --is-ancestor 22c70c3 HEAD` (or at least `fd51dcfed6b33f4a8707c0db602328146df17cc9`) is checked, then this slice is stacked on the injected live-path composer, not on a stale 2.0.12 checkout.
- [ ] **AC-A2:** Given the successor diff vs `HEAD`/`origin/main`, when files are listed, then product edits stay under `factory/src/adaptive_factory/` (new executor module + optional thin runtime wrappers), `factory/tests/test_landing_live_executors.py`, optional `factory/README.md` host table, optional `.env.example` **placeholder names only**, this change package / evidence, and at most a short `decisions.md`/`mistakes.md` fact. Architecture YAML only if fitness ownership requires it. No `pilot/`, no `trust-ci/`, no `delivery/` publisher transport, no `VERSION`, no `packages/` ZIP, no `.github/workflows/`, no SQL `019`, no `.env`.
- [ ] **AC-A3:** Given AGENTS.md last-mile rules, when this route closes, then no merge, tag, deploy, live API write, model invocation, `.env` read, landing push, or human-key use has occurred.
- [ ] **AC-A4:** Given sibling routes (M8 accounting, PR #12, hosting), when this successor is published, then it is a **new** PR to `main` and does not mix those scopes.

### B. Default-off and fail-closed credentials

- [ ] **AC-B1:** Given `server.build_app()` with quarantine configured, when a landing submit is processed, then the job is `provider_unavailable` / `profile_unavailable`, and `server.py` does not import `landing_live_executors` or read `FACTORY_LANDING_*_API_KEY`.
- [ ] **AC-B2:** Given `grok_landing_executor` / `qwen_landing_executor`, when `api_key` is missing, empty, or whitespace, then construction raises `LandingProviderError` with `credential_unavailable` and no `httpx.Client` request is made.
- [ ] **AC-B3:** Given `api_key_from_environ(name, {})` or a mapping whose value is blank, when called, then it raises `credential_unavailable`. Tests pass an explicit mapping; they do not require a process env key to be set.
- [ ] **AC-B4:** Given executor constructors, when inspected, then they do **not** call `os.environ` or open a dotenv path unless the caller explicitly invoked `api_key_from_environ`. Importing the module does not read credentials.
- [ ] **AC-B5:** Given `compose_landing_live` with `enabled=False` or unavailable profile, when Grok/Qwen factories are not even required, then existing `live_disabled` / `profile_unavailable` behavior remains.

### C. MockTransport Grok and Qwen executors

- [ ] **AC-C1:** Given `grok_landing_executor(api_key="test-grok", transport=MockTransport)`, when `run` is called with a closed stdin `{instruction, request}`, then the mock receives `POST` whose path ends with `/chat/completions`, JSON `model == "grok-4"`, and `Authorization` starts with `Bearer `; stdout equals the mocked assistant content bytes; `exit_code == 0`.
- [ ] **AC-C2:** Given `qwen_landing_executor(api_key="test-qwen", transport=MockTransport)`, when `run` is called, then the same protocol holds with `model == "qwen-plus"` and Qwen base URL.
- [ ] **AC-C3:** Given MockTransport returning HTTP 500, raising `httpx.HTTPError`, or JSON without `choices[0].message.content`, when `run` is called, then it raises `LandingProviderError` (`executor_http` / `executor_transport` / `executor_result`) and does not return a successful `CodexExecutionResult`.
- [ ] **AC-C4:** Given every test in `test_landing_live_executors.py` that constructs an executor used for `run`, when the test runs, then a `MockTransport` (or other injected `httpx.BaseTransport`) is supplied. No test constructs the executor with `transport=None` and then calls `run`.
- [ ] **AC-C5:** Given the executor object, when type-checked structurally, then it implements `CodexLandingExecutor.run(CodexExecutionRequest) -> CodexExecutionResult`.

### D. Injected composition still auto-seals; `live_url` stays null

- [ ] **AC-D1:** Given enabled binding + available dummy Codex profile + Grok executor with MockTransport returning closed draft JSON + `sealed_target()`, when an authenticated operator submits `text/plain` once, then `created.job.state == "artifact_ready"`, `member_names == tuple(sorted(DEPLOY_MEMBERS))`, ZIP exists, and `result_view()["live_url"] is None`.
- [ ] **AC-D2:** Given the same path with the Qwen executor, when submitted, then the same artifact_ready / 20 members / `live_url is None` hold.
- [ ] **AC-D3:** Given those composition tests, when the fixture source clone is inspected, then HEAD/tree are unchanged (no extra commit, no push); generated files exist only in scratch and packager output.
- [ ] **AC-D4:** Given OpenAPI `landing-dogfood.v1.json` and migrations `001`–`018` vs `origin/main`, when the successor diff is taken, then those files are byte-identical.
- [ ] **AC-D5:** Given every terminal result from new executor tests, when `result_view()` is read, then `live_url is None`. No test assigns a URL string.

### E. Closed HostRequirements for current pins

- [ ] **AC-E1:** Given `CURRENT_LANDING_HOST_REQUIREMENTS` (or equivalent frozen dataclass), when compared to the table in this report, then every field matches exactly, including Python executable `/usr/bin/python3.12`, version prefix `3.12.3`, SHA-256 `a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223`, `factory_requires_python >=3.11`, and `httpx_version 0.28.1`.
- [ ] **AC-E2:** Given `factory/pyproject.toml`, when parsed, then `httpx==0.28.1` and `requires-python` contains `>=3.11`, matching the frozen record. Do not bump httpx.
- [ ] **AC-E3:** Given factory README (or an equivalent in-tree requirements surface next to the executors), when read, then it states those Python/system pins in a table, states default-off, states MockTransport tests, and states `live_url` remains null. It must not claim a live hosted site or a real API turn.
- [ ] **AC-E4:** Given tests, when they assert host requirements, then they compare the frozen record and pyproject pin — they do **not** require the CI runner’s `/usr/bin/python3.12` SHA to match this operator host.

### F. Architecture / httpx placement

- [ ] **AC-F1:** Given `FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY`, when `landing_runtime.py` / `landing_normalizer.py` / `landing_service.py` are grepped, then they still do not import `httpx`. HTTP lives in `landing_live_executors.py` (name may vary, but not those core files).
- [ ] **AC-F2:** Given architecture fitness, when `python3 scripts/grok_verify.py --mode pr` runs, then it PASSes. If `new_network_client` fires because `NODE-FACTORY-LANDING-DOGFOOD` is `network: none`, the architect/implementer must keep default-off honesty: do **not** declare operational always-on xAI/DashScope secrets; prefer owning the new file without claiming the dogfood node now has live network, or a separate injected-capability node. Do not expand Trust CI / delivery / pilot architecture.
- [ ] **AC-F3:** Given `.env.example`, if env **names** are added, then values are placeholders only (`replace-…`). No real key. Server still does not load them.

### G. Verification and review (this route)

- [ ] **AC-G1:** Given the final successor tree, when `python3 scripts/grok_verify.py --mode pr` runs, then it PASSes.
- [ ] **AC-G2:** Given that PASS, when `code_reviewer` and `test_reviewer` inspect the actual diff, then both reports are stored under this change package and `grok_review.py` receipts bind the **same** tree fingerprint.
- [ ] **AC-G3:** Given `required_evidence` is `verification` + `code_review` + `test_review`, when `python3 scripts/grok_status.py` runs after receipts, then evidence gaps for this route are empty. Local receipts are not merge authority.

### H. Explicit non-claims (must remain true)

- [ ] **AC-H1:** No real xAI/DashScope/Codex/ChatGPT turn in tests or default composition.
- [ ] **AC-H2:** No `.env` or credential-store read.
- [ ] **AC-H3:** No `gh` / git push to `ai-dark-factory-landing` or any GitHub PR create/merge.
- [ ] **AC-H4:** No cPanel/host transport; `UnavailableLandingPublisher` still the only shipped publisher; `live_url` frozen null.
- [ ] **AC-H5:** No M8 activation; no `external_action_authorized=True`.
- [ ] **AC-H6:** Published `v2.0.14` ZIP/sidecar bytes unchanged; no retag.

---

## Risk-based test plan (for implementer / test_reviewer)

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | HostRequirements frozen record equals current pins; pyproject `httpx==0.28.1` | `factory/tests/test_landing_live_executors.py` |
| P0 | Blank/missing API key → `credential_unavailable`; no HTTP | same |
| P0 | Grok MockTransport `run` returns draft JSON; model `grok-4` | same |
| P0 | Qwen MockTransport `run` returns draft JSON; model `qwen-plus` | same |
| P0 | Injected Grok composition: text submit → `artifact_ready` + 20 members + `live_url is None` | same |
| P0 | Injected Qwen composition: same | same |
| P0 | `server.build_app` still unavailable; no executor import | existing `test_landing_api.py` / `test_server.py` + grep/import assertion |
| P1 | HTTP 500 / transport error / malformed body fail closed | new executor tests |
| P1 | Existing `test_landing_live.py` RecordingExecutor path stays green | characterization |
| P2 | Constructor does not read `os.environ`; `api_key_from_environ` uses injected mapping | same |

Do not add live PostgreSQL, Docker, GitHub, or real-provider tests for this slice.

---

## Failure and edge cases

- Missing/blank API key: fail before client.
- Non-HTTPS base URL: reject at construction.
- Unknown `provider_id`: reject at construction.
- HTTP non-200 / `HTTPError`: `LandingProviderError`, no draft.
- Missing assistant content / oversize stdout: `executor_result`.
- Invalid stdin (not `{instruction, request}`): `executor_request`.
- PDF/audio on live composer: still `needs_human` before executor (existing normalizer).
- Observed SHA `80d6215` binding: still `source_binding_unimplemented` (existing runtime).
- Publisher / URL: unrepresentable.

---

## Non-functional

- **Security:** caller injects the key; it is not read from disk. Do not log Authorization headers or key material. Tests use obviously fake keys that will not trip secret-scan (`test-grok` / `test-qwen` / `secret` in a mapping). Raw source is not stored beyond existing digest/quarantine rules.
- **Reliability:** one HTTP POST per successful `run`; no retry loop; timeout from `CodexExecutionRequest.timeout_seconds`.
- **Performance:** one mocked request on success; no new workers.
- **Observability:** existing job `state` / `reason_code` / digests; `live_url` remains the honest null signal. Host requirements are a readable closed record, not a runtime probe of CI.

---

## What remains human-blocked after this slice

| Blocker | Why this route cannot clear it |
| --- | --- |
| Real Grok / Qwen API turn | No grant; tests must stay MockTransport; this agent must not read `.env` |
| Landing-repo push / draft PR | Pilot `--live` + exact `grok_approve.py` resource grants; not this composition |
| cPanel / HTTPS site / indexing | Publisher has no transport; `live_url` frozen null |
| Server default-on live providers | Would require a named grant plus secret provisioning outside git |
| M8 activation / auto-merge | Zero factual cohort; evaluation forbids external action |
| Merge of this PR | App-owned `adaptive-trust-ci/verified@06ecf1c875bc` + human merge |
| Landing profile refresh to `80d6215` | Separate reviewed renderer/inventory change |

Honest close statement: **default-off Grok and Qwen landing executors exist; current host Python 3.12.3 / httpx 0.28.1 pins are written; tests never leave the process; the site is not live.**

---

## Conflicts and rulings (do not stop)

1. **Uncommitted WIP already implements much of this.** Ruling: treat it as a draft. Keep it only if AC-B/C/D/E/F hold, including fail-closed HTTP errors, no `transport=None`+`run` in tests, no `httpx` import in landing core, and architecture fitness green. Missing P1 HTTP-error tests are in scope for the implementer, not optional.
2. **`CodexLandingProfile` still requires a dummy Codex executable.** Ruling: keep. This slice adds executors, not a second profile type. HTTP adapters ignore argv.
3. **`NODE-FACTORY-LANDING-DOGFOOD` is `network: none`.** Ruling: do not pretend the dogfood node is now a live HTTPS service. Architect owns the ownership/edge decision; implementer must not add secrets or always-on edges. Putting `httpx` only in a file **outside** `FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY` source_prefixes is the intended placement.
4. **Root README still says 19-member artifact; code has 20.** Ruling: out of scope. Factory README may add the host-requirements table only.
5. **Pilot runbook already pins `/usr/bin/python3.12` SHA.** Ruling: reuse that SHA in `LandingHostRequirementsV1`; do not edit the pilot runbook or `pilot/`.
6. **`.env.example` key names vs “cannot read `.env`”.** Ruling: placeholder names are documentation. Runtime must not load `.env`. Tests must not open it.
7. **`compose_landing_live_grok` in `landing_runtime.py` vs httpx ban.** Ruling: wrappers may lazy-import the executor module; they must not `import httpx` themselves.
8. **Image/DOCX through Grok HTTP.** Ruling: out of scope. Text/plain is the vertical. Existing RecordingExecutor tests already cover image/DOCX assembly.

---

## Implementer recipe (order)

1. Stay on l5-live `feat/factory-live-auto-landing` (HEAD `22c70c3` or its successor). Do not parent on PR #12 / stale 2.0.12.
2. Add failing `factory/tests/test_landing_live_executors.py` covering AC-B2, AC-C1/C2, AC-D1/D2, AC-E1/E2 **before** treating WIP as complete. If WIP already exists, make the missing fail-closed HTTP tests fail first if the code path is incomplete.
3. Implement `landing_live_executors.py` + closed `LandingHostRequirementsV1`. Keep HTTP out of the dogfood-boundary file list.
4. Optional thin composers that require `api_key` + `transport`.
5. README host table; `.env.example` placeholders only if names are documented.
6. Run focused:

```bash
python3 -m unittest factory.tests.test_landing_live_executors factory.tests.test_landing_live factory.tests.test_landing_normalizer factory.tests.test_landing_api
```

7. Then `python3 scripts/grok_verify.py --mode pr`. Dispatch `code_reviewer` and `test_reviewer` only after PASS.

Do not push, merge, deploy, call xAI/DashScope, or read `.env`.
