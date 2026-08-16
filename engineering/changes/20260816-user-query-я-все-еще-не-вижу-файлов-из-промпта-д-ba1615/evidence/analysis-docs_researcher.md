# Docs research — agent self-learning file names and locations

Route: `ba1615416da5`. Change: `20260816-user-query-я-все-еще-не-вижу-файлов-из-промпта-д-ba1615`.

Question: What do current docs say the agent self-learning files are named and where they live?

User complaint: «я все еще не вижу файлов из промпта для агентов в корне» — they still do not see the files from the agent prompt at the repo root.

Read-only. No APIs invented. No `.env`. No push / merge / deploy.

## Sources

- Root `AGENTS.md` first section (`## Agent self-learning`)
- `engineering/decisions.md` (header + 2026-08-16 authorship-related entries)
- `engineering/mistakes.md` (header + 2026-08-16 “Self-learning bullets never wired”)
- `README.md` (v2.0.8)
- `CHANGELOG.md` §2.0.8
- `tests/test_structure.py` `test_agents_md_starts_with_self_learning` and `test_required_files_exist`
- This change package (`brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`, `tasks.md`)
- Prior change `20260816-user-query-скажи-мне-ебаная-пидрила-где-ты-проеб-d55ce4` (`architecture.md`, `brief.md`, `requirements.md`, `implementation.md`)
- `QUICKSTART.md`, `docs/bitrix-local-AGENTS.md`
- `.grok/skills/**` and `.agents/skills/**` (zero hits)
- `scripts/install_into.py` ENSURE list
- `.grok-stack/adaptive_grok/doctor.py` required files
- `engineering/adr/` (empty)
- Workspace root listing (no `decisions.md` / `mistakes.md` at repo root)

No OpenAPI / AsyncAPI / schema is involved. There is no ADR that names, moves, or relocates these files.

---

## Verdict

| What | Documented name and path |
| --- | --- |
| **Standing contract (`AGENTS.md`)** | `engineering/decisions.md` and `engineering/mistakes.md` |
| **Changelog 2.0.8** | same two paths |
| **Structure test lock** | same two paths must appear in `AGENTS.md` before `## Mandatory entrypoint` |
| **On-disk sinks in this repo** | those two files exist under `engineering/` and already have entries |
| **User asked for / still looking at root** | `decisions.md` and `mistakes.md` at the repository root |
| **Root files today** | **do not exist.** There is no `decisions.md` and no `mistakes.md` next to `AGENTS.md`. |

Current docs do **not** name or require root-level `decisions.md` / `mistakes.md`. The 2.0.8 restore deliberately used the `engineering/` prefix so agents would not create those root files.

---

## Documented names vs what the user asked for

The original agent-prompt pair (quoted in change `d55ce4` and implied by “файлов из промпта … в корне”) is the classic Codex/Claude wording:

- log it in **`decisions.md`**
- record it in **`mistakes.md`**

Those are **bare filenames**. A reader looking at the repo root (`AGENTS.md`, `README.md`, `CHANGELOG.md`, `VERSION`, hook shims) will not see them.

What this repository currently documents, tests, and already stores:

| Role | User prompt (root, expected) | Current docs (actual) |
| --- | --- | --- |
| Correct durable pattern | `decisions.md` | `engineering/decisions.md` |
| Root-cause mistake | `mistakes.md` | `engineering/mistakes.md` |

The names match. The **directory does not**. That is why the user still does not see the files “in the root.”

---

## 1. `AGENTS.md` first section

`AGENTS.md` title is `# Adaptive Grok Build Pro Engineering Contract`. The first `##` heading is `## Agent self-learning`, then:

- If you make a decision that turns out to be correct and worth the effort, log it in **`engineering/decisions.md`** (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in **`engineering/mistakes.md`**.

The next heading is `## Mandatory entrypoint`. There is no mention of root `decisions.md` or root `mistakes.md`.

This is the only standing instruction Grok loads for the loop. `docs/bitrix-local-AGENTS.md` has no self-learning text.

---

## 2. The log files themselves

### `engineering/decisions.md`

Header:

> Patterns that paid for themselves. Each entry is at most three sentences.

That is the live sink. It is **not** at the repo root. Current dated entries live only in this file.

### `engineering/mistakes.md`

Header:

> Root causes, not symptoms. Record only mistakes that caused a real problem.

Top entry (2026-08-16 — Self-learning bullets never wired into AGENTS.md):

- Symptom: agents already had `engineering/decisions.md` and `engineering/mistakes.md` but no standing `AGENTS.md` order to write them.
- Root cause: authorship omission when `AGENTS.md` was first written (`ca63b2d`); the log files were added later (`097f5c9`) without wiring the trigger. Not a later delete.

That entry names the sinks as **`engineering/…`**, not root files.

---

## 3. `README.md`

`README.md` is titled Adaptive Grok Build Pro v2.0.8. It does **not** mention `decisions.md`, `mistakes.md`, or self-learning.

It only says:

- change packages live under `engineering/changes/`
- install copies `engineering/` into a consumer “if empty scaffold needed”

It does not list the two log files as required root artifacts.

`QUICKSTART.md` also does not name them.

---

## 4. `CHANGELOG.md` §2.0.8

```
## 2.0.8 — 2026-08-16

Agent self-learning is the first AGENTS.md rule.

- `AGENTS.md` starts with log-to-`engineering/decisions.md` / `engineering/mistakes.md`
- Structure test locks that placement so a rewrite cannot drop it
- Still no GitHub Actions
```

The published 2.0.8 identity is the `engineering/` paths. No changelog line ever promised root `decisions.md` / `mistakes.md`.

---

## 5. `tests/test_structure.py` `test_agents_md_starts_with_self_learning`

The lock is text-in-`AGENTS.md`, not “files exist at repo root”:

- first `##` heading == `## Agent self-learning`
- before `## Mandatory entrypoint` the prefix must contain:
  - `engineering/decisions.md`
  - `engineering/mistakes.md`
  - `log it in`
  - `record it in`
  - `worth the effort`
  - `no more than 3 sentences`
  - `root cause (not the symptom)`

`test_required_files_exist` requires `AGENTS.md`, `README.md`, config, hooks, adaptive-delivery skill, `scripts/grok_route.py`, `LICENSE`. It does **not** require `decisions.md`, `mistakes.md`, or even `engineering/decisions.md` / `engineering/mistakes.md` as files.

`doctor.py` required files are the same shape: `AGENTS.md` + config + hooks + adaptive-delivery + `routing.json`. Not the self-learning sinks.

---

## 6. Prior ruling that put them under `engineering/` on purpose

Change `d55ce4` restored the missing bullets. Its architecture is explicit:

> Point at the `engineering/` paths so agents do **not** create root-level `decisions.md` / `mistakes.md`.

Its requirements name `engineering/decisions.md` and `engineering/mistakes.md`. Its brief says “Name the real paths: `engineering/decisions.md` and `engineering/mistakes.md`.” Implementation left the sinks where they already were (added in `097f5c9` / v2.0.4) and only wired `AGENTS.md` + the structure test.

That is why 2.0.8 shipped the instruction and still has nothing at the repo root.

---

## 7. What is *not* documented as the sink

| Surface | Mentions the two self-learning files? |
| --- | --- |
| `.grok/skills/**`, `.agents/skills/**` (including `adaptive-delivery`) | **No** |
| `engineering/adr/` | empty; no ADR |
| Change-package template `## Decisions` | per-change rulings, not the durable logs |
| `install_into.py` ENSURE | `engineering/{changes,adr,runbooks,reviews,contracts/*}` only. Does **not** create `engineering/decisions.md` or `engineering/mistakes.md`, and does **not** create root logs |
| `docs/bitrix-local-AGENTS.md` | no |
| This repo root | no `decisions.md`, no `mistakes.md` |

Installer residual (from `d55ce4` implementation.md): consumers do not get the sink files unless they already exist or someone copies this repo’s `engineering/*.md`. That is a separate gap from “not in the root.”

---

## 8. This change package vs current docs

This package’s `test-plan.md` already proposes the opposite of the 2.0.8 contract:

- require `(ROOT / 'decisions.md').is_file()` and `(ROOT / 'mistakes.md').is_file()`
- require the bare strings `log it in decisions.md` / `record it in mistakes.md`
- fail if the live bullets still say `engineering/decisions.md` / `engineering/mistakes.md`

That is a **proposed move**, not a fact in standing docs. Current `AGENTS.md`, CHANGELOG 2.0.8, and `test_agents_md_starts_with_self_learning` would all go red if the bullets were rewritten to the root names without also changing those three surfaces.

`brief.md` / `requirements.md` / `architecture.md` in this package are still stubs and do not yet record a user-approved ruling to relocate the files.

---

## Fact for the write owner

If the user still wants to *see* the files in the root, current docs are the reason they cannot: the documented names are **`engineering/decisions.md`** and **`engineering/mistakes.md`**, and those files already exist there. Root **`decisions.md`** / **`mistakes.md`** are what the original prompt said and what the user is looking at; they are not what 2.0.8 documents or tests.
