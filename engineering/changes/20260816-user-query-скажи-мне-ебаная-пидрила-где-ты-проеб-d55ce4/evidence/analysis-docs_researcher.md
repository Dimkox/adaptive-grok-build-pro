# Docs research — missing AGENTS.md self-learning instruction

Route: `d55ce4cd4015`. Change: `20260816-user-query-скажи-мне-ебаная-пидрила-где-ты-проеб-d55ce4`.

Question: recover the original documented source of this agent self-learning instruction, and whether current docs still expect it.

Missing instruction (user quote):

- If you make a decision that turns out to be correct and worth the effort, log it in decisions.md (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in mistakes.md.

Read-only. No application-code edits. No `.env`. No push / merge / deploy. No APIs invented.

## Sources

- This change package (`brief.md`, `requirements.md`, `architecture.md`, `release.md`, `rollback.md`, `test-plan.md`, `tasks.md`, `state.json`, `route.json`)
- Current `AGENTS.md` (full file, 107 lines)
- GitHub history of `AGENTS.md`: only `ca63b2d` (initial) and `11da31a` (Stop-hook wording). Raw initial file: `https://raw.githubusercontent.com/Dimkox/adaptive-grok-build-pro/ca63b2d8ae3ce39765e8c7e043a1bd739ed0c9f8/AGENTS.md`
- `engineering/decisions.md`, `engineering/mistakes.md` (current + first committed copies at `097f5c9`)
- `engineering/adr/` (empty), `engineering/contracts/{openapi,asyncapi,schemas}/` (empty of product APIs)
- `README.md`, `QUICKSTART.md`, `CHANGELOG.md` §§2.0.0–2.0.7
- `.grok/skills/**` and `.agents/skills/**` (including `adaptive-delivery`, `feature-workflow`, `verification-evidence`, `task-triage`)
- `.grok/agents/*.{md,toml}` (including `docs_researcher`, `general_implementer`)
- `.grok-stack/templates/change/` (including `architecture.md` `## Decisions`)
- `.grok-stack/templates/ci/README.md`, `hook_root_shim.py`
- `scripts/install_into.py` (`merge_agents`, `ENSURE` dirs)
- `scripts/package_stack.py` + `.grok-stack/adaptive_grok/manifest.py` `included_files`
- `.grok-stack/adaptive_grok/{change.py,doctor.py}`
- `.grok/hooks/README.md`, `session_end.py`
- `tests/test_structure.py`, `tests/test_installer.py`
- `docs/bitrix-local-AGENTS.md`
- `packages/README.md`
- Prior packages that created or edited the log files: `757a43`, `2eacdf`, `19fc56`, `99b743`, `ec0388`, `9fd274`, `ef7b14`
- GitHub tree of `engineering/` at initial commit `ca63b2d`
- GitHub history of `engineering/decisions.md` and `engineering/mistakes.md`
- Repo-wide search for the exact bullets, `worth the effort`, `why it worked`, `not the symptom`, `self-learning`, `compounding`, `memory`

No OpenAPI / AsyncAPI / schema change is involved. There is no ADR that added, moved, or deleted this instruction.

---

## Verdict (three required answers)

| Question | Fact |
| --- | --- |
| **Last known canonical location** | The two bullets were **never** in committed `AGENTS.md`. The last known canonical *sink* of the same idea is `engineering/decisions.md` + `engineering/mistakes.md`, first committed in `097f5c9` (2026-08-15, “v2.0.4: complete public product loop”). Their headers are a paraphrase of the missing bullets, not a copy. |
| **Current expected location** | Current standing docs do **not** expect those two bullets anywhere. If the duty were restored, the only file Grok loads as standing instructions is still root `AGENTS.md` (installer wraps the whole file as the `ADAPTIVE-GROK-PRO` block). The files the bullets name already live at `engineering/decisions.md` and `engineering/mistakes.md`. What current docs *do* expect instead is a bounded ruling in the **change package** (`architecture.md` `## Decisions`), plus optional ADRs under `engineering/adr/`. |
| **Do `decisions.md` / `mistakes.md` still exist, and for a different purpose?** | **Yes, they exist.** They are a **product-level pattern / root-cause log** that write owners have been appending during specific changes. They are **not** wired as the documented AGENTS.md self-learning loop. They are **not** copied to consumer repos. They are **not** the same thing as change-package `## Decisions` or `engineering/adr/`. |

Current docs do **not** still expect the missing instruction.

---

## 1. `AGENTS.md` never held those two bullets

GitHub history for `AGENTS.md` on `main` has exactly two commits:

| Commit | Date | What changed in `AGENTS.md` |
| --- | --- | --- |
| `ca63b2d` “Initial commit: Adaptive Grok Build Pro” | 2026-08-14 | File created. Full text is the Engineering Contract (route, `/adaptive-delivery`, one write owner, SoT order, Bitrix/API/data/AI rules, verify + receipts, prohibited actions). **No self-learning section. No `decisions.md` / `mistakes.md` bullets.** |
| `11da31a` “Fix 2.0.6 leftovers…” | 2026-08-16 | One line only. Stop hook “blocks completion” → “warns”. That is change `3c1039` (self-scan of product bugs), not self-learning. |

Initial `AGENTS.md` (raw at `ca63b2d`) already matches today’s file except that later Stop-hook wording. The current file still has no occurrence of `decisions.md`, `mistakes.md`, “worth the effort”, “why it worked”, “three sentences”, “root cause”, “self-learning”, “compounding”, or “memory”.

The only place the exact English bullets exist in this tree is **this change package** (user query copied into `brief.md` / `route.json` / stubs). A repo-wide search for `worth the effort` / `why it worked` / `log it in decisions.md` / `record it in mistakes.md` hits nothing else.

So the instruction was not deleted from `AGENTS.md` in a later rewrite. It was never committed there.

---

## 2. Last known canonical remnant: the two log files

### 2.1 First appearance

Initial `engineering/` at `ca63b2d` contained only:

- `adr/`
- `changes/`
- `contracts/`
- `runbooks/`

No `decisions.md`. No `mistakes.md`.

GitHub history:

- `engineering/mistakes.md` — first and only commit `097f5c9` (2026-08-15, v2.0.4 complete public product loop).
- `engineering/decisions.md` — first commit `097f5c9`, then appends in `7c0ae75` (2.0.5), `549f29d` (2.0.6 quality), `e75f3a1` (never GHA).

The `097f5c9` copies already have the headers that paraphrase the missing instruction. They are unchanged as headers through HEAD.

### 2.2 Current headers (the only in-repo paraphrase)

```1:3:engineering/decisions.md
# Decisions

Patterns that paid for themselves. Each entry is at most three sentences.
```

```1:3:engineering/mistakes.md
# Mistakes

Root causes, not symptoms. Record only mistakes that caused a real problem.
```

Mapping onto the missing bullets:

| Missing AGENTS.md duty | What the file header kept |
| --- | --- |
| log a correct, worth-the-effort decision in `decisions.md` (pattern + why it worked, ≤ 3 sentences) | “Patterns that paid for themselves. Each entry is at most three sentences.” |
| if a mistake causes a problem, record the root cause (not the symptom) in `mistakes.md` | “Root causes, not symptoms. Record only mistakes that caused a real problem.” |

The **duty** (“if you make… log it”) is absent. The **format** of the sink files is present.

### 2.3 What those files actually contain

`engineering/decisions.md` is a dated product-pattern log. Current entries (all ≤ 3 sentences, as the header requires):

- 2026-08-16 Never GitHub Actions
- 2026-08-16 Ruff lives in `ruff.toml`, not `pyproject.toml`
- 2026-08-15 Ten is a read-only ceiling
- 2026-08-15 Root hook shims fail-open after pull
- 2026-08-15 Commercial product, free, MIT
- 2026-08-15 MIT public, not a paid SKU
- 2026-08-15 SubagentStop must emit empty JSON
- 2026-08-15 Unwrap one `-c` layer; reuse follow-ups only if open and same session
- 2026-08-14 Match production side-effects as argv prefixes
- 2026-08-14 Rematch every non-follow-up; skip child briefs
- 2026-08-14 Run unittest from verify without a packaging marker
- 2026-08-14 Bind receipts after the last change-package write

`engineering/mistakes.md` has two 2026-08-14 entries, each with **Symptom** + **Root cause**:

- Treated a matcher bug as an environment block (hooks moved to `.grok/hooks.disabled/`)
- Bound verification to an intermediate tree (stale fingerprint)

Those match the 757a43 / 2eacdf failure modes. Later implementers kept appending to `decisions.md` (`19fc56` architecture: “Decision entry”; `ec0388` “ruff.toml not pyproject”; `9fd274` / `5be23b` “never GitHub Actions”). That is **product memory written by write owners**, not a documented every-agent self-learning loop.

No change-package architecture ever said “add these two bullets to `AGENTS.md`”. `757a43` implementation.md does not list creating the files. `19fc56` is the first change that names `engineering/decisions.md` as something to edit/revert.

---

## 3. Current docs do not expect the missing instruction

Negative search, quoted so this is not an inference from silence in one file:

| Surface | Mentions the two bullets / “log it in decisions.md” / “record it in mistakes.md”? |
| --- | --- |
| Current `AGENTS.md` | No |
| Initial `AGENTS.md` (`ca63b2d`) | No |
| `README.md` | Mentions `AGENTS.md` only as “multi-agent discipline” and as an install copy target |
| `QUICKSTART.md` | No |
| `CHANGELOG.md` 2.0.0–2.0.7 | No self-learning / compounding / memory section |
| `engineering/adr/` | Empty. No ADR |
| `engineering/contracts/*` | Empty of product APIs |
| `.grok/skills/**` and `.agents/skills/**` | **Zero** hits for `decisions.md` / `mistakes.md` / self-learn / compounding |
| `.grok/agents/*.{md,toml}` | **Zero** hits. `general_implementer.toml` has no log-to-decisions duty |
| `.grok/hooks/**` including `session_end.py` | Session end writes `last-session-end.json` only. No memory / decisions / mistakes write |
| `.grok-stack/templates/change/**` | `architecture.md` has a per-change `## Decisions` heading. It does not point at `engineering/decisions.md` |
| `docs/bitrix-local-AGENTS.md` | Bitrix-local rules only |
| `tests/test_structure.py` | Requires `AGENTS.md` to exist. Does not assert the bullets |
| `tests/test_installer.py` | Asserts the `ADAPTIVE-GROK-PRO:START` marker, not self-learning text |
| `doctor.py` required files | `AGENTS.md`, config, hooks, adaptive-delivery skill, routing.json. **Not** `decisions.md` / `mistakes.md` |

Packaged zips: `manifest.included_files()` takes the tree minus `.git` / `dist` / runtime / secrets / `*.zip`. So:

- v2.0.0–2.0.3 zips **cannot** contain `engineering/decisions.md` or `mistakes.md` (files did not exist).
- v2.0.4+ zips **do** contain those two files (they are ordinary tree members).
- Every packaged `AGENTS.md` is the Engineering Contract. Grep of `packages/` and `dist/` for the exact bullets is empty.

Web search for the exact English sentence did not return a copied upstream template in this repository. The instruction is not recovered from Dobryakov (`ef7b14` is a 57-tool SAST/CI handbook, not an AGENTS.md memory spec).

---

## 4. What current docs expect instead

### 4.1 `AGENTS.md` — rulings go in the change package

```19:28:AGENTS.md
## Source-of-truth order

1. User-approved scope and decisions.
2. Active route and durable change package under `engineering/changes/`.
3. Machine-readable API/event/data contracts.
4. ADRs and repository-local instructions.
5. Existing implementation and tests.
6. Chat history.

When sources conflict, stop only for a named human gate or an irreversible/security-sensitive decision. Otherwise, make a bounded ruling, record it in the change package, and continue.
```

“User-approved scope and decisions” is SoT #1 (the **user’s** decisions), not a pointer at `engineering/decisions.md`. The conflict rule names the **change package**, not `decisions.md` / `mistakes.md`. SoT #4 is ADRs + “repository-local instructions”; `engineering/adr/` is empty.

### 4.2 `/adaptive-delivery` — “decisions” means the change-package section

```31:31:.grok/skills/adaptive-delivery/SKILL.md
4. Use the change package for scope, requirements, architecture, tests, decisions, release, rollback, and human approval evidence.
```

`change.py` copies `.grok-stack/templates/change/`, whose `architecture.md` has:

```20:20:.grok-stack/templates/change/architecture.md
## Decisions
```

That is a **per-change** heading. It is not `engineering/decisions.md`. `.agents/skills/adaptive-delivery/SKILL.md` is the same file.

### 4.3 `feature-workflow` — new deps need an ADR, not a decisions.md line

> A new service, queue, datastore, framework, or major dependency requires an ADR and named approval.

Target directory: `engineering/adr/` (still empty).

### 4.4 Installer — does not ship the log files to consumers

`install_into.merge_agents` copies the **entire current `AGENTS.md`** into the consumer file between `<!-- ADAPTIVE-GROK-PRO:START -->` and `END`. Whatever is missing from this repo’s `AGENTS.md` is therefore also missing from every installed consumer.

`install()` then `ENSURE`s empty directories only:

- `engineering/changes`
- `engineering/adr`
- `engineering/runbooks`
- `engineering/reviews`
- `engineering/contracts/openapi`
- `engineering/contracts/asyncapi`
- `engineering/contracts/schemas`

It does **not** copy or create `engineering/decisions.md` or `engineering/mistakes.md`. A consumer install does not receive the self-learning sinks or the missing bullets.

---

## 5. How the two files are used today (different purpose)

They exist and are **in active use**, but as a **this-product pattern/anti-pattern notebook**, not as the missing AGENTS.md duty.

| Use | `engineering/decisions.md` / `mistakes.md` | Missing AGENTS.md loop | Change-package `## Decisions` | `engineering/adr/` |
| --- | --- | --- | --- | --- |
| Who writes | Write owners, when they remember | Every agent, after a good call or a real mistake | The route’s design/write wave | Explicit new-architecture ADR |
| Required by | Informal habit + later analysis reports citing them | The missing bullets | `AGENTS.md` + adaptive-delivery | `feature-workflow` |
| Audience | Later agents on **this** repo | Compounding memory for any task | One change | Formal architecture |
| Copied by installer | No | Would have been, if in `AGENTS.md` | Template only | Empty dir ensured |
| Doctor / tests | Not required | Not asserted | Template exists | Dir only |

Later analysis reports (`ec0388`, `ef7b14`, `9fd274`, `cd8a96`, `864726`, `2929c0`) treat `decisions.md` / `mistakes.md` as **citable product constraints** (no `pyproject.toml`, bind receipts last, never GHA). That is closer to a lightweight ADR log than to “log every correct decision in ≤ 3 sentences.”

`mistakes.md` has not grown since 2026-08-14. If the AGENTS.md duty were live, later failures (GHA contour, leftover 2.0.6 bugs in `3c1039`, Stop-hook wording) would have new mistake entries. They do not.

---

## 6. Where the “loss” actually is (for the write owner)

Not a deletion from `AGENTS.md`. The Engineering Contract shipped without the two-bullet self-learning section. The sink files were added in v2.0.4 with matching headers, then used informally. The standing contract that occupies the same slot is:

> make a bounded ruling, record it in the change package, and continue.

If this route’s outcome is to restore the instruction, the documented place to put the two bullets is **root `AGENTS.md`** (that is what Grok loads and what the installer merges). The files those bullets name already exist at `engineering/decisions.md` and `engineering/mistakes.md` and should not be reinvented as ADRs or as change-package-only notes. Current docs do **not** require that restore; this report only locates the gap.

This report is analysis only. It does not authorize editing `AGENTS.md`.
