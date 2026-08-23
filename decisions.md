# Decisions

Patterns that paid for themselves. Each entry is at most three sentences.

## 2026-08-23 — Draft pull requests must still enqueue Trust CI jobs

Handoff keeps PR #2 draft until the App-owned check exists, so ignoring `draft=true` webhooks makes that check unreachable. Enqueue opened/synchronize/reopened draft events; keep closed-draft cancellation.

## 2026-08-23 — PostgreSQL restart drills need a named volume

`compose restart` stops the container and discards tmpfs. A named test volume plus `down --volumes` in the trap proves catalog recovery without leaving data behind.

## 2026-08-17 — Skip no-op checks; always push main and release

A dirty change-package tree is not a product change. Do not spend an analysis/review wave on status or leftover paperwork. When product files do change and verify is green, push `origin main` and publish the GitHub Release.

## 2026-08-17 — New release after an existing tag is 2.0.11

`v2.0.10` already peels to `975ccb2`. A new push/release therefore bumps VERSION, rebuilds the zip, and tags `v2.0.11`. Do not retag `v2.0.10`.

## 2026-08-16 — New release after an existing tag is 2.0.10

`v2.0.9` already peels to `f72c0fc`. A new «релиз сделай» therefore bumps VERSION, rebuilds the zip, and tags `v2.0.10`. Do not retag `v2.0.9`.

## 2026-08-16 — New release after an existing tag is 2.0.9

`v2.0.8` already peels to `0284241`. A new «релиз сделай» therefore bumps VERSION, rebuilds the zip, and tags `v2.0.9`. Do not retag `v2.0.8`.

## 2026-08-16 — Green verify means a new release

If `grok_verify --mode pr` and required reviews pass, publish: refresh README, rebuild the zip, tag, push, `gh release create`. Do not sit on an untagged VERSION when the user has standing release consent.

## 2026-08-16 — Publish unpublished 2.0.8, do not invent 2.0.9

`VERSION` is already 2.0.8 and no `v2.0.8` tag exists, so the new GitHub Release is 2.0.8 of the current tree. Rebuild the zip after notes, then tag that commit. Do not retag 2.0.7.

## 2026-08-16 — Split one large task; share memory

One giant prompt produces a stale README and half-finished last miles. Split into concrete subtasks that write facts into `AGENTS.md` / `decisions.md` / `mistakes.md` so the next slice can start without the chat. That is how the self-learning files stay the product map instead of session debris.

## 2026-08-16 — README is the push-time product map

A cold reader (human or LLM) only gets current context if `README.md` is refreshed to the tree being shipped. Before every `git push` or `grok_deploy`, rewrite current state and keep the mermaid a complete pairwise-linked graph. Structure tests fail if that AGENTS.md rule or the complete graph disappears.

## 2026-08-16 — README stack graph is K10 with every pair written out

The caption already promised every core piece is linked to every other. Once `AGENTS.md` / `decisions.md` / `mistakes.md` became core, a K7 mermaid was a lie. Enumerate all 45 `---` pairs so a structure test can fail on a missing link instead of trusting mermaid shorthand.

## 2026-08-16 — Move the live logs; stub the old path

`git mv` (not copy) keeps one source of truth and blame. A two-line stub at the old `engineering/` path stops a stale writer from starting a second log. Root `decisions.md` / `mistakes.md` are what the original prompt named and what a root listing shows.

## 2026-08-16 — Pin tests after bump, pack after VERSION

Hardcoded version asserts go red first so a skipped identity file cannot hide. Pack only after `VERSION` is `2.0.8` so the zip name and in-zip `VERSION` cannot still say `2.0.7`. The 2.0.8 ship used that sequence and the in-zip `VERSION` matched.

## 2026-08-16 — Never GitHub Actions

Local `make verify` / `python3 scripts/grok_verify.py --mode pr` is the only quality gate. Do not add `.github/workflows/`, Dependabot, `--with-ci` copies, or another CI SaaS. `install_into --with-ci` is `SystemExit` / forbidden.

## 2026-08-16 — Ruff lives in ruff.toml, not pyproject.toml

`grok_verify` runs Ruff/Bandit without a packaging marker. Config is root `ruff.toml` (and `bandit.yaml`). Do not add `pyproject.toml` / `requirements.txt` / `setup.py` — those flip `detect_repo` and, with pytest on PATH, skip `python-unittest`.

## 2026-08-15 — Ten is a read-only ceiling

Launch every listed analysis agent in one wave. Ten is `max_parallel_analysis`, not a staffing target and not ten writers. `routing.json` names floors; domain specialists join only on match; `docs_researcher` is on every non-micro wave.

## 2026-08-15 — Root hook shims fail-open after pull

Grok `project/adaptive` may still run `python3 pre_tool_use.py` from the project root. Missing that file is python exit 2 and a full tool lockout. Keep thin root dispatchers into `.grok/hooks/` and `||` allow fallbacks. Never put `_lib.py` at the repo root.

## 2026-08-15 — Commercial product, free, MIT

Treat Adaptive Grok Build Pro as a commercial-grade product that is free of charge and MIT-licensed. No EULA, no paid tier. Do not read «коммерческий продукт» as a production deploy: `_risk` matches `прод` as a word, not as a substring of `продукт`.

## 2026-08-15 — MIT public, not a paid SKU

The repo is MIT, free, and public. Commercial means product bar, not billing. `grok_deploy.py` is public release tooling.

## 2026-08-15 — SubagentStop must emit empty JSON

Grok re-fires SubagentStop when the hook returns `additionalContext`, eight times per agent. Emit `{}` and record the stop only while the id is still in `active`. Do not resume a finished reviewer to recover a truncated report — that is a second loop.

## 2026-08-15 — Unwrap one `-c` layer; reuse follow-ups only if open and same session

`bash -lc 'git push'` is one argv prefix miss, not a reason to write a shell parser: strip a matching quoted `-c`/`-lc` payload and run the existing invocation matcher on the inner chunks. Follow-up tokens stay a prompt-shape test (`should_reuse_active_route`); the hook uses `can_reuse_active_route` so `делай` does not revive a ready route or a leftover from another session.

## 2026-08-14 — Match production side-effects as argv prefixes

Split Bash on `&&` / `||` / `;` / `|` / newlines, strip comments, `NAME=value`, and wrappers, then compare leading tokens to `git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`. Bare-word `\brelease\b` / `\bpublish\b` / `\bprod(?:uction)?\b` on the whole string locked `ls`/`cat` of change-package paths and `scripts/grok_approve.py production`. Invocation prefixes unstuck ordinary tools while the real commands stayed gated.

## 2026-08-14 — Rematch every non-follow-up; skip child briefs

Reuse the active route only when `FOLLOW_UP_RE` matches the whole prompt, or the UserPromptSubmit payload is a child (`agent_id` / `You are …`). `is_development_prompt` is the inverse of “has intent keywords”, so leftover high-risk routes stuck on `repair yourself` and architect briefs overwrote the parent `route_id`. Follow-up-only reuse plus child-skip let a repair prompt get a write owner and let reviews run without replacing the route.

## 2026-08-14 — Run unittest from verify without a packaging marker

`verification._python` used `pyproject.toml` / `requirements.txt` / `setup.py` as the only trigger, so this repo’s `tests/` never ran under `grok_verify`. Detect `tests/test*.py` and run `python -m unittest discover -s tests`. Do not add a packaging marker just to light the check — that flips `detect_repo` and, when pytest is present, skips unittest.

## 2026-08-14 — Bind receipts after the last change-package write

`tree_fingerprint` hashes every non-runtime changed file, including `engineering/changes/**/state.json`. Transition the durable package to `ready` first, then run `grok_verify` and `grok_review`. Recording evidence before that last write guarantees stale receipts and a second verification loop.
