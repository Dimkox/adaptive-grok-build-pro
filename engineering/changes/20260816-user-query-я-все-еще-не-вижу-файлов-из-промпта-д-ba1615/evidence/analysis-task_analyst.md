# Analysis — task_analyst

Change: `20260816-user-query-я-все-еще-не-вижу-файлов-из-промпта-д-ba1615`  
Route: `ba1615416da5` · intent=`feature` · risk=`low` · write=`general_implementer`  
Reviews after implementation: `code_reviewer` + `test_reviewer`  
Evidence kinds: `verification`, `code_review`, `test_review`  
Human gates on this route: none  
Narrow question: **What is the acceptance criteria for putting the agent-prompt log files in the repo root?**

Read-only. No application-code edits. No `.env`. No push / tag / merge / deploy.

---

## Ruling (one screen)

The original agent prompt named the exact filenames `decisions.md` and `mistakes.md`. The user is looking at the **repo root** and still does not see them.

d55ce4 / 37141f restored the self-learning *rule* but pointed it at `engineering/decisions.md` and `engineering/mistakes.md` on purpose (“so agents do not create root-level files”). That was the wrong sink relative to the prompt the user keeps quoting. The logs exist; they are in the wrong directory.

- **In:** create root `decisions.md` and `mistakes.md`; move every existing entry into them; retarget `AGENTS.md` first section to those **root** names (not `engineering/`); lock the root names in `tests/test_structure.py`; keep `VERSION` at `2.0.8` unless `v2.0.8` is already a published tag/release.
- **Out:** installer seed for consumers; rewrite of historical change packages; GitHub tag / push / `gh release`; Bitrix; `pyproject.toml`; GitHub Actions; a 2.0.9 bump just to move two files.

Last mile remains `python3 scripts/grok_deploy.py`. This prompt does not authorize it.

---

## Current facts (do not treat as done)

| Item | Today |
| --- | --- |
| Root `decisions.md` | **Absent** (not in repo root listing) |
| Root `mistakes.md` | **Absent** |
| Live sinks | `engineering/decisions.md` (13 `##` entries) and `engineering/mistakes.md` (3 `##` entries) |
| `AGENTS.md` first `##` | `## Agent self-learning` — names `engineering/decisions.md` / `engineering/mistakes.md` |
| Structure lock | `tests/test_structure.py` `test_agents_md_starts_with_self_learning` asserts those **`engineering/`** strings in the prefix |
| `VERSION` / `__version__` | `2.0.8` |
| Local tags | `v2.0.0` … `v2.0.7` only. **No `v2.0.8` tag** |
| CHANGELOG latest | `## 2.0.8` documents log-to-`engineering/decisions.md` / `engineering/mistakes.md` |
| Installer | `install_into` does **not** copy either log (`MANAGED_FILES` / `ENSURE` dirs only) |
| Route `human_gates` | `[]` |

Original prompt filenames (d55ce4 user quote, never `engineering/`):

- log it in `decisions.md`
- record it in `mistakes.md`

---

## 1. Outcome

A person (or agent) who opens the repository root next to `AGENTS.md` sees `decisions.md` and `mistakes.md`. Agents that follow the first `AGENTS.md` section write those two root files. Every entry that already exists under `engineering/` is still present. A structure test fails if the named sinks become `engineering/` again or if the root files disappear.

---

## 2. Acceptance criteria

### 2.1 Root files exist

- [ ] **Given** the product tree root, **when** a human lists it next to `AGENTS.md`, **then** both `decisions.md` and `mistakes.md` exist as regular files (`(ROOT / 'decisions.md').is_file()` and `(ROOT / 'mistakes.md').is_file()`).
- [ ] **Given** those root files, **when** they are opened, **then** they keep the current headers and purpose:
  - `decisions.md` starts with `# Decisions` and “Patterns that paid for themselves. Each entry is at most three sentences.”
  - `mistakes.md` starts with `# Mistakes` and “Root causes, not symptoms. Record only mistakes that caused a real problem.”
- [ ] **Given** the move, **when** implementation finishes, **then** there is **one** live pair of sinks. Do not keep two living logs. Either delete `engineering/decisions.md` / `engineering/mistakes.md` or replace them with a one-line pointer to the root files. Dual-write fails this change.

### 2.2 AGENTS.md first section names the root files (not `engineering/`)

- [ ] **Given** `AGENTS.md`, **when** `##` headings are collected, **then** `headings[0]` is still `## Agent self-learning` and it still sits before `## Mandatory entrypoint`.
- [ ] **Given** the text before `## Mandatory entrypoint`, **when** an agent reads the two bullets, **then** they name the exact prompt filenames:
  - `log it in decisions.md` (pattern + why it worked, no more than 3 sentences)
  - `record it in mistakes.md` (root cause, not the symptom)
- [ ] **Given** that same prefix, **when** it is searched, **then** it does **not** contain `engineering/decisions.md` or `engineering/mistakes.md`.
- [ ] **Given** the rest of the Engineering Contract, **when** this section is retargeted, **then** no other `AGENTS.md` rule is rewritten (entrypoint, SoT order, Bitrix, verify, prohibited actions stay).

Trap: `assertIn('decisions.md', prefix)` is **true** for `engineering/decisions.md`. The lock must require the **root** phrases and **forbid** the `engineering/` paths.

### 2.3 Existing entries are not lost

Move or copy-then-delete. Do not start empty stubs.

`decisions.md` must still contain every current `##` heading, in the same order, with the same body text:

- [ ] `## 2026-08-16 — Pin tests after bump, pack after VERSION`
- [ ] `## 2026-08-16 — Never GitHub Actions`
- [ ] `## 2026-08-16 — Ruff lives in ruff.toml, not pyproject.toml`
- [ ] `## 2026-08-15 — Ten is a read-only ceiling`
- [ ] `## 2026-08-15 — Root hook shims fail-open after pull`
- [ ] `## 2026-08-15 — Commercial product, free, MIT`
- [ ] `## 2026-08-15 — MIT public, not a paid SKU`
- [ ] `## 2026-08-15 — SubagentStop must emit empty JSON`
- [ ] `## 2026-08-15 — Unwrap one `-c` layer; reuse follow-ups only if open and same session`
- [ ] `## 2026-08-14 — Match production side-effects as argv prefixes`
- [ ] `## 2026-08-14 — Rematch every non-follow-up; skip child briefs`
- [ ] `## 2026-08-14 — Run unittest from verify without a packaging marker`
- [ ] `## 2026-08-14 — Bind receipts after the last change-package write`

`mistakes.md` must still contain:

- [ ] `## 2026-08-16 — Self-learning bullets never wired into AGENTS.md`
- [ ] `## 2026-08-14 — Treated a matcher bug as an environment block`
- [ ] `## 2026-08-14 — Bound verification to an intermediate tree`

- [ ] **Given** the pre-move bodies, **when** the root files are compared, **then** each of those 16 sections is present with the same wording (byte-identical bodies except the path change itself). Do not paraphrase, merge, or drop entries.
- [ ] A new entry for *this* relocation is optional and must not replace any of the 16.

### 2.4 Structure test locks the root names

Failing test first. Same file: `tests/test_structure.py`.

- [ ] **Given** current `AGENTS.md` (still names `engineering/…`), **when** the updated test runs, **then** it is **red** before the product edit.
- [ ] **Given** the updated `test_agents_md_starts_with_self_learning`, **when** it inspects the prefix before `## Mandatory entrypoint`, **then** it asserts:
  - `headings[0] == '## Agent self-learning'`
  - `'log it in decisions.md'` in prefix
  - `'record it in mistakes.md'` in prefix
  - `'engineering/decisions.md'` **not** in prefix
  - `'engineering/mistakes.md'` **not** in prefix
  - existing wording locks stay: `worth the effort`, `no more than 3 sentences`, `root cause (not the symptom)`
- [ ] **Given** `test_required_files_exist` (or an adjacent existence assert), **when** it runs, **then** it requires root `decisions.md` and `mistakes.md` as files.
- [ ] **Given** a regression that puts `engineering/decisions.md` back into the first section, **when** unittest runs, **then** that test fails even though the substring `decisions.md` is still present.
- [ ] Existing structure tests stay green (`test_version_is_2_0_8_…` still expects `2.0.8` unless §2.5 forces a bump).

### 2.5 No version bump unless required

Required only if implement-time evidence shows `v2.0.8` is already a **published** identity (local or origin tag `v2.0.8`, or GitHub Release `v2.0.8`). At analysis time: local tags stop at `v2.0.7`; 37141f recorded GitHub Latest as `v2.0.7`; `VERSION` is already `2.0.8`.

- [ ] **Given** no published `v2.0.8` tag/release, **when** this change lands, **then** `VERSION` and `__version__` stay `2.0.8`. Do **not** open `2.0.9`. Do **not** retarget `test_version_is_2_0_8_and_github_actions_are_absent` or the manifest `2.0.8` pins.
- [ ] **Given** that unpublished-2.0.8 case, **when** `CHANGELOG.md` §2.0.8 is read, **then** the self-learning bullet is amended in place to log-to-`decisions.md` / `mistakes.md` (root). Older `## 2.0.7` and below are not rewritten.
- [ ] **Given** a published `v2.0.8` *is* found at implement time, **when** the path move still ships, **then** identity becomes `2.0.9` on every pin surface (`VERSION`, `__version__`, README H1, CHANGELOG new top section, package zip name, structure/manifest pins). That is the only bump this change may make.
- [ ] **Given** either case, **when** this route closes, **then** agents have not run `git tag`, `git push`, or `gh release create`.

Rebuilding `packages/adaptive-grok-build-pro-v2.0.8.zip` is **not** required to satisfy “I can see the files in the root.” If the unpublished zip is rebuilt, pack **after** the move and keep the name `v2.0.8`. Do not bump just to refresh the zip.

---

## 3. Failure and edge cases

- [ ] Empty root stubs that drop the 16 headings fail §2.3.
- [ ] Copying to root and leaving full living copies under `engineering/` fails §2.1 (two sinks).
- [ ] Changing only `AGENTS.md` and not creating the root files fails §2.1 (user still sees nothing).
- [ ] Changing only the files and leaving `AGENTS.md` / the structure test on `engineering/` fails §2.2 and §2.4 (next rewrite puts them back).
- [ ] `assertIn('decisions.md')` without forbidding `engineering/decisions.md` fails §2.4 (false green).
- [ ] Bumping to 2.0.9 while `v2.0.8` is unpublished fails §2.5.
- [ ] Leaving `VERSION` at 2.0.8 while a published `v2.0.8` already exists fails §2.5 (amend a released identity).
- [ ] Historical change-package text that still says `engineering/decisions.md` is **not** a failure. Those packages are closed evidence. Do not mass-edit them.

---

## 4. Out of scope

- Installer `ENSURE` / seed of empty root logs in consumer trees (`install_into` still does not copy them; same as today’s `engineering/` copies).
- Updating `.agents/skills/**` or every agent `.toml`. The standing contract is `AGENTS.md` + the structure test.
- Rewriting d55ce4 / 37141f briefs, reviews, or other change packages.
- Publish, tag, push, merge, deploy, GitHub Actions, Dependabot, `pyproject.toml` / `requirements.txt` / `setup.py`.
- Bitrix core or Bitrix-local overlay.
- Opening 2.1.0.

---

## 5. Test plan (for the write owner)

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Updated self-learning test is red on current `AGENTS.md` (`engineering/` still in prefix) | failing `test_agents_md_starts_with_self_learning` |
| P0 | After the move: root files exist; prefix names `decisions.md` / `mistakes.md`; prefix rejects `engineering/` | green `tests/test_structure.py` |
| P0 | All 13 decision headings + 3 mistake headings still in the root files | review of the moved files, or a one-shot characterization assert |
| P1 | `VERSION` still `2.0.8` unless the published-tag gate trips | `test_version_is_2_0_8_…` unchanged by default |
| P1 | Full `python-unittest` still green; no packaging marker added | `python3 scripts/grok_verify.py --mode pr` |

Manual: list the repo root and confirm `decisions.md` and `mistakes.md` sit beside `AGENTS.md`.

---

## 6. Constraints

- Backward compatibility: additive path move + AGENTS retarget. Consumer `AGENTS.md` updates only on re-install (`merge_agents` copies root `AGENTS.md` verbatim).
- Data: do not lose log history. Pointers under `engineering/` are allowed; empty replacements are not.
- Operational: no production mutation. No named human gate; proceed after this bounded ruling.
- Identity: default keep `2.0.8`. Bump only if `v2.0.8` is already published.

---

## 7. Suggested write-owner slice

1. Flip `test_agents_md_starts_with_self_learning` (+ existence asserts) to root names; confirm red.
2. Create root `decisions.md` / `mistakes.md` with the current `engineering/` contents; retire the living `engineering/` copies.
3. Edit the two `AGENTS.md` bullets to `decisions.md` / `mistakes.md`.
4. Amend CHANGELOG §2.0.8 (or add §2.0.9 only if the publish gate trips).
5. Run focused structure tests, then `python3 scripts/grok_verify.py --mode pr`.
6. Transition the change package to `ready` **before** recording verification / reviews.
