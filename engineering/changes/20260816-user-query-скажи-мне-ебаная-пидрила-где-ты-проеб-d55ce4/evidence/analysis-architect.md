# Analysis — architect

Change: `20260816-user-query-скажи-мне-ебаная-пидрила-где-ты-проеб-d55ce4`  
Route: `d55ce4cd4015` · write owner: `general_implementer`  
Question: authorship of `AGENTS.md`; was the self-learning loop (`decisions.md` / `mistakes.md`) intentionally replaced by “record it in the change package”, or dropped as collateral?

Read-only. No application edits. No `.env`. No push / merge / deploy.

---

## Verdict

**Accidental drop at initial authorship. Not an intended replacement.**

The two bullets were **never present** in this repository’s `AGENTS.md`. They were not later rewritten away. The Engineering Contract was authored without them. `"record it in the change package"` is a different rule (per-change conflict resolution) and does not supersede the durable self-learning logs.

If the instruction should still exist, the owning file is **`AGENTS.md`** (the product contract `install_into` ships). The log sinks already exist as **`engineering/decisions.md`** and **`engineering/mistakes.md`**. Operational reminder belongs in **`.grok/skills/adaptive-delivery/SKILL.md`** (and its `.agents/skills/` mirror). No skill currently carries the loop.

---

## 1. What is missing

Quoted user instruction (never found as live `AGENTS.md` text in this tree or in any tagged `AGENTS.md`):

- If you make a decision that turns out to be correct and worth the effort, log it in `decisions.md` (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in `mistakes.md`.

Current `AGENTS.md:28` says something else:

> When sources conflict, stop only for a named human gate or an irreversible/security-sensitive decision. Otherwise, make a bounded ruling, **record it in the change package**, and continue.

Those are not the same contract.

| Concern | Self-learning bullets | `AGENTS.md:28` |
| --- | --- | --- |
| Scope | Repo-wide, cross-change | This change only |
| Trigger | A pattern paid off, or a real mistake | Sources of truth conflict |
| Sink | `engineering/decisions.md` / `engineering/mistakes.md` | `engineering/changes/<id>/` (e.g. `architecture.md` `## Decisions`) |
| Format | ≤3 sentences; symptom vs root cause | Unspecified “bounded ruling” |
| Lifetime | Durable product memory | Dies with the change package |

---

## 2. Authorship chain of `AGENTS.md`

`AGENTS.md` is **hand-authored at repo root**. It is not generated.

| Layer | Role |
| --- | --- |
| Root `AGENTS.md` | Source of truth. Title: “Adaptive Grok Build Pro Engineering Contract”. |
| `.grok-stack/templates/` | Change-package stubs only. **No `AGENTS.md` template.** |
| `scripts/package_stack.py` | Zips `included_files()`. Does not author `AGENTS.md`. |
| `scripts/install_into.py` `managed_agents_text()` | Reads `source/AGENTS.md` and wraps it in `<!-- ADAPTIVE-GROK-PRO:START/END -->` on the consumer. |
| `docs/bitrix-local-AGENTS.md` | Separate Bitrix overlay for `local/AGENTS.md`. No self-learning text. |
| `.grok-stack/adaptive_grok/doctor.py` | Existence check only (`file:AGENTS.md`). |
| `tests/test_structure.py` | Existence check only. **No content assertion** about decisions/mistakes/self-learning. |
| `tests/test_installer.py` | Asserts the managed marker and idempotence. Does not assert self-learning text. |
| `tests/_support.py` `project_copy` | Copies `AGENTS.md`. Creates empty `engineering/{changes,adr,runbooks,reviews}`. **Does not seed `decisions.md` / `mistakes.md`.** |

GitHub history of `AGENTS.md` on `main` is two commits:

1. `ca63b2d` (2026-08-14) — *Initial commit: Adaptive Grok Build Pro*. Already the full Engineering Contract, including the source-of-truth list and “record it in the change package”. **No self-learning bullets.**
2. `11da31a` (2026-08-16) — *Fix 2.0.6 leftovers*. One sentence: Stop hook “blocks” → “warns” (`3c1039`). Unrelated.

Raw `AGENTS.md` at `v2.0.0` and `v2.0.3` matches `ca63b2d`. The contract was not rewritten later; it was written this way on day one of this product.

This repo is a Codex → Grok port (historical zip prefix `adaptive-codex-pro/`, change `bf62a5` / `e86e93`). The quoted bullets are the classic Codex/Claude `AGENTS.md` self-learning pair. When the Grok-native Engineering Contract was written, that pair was not carried over. There is **no ADR, CHANGELOG bullet, architecture decision, or test** that says “stop using `decisions.md`/`mistakes.md`; use the change package instead.”

---

## 3. The log files exist anyway — and match the missing instruction

`engineering/decisions.md` and `engineering/mistakes.md` were **not** in the initial commit (`ca63b2d` → 404).

They first appear in `097f5c9` (2026-08-15, *v2.0.4: complete public product loop*). Their headers are a byte-for-byte restatement of the missing bullets:

```1:3:engineering/decisions.md
# Decisions

Patterns that paid for themselves. Each entry is at most three sentences.
```

```1:3:engineering/mistakes.md
# Mistakes

Root causes, not symptoms. Record only mistakes that caused a real problem.
```

Later agents kept appending (matcher prefixes, rematch, unittest-without-marker, receipt binding, SubagentStop, GHA ban, ruff-not-pyproject). Practice survived. The standing instruction did not.

`install_into.py:138-149` ENSURE-mkdirs:

- `engineering/changes`, `adr`, `runbooks`, `reviews`, `contracts/{openapi,asyncapi,schemas}`

It does **not** create `engineering/decisions.md` or `engineering/mistakes.md`. A consumer that only runs the installer never gets the sinks. `package_stack` will ship this repo’s copies because they are ordinary tree files, not because the product scaffolds them.

---

## 4. Skills do not carry an equivalent loop

Checked: `adaptive-delivery`, `verification-evidence`, `feature-workflow`, `bugfix-workflow`, `incident-response`, `task-triage`, `release-readiness`, both skill trees, agent `.md`/`.toml`, `session_start.py`.

| Skill / agent | What it says | Self-learning loop? |
| --- | --- | --- |
| `adaptive-delivery` §1.4 | Use the **change package** for scope, requirements, architecture, tests, **decisions**, release, rollback | No. “Decisions” = this-change docs. |
| `verification-evidence` | Fingerprint-bound receipts | No |
| `feature-workflow` | New service/queue/store needs an **ADR** | No `decisions.md` |
| `bugfix-workflow` | Distinguish root cause from symptoms | Process only; no `mistakes.md` |
| `incident-response` | Identify root cause | Process only |
| Change template `architecture.md` | `## Decisions` | Per-change stub |
| Agent TOMLs / `session_start` | Route + change id | No |

`adaptive-delivery` is the mandatory controller (`AGENTS.md:10`). If the loop were meant to move out of `AGENTS.md`, this is where it would have landed. It did not.

---

## 5. Why this is not an intended replacement

1. **Different trigger.** `AGENTS.md:28` fires on source-of-truth conflict. The missing bullets fire on “this pattern paid for itself” and “this mistake caused a real problem,” including when nothing is in conflict.
2. **Different sink.** Change package `## Decisions` vs durable `engineering/decisions.md` / `engineering/mistakes.md`.
3. **No recorded ruling.** No ADR, no `decisions.md` entry, no CHANGELOG line, no architecture note: “supersede the self-learning files.”
4. **Later practice contradicts replacement.** v2.0.4+ agents created and filled those files in the exact missing format. They treated the loop as still in force.
5. **Installer / tests never encoded a replacement.** Tests do not forbid `decisions.md`. They also do not require the bullets in `AGENTS.md`. The contract hole is untested, not designed.

Bounded ruling for this change: treat the omission as **collateral of writing a new Grok Engineering Contract** (`ca63b2d`), not as a decision to retire repo-wide learning.

---

## 6. Owning file if the instruction should still exist

**Primary: `AGENTS.md`.** That is the standing product contract, the file the user asked about, and the blob `install_into.merge_agents` copies into every consumer.

**Also restore, or the bullets are dead on install:**

| File | Why |
| --- | --- |
| `AGENTS.md` | Standing rule. Own the two bullets (or a one-line pointer to the sinks). |
| `.grok/skills/adaptive-delivery/SKILL.md` + `.agents/skills/adaptive-delivery/SKILL.md` | Mandatory controller. Close/design should say: correct durable pattern → `engineering/decisions.md`; root-cause mistake → `engineering/mistakes.md`. |
| `engineering/decisions.md` / `engineering/mistakes.md` | Already the sinks on this tree. Seed empty stubs from the installer if consumers are supposed to have them. |
| `scripts/install_into.py` ENSURE list | Today it does not create the sinks. |
| `tests/test_structure.py` | Today it only checks `AGENTS.md` exists. A content lock is what would have caught `ca63b2d`. |

Do **not** put the loop only in a change-package `## Decisions` section. That is this-change memory. The missing instruction is product memory.

Do **not** invent an ADR for this unless the user wants a new architectural rule. The files and format already exist; the contract text is what was dropped.

---

## 7. Smallest restore (for the write owner; not done here)

If this route’s outcome is “put the instruction back”:

1. Add the two bullets to `AGENTS.md` under a short heading (e.g. after Source-of-truth, or as a sibling of Development discipline). Keep `AGENTS.md:28` — it is a different rule.
2. Mirror one sentence into both `adaptive-delivery` skills.
3. Optionally ENSURE empty `engineering/decisions.md` / `engineering/mistakes.md` on install (same headers as this repo).
4. Add a structure test that `AGENTS.md` names `decisions.md` and `mistakes.md`.

Out of scope unless asked: rewriting historical change packages; moving the logs under `engineering/changes/`.

---

## Residual

- Pre-`ca63b2d` Codex-era `AGENTS.md` is not in this git history. Inference that the bullets lived there is from the port story plus the exact header match on the later log files. It does not change the verdict: **this product never shipped them in `AGENTS.md`.**
- I did not unpack old `packages/*.zip` members; tagged raw `AGENTS.md` at `v2.0.0`/`v2.0.3` already matches the initial contract.
