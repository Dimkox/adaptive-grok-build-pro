# Security review — `ef7b14ec854d`

**PASS**

Route: `ef7b14ec854d` (intent=`release`, risk=`high`, `write_agent: null`)  
Change: `20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14`  
Product: Adaptive Grok Build Pro **v2.0.5** (stdlib Python CLI / hook framework; GitHub Release zip, not an HTTP service)  
Reviewer inspected the change package, analysis reports, human approval, and the live v2.0.5 security controls (`verification.py`, `policy.py`, `policy.json`, `deploy.py`, `manifest.py`, CI, tests). No application code was edited on this route. `.env` was not read. No push, tag, merge, or deploy.

---

## Verdict in one screen

Keeping published **v2.0.5** without Bandit / Ruff / Dependabot / DAST is **not** an unacceptable secret, SCA, or DAST hole **for this CLI**. Regex `secret-scan` plus policy hooks are an honest holding control until a later write-owner route lands Bucket A. The approved A/B plan (Dependabot Actions-only, no `pyproject.toml`, no SaaS) does not introduce a new trust-boundary failure. This route performed no production mutation.

Residual risks exist and are named below. They are **documented honesty gaps**, not a reason to unpublish, retag, or block the already-shipped zip.

---

## 1. Does keeping v2.0.5 published without new scanners leave an unacceptable hole?

**No.**

| Class | Is there a hole on *this* product? | Unacceptable for staying published? |
| --- | --- | --- |
| **DAST** | None. No HTTP listener, no staging URL, no OpenAPI served at runtime. `engineering/contracts/openapi/` is empty; only `examples/contracts/openapi/example.yaml` exists. | **No.** ZAP/Burp/Nessus would scan air. Absence is correct, not a defect. |
| **SCA** | No runtime third-party graph (`pyproject.toml` / `requirements.txt` / lockfile absent by design). `adaptive_grok` imports stdlib + local modules. `util.run` uses argv lists, not `shell=True`. | **No.** pip-audit of nothing is theater. Real residual is **unpinned GitHub Actions tags** (`actions/checkout@v4`, `setup-python@v5`, `upload-artifact@v4`). Bounded; does not unpublish a stdlib zip. |
| **Secrets** | Lite, real, not complete. `secret-scan` is three regexes on **changed files** (diff vs `base` + unstaged + untracked). Packager excludes `.env` / `.env.*` / `*.pem|key|p12|pfx`. PreToolUse denies `secret_read_paths`. Findings report path + label, not secret values. | **No.** The published artifact is MIT source that must not contain customer secrets. Residual is pattern coverage and history, not a live leak in the shipped zip. |

**Prod for this repo** is a human-owned GitHub Release of a SHA256 zip (`grok_deploy.py` prints `git tag` / `git push` / `gh release create` and never subprocesses them; tested in `tests/test_deploy.py`). CI has verify + conditional package and **no publish job**. Handbook gaps do not create a network attack surface on the already-tagged Latest release.

Do **not** retag v2.0.5 to “add scanners.” Do **not** claim Dobryakov-complete / enterprise SAST. Those would be false or irreversible. The design already forbids both.

---

## 2. Is regex `secret-scan` + policy hooks enough until Bandit / Ruff land?

**Yes, as a holding control for this CLI remaining published.**  
**No, as a claim of complete SAST.** The change package is honest about that split.

### What actually holds today

`verification._secret_scan` (`verification.py` L49–64), fail-closed on any match:

- `-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----`
- `AKIA[0-9A-Z]{16}`
- `(?i)(?:api[_-]?key|secret|password|token)\s*[:=]\s*["'][^"']{12,}["']`

Scope: `changed_files()` = `git diff base...HEAD` + staged + unstaged + untracked (`util.py` L145–162). Files > 2 MB skipped. Characterized in `tests/test_verification_doctor.py::test_secret_scan_detects_key`.

Policy (`policy.py` + `policy.json`):

- Block **reads** of `.env`, `*.pem` / `*.key` / `*.p12` / `*.pfx`, `id_rsa`, `id_ed25519`, `credentials*`, `secrets/**` (tested: `test_blocks_secret_read`).
- Block **writes** to those paths and `bitrix/**` without `protected-path`.
- Block destructive argv and production invocations (`git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`) without `production` approval.
- Block MCP side-effect tools without `external-write`.
- Block off-route agents and a second write owner.

Packager (`manifest.py`): `.env`, `.env.*` (except `.env.example`), key suffixes never enter the zip.

Deploy: `deploy.py` does not import `subprocess`; `--record` requires production approval; change must be `ready`/`released`.

### Known gaps (accepted until A2, not blockers)

| Gap | Why it is acceptable until Bandit/Ruff |
| --- | --- |
| Only the current diff + untracked, not git history / whole tree | Historical commits are already public on GitHub if they existed. New leaks still fail `grok_verify` on the introducing change. |
| Three regex families only — misses `ghp_` / `github_pat_`, Slack `xoxb-`, JWT `eyJ`, GCP/Azure, unquoted `export FOO=`, high-entropy without a keyword | This tree is not a secret store. Bandit (A2) is AST (eval, MD5, `subprocess` misuse, hardcoded passwords), **complementary**, not a replacement. Design correctly keeps both. |
| Hooks fail-open on import/exception and if the canonical hook file is missing (`pre_tool_use.py` root shim) | Documented: “guardrails, not a complete OS security boundary.” Stop is warn-only. A human or a broken hook can still `cat .env`. That is an agent-runtime limit, not a reason to unpublish. |
| `quality-profiles/*.json` `required_checks` are documentation; `verify()` does not read them | Honesty gap. Core `secret-scan` still always runs. Do not sneak JSON wiring into A1. |

**Enough until A1/A2 land on a new write-owner route. Not enough to skip those slices forever.**

---

## 3. Risks in the approved A/B plan

Human `scope_and_design_approval` (2026-08-16): Bucket A later on a **new** write-owner route (Ruff → Bandit → Coverage.py after a measured baseline → Dependabot `github-actions` only); Bucket B later as **optional consumer** checks (Semgrep, Trivy image, ESLint/Prettier); no `pyproject.toml`; no new service / DB / paid SaaS; do not retag v2.0.5.

| Plan choice | Security judgment |
| --- | --- |
| **Dependabot `github-actions` only** | **Correct.** The only third-party surface on this repo today is Actions tags. No pip lockfile → a `pip` ecosystem would be theater. Residual: Dependabot PRs are themselves supply-chain events — **no automerge**. When A1 adds `pip install ruff` in CI, that creates a **new** unpinned pip surface; the later writer must pin (hash or `requirements-ci.txt`) and only then consider pip-audit. Do not invent a lockfile on this design route. |
| **No `pyproject.toml`** | **Security-positive.** Adding a packaging marker flips `detect_repo` and, if pytest is on PATH, **skips** `python-unittest` (`decisions.md` 2026-08-14). That would weaken the only behavioral gate this repo has. `ruff.toml` is the right config. |
| **No SaaS** (no Sonar, Codecov, Snyk org, Sentry DSN, ELK) | **Security-positive.** `AGENTS.md` forbids sending secrets, customer data, or proprietary/consumer trees to external tools without authorization. Coverage.py local XML/HTML only is the right A3 shape. |
| **Bandit does not replace `secret-scan`** | **Correct complementary design.** Regex-on-diff vs whole-tree AST. Keep both. |
| **Local skip-if-missing / CI fail-closed** | **Correct.** Do not invert. Developers must not think local `make verify` equals CI once A1 lands. |
| **Bucket B optional, not default on this tree** | **Correct tenant/consumer isolation.** Semgrep/Trivy/ESLint fire only when the consumer tree has the signal. Semgrep Cloud / Trivy SaaS would be a **new** human gate. Prefer local binaries; do not upload consumer Bitrix/PHP trees. |
| **No new service / DB** | **Correct.** No new authn/authz plane, no PII store, no multi-tenant SaaS. |
| **Quality-profile JSON still decorative** | Residual honesty gap for a later slice. Mis-wiring `required_checks` could fail-open a check. Out of scope here. |

No finding in the A/B plan requires FAIL. Constraints for the **next** writer (not this route): pin CI tool installs; no automerge; do not enable B by default; do not add `pyproject.toml`; do not pull Ruff/Bandit via `install_into.py` (`--no-deps` / required toolchain stays python3+git).

---

## 4. Confirm: no `.env` read, no production mutation on this route

| Check | Evidence |
| --- | --- |
| `.env` / keys / dumps not read | This review opened change-package markdown/JSON, analysis reports, `verification.py`, `policy.py`, `policy.json`, `deploy.py`, `manifest.py`, CI, tests, `install_into.py` header, `decisions.md`, `VERSION`, quality-profile JSON. No `.env`, `*.pem`, `*.key`, `credentials*`, or production dump was opened. Policy would deny `Read` of those paths (`test_blocks_secret_read`). |
| No product-code mutation | `write_agent: null`. Change tree is design docs only under `engineering/changes/20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14/` (`brief`, `architecture`, `requirements`, `tasks`, `release`, `rollback`, `test-plan`, `state.json`, `route.json`, analysis + approval evidence). |
| No push / tag / merge / deploy | Reviewer did not invoke publish commands. `PRODUCTION_INVOCATIONS` still require `production` approval. `grok_deploy.py` is prepare-only. |
| Production approval for *this* route | **Not granted.** `human-approval.md` is `scope_and_design_approval` for the A/B **design**, explicitly not implementation or publish. `approvals.json` still contains **expired** v2.0.5 publish grants (`3c0ab95c9f72` production, `5fd6bdb8db43` external-write; window `16:09:55`–`16:24:55` Z). Those are stale, out of scope, and must not be reused. |
| Irreversible actions | Design forbids retagging v2.0.5 and standing up a quality-platform release. Rollback for this route: nothing — no product mutation. |

**Authz:** no new permission model. Last-mile publish remains human + short-lived `grok_approve.py production`.  
**PII:** no customer data store; no coverage/SaaS upload; secret-scan details omit secret material.  
**Tenant isolation:** product installs into consumer git trees; Bucket B stays optional per-consumer and must not ship consumer code to a scanner SaaS.  
**Irreversible:** none on this route.

---

## Findings

No blocking findings.

| ID | Severity | Item | Disposition |
| --- | --- | --- | --- |
| S1 | Residual (accepted) | `secret-scan` is 3 regexes on the current change set, not gitleaks / history / high-entropy | Hold until A2 Bandit; keep regex. Do not claim equivalence. |
| S2 | Residual (accepted) | Hooks fail-open; Stop is warn-only; not an OS boundary | Already documented in `policy.json` / CHANGELOG 2.0.4. |
| S3 | Residual (accepted) | CI Actions are floating major tags; no Dependabot yet | Close on the later A4 slice. Review Dependabot PRs; no automerge. |
| S4 | Forward constraint | A1 `pip install ruff` without a pin creates a new SCA surface | Later write owner pins or adds `requirements-ci.txt` + audit. Not this route. |
| S5 | Honesty, not a hole | Profile JSON `required_checks` unused by `verify()` | Separate later slice. Core secret-scan still always runs. |

---

## Recommendation

**PASS.** Ship the design as recorded. Keep **v2.0.5** as Latest. Do not implement scanners on this write-less route. Do not retag. Do not open a quality-platform “prod dump.” Implementation of A (then optional B) requires a **new** route with a write owner, characterization tests, and the existing production gate only if that later route actually publishes.

Independent of this report: `release_reviewer` still owns go/no-go for any future version bump.
