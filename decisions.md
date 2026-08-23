# Decisions

Patterns that paid for themselves. Each entry is at most three sentences.

## 2026-08-23 — Human gates must match the GitHub identity model

A pull-request author cannot approve their own pull request, and Environment self-review prevention blocks the deployment initiator. Use owner inspection and manual merge for the current solo identity, then enable required CODEOWNER review and self-review prevention after a separate bot, App, or collaborator owns authorship and dispatch.

## 2026-08-23 — Shell protection has a code fallback

`policy.json` improves and configures shell matching, but a missing or malformed policy file must not reopen control-plane writes. Common shell mutations are denied from `policy.py` defaults before configurable command patterns run.

## 2026-08-23 — Protected PR and Environment are the authority

Local hooks and receipts are feedback, not authorization. Delivery is branch → exact-SHA `trusted-ci` → configured human gate → protected merge; release is the verified `main` SHA behind the `production` Environment. Grok never executes the side effect.

## 2026-08-23 — Approval files are requests, never grants

An agent that can run Bash can call any local CLI, so a local approval file cannot be a trust boundary. `grok_approve.py` records route, HEAD, fingerprint, scope, and reason for a human, while policy outcome stays denied.

## 2026-08-23 — Strict CI fails on missing tools

A passing authoritative job must mean the required check ran. `--strict` turns absent Ruff, Bandit, or Coverage.py into failures; non-strict local verification keeps skip behavior for iterative work.

## 2026-08-17 — Skip no-op checks; use protected delivery for product changes

A dirty change-package tree is not a product change, so do not spend an analysis or review wave on paperwork. Product changes go through a pull request and required checks rather than direct push.

## 2026-08-17 — New release after an existing tag is 2.0.11

`v2.0.10` already peels to `975ccb2`. A later release therefore needs a new VERSION and tag; never retag `v2.0.10` or overwrite `v2.0.11`.

## 2026-08-16 — New release after an existing tag is 2.0.10

`v2.0.9` already peels to `f72c0fc`. A new release therefore bumps VERSION and creates a new tag; never retag `v2.0.9`.

## 2026-08-16 — New release after an existing tag is 2.0.9

`v2.0.8` already peels to `0284241`. A new release therefore bumps VERSION and creates a new tag; never retag `v2.0.8`.

## 2026-08-16 — Green verify means protected delivery

A green local verify opens the delivery path but cannot authorize merge or release. Required GitHub checks and the configured human gate decide merge; the protected Environment decides release.

## 2026-08-16 — Publish unpublished 2.0.8, do not invent 2.0.9

`VERSION` was already 2.0.8 and no `v2.0.8` tag existed, so that historical release used 2.0.8 of the current tree. Never retag an existing version.

## 2026-08-16 — Split one large task; share memory

One giant prompt produces a stale README and half-finished last miles. Split into concrete subtasks that write durable facts into `AGENTS.md`, `decisions.md`, and `mistakes.md`.

## 2026-08-16 — README is the delivery-time product map

A cold reader gets current context only when `README.md` matches the tree under review. Refresh it before the pull request or deploy preparation and keep the Mermaid graph complete.

## 2026-08-16 — README stack graph is K10 with every pair written out

The graph promises every core piece links to every other. Enumerate all 45 undirected pairs so a structure test detects a stale map.

## 2026-08-16 — Move the live logs; stub the old path

`git mv` keeps one source of truth and blame. Root `decisions.md` and `mistakes.md` are canonical; the old engineering paths are pointers only.

## 2026-08-16 — Pin tests after bump, pack after VERSION

Hardcoded version assertions fail first so a skipped identity file cannot hide. Package only after VERSION is final so the archive name and embedded VERSION agree.

## 2026-08-16 — Superseded: local-only quality gate

The historical local-only rule prevented independent validation and is superseded by the 2026-08-23 trust boundary. Local verification remains useful, but `trusted-ci` and GitHub protection are authoritative.

## 2026-08-16 — Ruff lives in ruff.toml, not pyproject.toml

`grok_verify` runs Ruff and Bandit without a packaging marker. Do not add `pyproject.toml`, `requirements.txt`, or `setup.py` merely to configure quality tools because they change repository detection and runner selection.

## 2026-08-15 — Ten is a read-only ceiling

Launch listed analysis agents in one wave. Ten is `max_parallel_analysis`, not a staffing target and never ten writers.

## 2026-08-15 — Root hook shims fail open after pull

Older Grok project configs may run root hook files. Thin root dispatchers and fail-open fallbacks prevent a missing file from freezing the session; GitHub protection carries the independent boundary.

## 2026-08-15 — Commercial product, free, MIT

Commercial means product-quality expectations, not billing. The repository is public, free of charge, MIT-licensed, and has no paid tier or EULA.

## 2026-08-15 — SubagentStop must emit empty JSON

Grok re-fires SubagentStop when the hook returns additional context. Emit `{}` and record a stop only while the agent id is active.

## 2026-08-15 — Unwrap one shell layer; reuse follow-ups only in the same open session

Strip one quoted shell `-c` or `-lc` payload before invocation matching. Reuse a route only for a true follow-up from the same session and never revive a closed route.

## 2026-08-14 — Match production side effects as argv prefixes

Split shell chains, strip wrappers and environment assignments, and compare leading argv tokens. This avoids path-text false positives while keeping real push, merge, workflow, publish, and release commands denied.

## 2026-08-14 — Rematch every non-follow-up; skip child briefs

Reuse the active route only for whole-prompt follow-ups or child-agent payloads. New work rematches so stale routes do not remove the required write owner.

## 2026-08-14 — Run unittest without a packaging marker

Detect top-level `tests/test*.py` and run unittest directly. Do not add a packaging marker solely to activate tests.

## 2026-08-14 — Bind receipts after the last change-package write

The tree fingerprint includes non-runtime change-package files. Record final verification and review evidence only after the last durable write, otherwise the receipts are immediately stale.
