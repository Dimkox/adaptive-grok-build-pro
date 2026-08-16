# Analysis — repo_explorer

Change: `20260816-user-query-я-все-еще-не-вижу-файлов-из-промпта-д-ba1615`  
Route: `ba1615416da5` · write owner: `general_implementer`  
Question: Which files does the agent self-learning prompt name, and where do they actually live?

User: «я все еще не вижу файлов из промпта для агентов в корне»

Read-only map. No `.env`. No push / merge / deploy.

## One-sentence answer

The standing `AGENTS.md` self-learning bullets name `engineering/decisions.md` and `engineering/mistakes.md`; those two files exist only under `engineering/` in this repo; root `decisions.md` / `mistakes.md` do not exist; `install_into` never copies either pair into a consumer root.

## 1. Root `decisions.md` / `mistakes.md`

| Path | Exists? |
| --- | --- |
| `/home/pall/grok-projects/adaptive-grok-build-pro/decisions.md` | **No** (read returns “does not exist”) |
| `/home/pall/grok-projects/adaptive-grok-build-pro/mistakes.md` | **No** (read returns “does not exist”) |

Root listing has `AGENTS.md`, `CHANGELOG.md`, hook shims, `VERSION`, etc. No self-learning log files. `.gitignore` does not mention either name, so they are not hidden — they were never created at root.

This is why a user looking at the repo root still does not see “the files from the agent prompt.”

## 2. `engineering/decisions.md` / `engineering/mistakes.md`

| Path | Exists? | Role |
| --- | --- | --- |
| [`engineering/decisions.md`](../../../../engineering/decisions.md) | **Yes** | Dated pattern log. Header: “Patterns that paid for themselves. Each entry is at most three sentences.” Latest entry 2026-08-16 pin-after-bump. |
| [`engineering/mistakes.md`](../../../../engineering/mistakes.md) | **Yes** | Root-cause log. Header: “Root causes, not symptoms.” Latest entry 2026-08-16 authorship omission of the AGENTS.md bullets. |

First committed in `097f5c9` (v2.0.4). They are this-repo memory, not a consumer scaffold.

## 3. What the prompt actually names

### Original user quote (route `d55ce4`, still the filenames the user wants)

- `decisions.md` (no prefix)
- `mistakes.md` (no prefix)

### Current committed `AGENTS.md` first section (lines 5–6)

```5:6:AGENTS.md
- If you make a decision that turns out to be correct and worth the effort, log it in engineering/decisions.md (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in engineering/mistakes.md.
```

That `engineering/` prefix was an intentional rewrite in change `d55ce4`. Its architecture said: “Point at the `engineering/` paths so agents do not create root-level `decisions.md` / `mistakes.md`.” The current complaint is that rewrite: the user still wants the files at root, under the original names.

`CHANGELOG.md` §2.0.8 documents the prefixed names:

```7:7:CHANGELOG.md
- `AGENTS.md` starts with log-to-`engineering/decisions.md` / `engineering/mistakes.md`
```

## 4. Every product hardcode of `engineering/decisions.md` / `engineering/mistakes.md`

Searched the tree. Excluding historical change-package write-ups, the live product hits are:

| File | What it hardcodes | Kind |
| --- | --- | --- |
| [`AGENTS.md`](../../../../AGENTS.md) `:5-6` | Standing order: log to `engineering/decisions.md` / `engineering/mistakes.md` | Prompt |
| [`tests/test_structure.py`](../../../../tests/test_structure.py) `:30-31` (`test_agents_md_starts_with_self_learning`) | `assertIn('engineering/decisions.md', prefix)` and `assertIn('engineering/mistakes.md', prefix)` before `## Mandatory entrypoint` | Test lock |
| [`CHANGELOG.md`](../../../../CHANGELOG.md) `:7` | 2.0.8 bullet naming the prefixed paths | Docs |
| [`engineering/mistakes.md`](../../../../engineering/mistakes.md) `:7` | Symptom text that repeats the prefixed paths | This-repo log |

**Not hardcoded in any installer, packager, skill, agent, or runtime module:**

| Location | Result |
| --- | --- |
| `scripts/install_into.py` | No `decisions.md` / `mistakes.md` string |
| `scripts/package_stack.py` | No mention; zips whatever `included_files()` returns |
| `.grok-stack/adaptive_grok/manifest.py` | No mention; includes ordinary tree files except exclusions |
| `.grok-stack/config/managed.json` | Lists agents/skills/hooks/scripts only |
| `.grok/skills/**` (including both `adaptive-delivery` mirrors) | “decisions” means change-package `## Decisions`, not these files |
| `.agents/skills/**` | Same as `.grok/skills` |
| `.grok/agents/**` | No path |
| `docs/bitrix-local-AGENTS.md` | No self-learning text |
| `README.md`, `QUICKSTART.md` | No mention |
| `tests/test_installer.py` | No mention |
| `tests/_support.py` | Creates empty `engineering/{changes,adr,runbooks,reviews}` only |
| `.grok-stack/templates/**` | Change-package `architecture.md` has a `## Decisions` heading, not a pointer at either log |

Skills that talk about “decisions” without these filenames:

- `.grok/skills/adaptive-delivery/SKILL.md` and `.agents/skills/adaptive-delivery/SKILL.md` line 31: “Use the change package for … decisions …”
- `.grok/skills/feature-workflow/SKILL.md`: new store/framework needs an **ADR**, not `decisions.md`
- `.grok/skills/task-triage/SKILL.md`: “product decisions only the user can make”

No skill tells an agent to write `engineering/decisions.md` or root `decisions.md`.

## 5. Does `install_into` copy those logs into a consumer repo root?

**No. Not to root, and not under `engineering/` either.**

[`scripts/install_into.py`](../../../../scripts/install_into.py) copies only:

1. Everything under `MANAGED_DIRS` = `.grok`, `.agents`, `.grok-stack` (minus runtime).
2. `MANAGED_FILES` = grok scripts, root hook shims, `ruff.toml`, `bandit.yaml`, `.coveragerc`.
3. Root `AGENTS.md` **verbatim** into the consumer `AGENTS.md` managed block (`merge_agents`, lines 68–85).
4. Bitrix-only: `docs/bitrix-local-AGENTS.md` → `local/AGENTS.md` if missing.
5. Empty directories (`ENSURE`, lines 138–149):

```138:149:scripts/install_into.py
    for rel in (
        'engineering/changes',
        'engineering/adr',
        'engineering/runbooks',
        'engineering/reviews',
        'engineering/contracts/openapi',
        'engineering/contracts/asyncapi',
        'engineering/contracts/schemas',
    ):
        print(f'ENSURE {rel}')
        if not dry_run:
            (target / rel).mkdir(parents=True, exist_ok=True)
```

There is no `COPY` / `ENSURE` for:

- `decisions.md`
- `mistakes.md`
- `engineering/decisions.md`
- `engineering/mistakes.md`

`tests/test_installer.py` never asserts those four paths. `tests/_support.py` `project_copy` also does not seed them.

### Packager vs installer

`package_stack.py` → `included_files()` ships **this repo’s** `engineering/decisions.md` and `engineering/mistakes.md` inside the product zip, because they are ordinary tree files and are not in `EXCLUDED_FILES`. They sit at `adaptive-grok-build-pro/engineering/…` in the archive, not at zip-root `decisions.md` / `mistakes.md`.

A consumer that only runs `python3 scripts/install_into.py <target>` never receives those two files. They only receive an `AGENTS.md` block that *names* `engineering/decisions.md` / `engineering/mistakes.md`. After install, a consumer root still has neither `decisions.md` nor `mistakes.md`, and `engineering/` has empty scaffold dirs only.

## 6. Naming mismatch the user is hitting

| Source | Filenames |
| --- | --- |
| Original prompt the user quoted | `decisions.md`, `mistakes.md` (repo root) |
| Current `AGENTS.md` + structure test + CHANGELOG 2.0.8 | `engineering/decisions.md`, `engineering/mistakes.md` |
| Files that exist on this tree | only the `engineering/` pair |
| Files a consumer install creates | **none of the four** |
| Prior architecture (`d55ce4`) | deliberately avoided root files |

So “I still don’t see the files from the prompt in the root” is factually correct on both this product tree and any `install_into` consumer.

## 7. Impact surface if the write owner moves the logs to root

This change package already sketches the move (`tasks.md` / `test-plan.md`): fail a structure test that requires root files + root names, move the logs, leave stubs under `engineering/`, retarget `AGENTS.md`.

Must change together:

| File | Why |
| --- | --- |
| `AGENTS.md` | First-section bullets must say `decisions.md` / `mistakes.md` (no `engineering/` prefix) |
| `tests/test_structure.py` | Current `assertIn('engineering/decisions.md')` **fails** the planned test-plan (“fails if the live bullets still say `engineering/…`”). Switch to exact root names and add `is_file()` for both root logs. |
| New root `decisions.md` / `mistakes.md` | Move (not copy-only) the live logs so the user can see them at root |
| `engineering/decisions.md` / `engineering/mistakes.md` | Leave stubs that point at the root files, or the old paths become dead sinks |
| `CHANGELOG.md` §2.0.8 | Still claims the prefixed paths |
| `scripts/install_into.py` | Today a consumer still will not get root logs after the AGENTS.md rename unless the installer `COPY`s / `ENSURE`s `decisions.md` and `mistakes.md`. `merge_agents` will ship the new names; the files themselves will not appear unless this is added. |
| `tests/test_installer.py` / `tests/_support.py` | No current coverage; needed if installer starts seeding the logs |
| `engineering/mistakes.md` 2026-08-16 entry | Text still names the prefixed paths; becomes stale if that file is stubbed |

Do **not** need to edit skills, agents, `package_stack.py`, or `manifest.py` for the rename itself. `package_stack` will pick up whatever tree files exist.

Do **not** treat change-package `## Decisions` or `engineering/adr/` as substitutes. Those are different sinks (already recorded in `d55ce4`).

## Residual

- Not verified by unzipping `packages/adaptive-grok-build-pro-v2.0.8.zip`; inclusion follows `included_files()` and the files are not excluded.
- Sibling consumer trees on this machine were not re-opened in this route. Prior `d55ce4` report: consumers only had the managed `AGENTS.md` block and no log files.
- This report does not implement the move. Write owner is `general_implementer`.
