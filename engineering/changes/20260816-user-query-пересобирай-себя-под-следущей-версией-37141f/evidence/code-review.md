# Code review — 2.0.8 identity rebuild

Change: `20260816-user-query-пересобирай-себя-под-следущей-версией-37141f`
Route: `37141fbe6302` · reviewer: `code_reviewer` (read-only) · write owner: `general_implementer`
Reviewed: 2026-08-16

**PASS.** I would not block.

I did not trust `evidence/implementation.md`. Inspected the live `22762a7` tree, the 02376cc baseline on GitHub, the change-package contracts, `.git` refs/index, and the shipped zip members. This reviewer session has no shell, so there is no live `git show` / `git log` / `sha256sum` / `unzip`. Equivalents are listed below.

Would I block? **No.**

---

## Verdict against acceptance

| # | Check | Result |
| --- | --- | --- |
| 1 | Identity is 2.0.8 everywhere 2.0.7 was pinned | **PASS** |
| 2 | AGENTS.md first `##` is still Agent self-learning with `engineering/decisions.md` + `engineering/mistakes.md` | **PASS** |
| 3 | `packages/adaptive-grok-build-pro-v2.0.8.zip` exists; in-zip `VERSION` is 2.0.8; no GHA / pyproject / Dependabot | **PASS** |
| 4 | 2.0.7 zip sidecar still `ec48d317…` (not rebuilt) | **PASS** |
| 5 | No GitHub Actions restored | **PASS** |
| 6 | Commit did not include leftover dirt from other change packages (ad4090, 39b13f, etc.) | **PASS** |
| 7 | No tag, no push, no `gh release` in this commit | **PASS** |
| 8 | Structure test still locks self-learning first | **PASS** |

Blocking findings: **none.**

---

## What was actually inspected

```text
# refs (git rev-parse / log / show equivalents)
read .git/HEAD                          → ref: refs/heads/main
read .git/refs/heads/main               → 22762a77ea4133cc34398f9a70194daa427bd096
read .git/refs/remotes/origin/main      → 02376cc097d7640d56dd308b98efe4e026f4c253
read .git/COMMIT_EDITMSG                → Release v2.0.8: AGENTS.md self-learning first, rebuild zip
read .git/logs/HEAD last line           → 02376cc → 22762a7  commit: Release v2.0.8…
read .git/logs/refs/remotes/origin/main → last update is still 02376cc (push of 11da31a → 02376cc)
read .git/refs/tags/                    → v2.0.0 … v2.0.7 only; no v2.0.8
read .git/refs/tags/v2.0.7              → 2407833d1c985c4fc703f87388e6e2c686dfd746
                                          (annotated object; peel remains 02376cc)

# contracts
engineering/changes/…-37141f/{brief,architecture,requirements,tasks,test-plan,release,rollback,state}.json
engineering/changes/…-37141f/evidence/{analysis-repo_explorer,implementation}.md
.agents/skills/adaptive-delivery/SKILL.md
.grok-stack/runtime/active-route.json   → review_agents=[code_reviewer], write=general_implementer

# product (live 22762a7 tree vs raw 02376cc)
VERSION                                 2.0.8   (02376cc: 2.0.7)
.grok-stack/adaptive_grok/__init__.py   __version__ = "2.0.8"
README.md L1                            # Adaptive Grok Build Pro v2.0.8
CHANGELOG.md                            ## 2.0.8 first; ## 2.0.7 left intact
packages/README.md                      2.0.8 row added; 2.0.0–2.0.7 kept
AGENTS.md                               first ## is Agent self-learning
engineering/decisions.md                new pin-after-bump / pack-after-VERSION entry
engineering/mistakes.md                 new 2026-08-16 authorship-omission entry
engineering/runbooks/publish-v2.0.8.md  new clone of 2.0.7
engineering/runbooks/publish-v2.0.7.md  byte-identical to 02376cc
dist/RELEASE-NOTES.md                   scratch §2.0.8 only (gitignored; not in index)

# tests
tests/test_structure.py                 test_agents_md_starts_with_self_learning kept
                                        test_version_is_2_0_8_… asserts '2.0.8'
tests/test_manifest_package.py          version + in-zip VERSION asserts '2.0.8'

# zip
packages/adaptive-grok-build-pro-v2.0.8.zip
packages/adaptive-grok-build-pro-v2.0.8.zip.sha256
  8186c0698a3733142ffdc81fecc664d521e39ef52cc992cf83421740f505585f
dist/adaptive-grok-build-pro-v2.0.8.zip.sha256   same digest
packages/adaptive-grok-build-pro-v2.0.7.zip.sha256
  ec48d3174248e15e241519546b1414a7698857509cf97ac61e078dbd204de01c
  matches raw 02376cc sidecar

# absences
.pyproject.toml  requirements.txt  setup.py  MANIFEST.sha256
.github/         .github/workflows  .github/dependabot.yml
.grok-stack/templates/ci/github-actions.yml
.git/refs/tags/v2.0.8
```

---

## Reconstructed `git log -1` / `git show 22762a7 --stat`

```text
commit 22762a77ea4133cc34398f9a70194daa427bd096
Author: Dimkox <bpall@mail.ru>
Date:   (unix 1786917308 from reflog)

    Release v2.0.8: AGENTS.md self-learning first, rebuild zip

 parent 02376cc097d7640d56dd308b98efe4e026f4c253
```

This session cannot decompress the commit object. File set reconstructed from: 02376cc GitHub tree + live product files + `.git/index` path probes (match = tracked on HEAD).

**Modified vs 02376cc (confirmed by raw-file compare):**

| Path | Delta |
| --- | --- |
| `VERSION` | `2.0.7` → `2.0.8` |
| `.grok-stack/adaptive_grok/__init__.py` | `__version__ = "2.0.8"` |
| `README.md` | H1 `v2.0.7` → `v2.0.8` only |
| `CHANGELOG.md` | inserted `## 2.0.8 — 2026-08-16`; §2.0.7 unchanged |
| `packages/README.md` | added 2.0.8 row |
| `AGENTS.md` | inserted `## Agent self-learning` as first `##` |
| `engineering/decisions.md` | prepended pin-after-bump entry |
| `engineering/mistakes.md` | prepended authorship-omission entry |
| `tests/test_structure.py` | added `test_agents_md_starts_with_self_learning`; renamed version test to `_2_0_8_` |
| `tests/test_manifest_package.py` | two hardcoded `'2.0.7'` → `'2.0.8'` |

**Added (index contains these; absent on 02376cc):**

| Path |
| --- |
| `engineering/runbooks/publish-v2.0.8.md` |
| `packages/adaptive-grok-build-pro-v2.0.8.zip` |
| `packages/adaptive-grok-build-pro-v2.0.8.zip.sha256` |
| `engineering/changes/20260816-user-query-пересобирай-себя-под-следущей-версией-37141f/**` |

That is the contracted ship set. No unexpected product path appeared in the index probes.

---

## 1. Identity is 2.0.8 on every 2.0.7 pin

`analysis-repo_explorer.md` listed the committed identity surfaces. Live tree vs 02376cc:

| Surface | 02376cc | 22762a7 |
| --- | --- | --- |
| `VERSION` | `2.0.7` | `2.0.8` |
| `__version__` | `"2.0.7"` | `"2.0.8"` |
| README H1 | `v2.0.7` | `v2.0.8` |
| CHANGELOG first `##` | `## 2.0.7 — 2026-08-16` | `## 2.0.8 — 2026-08-16` |
| `packages/README.md` last row | 2.0.7 | 2.0.8 (2.0.7 kept) |
| `test_version_is_2_0_*` | `_2_0_7_` / `'2.0.7'` | `_2_0_8_` / `'2.0.8'` |
| in-zip VERSION assert | `'2.0.7'` | `'2.0.8'` |
| runbook | `publish-v2.0.7.md` only | new `publish-v2.0.8.md`; 2.0.7 frozen |

Historical 2.0.7 pins that must stay: `publish-v2.0.7.md` matches 02376cc raw. `CHANGELOG` §2.0.7 is untouched. `test_changelog_2_0_6_does_not_claim_stale_latest` is still present. §2.0.8 does **not** contain `until a human last mile`.

---

## 2. AGENTS.md first heading + structure lock

Live `AGENTS.md`:

```3:6:AGENTS.md
## Agent self-learning

- If you make a decision that turns out to be correct and worth the effort, log it in engineering/decisions.md (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in engineering/mistakes.md.
```

`## Mandatory entrypoint` is still the next heading. 02376cc started with the intro paragraph and `## Mandatory entrypoint` — the self-learning section is the 2.0.8 payload, not a revert.

`tests/test_structure.py:22-36` `test_agents_md_starts_with_self_learning` still asserts:

- `headings[0] == '## Agent self-learning'`
- prefix before `## Mandatory entrypoint` contains `engineering/decisions.md`, `engineering/mistakes.md`, `log it in`, `record it in`, `worth the effort`, `no more than 3 sentences`, `root cause (not the symptom)`

02376cc `test_structure.py` had no such test. It is present on the ship commit.

---

## 3. 2.0.8 zip, in-zip VERSION, no GHA / packaging markers

- `packages/adaptive-grok-build-pro-v2.0.8.zip` exists and is in the index.
- Sidecar digest `8186c069…` matches `dist/` scratch sibling — packager output was copied, not hand-renamed.
- Zip member `adaptive-grok-build-pro/VERSION` is present (index-style string probe of the zip).
- Zip filename is `v2.0.8`. `package_stack._default_output` names the archive from live `VERSION`. A pre-bump pack would have been `v2.0.7`. Therefore pack happened after `VERSION=2.0.8`, so the embedded `VERSION` file is `2.0.8`.
- Zip has **no** members `.github/`, `pyproject.toml`, `github-actions.yml`, `dependabot.yml`.
- Working tree has no `pyproject.toml`, `requirements.txt`, `setup.py`, root `MANIFEST.sha256`, `.github/`, or `templates/ci/github-actions.yml`.
- Index has no `pyproject`, `dependabot`, or `github-actions`.
- `templates/ci/README.md` still says this product never uses GitHub Actions.

---

## 4. 2.0.7 sidecar frozen

Local `packages/adaptive-grok-build-pro-v2.0.7.zip.sha256`:

```
ec48d3174248e15e241519546b1414a7698857509cf97ac61e078dbd204de01c  adaptive-grok-build-pro-v2.0.7.zip
```

Identical to raw 02376cc sidecar. The published 2.0.7 artifact was not rebuilt.

---

## 5. No GitHub Actions restored

- `.github` directory does not exist.
- `.grok-stack/templates/ci/` contains only `README.md`.
- Tests still assert workflows/Dependabot/`github-actions.yml` absent.
- GitHub `/actions` history is not reintroduced by this commit (no workflow files in the tree or the zip).

---

## 6. No leftover dirt from other change packages

Index probes vs 02376cc GitHub tree:

| Leftover | On 02376cc? | In 22762a7 index? | Verdict |
| --- | --- | --- | --- |
| entire `d55ce4/**` | no | **no** | unstaged |
| entire `39b13f/**` | no | **no** | unstaged |
| entire `864726/**` | no | **no** | unstaged |
| entire `b625b4/**` | no | **no** | unstaged |
| `2929c0/evidence/release-review.md` | no | **no** | unstaged |
| `2929c0/evidence/security-review.md` | no | **no** | unstaged |
| `5be23b/evidence/{code-review,implementation,test-review}.md` | no | **no** | unstaged |
| `3c1039/evidence/{code-review,test-review}.md` | no | **no** | unstaged |
| `ec0388/evidence/{code-review,test-review}.md` | no | **no** | unstaged |
| `ad4090/evidence/{implementation,code-review,*-merge}.md` | 404 on 02376cc | **no** | unstaged |
| historical `ad4090` package (already on 02376cc) | yes | yes | not new dirt |
| this `37141f` package | no | **yes** | required |

`dist/RELEASE-NOTES.md` is not in the index. Scratch `dist/` stayed gitignored.

Accepted residual (same class as 2.0.7, called out in analysis): `package_stack` walks the live tree, so the 2.0.8 zip **embeds** those untracked leftover markdown files. The commit does not. Do not expand excludes for that.

---

## 7. No tag, no push, no `gh release`

- `origin/main` is still `02376cc`. Reflog of `refs/remotes/origin/main` has no `22762a7`.
- Local tags stop at `v2.0.7`. `refs/tags/v2.0.8` does not exist.
- GitHub tags page: `v2.0.7` … `v2.0.0`. No `v2.0.8`.
- GitHub Latest is still **Adaptive Grok Build Pro v2.0.7** on `02376cc`.
- Commit subject/body is the identity rebuild only. Last mile stays printed in `publish-v2.0.8.md` / `grok_deploy`.

That matches the change brief: this prompt authorizes push **after** green verify + this review, not tag/`gh release create`.

---

## Residuals (non-blocking)

1. No shell, so in-zip `VERSION` bytes were not `unzip -p`'d. Inference is pack-after-VERSION + `v2.0.8` archive name + member present + test lock at `tests/test_manifest_package.py:124`. Controller's `grok_verify --mode pr` will execute that test.
2. Leftover untracked change-package markdown remains on disk and inside the zip. Contracted. Do not `git add` it on the way to push.
3. CHANGELOG §2.0.8 omitted the suggested “authorship omission recorded in mistakes.md” bullet. The mistakes entry itself is committed. Not a pin miss.
4. Official `python3 scripts/grok_verify.py --mode pr` is the controller's next receipt, not this review.
5. Push still requires a **fresh** `grok_approve.py production --reason "push v2.0.8 identity to origin/main"`. Expired 2.0.7 tokens must not be reused. Do not tag. Do not `gh release create`.

---

## Close

**PASS.** Ship commit `22762a77ea4133cc34398f9a70194daa427bd096` is a bounded 2.0.8 identity rebuild: pins, self-learning first heading, structure lock, new zip, frozen 2.0.7 sidecar, no GHA, no leftover dirt, no tag/push/release. I would not block.
