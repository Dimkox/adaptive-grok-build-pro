# Analysis — architect (smallest 2.0.10 last mile)

Change: `20260816-system-reminder-background-subagent-01a00cea-6b8-70b284`  
Route: `70b284082a16` · intent=`release` · risk=`high` · `write_agent`=`null` · reviews=`security_reviewer`+`release_reviewer` · gates=`scope_and_design_approval`,`production_action_approval` (satisfied) · evidence=`verification`,`security_review`,`release_review`

Read-only design. This agent does not edit product files, does not `git push` / `git tag` / `gh release`, and does not read `.env`.

Loaded `/adaptive-delivery` from `.grok/skills/adaptive-delivery/SKILL.md` and `/release-readiness` from `.grok/skills/release-readiness/SKILL.md`. This agent is in `allowed_agents`.

Narrow question: smallest 2.0.10 last mile. Pin tests first, then identity, pack only after `VERSION` is `2.0.10`, `grok_verify --mode pr`, then independent reviews, then commit/tag/push/`gh release create`. Do not retag `v2.0.9`. No GitHub Actions. No `pyproject.toml`. No force-push.

---

## Ruling (one screen)

**Next SKU is 2.0.10 because `v2.0.9` already exists on `f72c0fc` and is GitHub Latest. Controller implements. Do not spawn a write agent. Do not retag `v2.0.9`.**

`AGENTS.md` §Release when green: bump `VERSION` only if the last tag already exists. Last tag exists. Identity 2.0.9 stays frozen on `f72c0fc`.

| In | Out |
| --- | --- |
| New commit after `f72c0fc` with 2.0.10 identity + zip packed **after** the bump | `git tag -f v2.0.9`; any touch of `v2.0.9` / `v2.0.8` |
| Annotated `v2.0.10` on **that** new SHA | Tag `f72c0fc` as `v2.0.10`; retag any older SKU |
| `gh release create v2.0.10 … --title "Adaptive Grok Build Pro v2.0.10"` | `gh release create v2.0.9`; `gh release edit v2.0.9`; MCP `create_release` |
| Pin tests **first** (fail), then identity, then pack | Pack while `VERSION` is still `2.0.9` (zip name + in-zip stay 2.0.9) |
| Controller executes (`git`/`gh`) | Spawn `general_implementer` / any write role (`write_agent` is null) |
| Local `python3 scripts/grok_verify.py --mode pr` | `.github/workflows/`; `pyproject.toml` / `requirements.txt` / `setup.py` |
| Path-limited add of the in-scope list + **this** change package | `git add -A`; commit other `engineering/changes/*` session evidence |
| Rollback = delete Release + `v2.0.10` tag only | Force-push; delete `v2.0.9`; rewrite `main` |

Named gates are already recorded in `evidence/human-approval.md` from «релиз сделай» plus standing Release when green. This report is design, not a second ask.

---

## 1. Current facts (inspected this wave)

| Item | Value |
| --- | --- |
| `HEAD` / `refs/heads/main` / `origin/main` | `f72c0fc2bb27de5dee67f799517f71cd678eb068` — *Release v2.0.9: published identity after v2.0.8* |
| Route `base_commit` / `base_fingerprint` | same SHA / `21107dbd…` |
| Local tags | `v2.0.0`–`v2.0.9`. **No** `refs/tags/v2.0.10` |
| Tag object `v2.0.9` | `020921e7ac069bbbabe3686c3af74678fabd9cce` (annotated). Peels to `f72c0fc`. Do not move. |
| Tag object `v2.0.8` | `695ee7918b6b21cfe5d9bd8d2497067a6a38a594`. Leave. |
| GitHub Latest | Adaptive Grok Build Pro **v2.0.9** on `f72c0fc` (package brief + human-approval). |
| `VERSION` / `__version__` / README H1 | **2.0.9** |
| Tracked 2.0.9 zip sidecar | `b9d2398ac6c4863c72476bf069d405eb2938ccefa16c39cdf9c0b9f43dfa2f4b` — **do not rebuild** |
| GHA | **none**. No `.github/workflows/`, no Dependabot, no `templates/ci/github-actions.yml` |
| Packaging markers | **absent** — no `pyproject.toml` / `requirements.txt` / `setup.py` |
| This change | `approved`. Active change pointer is this `70b284` package |
| `write_agent` | **null** — controller is the only actor who may edit identity, pack, commit, last mile |
| `deploy.py` printer | reads `VERSION` dynamically. Do not edit. Will refuse until status is `ready`/`released` + receipts exist |

A new «релиз сделай» on this SHA must not retag it.

---

## 2. In-scope file list

Same eight identity/pin surfaces as 2.0.9, plus the new runbook and the new zip pair. Leave every `v2.0.9` artifact frozen.

### 2.1 Pin first (edit; fail before identity)

| Path | Live 2.0.9 pin | 2.0.10 action |
| --- | --- | --- |
| `tests/test_structure.py` | `assertIn('2.0.9', README)`; `test_version_is_2_0_9_and_github_actions_are_absent` asserts `VERSION == '2.0.9'` | both `'2.0.10'`; **rename** the method → `test_version_is_2_0_10_and_github_actions_are_absent`. Keep GHA-absent asserts. Keep `test_changelog_2_0_6_does_not_claim_stale_latest`. Keep `test_package_version_matches_version_file` (reads live `VERSION`). Do not touch the K10 mermaid test. |
| `tests/test_manifest_package.py` | `test_included_files_and_shipped_zip_have_no_github_actions`: `version == '2.0.9'` and in-zip `VERSION == '2.0.9'` | both `'2.0.10'`. Leave the rest of the file. |

Run `python3 -m unittest tests.test_structure tests.test_manifest_package` after this edit and **before** `VERSION` changes. Expect red.

### 2.2 Then identity (edit / create)

| Path | Action |
| --- | --- |
| `VERSION` | single line `2.0.10` |
| `.grok-stack/adaptive_grok/__init__.py` | `__version__ = "2.0.10"` |
| `README.md` | H1 `# Adaptive Grok Build Pro v2.0.10`. Current-state first bullet: `Identity: **2.0.10** (\`VERSION\`, README H1). Published GitHub Release is \`v2.0.10\`.` Keep the other Current-state bullets (self-learning, no GHA, no packaging markers). **Do not edit a mermaid line.** |
| `CHANGELOG.md` | **insert** `## 2.0.10 — 2026-08-16` above `## 2.0.9`. Do **not** rewrite §2.0.9 or older. |
| `packages/README.md` | **add** row `adaptive-grok-build-pro-v2.0.10.zip` / `2.0.10`. Keep 2.0.0–2.0.9. |
| `engineering/runbooks/publish-v2.0.10.md` | **new**. Copy `publish-v2.0.9.md` shape with every `2.0.9` → `2.0.10`. Do **not** rewrite `publish-v2.0.9.md`. |

Exact new CHANGELOG section (heading + lead + three bullets; no “until a human last mile”; no “2.0.9 remains”):

```markdown
## 2.0.10 — 2026-08-16

Published identity of current main after `v2.0.9`.

- Same product surface as 2.0.9 plus this version identity
- Standing rule still: green verify → new release
- Still no GitHub Actions
```

### 2.3 Pack only after `VERSION` is `2.0.10` (create)

| Path | Action |
| --- | --- |
| `dist/RELEASE-NOTES.md` | scratch (gitignored). Overwrite with CHANGELOG **§2.0.10 only**. `--notes-file` for `gh release create`. |
| `dist/adaptive-grok-build-pro-v2.0.10.zip*` | packager default output (gitignored). |
| `packages/adaptive-grok-build-pro-v2.0.10.zip` | `cp` after pack. Tracked. |
| `packages/adaptive-grok-build-pro-v2.0.10.zip.sha256` | sibling. Tracked. |

`scripts/package_stack.py` names the zip from live `VERSION`. Packing before the bump produces `v2.0.9` again. Stop if stdout path is not `…/dist/adaptive-grok-build-pro-v2.0.10.zip`. Stop if root `MANIFEST.sha256` remains. Stop if `packages/adaptive-grok-build-pro-v2.0.9.zip.sha256` changes from `b9d2398a…`.

In-zip `adaptive-grok-build-pro/VERSION` must be `2.0.10`.

### 2.4 This change package (may commit; it is the durable 2.0.10 record)

`engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/**` including this report and later review reports.

### 2.5 Out of scope (do not edit)

| Path | Why |
| --- | --- |
| `packages/adaptive-grok-build-pro-v2.0.9.zip*` | published 2.0.9 artifact. Digest stays `b9d2398a…` |
| `engineering/runbooks/publish-v2.0.9.md` and older runbooks | frozen last-miles |
| Other `engineering/changes/*` | session evidence stays **uncommitted** |
| `decisions.md` | standing “Green verify means a new release” already covers this. The “next SKU is 2.0.9” entry is historical. Not an identity pin. |
| `AGENTS.md`, `QUICKSTART.md`, mermaid fence | no version pin / graph is frozen |
| `scripts/package_stack.py`, `scripts/grok_deploy.py`, `.grok-stack/adaptive_grok/deploy.py` | read `VERSION` dynamically |
| `pyproject.toml` / `requirements.txt` / `setup.py` | **must not exist** |
| `.github/workflows/**`, Dependabot, `templates/ci/github-actions.yml` | **must stay absent** |

---

## 3. Sequence (controller; CLI only)

Working directory: repo root. `write_agent` is null — do not spawn an implementer. Do not add GitHub Actions or `pyproject.toml` at any step. Do not `git add -A`.

### Phase A — freeze

```bash
test "$(git rev-parse --abbrev-ref HEAD)" = main
test "$(git rev-parse HEAD)" = f72c0fc2bb27de5dee67f799517f71cd678eb068
test "$(tr -d '[:space:]' < VERSION)" = 2.0.9
test ! -e pyproject.toml && test ! -e requirements.txt && test ! -e setup.py
test ! -e .github/workflows && test ! -e .github/dependabot.yml
test ! -e .grok-stack/templates/ci/github-actions.yml
git show-ref --verify --quiet refs/tags/v2.0.10; echo $?   # expect 1
git rev-parse 'v2.0.9^{}'                                 # expect f72c0fc2bb27de5dee67f799517f71cd678eb068
```

Stop if any check fails.

### Phase B — pin tests first

Edit only the two test files in §2.1. Then:

```bash
python3 -m unittest tests.test_structure tests.test_manifest_package
```

Expect **FAIL** on the four 2.0.10 asserts. If they are already green, identity leaked early — stop and inspect.

### Phase C — identity

Write the six surfaces in §2.2. Confirm:

```bash
test "$(tr -d '[:space:]' < VERSION)" = 2.0.10
test "$(python3 -c 'import sys; sys.path.insert(0,".grok-stack"); from adaptive_grok import __version__; print(__version__)')" = 2.0.10
```

### Phase D — pack (only now)

```bash
python3 - <<'PY'
from pathlib import Path
text = Path('CHANGELOG.md').read_text(encoding='utf-8')
start = text.find('## 2.0.10')
nxt = text.find('\n## ', start + 1)
section = text[start:] if nxt == -1 else text[start:nxt]
assert section.startswith('## 2.0.10')
assert 'until a human last mile' not in section
assert '2.0.9 remains' not in section
Path('dist').mkdir(exist_ok=True)
Path('dist/RELEASE-NOTES.md').write_text(section.rstrip() + '\n', encoding='utf-8')
print('wrote dist/RELEASE-NOTES.md')
PY
python3 scripts/package_stack.py
# stdout must end with dist/adaptive-grok-build-pro-v2.0.10.zip
test ! -f MANIFEST.sha256
cp dist/adaptive-grok-build-pro-v2.0.10.zip dist/adaptive-grok-build-pro-v2.0.10.zip.sha256 packages/
( cd packages && sha256sum -c adaptive-grok-build-pro-v2.0.10.zip.sha256 )
```

In-zip proof: member `adaptive-grok-build-pro/VERSION` == `2.0.10`. 2.0.9 sidecar still starts with `b9d2398a`.

`included_files()` walks the **working tree**. `engineering/changes/**` markdown is packed; `packages/*.zip` are not nested; `.grok-stack/runtime/**` is dropped. Dirty sibling change packages will land in the zip even if they stay uncommitted. That is the same shape as 2.0.9. Do not `git add` those siblings.

### Phase E — verify, then independent reviews

```bash
python3 scripts/grok_verify.py --mode pr
```

Must PASS. Then dispatch **only** `security_reviewer` and `release_reviewer` (route `review_agents`). Reports:

- `engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/evidence/security-review.md`
- `engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/evidence/release-review.md`

Review reports dirty the tree. Per `mistakes.md` (do not bind receipts to an intermediate tree): if those reports remain on disk, **re-pack once** so the tagged zip matches the ship tree, then **re-run** `python3 scripts/grok_verify.py --mode pr`. Record receipts only after the last file that will stay:

```bash
python3 scripts/grok_review.py security_review --status pass --report engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/evidence/security-review.md
python3 scripts/grok_review.py release_review --status pass --report engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/evidence/release-review.md
```

Any product edit after that invalidates all receipts.

`python3 scripts/grok_deploy.py` is a printer. It will fail until this change is `ready`/`released` and evidence is bound. Do not treat that failure as a publish blocker. Print/run the Phase F commands directly.

### Phase F — commit / tag / push / GitHub Release

Path-limited add (adjust only if a listed file was not touched):

```text
VERSION
.grok-stack/adaptive_grok/__init__.py
README.md
CHANGELOG.md
packages/README.md
packages/adaptive-grok-build-pro-v2.0.10.zip
packages/adaptive-grok-build-pro-v2.0.10.zip.sha256
tests/test_structure.py
tests/test_manifest_package.py
engineering/runbooks/publish-v2.0.10.md
engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/
```

Do **not** add other `engineering/changes/*`. Do not add `dist/`. Do not add `.grok-stack/runtime/`.

```bash
git commit -m "Release v2.0.10: published identity after v2.0.9"
git tag -a v2.0.10 -m "v2.0.10"
# fresh grok_approve.py production if PreToolUse requires it; do not reuse an expired token
git push origin main
git push origin v2.0.10
gh release create v2.0.10 \
  packages/adaptive-grok-build-pro-v2.0.10.zip \
  packages/adaptive-grok-build-pro-v2.0.10.zip.sha256 \
  --title "Adaptive Grok Build Pro v2.0.10" \
  --notes-file dist/RELEASE-NOTES.md
```

Post-checks:

```bash
git describe --tags --exact-match          # v2.0.10
git rev-parse 'v2.0.9^{}'                  # still f72c0fc2bb27de5dee67f799517f71cd678eb068
gh release view v2.0.10
gh release list                            # Latest = v2.0.10
```

No `git tag -f`. No `git push --force`. No GitHub Actions. No `pyproject.toml`.

---

## 4. Rollback

Delete the new Release and the new tag only. Do not force-push. Do not delete `v2.0.9`. GitHub Latest falls back to `v2.0.9` on `f72c0fc`.

```bash
gh release delete v2.0.10 --yes
git push origin :refs/tags/v2.0.10
git tag -d v2.0.10
```

If `main` already contains the 2.0.10 identity commit: leave it. Forward-fix is 2.0.11 on a later route. Do not rewrite published history.

Identity-only revert (if the commit is not yet pushed): `git reset --soft` is unnecessary; `git reset --hard f72c0fc` is allowed **only** while the 2.0.10 commit is local and unpushed. After `git push origin main`, hard reset is forbidden.

---

## 5. Residual risk

| Risk | Mitigation |
| --- | --- |
| Retag `v2.0.9` / tag `f72c0fc` as `v2.0.10` | Freeze checks; new annotated tag only on the **new** commit |
| Pack before `VERSION` bump | Zip name and in-zip `VERSION` stay 2.0.9; Phase D is gated on `VERSION=2.0.10` |
| `git add -A` ships sibling session evidence | Path-limited add. Other `engineering/changes/*` stays uncommitted |
| Working-tree pack embeds dirty sibling change packages | Same as 2.0.9. Zip is a live-tree snapshot; git commit is not. Do not delete other packages to “clean” the zip |
| Receipts bound before last review-report write | Re-verify after reports; record receipts last. `mistakes.md` already names this failure |
| Zip vs tagged tree drift if reviews write files after pack | One re-pack after the last staying file, then verify |
| Force-push / GHA / `pyproject.toml` | Forbidden. Existing structure tests fail if GHA or packaging markers appear |
| Reuse expired `grok_approve` production token | New short-lived approval whose reason is this 2.0.10 last mile |
| `grok_deploy.py` refuses while change is `approved` | Expected. Controller runs Phase F CLI, not the printer, until `ready` |
| Latest does not move if `gh release create` fails after tag push | Tag exists but Latest stays `v2.0.9` until the Release exists. Re-run **only** `gh release create v2.0.10` (not a second tag) |
| Controller treats this report as a second human gate | Gates are already satisfied. Proceed. |

No new services, migrations, Bitrix paths, OpenAPI, or dependencies. Smallest vertical is identity + pack + evidence + last mile.
