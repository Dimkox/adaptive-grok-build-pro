# Repo inventory — Dobryakov toolkit vs this tree

Change: `20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14`
Route: `ef7b14ec854d` (intent=release, write_agent=null, risk=high)
Product: Adaptive Grok Build Pro v2.0.5 — a **Python CLI/framework**, not a public HTTP app. No Java, no C++. “Прод” for this repo is a human-owned GitHub Release of a zip (`scripts/grok_deploy.py` prints commands; it never executes tag/push/release).

Verdict legend:

- **HAVE** — real files, checks, or CI jobs that run on *this* tree.
- **PARTIAL** — a working adapter or process equivalent exists, but the named Dobryakov tool is not installed/configured here, or it only fires in a consumer repo.
- **ABSENT** — no file, no check, no CI job, no config. Mentions in skill/checklist text are called out separately.

Do not treat quality-profile JSON names as proof a tool runs. `.grok-stack/adaptive_grok/verification.py` never loads `quality-profiles/*.json`. It uses profile *names* as flags (`php`, `bitrix`, `frontend`) and always runs a hardcoded core set.

---

## How quality actually runs

### Always-on core (`verification.verify`)

Source: [`.grok-stack/adaptive_grok/verification.py`](.grok-stack/adaptive_grok/verification.py)

On every `python scripts/grok_verify.py` call:

1. `git-diff-check` — `git diff --check`
2. `secret-scan` — three homemade regexes on *changed* files only (private key, `AKIA…`, `api_key|secret|password|token = '…'`)
3. `contract-structure` — JSON parse + `openapi:`/`asyncapi:` presence
4. `sql-safety` — regex for `DROP`/`TRUNCATE`/`DELETE` without WHERE / `UPDATE` without WHERE
5. `_python()` — see below

Conditional families:

| Trigger | Checks |
| --- | --- |
| profile `php`/`bitrix` **or** any changed `*.php` | `php -l`; if `composer.json` at repo root: `composer validate`; if `vendor/bin/{phpunit,phpstan,phpcs,deptrac}` exist, run them |
| profile `bitrix` | `bitrix-policy` ([`.grok-stack/adaptive_grok/bitrix_checks.py`](.grok-stack/adaptive_grok/bitrix_checks.py)) |
| profile `frontend` **or** root `package.json` | `npm run lint|typecheck|test|build` only if those scripts exist |
| `pyproject.toml` / `requirements.txt` / `setup.py` **and** `ruff` on PATH | `ruff check .` |
| those markers **and** `pytest` on PATH **and** `tests/` | `pytest -q` (skips unittest) |
| else `tests/test*.py` at top level | `python -m unittest discover -s tests` |

This tree has **no** `pyproject.toml`, `requirements.txt`, `setup.py`, `package.json`, or root `composer.json`. So `_python()` on *this* product is unittest only. Ruff never fires here. PHP/Node adapters never fire unless a change touches `*.php` or a consumer copies the stack.

### CI that actually exists

[`.github/workflows/adaptive-grok.yml`](.github/workflows/adaptive-grok.yml) (byte-identical to [`.grok-stack/templates/ci/github-actions.yml`](.grok-stack/templates/ci/github-actions.yml); locked by `tests/test_deploy.py`):

| Job | Steps | Publish? |
| --- | --- | --- |
| `verify` | `python -m unittest discover -s tests`; `python scripts/grok_doctor.py`; `python scripts/grok_verify.py --mode pr` | no |
| `package` (needs verify) | `python scripts/package_stack.py`; upload `dist/*.zip*` | no |

No other workflows. No Dependabot. No CodeQL. No scheduled scans.

Local entrypoints: [`Makefile`](Makefile) (`doctor`, `verify`, `status`, `package`, `deploy`).

### Quality-profile JSON (documented, not executed)

Nine files under [`.grok-stack/config/quality-profiles/`](.grok-stack/config/quality-profiles/). Schema is validated by `tests/test_structure.py::test_quality_profiles_are_valid`. Router assigns names ([`.grok-stack/adaptive_grok/router.py`](.grok-stack/adaptive_grok/router.py) ~386–393). The runner never reads `required_checks` / `optional_checks`.

| Profile | JSON claims | What the runner actually does |
| --- | --- | --- |
| `base` | required `git-diff-check`, `secret-scan`; optional contracts/sql | Those four always run regardless of JSON |
| `php` | required `php-lint`; optional composer/phpunit/phpstan/phpcs/deptrac | Runs `php -l` + vendor binaries *if present* |
| `bitrix` | required `php-lint`, `bitrix-policy`; optional phpunit/phpstan/phpcs | Same + homemade Bitrix rules |
| `frontend` | optional `npm-lint|typecheck|test|build` | `npm run <script>` if `package.json` has it |
| `contracts` / `integration` | required `contract-structure` | Already always-on |
| `data` | required `sql-safety` | Already always-on |
| `ai` / `infra` | required `secret-scan` | Already always-on |

This release route’s active profile list is `["base"]` only ([`.grok-stack/runtime/active-route.json`](.grok-stack/runtime/active-route.json)).

### Toolchain pins (not quality tools)

[`.grok-stack/config/toolchain.json`](.grok-stack/config/toolchain.json) pins: `python3`, `git`, `grok`, `gh`, `node`, `npm`, `php`, `composer`. Doctor/installer check those. **No ruff, bandit, eslint, prettier, coverage, trivy, snyk.**

### Policy / secret / production gates (not SAST)

[`.grok-stack/adaptive_grok/policy.py`](.grok-stack/adaptive_grok/policy.py) + [`.grok-stack/config/policy.json`](.grok-stack/config/policy.json):

- Block reads of `.env`, `*.pem`/`*.key`, `credentials*`, `secrets/**`
- Block writes to `bitrix/**` and secret-like paths without `protected-path` approval
- Block destructive argv (`git reset --hard`, `git push --force`, `terraform apply`, unbounded SQL, `rm -rf /`, …)
- Block production invocations (`git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`) without `production` approval
- Block MCP side-effect tools without `external-write` approval

These are **agent-runtime guardrails**, tested in `tests/test_policy.py`. They do not scan the tree the way Bandit/Semgrep/Sonar do.

### Tests that actually exist

156 `def test_*` methods in 12 modules under [`tests/`](tests/). All are stdlib `unittest`. They characterize the framework itself:

| Module | What it locks |
| --- | --- |
| `test_policy.py` | production/secret/Bitrix/MCP gates |
| `test_verification_doctor.py` | secret-scan, sql-safety, contracts, unittest/pytest branch, doctor |
| `test_hooks.py` | lifecycle, rematch, stop-as-warn |
| `test_repo_router.py` | routing, floors, risk, write-owner |
| `test_deploy.py` | prepare-only deploy + CI template = no publish |
| `test_toolchain.py` | pin/offer/install-url safety |
| `test_installer.py` | copy + dep pull |
| `test_manifest_package.py` | zip excludes `.env`/keys/`err.log`/`.coverage` |
| `test_bitrix.py` | homemade Bitrix policy |
| `test_change_receipts.py` | fingerprint-bound evidence |
| `test_structure.py` | files, MIT claims, profile JSON schema |
| `test_runtime_state.py` | lock recovery |

No performance tests. No DAST. No coverage collection. Example PHPUnit lives only in [`examples/bitrix-module/`](examples/bitrix-module/) (`phpunit/phpunit` ^11; no phpstan/phpcs/deptrac).

---

## Confirmed absences (files that would exist if those tools were wired)

Checked missing at repo root / `.github/`:

- `pyproject.toml`, `requirements.txt`, `setup.py`
- `.pre-commit-config.yaml`
- `.github/dependabot.yml` (`.github/` contains only `workflows/adaptive-grok.yml`)
- `package.json`, `composer.json` (root)
- `ruff.toml` / `.ruff.toml` / `bandit.yaml` / `.coveragerc` / `pytest.ini` / `tox.ini`
- `sonar-project.properties`, `.semgrep.yml`, `codecov.yml`
- ESLint / Prettier / Biome / Black / Clang-Format configs
- `Dockerfile`, `docker-compose*.yml`
- `engineering/reviews/` (directory does not exist; reports live under each change package)

`.gitignore` lists `coverage/`, `.pytest_cache/`; [`manifest.py`](.grok-stack/adaptive_grok/manifest.py) excludes `.coverage`. Those are ignore rules, not a coverage pipeline.

---

## Category 1 — SAST / Linting

**Category: PARTIAL**

Named Dobryakov tools:

| Tool | Status | Evidence |
| --- | --- | --- |
| SonarQube | ABSENT | no properties, no CI job, no mention outside this change |
| PMD | ABSENT | Java; no Java in tree |
| Checkstyle | ABSENT | Java |
| SpotBugs | ABSENT | Java |
| ESLint | PARTIAL (adapter only) | `verification._node` runs `npm run lint` if a consumer `package.json` has `lint`. This repo has no `package.json`. Profile: `quality-profiles/frontend.json` |
| Ruff | PARTIAL (adapter only) | `verification._python` runs `ruff check .` **only** when a Python project marker exists **and** `ruff` is on PATH. This repo has no marker, so ruff never runs on this product. Not in `toolchain.json`. Mentioned in older change notes (`20260814-complete-working-adaptive-grok-contour-2eacdf`) as optional consumer behavior |
| Semgrep | ABSENT | no config, no CI, no hit |
| Checkmarx | ABSENT | |
| Coverity | ABSENT | |
| Bandit | ABSENT | no config, no CI, no hit |
| clang-tidy | ABSENT | no C/C++ |
| cppcheck | ABSENT | no C/C++ |

**HAVE on this tree (homemade, not the named tools):**

- `secret-scan` — [`.grok-stack/adaptive_grok/verification.py`](.grok-stack/adaptive_grok/verification.py) L49–64; tested in `tests/test_verification_doctor.py::test_secret_scan_detects_key`; runs in CI via `grok_verify`
- `git-diff-check` — same file L43–46; CI
- `php-lint` adapter — L67–80 (`php -l`); not used on this product unless a `*.php` change
- `phpstan` / `phpcs` — L145–152, only if `vendor/bin/*` exists; listed as optional in `quality-profiles/php.json` and `bitrix.json`; **no binaries, no composer root**
- `bitrix-policy` — [`.grok-stack/adaptive_grok/bitrix_checks.py`](.grok-stack/adaptive_grok/bitrix_checks.py): core-path, `var_dump`/`eval`/`system`, `$_REQUEST`, legacy `$DB`, uninstall symmetry; tests in `tests/test_bitrix.py`
- `sql-safety` — verification L120–134
- LLM `security_reviewer` — [`.grok/agents/security_reviewer.toml`](.grok/agents/security_reviewer.toml); process review, not a scanner
- Skill checklist [`.agents/skills/security-sensitive-change/SKILL.md`](.agents/skills/security-sensitive-change/SKILL.md) (CSRF/SSRF/injection text only)

**Documented equivalent, not a scanner:** quality-profile names; security skill; agent review receipts via `scripts/grok_review.py`.

---

## Category 2 — DAST

**Category: ABSENT** (and not applicable to this product)

| Tool | Status |
| --- | --- |
| OWASP ZAP | ABSENT |
| Burp Suite | ABSENT |
| Nikto | ABSENT |
| Nessus | ABSENT |
| OpenVAS | ABSENT |
| HCL AppScan | ABSENT |

No HTTP server, no OpenAPI served at runtime, no staging URL, no DAST job. `engineering/contracts/openapi/` and `asyncapi/` are empty dirs; the only OpenAPI file is the example [`examples/contracts/openapi/example.yaml`](examples/contracts/openapi/example.yaml). Contract *structure* is a static YAML/JSON check, not a live scan.

---

## Category 3 — SCA (dependencies)

**Category: ABSENT**

| Tool | Status | Evidence |
| --- | --- | --- |
| OWASP Dependency-Check | ABSENT | |
| Snyk | ABSENT | |
| Black Duck | ABSENT | |
| GitHub Dependabot | ABSENT | no `.github/dependabot.yml`; `.github/` has only the one workflow |
| Trivy | ABSENT | |
| FOSSA | ABSENT | |

There is **no dependency lockfile to scan** for this product (no `requirements.txt` / `pyproject.toml` / root `composer.lock` / `package-lock.json`). `composer-validate` in `_composer()` is a consumer-repo adapter. Example module [`examples/bitrix-module/composer.json`](examples/bitrix-module/composer.json) pins only `phpunit/phpunit` and is not part of CI.

---

## Category 4 — Performance / load

**Category: ABSENT**

| Tool | Status |
| --- | --- |
| JMeter | ABSENT |
| Gatling | ABSENT |
| k6 | ABSENT |
| Locust | ABSENT |
| Artillery | ABSENT |
| LoadRunner | ABSENT |
| BlazeMeter | ABSENT |

No load-test directory, no CI job. [`.agents/skills/frontend-change/SKILL.md`](.agents/skills/frontend-change/SKILL.md) says “preserve … performance” as a writing rule, not a runner.

N/A for a CLI zip. Relevant only if this stack is later installed into a Bitrix/HTTP consumer.

---

## Category 5 — Coverage

**Category: ABSENT**

| Tool | Status | Note |
| --- | --- | --- |
| JaCoCo | ABSENT | Java |
| Istanbul / nyc | ABSENT | no Node project |
| Coverage.py | ABSENT | unittest is invoked **without** `coverage run` / `--cov` |
| gcov / lcov | ABSENT | |
| Codecov | ABSENT | no `codecov.yml`, no upload step |

Ignore-only traces: `.gitignore` `coverage/`; `manifest.py` `EXCLUDED_FILES` includes `.coverage`; `util.py` skips `.coverage` and `coverage/` from fingerprints. Review prose uses the word “coverage” to mean characterization completeness, not a metric.

CI does not fail (or even measure) line/branch coverage.

---

## Category 6 — APM

**Category: ABSENT**

| Tool | Status |
| --- | --- |
| Sentry | ABSENT |
| Datadog | ABSENT |
| New Relic | ABSENT |
| Dynatrace | ABSENT |
| Elastic APM | ABSENT |
| Prometheus | ABSENT |
| Rollbar | ABSENT |

**Documented checklist only:** [`.agents/skills/release-readiness/SKILL.md`](.agents/skills/release-readiness/SKILL.md) lists “SLI/SLO, dashboards, alerts, and support visibility”. No dashboards, no SDK, no metrics endpoint. N/A for this CLI; the product’s own “observability” is fingerprint-bound JSON receipts under `.grok-stack/runtime/receipts/`.

---

## Category 7 — Logs

**Category: ABSENT**

| Tool | Status |
| --- | --- |
| ELK | ABSENT |
| Splunk | ABSENT |
| Graylog | ABSENT |
| Loki | ABSENT |
| Fluentd / Fluent Bit | ABSENT |
| Sumo Logic | ABSENT |

`AGENTS.md` mentions Elasticsearch/OpenSearch as a *consumer data-domain* search projection, not a logging stack. [`.agents/skills/incident-response/SKILL.md`](.agents/skills/incident-response/SKILL.md) says “preserve logs, traces, metrics” as a human runbook. Local `err.log` is a hook dump, gitignored.

---

## Category 8 — Infra monitoring

**Category: ABSENT**

| Tool | Status |
| --- | --- |
| Grafana | ABSENT |
| Nagios | ABSENT |
| Zabbix | ABSENT |
| InfluxDB + Telegraf | ABSENT |

No Docker compose, no exporters, no host agents. Release-readiness skill again lists dashboards as a go/no-go question, not an implementation.

---

## Category 9 — Test management

**Category: PARTIAL**

Named products (TestRail, Zephyr, Xray, Allure TestOps): **ABSENT**. No Allure results, no TestOps config, no test-case IDs.

**HAVE (process equivalent, not those products):**

- Real suite: `tests/` + CI `unittest discover` (156 tests)
- Change-package `test-plan.md` template ([`.grok-stack/templates/change/test-plan.md`](.grok-stack/templates/change/test-plan.md))
- `test_reviewer` agent + `scripts/grok_review.py test_review`
- Fingerprint-bound receipts (`.grok-stack/runtime/receipts/<route>/verification.json`, `test_review.json`)
- Consumer adapters: PHPUnit if `vendor/bin/phpunit`; `npm test` if scripted; example [`examples/bitrix-module/phpunit.xml`](examples/bitrix-module/phpunit.xml)
- Bitrix testing *guidance*: [`.agents/skills/bitrix-development/references/testing-review.md`](.agents/skills/bitrix-development/references/testing-review.md) (unit / integration / E2E checklist; no runner)

This is a local evidence loop, not a test-management system.

---

## Category 10 — Architecture fitness

**Category: PARTIAL**

| Tool | Status |
| --- | --- |
| ArchUnit | ABSENT | Java |
| NDepend | ABSENT |
| Structure101 | ABSENT |
| CodeScene | ABSENT |
| Understand | ABSENT |

**HAVE / documented:**

- `deptrac` adapter — `verification._composer` runs `vendor/bin/deptrac analyse` if that binary exists; listed optional in `quality-profiles/php.json`. **No `deptrac.yaml`, no vendor binary in this tree.**
- LLM architects (`architect`, `bitrix_architect`, `data_architect`, `integration_architect`, `ai_architect`) + per-change `architecture.md`
- `engineering/adr/` exists and is empty
- Homemade Bitrix module-structure rules (`install/index.php`, unregister symmetry) are architectural *policy*, not ArchUnit

---

## Category 11 — Style / formatters

**Category: ABSENT** (for this product)

| Tool | Status |
| --- | --- |
| Prettier | ABSENT |
| Black | ABSENT |
| Biome | ABSENT |
| Clang-Format | ABSENT |

Closest adapters (not these tools, not used here):

- `phpcs` if `vendor/bin/phpcs` (PHP consumer)
- `ruff check` (lint, not `ruff format`) if a Python marker + binary exist
- `git-diff-check` is conflict/whitespace, not a formatter

No `.editorconfig` formatter hook, no pre-commit. CI does not format or fail on style.

---

## Category 12 — Tracing

**Category: ABSENT**

| Tool | Status |
| --- | --- |
| Jaeger | ABSENT |
| Zipkin | ABSENT |

No OpenTelemetry. Incident-response skill mentions “traces” as evidence to preserve. Receipts are change-control artifacts, not distributed traces.

---

## README / CHANGELOG claims vs this inventory

Sources: [`README.md`](README.md), [`CHANGELOG.md`](CHANGELOG.md), [`QUICKSTART.md`](QUICKSTART.md), [`dist/RELEASE-NOTES.md`](dist/RELEASE-NOTES.md).

| Claim | Reality |
| --- | --- |
| “Quality profiles and change packages” | Profiles exist as JSON + route names. Runner does **not** execute the JSON check lists. |
| Toolchain table (Python/Git/Grok/gh/Node/PHP/Composer) | True. Those are host pins, not SAST/SCA/DAST. |
| `make doctor` / `make verify` | True; doctor = structure + toolchain; verify = homemade core + unittest on this tree. |
| GitHub Actions: verify + conditional package, no publish | True; tested in `test_deploy.py`. |
| `grok_verify` runs unittest without `pyproject.toml` | True (2.0.4). That closed a hollow-verify gap; it did **not** add ruff/bandit/coverage. |
| Prepare-only `grok_deploy.py` | True; no production mutation from the CLI. |
| Commercial-grade / MIT / no paid tier | Positioning. Not a claim that Sonar/Snyk/ZAP are installed. |
| Release-readiness skill: SLI/SLO, dashboards, smoke/E2E | Checklist for *consumer* releases. This product has none of those systems. |

Nothing in README/CHANGELOG claims SonarQube, Semgrep, Bandit, Dependabot, Codecov, Sentry, Grafana, k6, or Allure are part of the ship.

---

## Scoreboard (12 categories)

| # | Category | Verdict | This product (v2.0.5 zip) | Consumer-repo adapters |
| --- | --- | --- | --- | --- |
| 1 | SAST / linting | **PARTIAL** | homemade secret-scan + git-diff + sql-safety + Bitrix rules; CI | ruff / phpstan / phpcs / `npm lint` / `php -l` if tools exist |
| 2 | DAST | **ABSENT** | N/A (no HTTP surface) | none |
| 3 | SCA | **ABSENT** | no lockfile, no Dependabot/Trivy/Snyk | `composer validate` only |
| 4 | Performance | **ABSENT** | N/A for CLI | none |
| 5 | Coverage | **ABSENT** | unittest with no coverage.py / Codecov | ignore rules for `.coverage` only |
| 6 | APM | **ABSENT** | receipts ≠ APM | skill checklist |
| 7 | Logs | **ABSENT** | `err.log` dump | skill checklist |
| 8 | Infra monitoring | **ABSENT** | N/A | skill checklist |
| 9 | Test management | **PARTIAL** | unittest + CI + review receipts | PHPUnit / npm test if present |
| 10 | Architecture | **PARTIAL** | LLM architects + Bitrix structure rules | deptrac if `vendor/bin/deptrac` |
| 11 | Style | **ABSENT** | no formatter | phpcs / ruff-check if present |
| 12 | Tracing | **ABSENT** | none | skill mention |

Of the **57 named tools**, **zero** are installed, configured, or invoked on this tree. Four names appear as *optional consumer passthroughs*: ESLint (via `npm run lint`), Ruff, plus PHP-adjacent phpstan/phpcs/deptrac (phpstan/phpcs sit in SAST; deptrac in architecture). None of those passthroughs execute in this repo’s CI.

---

## What is already real before a GitHub “prod” release

Safe to treat as existing gates for *this* zip:

1. 156 unittest cases + CI job
2. `grok_doctor` (managed agents/skills, toolchain pins, routing smoke)
3. `grok_verify --mode pr`: git whitespace, homemade secret regex on changed files, contract YAML/JSON shape, SQL danger regex, unittest
4. Policy hooks: no `.env`/key reads, no Bitrix-core writes, no `git push` / `gh release create` without approval
5. Packager excludes `.env`, keys, `err.log`, `.coverage`
6. Independent LLM reviews + fingerprint receipts (`security_reviewer`, `release_reviewer` on this route)
7. Prepare-only deploy printer

That is a **process and policy** contour, not a Dobryakov-grade scanner contour.

---

## Integration-shaped gaps (facts only; no design)

High leverage *if* the next change is to add tools before tagging, given this is a Python CLI with no lockfile and no HTTP surface:

1. **SAST that can actually run here:** Ruff (needs a project marker — currently avoided on purpose because a marker flips `detect_repo` and, if pytest is on PATH, skips unittest; see `engineering/decisions.md` 2026-08-14) and/or Bandit/Semgrep without adding `pyproject.toml`.
2. **SCA:** Dependabot or a lockfile + Trivy/pip-audit. Blocked today by having **no declared Python dependencies**.
3. **Coverage:** `coverage run -m unittest` / fail-under. Ignore rules already anticipate `.coverage`.
4. **Style:** Ruff format or Black — none present; no pre-commit.
5. **Not product-fit for this zip:** DAST, APM, log stacks, Grafana, k6, Jaeger, Java/C++ linters, commercial SAST (Checkmarx/Coverity), Allure TestOps.

Quality-profile JSON `required_checks` being unused by the runner is a separate honesty gap: docs look like a toolkit matrix; the runner is a small hardcoded set.

---

## Sources inspected

- `.grok-stack/runtime/active-route.json`
- `.grok-stack/adaptive_grok/{verification,policy,doctor,deploy,toolchain,bitrix_checks,receipts,repo,router,manifest}.py`
- `.grok-stack/config/{toolchain,policy,routing,managed}.json` and `quality-profiles/*.json`
- `.github/workflows/adaptive-grok.yml` and `.grok-stack/templates/ci/`
- `scripts/grok_{verify,doctor,deploy,review}.py`
- `tests/` (all 12 modules)
- `README.md`, `CHANGELOG.md`, `QUICKSTART.md`, `Makefile`, `VERSION`, `.gitignore`
- `.agents/skills/{release-readiness,security-sensitive-change,verification-evidence,incident-response,frontend-change,bitrix-development/references/testing-review}.md`
- `.grok/agents/{security_reviewer,release_reviewer,code_reviewer,test_reviewer}.toml`
- `examples/bitrix-module/{composer.json,phpunit.xml,README.md}`
- Confirmed missing: `pyproject.toml`, `requirements.txt`, `.pre-commit-config.yaml`, `.github/dependabot.yml`, root `package.json`, root `composer.json`

PDF was not re-downloaded. Inventory is the 57 tools / 12 categories supplied in the task.
