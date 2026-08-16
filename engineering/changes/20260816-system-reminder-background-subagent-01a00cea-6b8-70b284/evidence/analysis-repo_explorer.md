# Analysis — repo_explorer

Change: `20260816-system-reminder-background-subagent-01a00cea-6b8-70b284`  
Route: `70b284082a16` · write owner: **none** · intent: release · risk: high  
Question: last tag `v2.0.9` exists on `f72c0fc`. List every committed identity/pin surface that must move **2.0.9 → 2.0.10**, what to create, what stays frozen, and the last-mile commands.

Read-only. No product edit, tag, push, or `gh release` from this agent.

**Ruling: 2.0.10 because `v2.0.9` exists.** `HEAD` `f72c0fc` == `origin/main` == `v2.0.9^{}`. `AGENTS.md` §Release when green says bump `VERSION` only if the last tag already exists. Therefore the new identity is **2.0.10**. Do not retag `v2.0.9`. Do not invent `2.0.11`. No GitHub Actions. No `pyproject.toml`. No force-push.

---

## 0. Refs given for this route

| Check | Fact |
| --- | --- |
| `HEAD` / `origin/main` | `f72c0fc2bb27de5dee67f799517f71cd678eb068` |
| Last commit subject | `Release v2.0.9: published identity after v2.0.8` |
| Route `base_commit` | same SHA |
| Local tags | `v2.0.0` … **`v2.0.9`**. No `v2.0.10` |
| `v2.0.9` annotated-tag object | `020921e7ac069bbbabe3686c3af74678fabd9cce` → peels to `f72c0fc` |
| GitHub Latest (inspection start) | Adaptive Grok Build Pro **v2.0.9** on that SHA |
| `VERSION` live | still `2.0.9` (identity not bumped yet) |
| Published 2.0.9 zip digest | `b9d2398ac6c4863c72476bf069d405eb2938ccefa16c39cdf9c0b9f43dfa2f4b` |
| GHA / packaging markers | **absent** (`.github/` does not exist; no `pyproject.toml` / `requirements.txt` / `setup.py`) |
| This change | `state.json` = `approved`; `human-approval.md` authorizes 2.0.10 last mile |
| `write_agent` | **null** — analysis only; controller owns identity + last mile |

Unlike the 2.0.9 mid-wave explorer report, the eight identity files are still on 2.0.9. Nothing on disk has been rewritten to 2.0.10 except this change package’s own markdown.

---

## 1. File table

`VERSION` is source of truth. Packager default output, deploy printer, zip name, and runbook tag follow it. `__version__` is a hardcoded lock; `test_package_version_matches_version_file` fails if they diverge.

### Must edit (committed identity — eight surfaces)

| Path | On `f72c0fc` | 2.0.10 action |
| --- | --- | --- |
| `VERSION` | `2.0.9` (single line) | replace with `2.0.10` |
| `.grok-stack/adaptive_grok/__init__.py` | `__version__ = "2.0.9"` | `"2.0.10"` |
| `README.md` L1 | `# Adaptive Grok Build Pro v2.0.9` | `v2.0.10` |
| `README.md` Current state | Identity **2.0.9**; Published GitHub Release is `v2.0.9` | both **2.0.10** / `v2.0.10`. Keep the rest of the card (self-learning, no GHA, no packaging markers). Keep the K10 mermaid. |
| `CHANGELOG.md` | top is `## 2.0.9 — 2026-08-16` | **insert** `## 2.0.10 — 2026-08-16` above it. Do **not** rewrite §2.0.9 or older. |
| `packages/README.md` | last row `adaptive-grok-build-pro-v2.0.9.zip` / `2.0.9` | **add** `v2.0.10.zip` / `2.0.10`. Keep 2.0.0–2.0.9. |
| `tests/test_structure.py` | `test_readme_names_onboarding_docs_and_current_version` `assertIn('2.0.9')`; `test_version_is_2_0_9_and_github_actions_are_absent` asserts `VERSION == '2.0.9'` | both `'2.0.10'`; rename the version test → `test_version_is_2_0_10_and_github_actions_are_absent`. Keep GHA-absent asserts. Keep `test_changelog_2_0_6_does_not_claim_stale_latest`. Keep `test_package_version_matches_version_file` (reads live `VERSION`). |
| `tests/test_manifest_package.py` `test_included_files_and_shipped_zip_have_no_github_actions` | `version == '2.0.9'` and in-zip `VERSION == '2.0.9'` | both `'2.0.10'`. Leave the rest of the file. |

That is the complete **hardcoded current-identity** pin set. Eight files. Fail those asserts first, then change `VERSION` / `__version__`, then docs, then pack.

### Must create (committed)

| Path | Action |
| --- | --- |
| `engineering/runbooks/publish-v2.0.10.md` | **new**. Copy `publish-v2.0.9.md` shape with every `2.0.9` → `2.0.10`. Do **not** rewrite `publish-v2.0.9.md`. |
| `packages/adaptive-grok-build-pro-v2.0.10.zip` | pack **after** `VERSION=2.0.10` |
| `packages/adaptive-grok-build-pro-v2.0.10.zip.sha256` | sibling from packager |

### Scratch (gitignored — write, do not commit)

| Path | Action |
| --- | --- |
| `dist/RELEASE-NOTES.md` | overwrite with CHANGELOG **§2.0.10 only**. `--notes-file` for `gh release create`. |
| `dist/adaptive-grok-build-pro-v2.0.10.zip*` | packager default output |

### Frozen — still contain the string `2.0.9`, not identity pins

These mention 2.0.9 as history. **Leave them.**

| Path | Why it stays frozen |
| --- | --- |
| `CHANGELOG.md` `## 2.0.9` | frozen ship record. Insert above; do not edit the section |
| `packages/README.md` 2.0.9 row | historical artifact index. Keep. Add a 2.0.10 row under it |
| `packages/adaptive-grok-build-pro-v2.0.9.zip` | published artifact. Digest stays `b9d2398ac6c4863c72476bf069d405eb2938ccefa16c39cdf9c0b9f43dfa2f4b` |
| `packages/adaptive-grok-build-pro-v2.0.9.zip.sha256` | sibling of the frozen zip |
| `engineering/runbooks/publish-v2.0.9.md` | frozen last-mile for the **already published** tag |
| `decisions.md` «New release after an existing tag is 2.0.9» | historical 2.0.8→2.0.9 lesson. Do **not** rewrite the old heading. A new top entry may say the next SKU is 2.0.10 |
| `decisions.md` «Publish unpublished 2.0.8, do not invent 2.0.9» | older historical heading. Leave |
| `dist/adaptive-grok-build-pro-v2.0.9.zip*` / `dist/RELEASE-NOTES.md` | gitignored leftover of the 2.0.9 pack; overwrite notes, do not mutate the 2.0.9 zip in `packages/` |
| Historical `engineering/changes/**` 2.0.9 prose (06a59f, 8fe260, e4afbb, …) | do not rewrite |

### Do not treat as a version pin at all

| Path | Why |
| --- | --- |
| `AGENTS.md` §Release when green | the bump rule, not a SKU string |
| `QUICKSTART.md` | no version pin |
| `Makefile` | `package` / `deploy` / `verify` wrappers; no version |
| `scripts/package_stack.py`, `scripts/grok_deploy.py`, `.grok-stack/adaptive_grok/deploy.py` | read `VERSION` dynamically; after the bump they print 2.0.10 paths |
| `tests/test_deploy.py` / `tests/test_policy.py` | `v2.0.4` strings are fixtures |
| `tests/_support.py` | copies `VERSION` file, does not hardcode `2.0.9` |
| `examples/bitrix-module/composer.json` | example module; no product SKU |
| `engineering/runbooks/publish-v2.0.{4,5,6,7,8,9}.md` | historical. Frozen |
| `packages/adaptive-grok-build-pro-v2.0.{0–9}.zip*` | published artifacts. Leave. 2.0.8 sidecar stays `42a08851…` |
| `engineering/decisions.md` / `engineering/mistakes.md` | two-line stubs pointing at root logs |
| `pyproject.toml` / `requirements.txt` / `setup.py` | **must not exist** |
| `.github/workflows/**`, `.github/dependabot.yml`, `templates/ci/github-actions.yml` | **must stay absent** |

---

## 2. Pack after VERSION=2.0.10

`scripts/package_stack.py` → `_default_output` / `write_archive`:

1. Reads `VERSION` → `dist/adaptive-grok-build-pro-v{VERSION}.zip`.
2. Temporary root `MANIFEST.sha256`, zip with fixed time `(2026, 8, 14, 0, 0, 0)` DEFLATE 9, sibling `.sha256`, then unlink leftover root manifest.
3. `included_files()` walks the live tree; drops `.git`, `__pycache__`, `dist/`, `.grok-stack/runtime/**` (except `.gitkeep`), `*.zip`/`*.sha256`, `.env*`, keys, `err.log`. Prior `packages/*.zip` are **not** nested. `engineering/changes/**` markdown **is** packed.

```bash
python3 scripts/package_stack.py
# stdout must be …/dist/adaptive-grok-build-pro-v2.0.10.zip
test ! -f MANIFEST.sha256
cp dist/adaptive-grok-build-pro-v2.0.10.zip* packages/
( cd packages && sha256sum -c adaptive-grok-build-pro-v2.0.10.zip.sha256 )
```

Stop if the printed path still says `v2.0.9` (packed before the bump) or if `packages/adaptive-grok-build-pro-v2.0.9.zip.sha256` changed from `b9d2398a…`.

Confirm in-zip `VERSION` is `2.0.10`. Pack **before** `grok_verify --mode pr`: `test_included_files_and_shipped_zip_have_no_github_actions` only opens `packages/adaptive-grok-build-pro-v{VERSION}.zip` when that file exists.

`.grok-stack/adaptive_grok/deploy.py` `_human_commands` already prints the same last-mile list from live `VERSION`. After the bump it will emit the 2.0.10 commands below. Do not run `grok_deploy.py --record` until the change is `ready` and production approval is fresh.

---

## 3. Last-mile commands

`write_agent` is null. Humans / controller run **after** identity + zip + `python3 scripts/grok_verify.py --mode pr` PASS + independent `security_review` + `release_review` receipts on the tree that will be tagged:

```text
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.10.zip* packages/
git tag -a v2.0.10 -m "v2.0.10"
git push origin main
git push origin v2.0.10
gh release create v2.0.10 packages/adaptive-grok-build-pro-v2.0.10.zip packages/adaptive-grok-build-pro-v2.0.10.zip.sha256 --title "Adaptive Grok Build Pro v2.0.10" --notes-file dist/RELEASE-NOTES.md
```

Rollback (this package `rollback.md`):

```text
gh release delete v2.0.10 --yes
git push origin :refs/tags/v2.0.10
git tag -d v2.0.10
```

Latest then falls back to `v2.0.9` on `f72c0fc`. Never `git tag -f v2.0.9`. Never delete `v2.0.9`. Never force-push.

`git push` / `git tag` / `gh release create` are `PRODUCTION_INVOCATIONS`. Mint a fresh `python3 scripts/grok_approve.py production --reason "…"` row immediately before the last mile. Do not reuse expired 2.0.9 tokens.

---

## 4. Controller checklist

1. Fail the pins first: the two hardcoded `'2.0.9'` asserts in `tests/test_structure.py` and the two in `tests/test_manifest_package.py` (and the `test_version_is_2_0_9_…` name).
2. Set `VERSION` to `2.0.10` and `__version__ = "2.0.10"`.
3. README H1 + Current state → `v2.0.10`. Insert CHANGELOG `## 2.0.10` (leave `## 2.0.9`). Add `packages/README.md` 2.0.10 row.
4. Create `engineering/runbooks/publish-v2.0.10.md`. Do not edit `publish-v2.0.9.md`.
5. Overwrite scratch `dist/RELEASE-NOTES.md` with §2.0.10 only.
6. **Then** pack. Confirm no root `MANIFEST.sha256`. Confirm 2.0.9 sidecar is still `b9d2398a…`. Confirm in-zip `VERSION` is `2.0.10`.
7. Optional: append a ≤3-sentence `decisions.md` top entry (pattern: next SKU after an existing tag is 2.0.10). Do not rewrite the 2.0.9 heading.
8. Path-limited `git add` of the identity set + this change package. Do not `git add -A`. Do not stage `dist/` or `.grok-stack/runtime/`. Other session `engineering/changes/*` stays uncommitted.
9. Commit: `Release v2.0.10`.
10. After last file: `python3 scripts/grok_verify.py --mode pr`, then `security_reviewer` + `release_reviewer`, then mint production approval and run `publish-v2.0.10.md`.
