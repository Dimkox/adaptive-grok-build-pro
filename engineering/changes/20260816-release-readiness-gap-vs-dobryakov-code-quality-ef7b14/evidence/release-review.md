# Release review — `ef7b14ec854d`

Reviewer: `release_reviewer` (read-only). Write owner: **none**.
Change: `engineering/changes/20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14`
Intent: `release` · risk: `high` · profiles: `base`
Date: 2026-08-16

**PASS** with a split go/no-go. This route implemented no product code and must not ship.

| Act | Decision |
| --- | --- |
| Keep using already-published **v2.0.5** without new quality tools | **GO** |
| New quality-platform release, handbook-complete claim, or **retag of v2.0.5** today | **NO-GO** |
| Implement Bucket A (Ruff → Bandit → Coverage → Dependabot-actions) on this route | **NO-GO** |
| Treat A-land as a silent rewrite of the 2.0.5 zip / tag | **NO-GO** |

Do not tag. Do not `gh release create`. Do not bump `VERSION`. Do not run printed `grok_deploy` commands for this change.

## Verdict

| Gate | Result |
| --- | --- |
| Immutable published artifact | **PASS.** GitHub Latest is `v2.0.5` at `7c0ae75`. |
| Product mutation on this route | **PASS / empty.** `write_agent` is null. No scanner, no CI, no VERSION edit. |
| Rollback | **PASS / empty.** Nothing to revert in product code. |
| Last mile | **PASS.** Still prepare-only `python3 scripts/grok_deploy.py`; humans own printed commands. |
| Observability for this CLI | **PASS for current shape.** Receipts + `grok_verify` + doctor + CI. No APM/log/infra platform required. |
| A-land versioning | **PASS as a recorded constraint.** Next slice is a new versioned change, not 2.0.5. |
| New release today | **NO-GO.** Design only. Named `production_action_approval` is not a publish grant. |

## 1. Published v2.0.5 is the production surface — GO to keep using it

Independent re-check (HTML, not a live `gh` write):

| Check | Result |
| --- | --- |
| `https://github.com/Dimkox/adaptive-grok-build-pro/releases/latest` | Title **v2.0.5**, Latest badge, peel [`7c0ae7573535ddd0cfe3800f81278991ced81584`](https://github.com/Dimkox/adaptive-grok-build-pro/commit/7c0ae7573535ddd0cfe3800f81278991ced81584) |
| Local `refs/heads/main` and `refs/remotes/origin/main` | `7c0ae7573535ddd0cfe3800f81278991ced81584` (route `base_commit`) |
| Local annotated tag `refs/tags/v2.0.5` | `7f85f7be43fd8008f6af522a967ebc5268a481d1` (same object recorded by `cd8a96`) |
| `VERSION` | `2.0.5` |
| Local zip digest | `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd` in `packages/adaptive-grok-build-pro-v2.0.5.zip.sha256` |
| Release body | Starts `## 2.0.5 — 2026-08-15`; matches `dist/RELEASE-NOTES.md` / `CHANGELOG.md` |
| `v2.0.4` | Still published ([tag page](https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.4) → `33a02f1`). Not Latest. |
| Public REST `/releases/latest` | Rate-limited from this host. HTML Latest badge + prior `cd8a96` `GET /releases/latest` (`tag_name: v2.0.5`) stand. |

`cd8a96` already pushed the existing annotated tag and created the GitHub Release. This route did not rebuild the zip, retag, or edit notes.

Handbook gaps (no Ruff/Bandit/Coverage/Dependabot on this tree) do **not** unpublish 2.0.5. The shipped contour is a MIT CLI with unittest + doctor + `grok_verify` + prepare-only last mile. That is already production for this product’s definition of prod (GitHub Release + `install_into` consumers), not a running HTTP app.

## 2. New quality-platform release or retag today — NO-GO

Reasons, each independently blocking:

1. **`write_agent` is null.** Adaptive-delivery forbids implementation on this route.
2. **No product delta to version.** `VERSION` is still `2.0.5`. `grok_deploy` would print `git tag -a v2.0.5` and `gh release create v2.0.5` — a retag / asset rewrite of Latest.
3. **Human grant is design-only.** `evidence/human-approval.md`: A later, on a **new** write-owner route; not this route; not a production publish.
4. **`production_action_approval` is not satisfied for a new ship.** Leftover machine tokens in `.grok-stack/runtime/approvals.json` are the *prior* v2.0.5 publish (`id` `3c0ab95c9f72` / `5fd6bdb8db43`) and **expired** at `2026-08-16T16:24:55+00:00`. Do not reuse them.
5. **Change status is `approved`, not `ready`/`released`.** `prepare_deploy` refuses anything else (`ALLOWED_STATUSES = {ready, released}`). Do not “ready” this package just to unlock the printer.
6. **CI still has no publish job.** `.github/workflows/adaptive-grok.yml` is verify + conditional package + artifact upload. Tests lock “no `gh release` / `git push` / `docker push`” in the template.
7. **A1–A4 are not landed.** Claiming Dobryakov-complete or “enterprise quality platform” would be false (zero of 57 named tools run on this tree; Ruff is gated on a packaging marker this repo correctly lacks).

`release.md` is correct: go today = keep the published zip; no-go today = a new quality-platform release or handbook-complete claim.

## 3. Rollback is empty — confirmed

`rollback.md`: “No product mutation. Nothing to roll back.”

Inspected product surface vs `v2.0.5` / `7c0ae75`:

| Path | This route |
| --- | --- |
| `VERSION`, `CHANGELOG.md`, `dist/RELEASE-NOTES.md` | Unchanged 2.0.5 text |
| `scripts/`, `.grok-stack/adaptive_grok/`, hooks, `tests/` | No A-land edits |
| `ruff.toml`, `.bandit`, `.coveragerc`, `.github/dependabot.yml`, `pyproject.toml` | **Absent** (confirmed missing) |
| `.github/workflows/adaptive-grok.yml` | Still unittest + doctor + `grok_verify --mode pr`; no publish |
| `packages/adaptive-grok-build-pro-v2.0.5.zip*` | Same digest as the published asset |

What *did* change is paperwork: this change package, analysis reports, `human-approval.md`, runtime route/fingerprint. That is not a ship artifact. If the working tree is discarded, published Latest is unaffected.

Later A-land rollback (not this route): revert that future commit; CI returns to unittest + doctor + current `grok_verify`. **Do not retag v2.0.5** and do not delete the 2.0.5 GitHub Release as a way to “undo” Ruff.

If someone ever needed to withdraw 2.0.5 itself, that is the *previous* change’s delete-only rollback (`gh release delete v2.0.5` then delete the remote/local tag). Out of scope here. `v2.0.4` remains the previous Latest.

## 4. Last mile is still human-owned `grok_deploy` — confirmed

Unchanged contract, still characterized:

| Layer | Evidence |
| --- | --- |
| Skill | `adaptive-delivery` close: do not deploy; last mile is `python3 scripts/grok_deploy.py`; humans own printed commands |
| Skill | `release-readiness`: after go/no-go, run `grok_deploy.py`; `--record` only with production approval; humans run printed commands |
| CLI | `scripts/grok_deploy.py` docstring: “Never executes tag, push, or release.” |
| Implementation | `.grok-stack/adaptive_grok/deploy.py` `_human_commands` returns strings only; no `subprocess` / `os.system` |
| Tests | `tests/test_deploy.py::test_prepare_sources_do_not_execute_publish_commands` |
| CI | `test_template_package_job_is_conditional_and_has_no_publish` |
| Makefile | `deploy:` → `python3 scripts/grok_deploy.py` |
| README | “prepare-only … humans run the printed tag / push / GitHub Release commands” |
| Policy | `git push` / `gh release create` remain production invocations |

Printed command list still includes `git tag -a v{VERSION}`. While `VERSION` is `2.0.5`, those commands are a retag. Another reason this change must not be driven through `grok_deploy`.

## 5. A-land must be a new versioned change — confirmed

User-approved order (`human-approval.md` + `architecture.md`):

1. **Ruff first** via `ruff.toml` (not `pyproject.toml`), new `grok_verify` check, local skip-if-missing, CI fail-closed.
2. **Bandit** second. Does not replace regex `secret-scan`.
3. **Coverage.py** third, after a measured baseline. No guessed 90%. No Codecov.
4. **Dependabot** only `.github/dependabot.yml` for `github-actions`.
5. Optional later consumer profiles: Semgrep / Trivy image / ESLint. Not default on this tree.

Hard constraints that survive into that future route:

- New route, new write owner. Not a silent continuation of `ef7b14ec854d`.
- New `VERSION` (2.0.6-class or whatever the writer is approved to cut) **before** any `grok_deploy` print. Do not retag `v2.0.5`. Do not rebuild and overwrite `packages/adaptive-grok-build-pro-v2.0.5.zip`.
- Do not add `pyproject.toml` / `requirements.txt` / `setup.py` to light Ruff (`decisions.md` 2026-08-14: flips `detect_repo`, pytest-wins skips unittest). `verification._python` still gates `ruff` on those markers.
- No new service, database, or paid SaaS. No SonarQube / Sentry / ELK / Datadog / ZAP / JMeter dump.
- `verify()` remains the single quality bar. Do not grow a parallel CI-only gate.
- Wiring `quality-profiles/*.json` `required_checks` into `verify()` is a **separate** later slice, not A1. Today those JSON lists are documentation.

`tasks.md` still has the implementation box open on purpose: “New write-owner route implements A, then optional B. Not this route.”

## Observability (this product, this change)

This is a stdlib CLI, not a long-running service. Dobryakov APM / logs / infra / tracing are correctly **absent**. Do not treat that absence as a 2.0.5 ship blocker.

What already observes success/failure for the *published* product:

- `grok_verify --mode pr`: `git-diff-check`, `secret-scan` (changed files), `contract-structure`, `sql-safety`, `python-unittest`
- `grok_doctor` + toolchain pins
- CI `verify` then conditional `package` (artifact only)
- Fingerprint-bound receipts under `.grok-stack/runtime/receipts/`
- Independent review reports in change packages

Honesty gaps (do not “fix” as a side quest on a retag):

- Profile JSON is not executed by `verify()`.
- `secret-scan` is three regexes on the diff, not Bandit/gitleaks/history.
- Ruff adapter exists and is **dead on this repo** (no packaging marker).
- No coverage number.

For *this* design route the observable record is the change package itself: analysis reports, `human-approval.md`, `state.json` = `approved`. That is enough. There is no deploy SLI because there is no deploy.

## Remaining risk (not FAIL)

1. **Working-tree fingerprint moved** (`last-fingerprint.json` is `2f11c380…`; route `base_fingerprint` is `28f91dac…`) because the change package and runtime were written after `7c0ae75`. Expected. A later `git add -A` that also scoops leftover `ad4090` / runtime / `err.log` could create a commit that is *not* 2.0.5. Do not tag that commit `v2.0.5`.
2. **Cosmetic:** GitHub Release name for 2.0.5 is the bare tag (prior releases used `Adaptive Grok Build Pro v2.0.x`). `gh release edit` only; not a retag.
3. **Expired production tokens** still sit in `approvals.json`. Harmless once expired; do not treat them as live publish rights.
4. **First Ruff landing will fail on style debt** unless the future writer starts with a narrow `select` (`E`/`F`/`I`) or autofixes in the same versioned change.
5. **Coverage without a measured baseline** will flake. Architecture already forbids a guessed threshold.

## What this review is not

- Not `production_action_approval` for any command.
- Not approval to implement A/B on this tree.
- Not a claim the product is Dobryakov-complete.
- Did not run `grok_verify` (would write a receipt). Did not push, tag, or release.

## Stop

**PASS.**

- **GO:** keep using published v2.0.5 as-is.
- **NO-GO:** new quality-platform release, retag, or silent 2.0.5 rewrite today.
- Rollback: empty.
- Last mile: human-owned `grok_deploy`.
- A-land: new versioned write-owner change only.
