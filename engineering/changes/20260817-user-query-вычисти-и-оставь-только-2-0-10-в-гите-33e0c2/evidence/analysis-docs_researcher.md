# Docs research — stay on published 2.0.10; no product-doc edits

Route: `33e0c2404a15`. Change: `20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2`.

Question: if we only discard uncommitted dirt and stay on published `v2.0.10` (`975ccb2`), do `README.md` / `CHANGELOG.md` / `AGENTS.md` need edits? Must `packages/README.md` and CHANGELOG historical sections stay if old zips are kept? Confirm no GitHub Actions and no `pyproject.toml`.

Read-only. No APIs invented. No `.env`. No push / merge / deploy.

## Sources

- This change package: `brief.md`, `requirements.md`, `architecture.md`, `release.md`, `rollback.md`, `tasks.md`, `test-plan.md`, `state.json`
- `/adaptive-delivery` (`.grok/skills/adaptive-delivery/SKILL.md`) and `feature-workflow`
- `AGENTS.md` SoT order + README-before-push / Release when green
- `README.md`, `CHANGELOG.md`, `VERSION` (`2.0.10`), `QUICKSTART.md`, `packages/README.md`
- Root `decisions.md` / `mistakes.md`; `engineering/decisions.md` stub
- `engineering/runbooks/publish-v2.0.10.md`; older publish runbooks 2.0.4–2.0.9
- `.grok-stack/templates/ci/README.md`
- `tests/test_structure.py` (identity, changelog, packaging-marker, GHA absence)
- `docs/bitrix-local-AGENTS.md`, `examples/bitrix-module/README.md`
- `engineering/adr/` (empty); `engineering/contracts/{openapi,asyncapi,schemas}/` (empty); `engineering/reviews/` (absent)

No ADR or contract defines a docs API for cleanup. Product identity is already written in the committed 2.0.10 tree.

---

## Verdict

**Docs touch list is empty.** `README.md`, `CHANGELOG.md`, and `AGENTS.md` already describe published **2.0.10** and do not need edits if the implementer only restores dirty `state.json` files and deletes untracked sibling evidence.

**`packages/README.md` and every CHANGELOG section `## 2.0.0`–`## 2.0.9` must stay frozen** if historical zips stay. Those rows/sections are the published history of 2.0.10, not leftover dirt.

**No GitHub Actions. No `pyproject.toml`.** Do not add either.

This is not a release (`release.md`: stay 2.0.10; no tag; no GitHub Release edit). `AGENTS.md` “README before push” and “Release when green” do not fire: no new commit, no `git push`, no `grok_deploy`.

---

## Docs touch list vs frozen

| Path | Action | Why |
| --- | --- | --- |
| `README.md` | **FROZEN — do not edit** | H1 and Current state already say **2.0.10** / published GitHub Release `v2.0.10`. Already names **No GitHub Actions** and **Do not add `pyproject.toml`**. Structure test requires the string `2.0.10`. Cleanup does not change the shipped tree. |
| `CHANGELOG.md` | **FROZEN — do not edit** | Latest section is `## 2.0.10 — 2026-08-16`. Historical `## 2.0.0`–`## 2.0.9` stay. Brief forbids deleting CHANGELOG sections. |
| `AGENTS.md` | **FROZEN — do not edit** | Version-agnostic contract. No VERSION string. Self-learning / README-before-push / Release when green already match 2.0.8+ product. Cleanup is not a push or a new identity. |
| `packages/README.md` | **FROZEN — do not edit** | Table lists `v2.0.0`–`v2.0.10` zips. Those files exist under `packages/`. Brief forbids deleting `packages/…v2.0.0`–`v2.0.9.zip*`. Dropping rows while keeping zips would stale the table. |
| `VERSION` | **FROZEN** | `2.0.10`. Requirements: no bump. |
| `QUICKSTART.md` | **FROZEN** | Version-agnostic how-to. No identity claim to refresh. |
| `decisions.md` / `mistakes.md` | **FROZEN for this cleanup** | Already record Never-GHA, no-`pyproject.toml`, 2.0.10-after-2.0.9-tag. Optional self-learning append is out of docs-researcher scope and not required to stay on 2.0.10. |
| `docs/bitrix-local-AGENTS.md` | **FROZEN** | Bitrix local guidance; unrelated. |
| `examples/bitrix-module/README.md` | **FROZEN** | Example module; unrelated. |
| `engineering/runbooks/publish-v2.0.10.md` and older `publish-v2.0.{4,5,6,7,8,9}.md` | **FROZEN** | Historical last-mile notes. 2.0.10 runbook: last mile is `gh`, not GHA. Not dirt. |
| `.grok-stack/templates/ci/README.md` | **FROZEN** | “This product never uses GitHub Actions.” |
| `engineering/decisions.md` / `engineering/mistakes.md` | **FROZEN stubs** | Pointers only. |

**Touch list (product / identity docs): empty.**

The only files this route may change are uncommitted dirt named in `architecture.md` (restore sibling `state.json`; `rm` untracked sibling evidence) plus this change package’s own untracked files. Those are not product docs.

---

## Why README / CHANGELOG / AGENTS.md stay untouched

Committed identity already matches the ruling (`HEAD` stays `975ccb2` / `v2.0.10`):

- `VERSION` = `2.0.10`
- `README.md` line 1: `# Adaptive Grok Build Pro v2.0.10`
- `README.md` Current state: Identity **2.0.10**; published GitHub Release `v2.0.10`
- `CHANGELOG.md` opens at `## 2.0.10 — 2026-08-16`
- `AGENTS.md` has no version field to bump

`tests/test_structure.py`:

- `test_readme_names_onboarding_docs_and_current_version` asserts README contains `2.0.10`
- `test_version_is_2_0_10_and_github_actions_are_absent` asserts `VERSION` is `2.0.10`

README-before-push applies only before `git push` or `python3 scripts/grok_deploy.py`. This change is explicitly **not** a release and **must not** create a new commit. Refreshing README would itself be a product-doc edit and a new tree, which stops being “only 2.0.10”.

Discarding uncommitted session paperwork does not change “what exists, where it lives, and how the pieces connect.” The K10 mermaid and Current state already match the published tree.

---

## Why packages/README and CHANGELOG history must stay

`brief.md`: do not delete published tags, GitHub Releases, **historical zips**, **CHANGELOG sections**, or tracked change packages. Those objects are the history of 2.0.10.

`packages/README.md` table (must remain 1:1 with kept files):

| File | Version |
| --- | --- |
| `adaptive-grok-build-pro-v2.0.0.zip` … `v2.0.9.zip` | 2.0.0–2.0.9 |
| `adaptive-grok-build-pro-v2.0.10.zip` | 2.0.10 |

Those zip + `.sha256` pairs exist under `packages/` today. If they stay, the table rows stay. Editing the table to “only 2.0.10” would be a docs change that implies zip deletion, which is out of scope.

`CHANGELOG.md` sections that must remain as history (not rewritten, not truncated):

- `## 2.0.10` — current published identity
- `## 2.0.9` … `## 2.0.0` — prior published identities

`## 2.0.4` still records “This-repo GitHub Actions: verify plus a conditional package job”. That is **historical 2.0.4 fact**. Later `## 2.0.6` records the ban. Do not rewrite 2.0.4 to pretend GHA never existed.

`test_changelog_2_0_6_does_not_claim_stale_latest` only forbids stale “until a human last mile” / “2.0.5 remains” wording **inside the 2.0.6 section**. It does not allow deleting older sections.

---

## No GitHub Actions. No pyproject.toml.

Facts (do not invent a CI or packaging API):

- `.github/` **does not exist**
- Root **has no** `pyproject.toml`, `requirements.txt`, or `setup.py`
- `README.md` Current state: local `python3 scripts/grok_verify.py --mode pr` only; **No GitHub Actions**; do not add `pyproject.toml` / `requirements.txt` / `setup.py`
- `decisions.md`: “Never GitHub Actions”; “Ruff lives in ruff.toml, not pyproject.toml”
- `tests/test_structure.py` `test_product_tree_has_no_packaging_markers` and `test_version_is_2_0_10_and_github_actions_are_absent`
- `.grok-stack/templates/ci/README.md`: never use GitHub Actions; do not add `.github/workflows/` or Dependabot
- `engineering/runbooks/publish-v2.0.10.md`: last mile is GitHub CLI, not GitHub Actions
- CHANGELOG 2.0.6+ and 2.0.10: still no GitHub Actions

Implementer must not add `.github/workflows/`, Dependabot, `--with-ci`, or a packaging marker as part of “cleanup.”

---

## Empty contract / ADR set

- `engineering/adr/` — empty
- `engineering/contracts/openapi/`, `asyncapi/`, `schemas/` — empty
- No OpenAPI/AsyncAPI/schema names a cleanup, zip-retention, or identity API

Do not invent one. Retention rule is the change-package ruling plus existing docs/tests above.

---

## Fact for the write owner

1. **Do not touch** `README.md`, `CHANGELOG.md`, `AGENTS.md`, `packages/README.md`, `VERSION`, `QUICKSTART.md`, runbooks, or CI-template README.
2. Keep **all** CHANGELOG `## 2.0.0`–`## 2.0.10` sections and **all** `packages/README.md` zip rows if old zips stay (they must stay).
3. **No** `.github/workflows`. **No** `pyproject.toml` / `requirements.txt` / `setup.py`.
4. Path-limited dirt only: restore named sibling `state.json`; delete untracked sibling evidence. Leave this change package uncommitted.

This report is analysis only. It does not authorize deletes or commits.
