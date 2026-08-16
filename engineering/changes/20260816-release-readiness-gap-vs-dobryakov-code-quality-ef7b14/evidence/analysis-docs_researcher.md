# Docs research — quality / verify / release vs Dobryakov

Route: `ef7b14ec854d`. Change: `20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14`.
Question: what README, CHANGELOG, ADRs, quality-profile JSON, `AGENTS.md`, and prior change packages already promise about code-quality / verify / release, and which Dobryakov categories are already claimed as covered by in-house equivalents.

Sources read (no APIs invented; `.env` not read; no push/merge/deploy):

- `README.md`, `CHANGELOG.md` §§2.0.4–2.0.5, `QUICKSTART.md`, `AGENTS.md`, `Makefile`, `VERSION`
- `.grok-stack/config/quality-profiles/*.json`, `toolchain.json`, `policy.json`, `routing.json`
- `engineering/decisions.md`, `engineering/mistakes.md`, `engineering/adr/` (empty), `engineering/runbooks/publish-v2.0.4.md`, `publish-v2.0.5.md`
- `.grok/skills/{adaptive-delivery,release-readiness,verification-evidence,security-sensitive-change}/SKILL.md`
- `.grok/hooks/README.md`, `.github/workflows/adaptive-grok.yml`
- This change package (still a stub) and prior packages `2eacdf`, `aea9d4`, `99b743`, `bb6ab3`, `ad4090`, `cd8a96`
- Dobryakov PDF (external, 31 pp., Aug 2026): 57 tools / 12 categories
- Implementation cross-check only for check **names** already listed in profiles / CHANGELOG: `.grok-stack/adaptive_grok/verification.py`, `doctor.py`, `scripts/grok_verify.py`, `scripts/grok_doctor.py`

`engineering/contracts/{openapi,asyncapi,schemas}/` have no product APIs. `engineering/adr/` has no files.

No repository document names Dobryakov, SonarQube, Semgrep, Bandit, Dependabot, Trivy, gitleaks, Codecov, Snyk, or Sentry. Mappings below are analyst equivalences against what the tree **already claims**, not product claims that those vendors are covered.

---

## 1. Claimed quality contour vs what the docs admit is missing

### 1.1 What the stack advertises as the quality contour

**Loop (README, `adaptive-delivery`, `release-readiness`, CHANGELOG 2.0.4):**

```
route → change → verify → independent reviews → ready
  → python3 scripts/grok_deploy.py (prepare-only)
  → humans run printed tag / push / GitHub Release
```

Local aliases: `make doctor` / `make verify`. Modes on `grok_verify.py`: `fast` | `pr` | `release` (default `pr`). Receipts are fingerprint-bound; any later tree write stale them (`AGENTS.md`, `verification-evidence`, `decisions.md` 2026-08-14).

**Quality profiles** (machine-readable; this route selects only `base`):

| Profile | Required checks | Optional checks |
| --- | --- | --- |
| `base` | `git-diff-check`, `secret-scan` | `contract-structure`, `sql-safety` |
| `ai` | `secret-scan` | — |
| `infra` | `secret-scan` | — |
| `contracts` / `integration` | `contract-structure` | — |
| `data` | `sql-safety` | — |
| `php` | `php-lint` | `composer-validate`, `phpunit`, `phpstan`, `phpcs`, `deptrac` |
| `bitrix` | `php-lint`, `bitrix-policy` | `phpunit`, `phpstan`, `phpcs` |
| `frontend` | — | `npm-lint`, `npm-typecheck`, `npm-test`, `npm-build` |

**What `verify()` actually always runs** (implementation; not extra profile JSON): `git-diff-check`, `secret-scan`, `contract-structure`, `sql-safety`, then `_python()`. PHP / Composer / Bitrix / npm light only when the matching profile is selected or the tree has `.php` / `package.json`. Prior v2.0.5 receipts (`cd8a96` test-review) show this product tree under `base`: `git-diff-check` + `secret-scan` (0) + `contract-structure` (0 contracts) + `sql-safety` (0) + `python-unittest` (156 tests).

**`_python` contract** (CHANGELOG 2.0.4, `decisions.md` 2026-08-14, change `2eacdf` / `aea9d4`):

- If `pyproject.toml` / `requirements.txt` / `setup.py` exist: optional `ruff check .` **if `ruff` is on PATH**; if pytest is present and `tests/` exists, run pytest and **return** (no unittest).
- Else if `tests/test*.py` exist at the top of `tests/`: `python -m unittest discover -s tests` as check `python-unittest`.
- Do **not** add a packaging marker on this repo just to light ruff/pytest — that flips `detect_repo` and, with pytest present, skips unittest.

This product tree has no `pyproject.toml` / `requirements.txt` / `setup.py`. Therefore **ruff is not part of this repo’s advertised verify run**, even if the binary is installed.

**`secret-scan`** (implementation, characterized in `tests/test_verification_doctor.py`): regex over changed files only — PEM/OpenSSH private key header, `AKIA[0-9A-Z]{16}`, and `api_key|secret|password|token = '…'` with ≥12 chars. Not a secret engine, not image/IaC scan, not git-history scan.

**Doctor** (README, CHANGELOG 2.0.5, `toolchain.json`): stack self-health + toolchain pins (Python/Git/Grok/`gh`/Node/npm/PHP/Composer). Offers fallback install. Does **not** run SAST, SCA, coverage, or load tests. Checks required files, managed agents/skills, a sample Bitrix route, optional `MANIFEST.sha256`, and host tool versions.

**Hooks / policy** (README, `.grok/hooks/README.md`, `policy.json`, CHANGELOG 2.0.4):

- PreToolUse: block secret-path reads, Bitrix core, destructive shell, and production **invocations** (`git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`).
- On import/exception: **allow** (fail-open).
- Stop: missing/stale evidence is a **warning**, never a hard block.
- `policy.json` note: “Hooks are guardrails, not a complete OS security boundary.”

**This-repo CI** (CHANGELOG 2.0.4, `99b743` architecture, `.github/workflows/adaptive-grok.yml`): on push/PR — unittest + doctor + `grok_verify --mode pr`; conditional `package` job; **no publish** job.

**Release last mile** (README, runbooks, `99b743`, `cd8a96`): `grok_deploy.py` prints human commands; never subprocesses push/tag/`gh release`. GitHub Release `v2.0.5` is already live (tag peels to `7c0ae7573535ddd0cfe3800f81278991ced81584`; Latest badge; zip sha256 `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd`). `v2.0.4` remains a previous release.

**`release-readiness` skill** asks the reviewer to *check* immutable artifact, migrations, flags, smoke/E2E/contract evidence, SLI/SLO, dashboards, alerts, rollback — and to write a go/no-go report. It does **not** claim those observability/load/coverage products exist in this tree.

### 1.2 What the docs already admit is missing or deliberately weak

| Admitted gap | Where |
| --- | --- |
| Verify used to be hollow on this repo (no unittest without a packaging marker). Fixed in 2.0.4; ruff still off unless a consumer adds a marker. | `2eacdf` brief/architecture; CHANGELOG 2.0.4; `decisions.md` |
| Stop is warn-only; PreToolUse fail-open. Not a hard quality gate. | CHANGELOG 2.0.4; hooks README; `mistakes.md` (disabling hooks hid bugs) |
| Hooks are not an OS security boundary. | `policy.json` notes |
| CI has no publish / no deploy job. | CHANGELOG 2.0.4; `99b743` architecture decision 4 |
| No product OpenAPI/AsyncAPI contracts; `engineering/adr/` empty. | prior `docs_researcher` reports `ad4090`, `cd8a96` |
| No EULA, no paid tier, no SaaS SKU. | README; CHANGELOG 2.0.4; `decisions.md`; `99b743` / `bb6ab3` |
| `99b743` out of scope: new skill, service, queue, billing, EULA, real infra deploy adapters. | `99b743` brief |
| This change package (`ef7b14`) is still a stub: empty scope, empty acceptance, empty architecture. | `brief.md`, `requirements.md`, `architecture.md`, `state.json` = `draft` |
| Current route `write_agent` is `null`; analysis-only. | `active-route.json` |

Zero in-tree mentions of Dependabot, Trivy, gitleaks, Sonar, Codecov, Snyk, Semgrep, Bandit, Sentry, k6, Jaeger. `.coverage` appears only as a **packaging exclude**, not as a measured gate.

---

## 2. In-house equivalents vs Dobryakov’s 12 categories

Dobryakov (Aug 2026 PDF) is a catalogue of 57 non-AI tools in 12 categories. The repo never claims that catalogue. The table is “does an in-house named check already occupy that job,” not “we are SonarQube.”

| # | Dobryakov category (PDF) | Already claimed in-house? | Equivalent that exists | What is **not** claimed |
| --- | --- | --- | --- | --- |
| 01 | SAST / linting (SonarQube, PMD, ESLint, **Ruff**, Semgrep, Checkmarx, Coverity, Bandit, …) | **Partial, opportunistic** | `grok_verify` as a local quality gate; `phpstan`/`phpcs` optional on PHP/Bitrix profiles; `npm-lint` optional on frontend; `ruff` only if consumer has a Python packaging marker **and** `ruff` on PATH; `sql-safety` / `bitrix-policy` as project-specific static rules | No SonarQube server/SaaS, no Semgrep/Bandit/Checkmarx, no metrics history, no quality-gate thresholds beyond pass/fail of listed checks. **This product repo does not run ruff.** |
| 01b | Secrets subset of SAST (Bandit hardcoded passwords; Trivy secrets) | **Yes, lite** | `secret-scan` (3 regexes on changed files) + PreToolUse `secret_read_paths` + packager excludes `.env` / keys | Not gitleaks, not Trivy, not git-history, not container/IaC secret scan |
| 02 | DAST (ZAP, Burp, Nikto, Nessus, OpenVAS, AppScan) | **No** | — | This product is a CLI/hook stack, not a running web app. No DAST job in CI. |
| 03 | SCA (Dependency-Check, Snyk, Black Duck, **Dependabot**, **Trivy**, FOSSA) | **No** | `toolchain.json` + doctor pin *host* tools (Python/Git/`gh`/Node/PHP). That is version hygiene for the installer, not CVE/SCA | No Dependabot config, no lockfile audit, no image/SBOM/CVE scan |
| 04 | Load testing (JMeter, Gatling, k6, Locust, …) | **No** | — | `release-readiness` mentions SLI/SLO as a *review checklist*, not a tool |
| 05 | Code coverage (JaCoCo, Istanbul, Coverage.py, Codecov) | **No** | `.coverage` is excluded from the zip (`manifest.py` / prior reviews). Test-review “coverage” means characterization vs acceptance, not line coverage | No coverage.py run, no threshold, no Codecov |
| 06 | APM / error tracking (Sentry, Datadog, New Relic, Prometheus, Rollbar) | **No** | — | Product is not a long-running service |
| 07 | Log management (ELK, Splunk, Graylog, Loki, Fluentd) | **No** | — | |
| 08 | Infra monitoring (Grafana, Nagios, Zabbix, Influx) | **No** | `grok_doctor` is **stack/toolchain health**, not host/cluster monitoring | Do not equate doctor with Nagios |
| 09 | Test management (TestRail, Zephyr, Xray, Allure) | **Process analog only** | Change-package `test-plan.md` + fingerprint-bound unittest/review receipts | No TMS, no Allure history |
| 10 | Architecture analysis (ArchUnit, NDepend, Structure101, CodeScene) | **Optional PHP only** | `deptrac` if `vendor/bin/deptrac` exists (php profile, optional) | No ArchUnit/CodeScene; this repo is Python and does not run deptrac |
| 11 | Formatters (Prettier, Black, Biome, clang-format) | **No required formatter** | Same opportunistic `ruff` / `npm-lint` as row 01; no Black/Prettier pin | No format-check in `base` |
| 12 | Distributed tracing (Jaeger, Zipkin) | **No** | — | |

### Suggested equivalences (user’s framing) — confirmed against docs, not vendor claims

| User mapping | What the tree actually supports |
| --- | --- |
| `secret-scan` ≈ gitleaks / Trivy secrets | **Lite analog only.** Changed-file regex + hook deny on `.env`/keys. Not history, not containers, not Trivy `fs`/`image`. |
| `grok_verify` ≈ CI quality gate | **Yes, as the named gate.** README calls it “Verification gate.” CI job *is* `grok_verify --mode pr` plus unittest + doctor. Functionally the Sonar “gate blocks merge/publish” *role*, without Sonar metrics. |
| Policy hooks ≈ pre-commit / SAST-lite | **Partial.** PreToolUse is a Grok-lifecycle deny list (secrets, Bitrix core, force-push, real publish invocations), fail-open, not a `.pre-commit-config.yaml` and not AST SAST. |

**Already claimed as covered (in-house, not Dobryakov-named):** secret lint on the diff; git whitespace/conflict check; unittest (this repo) / optional pytest-or-phpunit-or-npm-test (consumers); contract JSON/OpenAPI/AsyncAPI shape; unbounded SQL regex; Bitrix policy; doctor/toolchain; CI verify+package; human-gated GitHub Release.

**Not claimed, and not present:** SCA, DAST, coverage gate, load test, APM/logs/infra/tracing, Dependabot, Sonar, paid SAST.

---

## 3. Constraints that forbid adding a service or paid SaaS without an ADR

There is **no ADR file**. Introducing a service still requires an explicit architectural justification *before* implementation (`AGENTS.md` development discipline). Combined constraints:

1. **`AGENTS.md`:** “Do not introduce a service, database, queue, framework, or dependency without explicit architectural justification.”
2. **Source-of-truth order:** ADRs sit above existing implementation. `engineering/adr/` is empty, so a new service/SaaS has no standing decision.
3. **MIT / no paid tier (README, CHANGELOG 2.0.4, `decisions.md` 2026-08-15, `bb6ab3`):** commercial-grade product that is free of charge; no EULA; no paid SKU. Adding SonarQube Developer ($750+/yr in the PDF), Snyk Team, Codecov Team, Sentry Team, etc. would contradict the published positioning unless a new ADR revises it.
4. **`99b743` brief out of scope:** “New skill, service, queue, billing, EULA” and “Real infra deploy adapters.” Task-analyst evidence: “No SaaS. Commercial = versioned engineering product, not monetization.”
5. **AI/security rule (`AGENTS.md`):** do not send secrets, customer data, or proprietary code to external tools unless explicitly authorized. Cloud SAST/SCA/coverage that upload the tree needs that authorization.
6. **This route:** `human_gates` = `scope_and_design_approval` + `production_action_approval`; `write_agent` = `null`. Adaptive-delivery requires stopping before implementation on the named scope gate.
7. **Policy / hooks:** production side-effects stay human-owned; CI must not grow a publish job (`99b743` decision 4).

Local, free, optional CLI tools (ruff, phpstan already listed as optional profile checks) are a smaller lift than a new service: they still need a change-package decision (especially ruff, because adding `pyproject.toml` was **explicitly rejected**).

---

## 4. What «прод» means in *this* product

**It does not mean installing the stack into a consumer’s production application runtime.**

Documented meaning:

| Sense | Verdict | Source |
| --- | --- | --- |
| Word `прод` as a **risk classifier** | Matches as a whole word; must **not** fire on `продукт`. Triggers high-risk + `production_action_approval`. | CHANGELOG 2.0.4; `decisions.md`; `bb6ab3` |
| This product’s **last mile / “prod”** | Public **GitHub Release** (tag + zip + sha256). Humans run the printed `git tag` / `git push` / `gh release create`. `grok_deploy.py` is prepare-only. | README; runbooks; `99b743`; `cd8a96` |
| GitHub Release **already shipped** | **v2.0.5 is Latest** on `Dimkox/adaptive-grok-build-pro`, peel `7c0ae75`, zip digest `b80e6310…`. `v2.0.4` still exists. | `cd8a96` test-review / state `ready` |
| `install_into.py` | Copies the stack into **another git repo** (consumer project) and may install host toolchain pins. Documented as install, not production deploy. | README; QUICKSTART; CHANGELOG 2.0.5 |
| Runtime prod (K8s, Bitrix prod, 1C, payments) | Explicitly out of scope for unapproved agent action. No infra deploy adapters. | `AGENTS.md` prohibited actions; `99b743` |

So the user phrase «перед заливкой на прод» in *this* repository’s contract language is: **before the next GitHub Release** (a 2.0.6-class publish), not “before we install into customer production.” v2.0.5 is already on Latest; any Dobryakov integration would be a **new** versioned change, with `scope_and_design_approval` first, and `production_action_approval` only for the later tag/release.

Consumer production repos are relevant only as **install targets** after that release (`python3 scripts/install_into.py /path/to/repo`). They are not this product’s production environment.

---

## 5. Facts useful to the architect (no recommendations invented as APIs)

- Active route quality profile is **`base` only**. Integrating ruff/phpstan/Dependabot is out of the current machine-readable profile unless a later approved design adds checks or profiles.
- Adding `pyproject.toml` to light ruff on *this* repo is a known anti-pattern (`decisions.md`).
- Cheap, already-wired, still-off-on-this-tree knobs: keep using `secret-scan` / unittest / CI verify; optionally document consumer-side `ruff` / `phpstan` / `npm-lint` as profile behavior (already coded).
- Anything that is a new hosted service, paid SKU, or tree-uploading scanner needs an ADR that does not yet exist, plus the two human gates on this route.
- This change package has no acceptance criteria yet; do not treat the PDF as a backlog the repo already promised.

End of report.
