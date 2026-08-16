# Analysis — architect

Change: `20260816-user-query-я-все-еще-не-вижу-файлов-из-промпта-д-ba1615`  
Route: `ba1615416da5` · write owner: `general_implementer` · reviews: `code_reviewer` + `test_reviewer`  
Question: How should we place `decisions.md` and `mistakes.md` in the repo root without splitting the log into two sources of truth?

Options: **move**, **copy**, **stub pointer under `engineering/`**. Recommend one. Note installer/packager impact. Do not add `pyproject.toml`. Do not restore GitHub Actions.

Read-only. No application-code edits. No `.env`. No push / merge / deploy.

Facts from this package plus sibling analysis (`evidence/analysis-repo_explorer.md`, `evidence/analysis-docs_researcher.md`) and prior `d55ce4`.

---

## Ruling

**Recommend: stub pointer under `engineering/`.**

That means:

1. The **live logs move** (not copy) to the repo root: `decisions.md` and `mistakes.md`.
2. The old paths stay as **two-line pointers only**. They are not a second log.

| Option | Verdict | Why |
| --- | --- | --- |
| **copy** | Reject | Two append-only files. Agents write whichever path they see. Logs diverge. That *is* two sources of truth. |
| **bare move** (delete old path) | Reject | 2.0.8 `AGENTS.md`, CHANGELOG, and ~100 change-package citations still name `engineering/…`. The next agent following that muscle memory recreates a live file at the old path — a silent split. Historical links 404. |
| **stub pointer under `engineering/`** | **Choose** | Root files are what the user can see and what the original prompt named. Old path still exists so a stale writer lands on “Moved to /decisions.md” instead of starting a second log. Structure test locks the stubs so they cannot grow into a second log. |

This is the same shape the approved package already sketches (`architecture.md` steps 1–3, `requirements.md` “pointers, not a second log”). This report makes that the named option and bounds installer/packager so the write owner does not invent a second seed.

Do **not** add `pyproject.toml` / `requirements.txt` / `setup.py`.  
Do **not** restore `.github/workflows`, Dependabot, `--with-ci`, or any CI SaaS.

---

## 1. Why this is the user-visible bug

The original prompt (quoted in `d55ce4`) names bare filenames:

- log it in `decisions.md`
- record it in `mistakes.md`

`d55ce4` rewrote those to `engineering/decisions.md` / `engineering/mistakes.md` **on purpose** so agents would not create root files. 2.0.8 shipped that rewrite. The user is looking at the repo root (`AGENTS.md`, `CHANGELOG.md`, `README.md`, `QUICKSTART.md`) and still does not see the prompt files. That rewrite is the bug this change undoes.

The logs already exist and already have entries. This is a **relocation of one SoT**, not a new log and not a copy.

---

## 2. Canonical vs pointer (one SoT)

| Path | Role after this change |
| --- | --- |
| `decisions.md` | **Canonical.** Full current body of `engineering/decisions.md` (headers + every dated entry). |
| `mistakes.md` | **Canonical.** Full current body of `engineering/mistakes.md`. |
| `engineering/decisions.md` | Pointer only. No dated `## 20` entries. |
| `engineering/mistakes.md` | Pointer only. No dated `## 20` entries. |

Implement with `git mv` so blame follows, then overwrite the old paths with the stubs. Do **not** `cp` and leave the old files intact.

Exact stub text (two lines + trailing newline, nothing else):

```markdown
# Moved

Canonical log is /decisions.md. Do not append here.
```

```markdown
# Moved

Canonical log is /mistakes.md. Do not append here.
```

Do not put entries, “also see”, or a pasted summary in the stub. That would be a second log.

Do not use a symlink. Windows consumers, zip members, and Git-on-Windows treat links as a second object; a two-line markdown pointer is enough.

Do not rewrite historical change-package citations of `engineering/decisions.md`. Those documents describe the path that existed then. The stub is what a reader who follows an old link should hit.

The 2026-08-16 mistakes entry that names `engineering/…` is **historical symptom text**. After the file moves to root, leave that paragraph alone.

---

## 3. Live contract (`AGENTS.md`)

Replace only the two bullets. Keep heading order (`## Agent self-learning` first). Restore the original prompt filenames, no `engineering/` prefix:

```markdown
- If you make a decision that turns out to be correct and worth the effort, log it in decisions.md (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in mistakes.md.
```

`install_into.merge_agents` copies this file verbatim into the consumer managed block. After this edit, every new install tells agents to write **root** `decisions.md` / `mistakes.md`. That is intended.

Do **not** change `adaptive-delivery` “use the change package for … decisions”. That is per-change `architecture.md ## Decisions`, a different sink. Do not edit skills or agents in this change.

---

## 4. Tests (fail first)

Extend `tests/test_structure.py` `test_agents_md_starts_with_self_learning` (or a sibling) so the current tree is red:

1. `(ROOT / 'decisions.md').is_file()` and `(ROOT / 'mistakes.md').is_file()`.
2. Prefix before `## Mandatory entrypoint` contains `log it in decisions.md` and `record it in mistakes.md`.
3. That same prefix does **not** contain `engineering/decisions.md` or `engineering/mistakes.md`.
4. First `##` heading remains `## Agent self-learning`.
5. Stub lock: each of `engineering/decisions.md` and `engineering/mistakes.md` exists, contains `Canonical log is /`, contains `Do not append here`, has **no** line starting `## 20`, and is at most 5 lines.

Assertion (3) is what makes a leftover `engineering/` live bullet fail. Assertion (5) is what keeps the chosen option from rotting into option “copy”.

Do not put `decisions.md` into `test_required_files_exist` unless it is cheaper; the self-learning test is the right home.

Do not add installer tests unless the installer changes. It should not.

---

## 5. Installer impact

`scripts/install_into.py` today:

- does **not** mention `decisions.md` / `mistakes.md` at either path;
- `MANAGED_FILES` is scripts + hook shims + `ruff.toml` + `bandit.yaml` + `.coveragerc`;
- `ENSURE` mkdirs `engineering/{changes,adr,runbooks,reviews,contracts/*}` only;
- `merge_agents` ships `AGENTS.md` as the only self-learning contract.

**This change must not add the logs to `MANAGED_FILES` and must not `COPY` this repo’s filled logs into a consumer.**

Those two files are **this product’s memory** (GHA ban, ruff-not-pyproject, pin-after-bump). Copying them would:

- leak Adaptive Grok Build Pro internals into every consumer tree;
- later `--force` overwrite a consumer-written log.

**Do not ENSURE empty consumer stubs in this change.** Brief already says “No installer seed.” After `AGENTS.md` is retargeted, a consumer agent creates root `decisions.md` / `mistakes.md` on first real write — same “file appears when used” behavior as today under `engineering/`. Seeding empty root files is a separate product decision with its own tests.

`tests/_support.py` `project_copy` does not need the logs. Structure tests run against this repo root, not the temp copy.

`--with-ci` stays `SystemExit` / forbidden. Do not add a workflow, Dependabot file, or CI template.

---

## 6. Packager / manifest impact

`scripts/package_stack.py` and `.grok-stack/adaptive_grok/manifest.py` `included_files()` walk the tree. They have no special case for these names.

After the move + stubs:

- the zip grows `adaptive-grok-build-pro/decisions.md` and `…/mistakes.md` (what an unzipped source tree shows at root);
- the zip keeps `adaptive-grok-build-pro/engineering/decisions.md` and `…/mistakes.md` as the short pointers;
- no packager code change.

This package’s `release.md` / brief: **no version bump, no zip rebuild, no publish.** Accept that the already-built `packages/adaptive-grok-build-pro-v2.0.8.zip` still has the logs only under `engineering/` until a later pack. Do not rebuild it here. Do not retag `v2.0.8`.

`CHANGELOG.md` §2.0.8 is the **ship record for 2.0.8** (“log-to-`engineering/…`”). Leave it. Do not rewrite published history to claim 2.0.8 already had root files. A later version can mention the relocation. Structure tests must not parse CHANGELOG for these paths.

---

## 7. Write-owner sequence

One owner. Smallest vertical.

1. Make the structure test fail on the current tree (root files missing; bullets still say `engineering/…`).
2. `git mv engineering/decisions.md decisions.md` and `git mv engineering/mistakes.md mistakes.md`.
3. Write the two-line stubs at the old paths.
4. Retarget the two `AGENTS.md` bullets to the bare filenames.
5. Confirm the structure test is green.
6. Do **not** touch `install_into.py`, `package_stack.py`, `manifest.py`, `pyproject.toml`, `.github/`, skills, historical change packages, `VERSION`, or `packages/*.zip`.

Optional after the move, not required: one ≤3-sentence root `decisions.md` entry that “canonical log at repo root + stub at the old path” paid for itself. Do not also write that entry under `engineering/`.

---

## 8. Rollback

Matches `rollback.md`:

- `git mv` the two root files back to `engineering/`;
- delete the stubs (they are replaced by the restored logs);
- restore the `AGENTS.md` `engineering/` bullets and the old `assertIn('engineering/…')` lines.

No data migration. No installer rollback. No zip rollback (none is built).

---

## 9. Risks

| Risk | Mitigation |
| --- | --- |
| Agent appends to the stub | Stub text is “Do not append”; structure test forbids `## 20` and a long file |
| Consumer `AGENTS.md` names root files that do not exist yet | Accept. Same as today’s missing `engineering/` sinks after install. No seed this change |
| 2.0.8 zip ≠ working tree | Accept. No pack / no bump in this package |
| Stale CHANGELOG §2.0.8 still names `engineering/` | Leave it as the 2.0.8 ship record. Do not let the structure test require CHANGELOG to match live paths |
| Someone “helps” by adding `pyproject.toml` so tools see the new root files | Forbidden. `test_product_tree_has_no_packaging_markers` already locks this. Markdown logs do not need a packaging marker |
| Someone “helps” by restoring GHA to advertise the layout change | Forbidden. `test_version_is_2_0_8_and_github_actions_are_absent` + `--with-ci` SystemExit stay |

---

## Residual

- `docs_researcher` read this package while some stubs were still empty; the filled `brief.md` / `architecture.md` / `requirements.md` now match this ruling (move live log to root, pointer under `engineering/`, no installer seed).
- I did not unzip `packages/adaptive-grok-build-pro-v2.0.8.zip`. Inclusion follows `included_files()`; the current members are the `engineering/` logs.
- `task_analyst` report was not on disk when this was written. If it later asks for installer ENSURE or a version bump, this ruling still wins: no seed, no bump, no pack.

Write owner is `general_implementer`. This report does not implement the move.
