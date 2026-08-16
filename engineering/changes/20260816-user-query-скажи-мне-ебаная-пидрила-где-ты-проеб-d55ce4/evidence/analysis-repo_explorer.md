# Analysis — repo_explorer

Change: `20260816-user-query-скажи-мне-ебаная-пидрила-где-ты-проеб-d55ce4`  
Route: `d55ce4cd4015` · write owner: `general_implementer`  
Question: where did the agent self-learning instruction disappear from `AGENTS.md`?

Missing instruction (user quote):

- If you make a decision that turns out to be correct and worth the effort, log it in decisions.md (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in mistakes.md.

Read-only hunt. No `.env`. No push / merge / deploy.

## One-sentence answer

The bullets were never in any committed `AGENTS.md`; they were omitted when the file was first authored as the Engineering Contract in initial commit `ca63b2d8ae3ce39765e8c7e043a1bd739ed0c9f8` (2026-08-14), and no later rewrite or generator added them.

## Working-tree search (exact phrases)

Searched the product tree for:

| Phrase | Hits outside this change package |
| --- | --- |
| `worth the effort` | **none** |
| `no more than 3 sentences` | **none** (near-miss: `engineering/decisions.md:3` says “at most three sentences”) |
| `record it in mistakes.md` | **none** |
| `log it in decisions.md` | **none** |
| `pattern + why it worked` | **none** |
| `root cause (not the symptom)` | **none** (near-miss: `engineering/mistakes.md:3` says “Root causes, not symptoms”) |

Every exact hit is this change package echoing the user query (`brief.md`, `requirements.md`, `route.json`, `state.json`, and the other stub docs). Current `AGENTS.md` does not contain those two bullets. Neither do `.grok/skills/**`, `.grok/agents/**`, `docs/bitrix-local-AGENTS.md`, `scripts/**`, or `.grok-stack/templates/**`.

Sibling consumers on this machine (`/home/pall/grok-projects/google-ads-automation/AGENTS.md`, `/home/pall/grok-projects/mee/AGENTS.md`) only carry the same managed Engineering Contract block (`<!-- ADAPTIVE-GROK-PRO:START -->` … `END`). They also lack the self-learning bullets.

## Who owns `AGENTS.md`

There is **no template that generates** `AGENTS.md`. `.grok-stack/templates/` only has change-package stubs, `ci/README.md`, and `hook_root_shim.py`.

| Owner | Role |
| --- | --- |
| Root [`AGENTS.md`](../../../../AGENTS.md) | Source of truth. Hand-written Engineering Contract. |
| [`scripts/install_into.py`](../../../../scripts/install_into.py) `managed_agents_text` / `merge_agents` (lines 68–85) | Copies that file **verbatim** into a consumer `AGENTS.md` between `<!-- ADAPTIVE-GROK-PRO:START -->` and `<!-- ADAPTIVE-GROK-PRO:END -->`. Does not synthesize extra sections. |
| [`scripts/package_stack.py`](../../../../scripts/package_stack.py) | Zips the existing file. Does not rewrite it. |
| [`docs/bitrix-local-AGENTS.md`](../../../../docs/bitrix-local-AGENTS.md) | Separate Bitrix-local snippet for `local/AGENTS.md`. No self-learning text. |
| [`tests/test_structure.py`](../../../../tests/test_structure.py) | Only asserts `AGENTS.md` exists. No content lock for the missing bullets. |
| [`tests/test_installer.py`](../../../../tests/test_installer.py) | Asserts the managed-block markers, not the self-learning wording. |

So if the instruction is missing from root `AGENTS.md`, every install and every zip is missing it too.

## Git history of `AGENTS.md`

Published history for this path is two commits only ([GitHub commits for `AGENTS.md`](https://github.com/Dimkox/adaptive-grok-build-pro/commits/main/AGENTS.md)):

| SHA | Date (UTC, from reflog) | Subject | What happened to the instruction |
| --- | --- | --- | --- |
| `ca63b2d8ae3ce39765e8c7e043a1bd739ed0c9f8` | 2026-08-14 (`1786735567`) | `Initial commit: Adaptive Grok Build Pro` | **First version.** Already the full “Adaptive Grok Build Pro Engineering Contract”. **Does not contain** the two self-learning bullets. |
| `11da31a3f3e60a0463233cb96c576da8517ddabd` | 2026-08-16 (`1786908008`) | `Fix 2.0.6 leftovers: installer configs, deploy title, stale notes` | Change `20260816-self-scan-and-fix-emerging-product-bugs-3c1039`. **Only** line 99: Stop hook “blocks completion” → “warns”. Did not add or delete the self-learning section. |

Checked the same `AGENTS.md` blob at other surviving SHAs (all identical to the initial contract, still no bullets):

- `003cffc9b024186030441f00f1313959f70b0120` — Release v2.0.0
- `83e6fe52340405c9c35441185b51e3cdef332f04` — Rename remaining Codex branding to Grok
- `eaf0a0026734cded4310ffed2725c5ebe6a48669` — `origin/main` after the 2026-08-14 reset
- `097f5c9a112430f5250920bdbf96fb1b0fdc2f1c` — v2.0.4 (this is when the *log files* appear; `AGENTS.md` unchanged)

HEAD at analysis time: `02376cc097d7640d56dd308b98efe4e026f4c253` (Release v2.0.7). `AGENTS.md` still matches `11da31a` (warn-only Stop sentence, no self-learning section).

There is no commit that last *contained* the instruction, because no commit ever did. The first (and only) authoring of `AGENTS.md` is the drop / omit point.

## Distinguishing the project logs from the missing instruction

These are **not** the same thing:

| Artifact | What it is | First committed | Ships to consumers? |
| --- | --- | --- | --- |
| `AGENTS.md` instruction (the missing bullets) | Standing order that *tells agents* to write short learning entries | **Never existed** in this repo | Would have, via `merge_agents` |
| [`engineering/decisions.md`](../../../../engineering/decisions.md) | This-repo project log. Header: “Patterns that paid for themselves. Each entry is at most three sentences.” | `097f5c9a112430f5250920bdbf96fb1b0fdc2f1c` (2026-08-15, `v2.0.4: complete public product loop`) | **No.** `install_into` only `ENSURE`s `engineering/changes`, `adr`, `runbooks`, `reviews`, `contracts/*`. It does not copy these two files. |
| [`engineering/mistakes.md`](../../../../engineering/mistakes.md) | This-repo project log. Header: “Root causes, not symptoms. Record only mistakes that caused a real problem.” | Same `097f5c9` | **No.** |

The log-file headers paraphrase the missing instruction (three-sentence cap; root cause not symptom). Agents have been appending to those files since the 2.0.4 contour (`757a43` / `2eacdf` lessons dated 2026-08-14). That is **practice**, not the `AGENTS.md` rule the user quoted.

Second omission, not a deletion: when `097f5c9` introduced the log files, `AGENTS.md` was left unchanged. No later generator, skill (`adaptive-delivery`, `verification-evidence`), or agent `developer_instructions` (e.g. `.grok/agents/general_implementer.toml`) was updated to point at `decisions.md` / `mistakes.md`.

## What was *not* the drop

- Not `11da31a` / change `3c1039`. That rewrite only corrected Stop-hook honesty.
- Not the Codex-to-Grok rename `83e6fe5` / change `b8b188`. `AGENTS.md` was already the Grok Engineering Contract and still lacked the bullets.
- Not `install_into.merge_agents`. It copies whatever root `AGENTS.md` already is.
- Not `package_stack.py` or a missing `.grok-stack/templates/AGENTS.md`. There is no such template.

## Impact surface if a write owner restores the bullets

- Edit root `AGENTS.md` (hand-written contract).
- Re-install / re-package so consumers get the managed block (`merge_agents`).
- Optionally add a structure test that locks the two sentences, or they can vanish the same way: no generator, no test, no skill reminder.
- `engineering/decisions.md` and `engineering/mistakes.md` already exist *in this repo*. Consumers will not get those files unless the installer also starts creating them.

## Residual

- There is no pre-`ca63b2d` git parent. If the wording lived in an uncommitted draft, a chat-only convention, or another product, that history is not in this repository.
- Compressed git objects were not greppable as text; conclusion is from checked-out `AGENTS.md` at every SHA that still resolves on GitHub, plus the two-commit path history.
