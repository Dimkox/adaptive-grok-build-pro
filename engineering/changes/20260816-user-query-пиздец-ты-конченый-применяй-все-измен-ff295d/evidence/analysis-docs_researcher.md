# Docs research — leftover packages vs later shipped outcomes; unique review copies

Route: `ff295dada3ef`. Change: `20260816-user-query-пиздец-ты-конченый-применяй-все-измен-ff295d`.

Question: which leftover change packages are obsolete because a later commit already shipped their outcome (2.0.6 / 2.0.7 / 2.0.8, root logs, K10 README)? Which evidence is still the only copy of a completed review?

Read-only. No APIs invented. No `.env`. No push / merge / deploy.

## Sources

- This change package (`brief.md`, `requirements.md`, `architecture.md`, `release.md`)
- `.grok/skills/adaptive-delivery/SKILL.md`, `.grok/skills/feature-workflow/SKILL.md`
- `AGENTS.md` first rule + SoT order; root `decisions.md` / `mistakes.md`; `engineering/` stubs
- `CHANGELOG.md` §§2.0.6–2.0.8; `VERSION` (`2.0.8`); `README.md` K10 mermaid
- `engineering/runbooks/publish-v2.0.{6,7,8}.md`
- `engineering/adr/` (empty); `engineering/reviews/` (absent); `engineering/contracts/{openapi,asyncapi,schemas}/` (empty)
- `.git/HEAD`, `.git/refs/heads/main`, `.git/refs/remotes/origin/main`, `.git/logs/HEAD`
- GitHub tree of `engineering/changes/` at `7152b75` (same SHA as local `main` / `origin/main`)
- GitHub evidence listings at `7152b75` for `5be23b`, `2929c0`, `3c1039`, `ec0388`, `37141f`, `a13da8`, `ba1615`, `ad4090`
- Leftover package briefs / reviews / implementations listed below
- Prior leftover inventories: `04ae05` `analysis-repo_explorer.md`, `2f9f5d` `analysis-repo_explorer.md`, `5be23b` `implementation.md`

No ADR or contract names leftover-package retention. Adaptive-delivery stores human-readable reviews in the change package; machine receipts live under `.grok-stack/runtime/receipts/` and are not a second copy of the report text.

---

## Verdict

**HEAD and `origin/main` are both `7152b75b610bada0ecc7468752900ab1515324f1`** (*Document root agent logs and complete K10 stack graph in README*). Product identity is **2.0.8**. Root `decisions.md` / `mistakes.md` exist. README mermaid is K10 (10 nodes, 45 `---` edges) and names those logs.

| Leftover package | Outcome already shipped by | Unique completed review on disk? | Dispose |
| --- | --- | --- | --- |
| `39b13f` | `e75f3a1` (2.0.6 GHA ban) | **No** (analysis only) | **DELETE** whole untracked dir |
| `864726` | `e75f3a1` + later 2.0.7/2.0.8 (not tag of `549f29d`) | **No** (analysis + `human-approval.md` only) | **DELETE** whole untracked dir |
| `0f3d94` | `7152b75` (K10 README + named root logs) | **No** (analysis only) | **DELETE** whole untracked dir |
| `2a31f5` | `7152b75` already on `origin/main` | **No** (analysis only) | **DELETE** whole untracked dir |
| `04ae05` | `7152b75` already on `origin/main` | **No** (analysis only) | **DELETE** whole untracked dir |
| `b625b4` | 2.0.6 card edit already live; Latest later became 2.0.7+ | **Yes** — `release-review.md`, `security-review.md` | Outcome obsolete. **Do not delete the two reviews** (only copy). This package is **not** on `7152b75`. |
| `2f9f5d` | `7152b75` already on `origin/main` | **Yes** — `release-review.md`, `security-review.md` | Work obsolete. **KEEP** the last-mile review record. |
| `d55ce4` | `22762a77` (2.0.8 self-learning) | **Yes** — whole package, including `code-review.md` + `test-review.md` | Product obsolete to re-do. **KEEP** (never on origin). |

**Only copies of completed reviews** (absent from GitHub `7152b75`; present only as leftover working-tree files):

| Path | Review | Of what |
| --- | --- | --- |
| `…/5be23b/evidence/code-review.md` | code **PASS** | `e75f3a1` GHA ban |
| `…/5be23b/evidence/test-review.md` | test **PASS** | same |
| `…/2929c0/evidence/release-review.md` | release **PASS** / GO | `02376cc` v2.0.7 last mile |
| `…/2929c0/evidence/security-review.md` | security **PASS** | same |
| `…/3c1039/evidence/code-review.md` | code **PASS** | `11da31a` leftover 2.0.6 product fixes |
| `…/3c1039/evidence/test-review.md` | test **PASS** | same |
| `…/ec0388/evidence/code-review.md` | code **PASS** | `549f29d` 2.0.6 quality contour |
| `…/ec0388/evidence/test-review.md` | test **PASS** | same |
| `…/37141f/evidence/code-review.md` | code **PASS** | `22762a77` 2.0.8 identity |
| `…/a13da8/evidence/code-review.md` | code **PASS** | `7152b75` K10 + root logs |
| `…/a13da8/evidence/test-review.md` | test **PASS** | same |
| `…/d55ce4/evidence/code-review.md` | code **PASS** | AGENTS.md self-learning restore (later packed as 2.0.8) |
| `…/d55ce4/evidence/test-review.md` | test **PASS** | same |
| `…/2f9f5d/evidence/release-review.md` | release **PASS** / GO | push of unpublished `7152b75` |
| `…/2f9f5d/evidence/security-review.md` | security **PASS** | same |
| `…/b625b4/evidence/release-review.md` | release **PASS** | `gh release edit` of v2.0.6 title/notes |
| `…/b625b4/evidence/security-review.md` | security **PASS** | same |
| `…/ad4090/evidence/code-review.md` | code | 2.0.5 ship extras |
| `…/ad4090/evidence/test-review.md` | test | same |
| `…/ad4090/evidence/code-review-merge.md` | code (merge wave) | same |
| `…/ad4090/evidence/test-review-merge.md` | test (merge wave) | same |

`ba1615` `code-review.md` and `test-review.md` are **already on `7152b75`**. They are not leftover-only copies.

This change’s `brief.md` DELETE list (`39b13f`, `864726`, `b625b4`, `0f3d94`, `2a31f5`, `04ae05`) matches the obsolete-outcome set **except `b625b4`**, which still holds the only completed reviews of the v2.0.6 card edit.

---

## 1. What later commits already shipped

`.git/logs/HEAD` then `.git/refs/heads/main` == `.git/refs/remotes/origin/main` == `7152b75`.

| Commit | Subject | Outcome named in the question |
| --- | --- | --- |
| `549f29d` | Release v2.0.6: ruff, bandit, coverage, dependabot | **2.0.6** quality contour (`ec0388`) |
| `e75f3a1` | Release v2.0.6: ban GitHub Actions, rebuild zip | **2.0.6** without GHA (`9fd274` / `5be23b`) |
| `11da31a` | Fix 2.0.6 leftovers: installer configs, deploy title, stale notes | leftover 2.0.6 product bugs (`3c1039`); later folded into 2.0.7 |
| `02376cc` | Release v2.0.7: leftover 2.0.6 fixes as a published identity | **2.0.7** (`2929c0`) |
| `22762a77` | Release v2.0.8: AGENTS.md self-learning first, rebuild zip | **2.0.8** (`37141f`; product of `d55ce4`) |
| `7152b75` | Document root agent logs and complete K10 stack graph in README | **root logs** + **K10 README** (`ba1615` + `a13da8`) |

Standing product at that tip (`CHANGELOG.md`, `VERSION`, `README.md`):

- 2.0.6: Ruff / Bandit / coverage 74 / no GHA
- 2.0.7: installer copies quality configs; deploy `--title`; unlink leftover root `MANIFEST.sha256`; `__version__` matches `VERSION`; Stop hook warns
- 2.0.8: `AGENTS.md` first section is self-learning
- Root logs live at `/decisions.md` / `/mistakes.md`; `engineering/` copies are “Moved” stubs
- README caption kept; mermaid is K10 including `Contract["AGENTS.md"]`, `Decisions["decisions.md"]`, `Mistakes["mistakes.md"]`

GitHub tree of `engineering/changes/` at `7152b75` does **not** contain: `39b13f`, `864726`, `b625b4`, `0f3d94`, `2a31f5`, `2f9f5d`, `04ae05`, `d55ce4`, or this `ff295d` package.

Packages that **are** on `7152b75` (so only *extras* can be leftover): `5be23b`, `2929c0`, `3c1039`, `ec0388`, `37141f`, `a13da8`, `ba1615`, `ad4090`, `9fd274`, `cd8a96`, `ef7b14`, and earlier 20260814/15 packages.

---

## 2. Obsolete leftover packages (outcome already shipped; no unique completed review)

These whole dirs are untracked relative to `7152b75`. Deleting them does not remove a completed independent review.

### `39b13f` — Ban GHA; publish 2.0.6 without them

`brief.md` is still a stub (“Describe the observable user or business result”). `state.json` is `draft`. Evidence: four analysis reports + README. **No** `code-review` / `test-review` / `release-review` / `security-review`.

Shipped by `e75f3a1`, which already committed `9fd274` + the `5be23b` skeleton. `04ae05` `analysis-repo_explorer.md` recorded this dir as **not** on `22762a77` (raw 404). Still not on `7152b75`.

### `864726` — Publish v2.0.6 GitHub Release (tag `549f29d`)

`brief.md` wanted Latest = v2.0.6 on `549f29d`. That SHA still had Dependabot/GHA. The published 2.0.6 tag peel recorded later is `e75f3a1`. Then 2.0.7 / 2.0.8 shipped. Evidence: analysis + `human-approval.md`. **No completed review report.** `human-approval.md` is approval, not an independent review.

### `0f3d94` — “ридми в корне ты конечно обновил…”

Stub `brief.md` / `draft`. Evidence: four analysis reports. Those analyses described a **K7** README that did not name `decisions.md` / `mistakes.md`. `7152b75` already put the K10 graph and the root-log names in README. Nothing left to implement.

### `2a31f5` — CLI last mile; do not launch Bitvise GUI

`brief.md` unfinished work was “verify + push commit `7152b75`”. `origin/main` is now that SHA. Evidence: four analysis reports. **No** completed review. The Bitvise/GUI question is answered in those analyses; it is not a review receipt.

### `04ae05` — «гони» push of the root logs

`brief.md` outcome: `origin/main` contains root `decisions.md` / `mistakes.md`. That is `7152b75`. Evidence: four analysis reports only. Its own `analysis-repo_explorer.md` told the write owner **not** to commit this package together with leftover `39b13f` / `d55ce4` / `ad4090` extras.

---

## 3. Outcome obsolete, but the leftover *reviews* are the only copy

### `b625b4` — Edit GitHub Release v2.0.6 title and notes

Not on `7152b75`. `state.json` is `ready`. `release-review.md` **PASS**: Latest title Adaptive Grok Build Pro v2.0.6; notes no longer say 2.0.5 remains Latest; tag still peels to `e75f3a1`. `security-review.md` **PASS**: card-only `gh release edit`; no retag / new zip / GHA.

The *work* is done and later superseded as Latest by v2.0.7 (`02376cc`) then unpublished 2.0.8/`7152b75` docs. There is **no** second copy of these two review files on origin or under `engineering/reviews/`. This package’s DELETE listing in `brief.md` would drop the only completed reviews of that card edit.

### `2f9f5d` — Push unpublished `7152b75`

Not on `7152b75` (written after that commit). `release-review.md` **PASS** / **GO** to HTTPS CLI push of `7152b75` only (no tag, no GitHub Release). `security-review.md` **PASS** for the same last mile. `origin/main` now equals that SHA, so the push work is finished. These two files plus `human-approval.md` are the last-mile record. Matches this package’s KEEP list.

### `d55ce4` — Restore AGENTS.md self-learning first

Whole package **not** on `7152b75` (`04ae05` already recorded raw 404 on `22762a77`). Product outcome shipped in `22762a77` (CHANGELOG 2.0.8; `AGENTS.md` first `##` is Agent self-learning). `code-review.md` and `test-review.md` are **PASS** and exist only here. Keep the directory; do not re-implement.

---

## 4. Packages already on `7152b75` — leftover *extras* that are the only review copies

Compared local `evidence/` to the GitHub listing at `7152b75`. Origin kept analysis + implementation (or human-approval) and **dropped the post-commit reviews**.

| Package on HEAD | On `7152b75` evidence | Leftover extras that are completed reviews |
| --- | --- | --- |
| `5be23b` (2.0.6 GHA ban) | analysis-*, `human-approval.md`, README | `code-review.md`, `test-review.md` (also leftover `implementation.md`, written after `e75f3a1`) |
| `2929c0` (publish 2.0.7) | analysis-*, `human-approval.md`, README | `release-review.md`, `security-review.md` |
| `3c1039` (2.0.6 leftover bugs → `11da31a`) | `analysis-repo_explorer.md`, `implementation.md`, README | `code-review.md`, `test-review.md` |
| `ec0388` (2.0.6 quality) | analysis-*, `implementation.md`, `coverage-baseline.md`, `ruff-first-run.md`, README | `code-review.md`, `test-review.md` |
| `37141f` (2.0.8 rebuild) | `analysis-repo_explorer.md`, `implementation.md`, README | `code-review.md` (no leftover `test-review.md` exists) |
| `a13da8` (K10 + root logs) | analysis-*, `implementation.md`, README | `code-review.md`, `test-review.md` |
| `ad4090` (2.0.5 publish) | analysis (non-merge), `*-continue.md`, `human-approval.md`, README | `code-review.md`, `test-review.md`, `code-review-merge.md`, `test-review-merge.md` (plus `*-merge.md` analyses and `implementation.md`) |

`ba1615` on `7152b75` **already includes** `code-review.md` and `test-review.md`. Local listing matches origin. Not a unique leftover copy. “If still dirty” in this brief is only relevant if the working copies differ in content from HEAD; the reviews themselves are already shipped.

`9fd274` is on `7152b75` and has no completed review files locally (analysis + `human-approval.md` + `implementation.md` only).

`engineering/reviews/` does not exist. Runtime receipts under `.grok-stack/runtime/receipts/{5be23b16d59f,2929c09b96b5,3c10395cf76e,ec0388060302,37141fbe6302,a13da8f96b5a,2f9f5d5bc202,b625b4f012f6,…}` are fingerprint JSON, not the human-readable reports.

---

## 5. What is *not* leftover / not obsolete

- This `ff295d` package is the active cleanup; it is not a superseded 2.0.6–2.0.8 / K10 draft.
- Tracked HEAD copies of `5be23b`, `2929c0`, `3c1039`, `ec0388`, `37141f`, `a13da8`, `ba1615`, `ad4090`, `9fd274`, `cd8a96` stay. Architecture in this change: if a DELETE candidate has tracked files, leave the HEAD copy; only remove untracked extras or a wholly untracked dir.
- No VERSION bump, tag, or GitHub Release is required for this paperwork commit (`release.md`, `VERSION` stays 2.0.8).
- Empty `engineering/adr/` and empty contracts do not add a retention API.

---

## Fact for the write owner

1. **DELETE whole untracked dirs** (outcome shipped; no unique completed review): `39b13f`, `864726`, `0f3d94`, `2a31f5`, `04ae05`.
2. **KEEP leftover review extras** on already-tracked packages: `5be23b` code+test; `2929c0` release+security; `3c1039` code+test; `ec0388` code+test; `37141f` code; `a13da8` code+test; `ad4090` code/test + merge reviews.
3. **KEEP whole leftover packages that hold unique reviews**: `d55ce4` (2.0.8 self-learning reviews), `2f9f5d` (last-mile GO for `7152b75`).
4. **`b625b4` is outcome-obsolete but review-unique.** Do not `rm -rf` it without first keeping `evidence/release-review.md` and `evidence/security-review.md`. Those are the only completed reviews of the v2.0.6 title/notes edit.
5. **`ba1615` reviews are already on `7152b75`.** Do not treat them as the only copy.
6. Path-limited `git add` of keepers + this package. No `git add -A`. No identity bump.

This report is analysis only. It does not authorize deletes or commits.
