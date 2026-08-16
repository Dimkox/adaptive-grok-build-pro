# Analysis — architect

Change: `20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14`  
Route: `ef7b14ec854d` · intent=`release` · risk=`high` · write=`NONE` · reviews=`security_reviewer`+`release_reviewer`  
Gates: `scope_and_design_approval` + `production_action_approval`  
Source: [Dobryakov, 57 code-quality tools](https://www.dobryakov.com/lead-magnets/code-quality-tools.pdf) (fetched 2026-08-16)

Read-only design. No application-code edits. No `.env`. No push / tag / merge / deploy.

Narrow question: what from the handbook is worth integrating **before** calling this product production-ready, what must wait, and what must never be bolted on?

## Ruling (one screen)

This product is already a shipped MIT CLI (`VERSION` = `2.0.5`, tagged, GitHub Latest). It is **not** a running HTTP app, container, or ops platform. Dobryakov’s handbook is a catalog for typical backend/web/enterprise estates. Mapping it 1:1 onto this repo is a category error.

- **Do not dump the handbook into this tree.**  
- **Do not stand up a service, database, or paid SaaS.**  
- **Do not treat «заливка на прод» as a reason to open 2.1.0 or retag 2.0.5.**  
- **Go for keeping 2.0.5 published.** It already has a real verify contour, CI, packaging, and human last mile.  
- **No-go for a new “quality-platform” prod claim today.** Process quality is real; Python SAST / coverage / supply-chain automation on *this* repo is still thin.  
- **If the user later says «делай»:** one write-owner route, one slice — **Ruff as a first-class `grok_verify` check without `pyproject.toml`.** Stop after that slice.

This route has `write_agent: null`. Design only. Implementation requires a new route with a write owner and the named human gates.

## What this product actually is

| Fact | Evidence |
| --- | --- |
| MIT Python CLI / hooks / agents / quality-profile framework installed into other repos | `README.md`, `scripts/install_into.py` |
| Stdlib-only runtime (`adaptive_grok/*` imports stdlib + local modules) | `.grok-stack/adaptive_grok/*.py` |
| No `pyproject.toml`, `requirements.txt`, `setup.py` | repo root; `engineering/decisions.md` 2026-08-14 |
| `detect_repo` is `kind=generic`, no languages | `active-route.json` `repo.kind` |
| Adding `pyproject.toml` flips `detect_repo` to `python` and, if pytest is on PATH, **skips** `python-unittest` | `repo.py:82-84`; `verification.py:181-201`; decisions.md |
| v2.0.5 already tagged and Latest | user context; `VERSION`; `packages/adaptive-grok-build-pro-v2.0.5.zip*` |
| “Prod” here = GitHub Release + install-into-consumer-repos, not a live service | `scripts/grok_deploy.py` is prepare-only; CI has no publish job |

## What we already have (mapped to the 12 handbook categories)

`verify()` always runs `git-diff-check`, `secret-scan`, `contract-structure`, `sql-safety`, then `_python()`. PHP/Bitrix/Node checks fire only on profile or tree signals. Quality-profile JSON lists `required_checks` / `optional_checks`, but **`verify()` does not read those lists** — they are documentation unless a later slice wires them.

| Handbook category | Closest existing capability | Status on *this* repo |
| --- | --- | --- |
| 01 SAST / linting | Regex `secret-scan` on **changed files**; `ruff` only if `command_exists('ruff')` **and** a Python project marker; PHP `php -l` / PHPStan / PHPCS for consumers | Ruff is **dead here** (no marker). Secret-scan is not Bandit/Semgrep. |
| 02 DAST | None | Correct absence: no HTTP target |
| 03 SCA | None | Correct-ish: **zero third-party runtime deps**. Actions pins are unmonitored. |
| 04 Performance | None | Correct absence: no request path |
| 05 Coverage | `python-unittest` via `grok_verify` + CI `unittest discover` | Tests exist; **no coverage number or fail-under** |
| 06 APM | None | Correct absence: CLI, not a service |
| 07 Log management | None | Correct absence |
| 08 Infra monitoring | None | Correct absence |
| 09 Test management | Change packages, fingerprint-bound receipts, independent review agents, `grok_status` evidence gaps | Stronger *for this product* than TestRail |
| 10 Architecture | `bitrix-policy`, optional Deptrac, `sql-safety`, `contract-structure` | Consumer-oriented; no Python layer rules |
| 11 Style | Half-wired Ruff; consumer `npm-lint` / PHPCS | Not running on this tree |
| 12 Tracing | None | Correct absence |

Process controls Dobryakov does not list, already shipped:

- Adaptive route + one write owner + fail-open hooks after `git pull`
- Production invocation matcher (`git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`)
- Secret-read and Bitrix-core path policy
- `grok_doctor` + toolchain pins + install offers
- `grok_deploy.py` prepare-only last mile; humans run printed commands
- SHA256-manifest packaging; CI `verify` + conditional `package`; **no publish**

That is already a production *workflow* product. It is not a production *quality-scanner* product.

## Bucket A — integrate into THIS repo before any further “prod-ready quality” claim

Small, free, local, Python-native. No new service. Each item is justified against *this* tree, not the handbook’s generic “every team should”.

### A1. Ruff (lint + format) — **do first**

- Handbook: Python de-facto linter/formatter; replaces Flake8/isort/pyupgrade and part of Bandit; 100× Pylint.
- Already in `_python`, but gated on `pyproject.toml` / `requirements.txt` / `setup.py`. This repo has none, by design.
- **Do not add `pyproject.toml` to light Ruff.** That is a recorded anti-pattern (`decisions.md`: flips `detect_repo`, pytest-wins skips unittest).
- Design: dedicated check `ruff` (and later `ruff-format`) that runs on `.grok-stack/adaptive_grok`, `scripts/`, `tests/`, and root hook shims when `ruff` is on PATH. Config in **`ruff.toml`**, not `pyproject.toml`.
- Local: skip if missing (same as today’s optional ruff). CI: `pip install ruff` then fail-closed.
- Why before a stronger prod claim: this is the only handbook SAST that matches the language, is already half-implemented, and currently gives a false sense of coverage.

### A2. Bandit — **do second, same family**

- Handbook: Python security AST (eval, MD5/SHA1, SQL concat, `subprocess` without `shell=False`, hardcoded passwords).
- This tree is full of `subprocess` runners, hook policy, and path handling. Regex `secret-scan` does not see those.
- Local skip-if-missing; CI install + fail-closed. Config `.bandit` / `bandit.yaml`. Exclude `tests/` noise if needed.
- Does **not** replace `secret-scan` (changed-file regex vs whole-tree AST). Complementary.

### A3. Coverage.py threshold — **do after measuring, not with a guessed 90%**

- Handbook: Coverage.py is the Python standard; CI `--fail-under`.
- We already run the suite twice in CI (bare unittest + `grok_verify` → `python-unittest`). Adding coverage should **replace** one of those runs, not add a third.
- First measure current line/branch on `.grok-stack/adaptive_grok` + `scripts`. Set `--fail-under` at **measured − 2 points** (or a documented floor once known). Config `.coveragerc`, omit tests/runtime.
- Do not add Codecov SaaS. Local XML/HTML is enough.

### A4. Dependabot for `github-actions` — **yes, GitHub-only**

- Handbook: 10-minute setup, weekly PRs, free on GitHub.
- This repo has no pip lockfile. Dependabot `pip` against nothing is theater.
- Add `.github/dependabot.yml` with `package-ecosystem: github-actions` weekly. Optionally a later `pip` ecosystem **only if** a `requirements-ci.txt` is introduced for ruff/bandit/coverage pins.

### A5. pip-audit / Trivy fs — **not first-class on this repo**

- **pip-audit:** there is no product dependency graph. Auditing air is not a gate. If A1–A3 introduce a CI requirements file, audit *that* file in CI only.
- **Trivy `fs`:** useful second secret/misconfig layer, but it is a binary/Docker tool, not Python-native, and overlaps `secret-scan`. If wanted, GitHub Action only, skip locally if missing. Do not put Trivy inside in-process `grok_verify`.

### A6. pre-commit — **optional developer convenience, not a prod gate**

- Fine as a wrapper around the same Ruff/Bandit commands.
- Must not become a second source of truth. Consumers must not be forced to install pre-commit. `make verify` / `grok_verify` remain canonical.

**A is not a dump.** Order is A1 → A2 → A3 (after a measured baseline) → A4. A5–A6 only if a human asks.

## Bucket B — later, OPTIONAL quality-profile checks for consumers

Do **not** force these on this repo. Wire them the same way PHPStan/PHPCS/npm-lint already work: skip unless the consumer tree has the tool and the profile/domain matches.

| Tool | Profile / trigger | Why wait |
| --- | --- | --- |
| Semgrep (`p/python`, later custom YAML) | `base` optional or new `security` | Best for *consumer* rules (Bitrix sinks, eval, shell). Extra binary + registry; not needed to lint this stdlib CLI. |
| Trivy `image` / `config` | `infra` | Only if the consumer has Docker/Terraform. This repo has neither. |
| ESLint / Prettier / Biome | `frontend` | Already delegated to `npm-lint` when `package.json` scripts exist. Do not vendor a JS toolchain here. |
| Istanbul / nyc | `frontend` | Only if consumer `npm test -- --coverage`. |
| OWASP Dependency-Check / Trivy fs on lockfiles | `php` / `frontend` / `integration` | Consumer Composer/npm/Maven graphs. Not this repo. |
| PHPStan / PHPCS / PHPUnit / Deptrac | `php` / `bitrix` | **Already optional** when `vendor/bin/*` exists. |
| Allure Report (OSS CLI, not TestOps) | any consumer with pytest/phpunit | Pretty HTML. Not a release blocker. |
| Locust / k6 | `integration` | Only if the consumer has an HTTP API. |
| CodeScene OSS / hotspot report | later docs | Git-history advice, not a verify gate. |
| Snyk free CLI | do not prefer | SaaS-leaning; pip-audit + Trivy cover the free local job. |

When B lands, honor profile JSON for real (`required_checks` / `optional_checks`) instead of growing more hard-coded branches in `verify()`. That wiring is a separate design, not part of A1.

## Bucket C — do not integrate

Wrong stack, paid enterprise, needs a running HTTP app, or is an ops platform — not a CLI product. Bolting any of these on would violate “no new service / DB / paid SaaS” and the MIT local-first contract (`templates/ci/README.md`).

| Tool | Why never here |
| --- | --- |
| SonarQube server | Docker service + Quality Gate platform. Open-core still needs a host. |
| Checkmarx, Coverity | Paid enterprise SAST; regulatory/safety-critical. |
| ZAP, Burp, Nikto, Nessus, OpenVAS, HCL AppScan | DAST / infra scanners. **No URL, no host inventory.** |
| JMeter, Gatling, k6, Locust, Artillery, LoadRunner, BlazeMeter | Load tests need an HTTP/protocol target. |
| Datadog, New Relic, Dynatrace | Paid APM agents. Nothing to instrument in production. |
| ELK, Splunk, Graylog, Loki, Fluentd, Sumo Logic | Log platforms. |
| Nagios, Zabbix, Grafana-as-required-platform, Influx/Telegraf | Infra monitoring. |
| TestRail, Zephyr, Xray, Allure TestOps | Paid/Jira TMS. We already have change packages + receipts. |
| ArchUnit, NDepend, Structure101 | Java/.NET architecture testers. |
| Jaeger, Zipkin | Distributed tracing for microservices. |
| Also out: PMD, Checkstyle, SpotBugs, clang-tidy, cppcheck, JaCoCo, gcov, Understand, Black Duck, FOSSA paid, Sentry/Rollbar as product APM, Prometheus as a required runtime | Wrong language, paid SCA, or a service this CLI does not run. |

Sentry-in-the-CLI would export user/repo context to a third party. Forbidden without an explicit, separately approved architecture decision.

## Answers to the four explicit questions

### 1. `grok_verify` checks or only GitHub Actions?

**Both, with one source of truth.**

| Kind | Where |
| --- | --- |
| Ruff, Bandit, Coverage.py | **`grok_verify` first** (in-process `_command_check`, no new service). CI installs the tool and runs the same `python scripts/grok_verify.py --mode pr`. |
| Dependabot | GitHub only (it is a GitHub product). |
| Trivy / pip-audit of CI pins | CI-only, skip locally if missing. |
| Parallel CI-only quality bar that local `make verify` cannot reproduce | **Forbidden.** |

Modes: `fast` may skip coverage; `pr` and `release` include A-gates once landed.

### 2. New service / DB / paid SaaS?

**None.** No SonarQube, no Codecov cloud, no Snyk org, no Sentry DSN, no ELK. Architectural justification for any of those does not exist for a stdlib CLI. If a future consumer profile wants Semgrep/Trivy, they bring their own binary.

### 3. Smallest vertical slice if the user later says «делай»

One change, one write owner (`general_implementer` on a **new** route — this route has no writer).

**Slice name:** Ruff without a packaging marker.

1. Characterization tests: unmarked tree with `tests/test*.py` still runs `python-unittest`; when `ruff` is present, a `ruff` check appears; when absent, skip (not fail); a planted unused import fails `ruff`.
2. `ruff.toml` at repo root (not `pyproject.toml`).
3. `_python` / new `_ruff`: run `ruff check` on the Python paths above **without** requiring a project marker.
4. CI: `pip install ruff` before Verify so the check is fail-closed on GitHub.
5. List `ruff` under `base.json` `optional_checks` (honest docs). Do not yet rewrite `verify()` to honor the JSON lists.
6. Do **not** add Bandit, coverage, Dependabot, pre-commit, or a VERSION bump in the same change.

Rollback: delete `ruff.toml`, revert the check, CI still has unittest+doctor+verify. No data, no service.

### 4. Go / no-go for «заливка на прод» TODAY without new tools

Split the Russian phrase; it mixed two different acts.

| Act | Decision | Why |
| --- | --- | --- |
| Keep / use already-published **v2.0.5** | **GO** | Tagged, Latest, SHA256 zip, unittest+doctor+verify CI, prepare-only deploy, MIT, no running attack surface. Handbook gaps do not unpublish it. |
| Agent or human “prod dump” of a **new** quality-platform release today | **NO-GO** | No write owner. Named gates not approved. A1–A3 not landed. Dumping 20 tools would violate product shape. |
| Claim “Dobryakov-complete / enterprise quality platform” | **NO-GO** | False. We have process + unittest + regex secrets. We do not have live Python SAST, coverage gate, or Actions SCA. |
| Human re-publish of 2.0.5 (retag / rebuild zip) | **NO-GO** | Already shipped. Rebuild would mix post-tag evidence. See prior `cd8a96` ruling. |
| Implement Bucket A on this route | **NO-GO** | `write_agent` is null. Need a new standard/low-risk route after `scope_and_design_approval`. |

**Today, without new tools, the product may stay in production as v2.0.5.**  
**Today, without new tools, do not ship a new version or a new “prod-ready” claim that implies handbook completeness.**

## Constraints for any later writer

- Do not add `pyproject.toml` / `requirements.txt` / `setup.py` to this repo to unlock tools.
- Do not introduce a runtime dependency into `adaptive_grok` (Ruff/Bandit/Coverage are CI/dev tools, invoked as commands).
- Do not make consumer installs pull Ruff/Bandit (`install_into.py --no-deps` / required toolchain stays python3+git).
- Do not publish, tag, or merge from the agent. Last mile remains `grok_deploy.py` print + human shell.
- Do not treat this analysis as implementation approval. Gate `scope_and_design_approval` is still open.

## Residual risks

- `secret-scan` only sees `changed_files` (diff + untracked), not the whole tree. A1/A2/A5-CI close that only if scoped to full Python paths.
- Profile JSON is decorative. A later “honor required_checks” slice is real work; do not sneak it into A1.
- Enabling Ruff fail-closed on this tree will fail on current style debt until the writer either autofixes or starts with a narrow `select`. First landing should use a small rule set (`E`, `F`, `I`) so the slice stays vertical.
- Coverage threshold without a measured baseline will flake the suite. Measure first.

## Stop

Design recorded. No implementation on this route. Human gate: accept Bucket A order (Ruff first) and the go/no-go split above, then open a write-owner route if they want the slice.
