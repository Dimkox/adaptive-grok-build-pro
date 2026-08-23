# Changelog

## Unreleased — trust boundary

Published identity remains `2.0.11`; these changes are proposed through the protected pull-request path.

- Added exact-SHA GitHub `trusted-ci` for Python 3.10 and 3.12 plus deterministic package construction
- Added strict verification: missing Ruff, Bandit, or Coverage.py fails authoritative checks
- Added a `production` Environment release workflow that verifies, packages, tags, and publishes the exact merged `main` SHA
- Converted `grok_approve.py` from a local grant into a non-authorizing request bound to route, Git HEAD, and tree fingerprint
- Made production commands, workflow dispatch, MCP writes, and control-plane edits non-bypassable from Grok policy
- Added CODEOWNERS and the branch-protection and Environment runbook in `docs/TRUST-BOUNDARY.md`
- Superseded direct-push and local-only quality-gate standing rules

## 2.0.11 — 2026-08-17

Skip the analysis/review wave when nothing product-changed; always push `main` and release when green.

- `AGENTS.md`: Skip no-op checks; Release when green now names `git push origin main`
- Same product surface as 2.0.10 plus this contract
- Still no GitHub Actions

## 2.0.10 — 2026-08-16

Published identity of current main after `v2.0.9`.

- Same product surface as 2.0.9 plus this version identity
- Standing rule still: green verify → new release
- Still no GitHub Actions

## 2.0.9 — 2026-08-16

Published identity of current main after `v2.0.8`.

- Same product surface as 2.0.8 plus this version identity
- Standing rule still: green verify → new release
- Still no GitHub Actions

## 2.0.8 — 2026-08-16

Agent self-learning, root memory files, and a complete-graph README.

- `AGENTS.md` starts with log-to-root `decisions.md` / `mistakes.md`
- Standing rules: refresh README before every push/deploy; split large tasks; share `AGENTS.md` / `decisions.md` / `mistakes.md`; publish a new release when verify is green
- README is the product map: Current state, Read first, Map, K10 complete graph
- Structure tests lock those placements
- Still no GitHub Actions

## 2.0.7 — 2026-08-16

Leftover 2.0.6 product fixes, published as their own release.

- `install_into` copies `ruff.toml`, `bandit.yaml`, and `.coveragerc`
- `grok_deploy` prints `--title "Adaptive Grok Build Pro v…"`
- `package_stack` unlinks leftover root `MANIFEST.sha256` after the zip embeds it
- `__version__` matches `VERSION`
- Stop hook wording is warn-only
- Still no GitHub Actions

## 2.0.6 — 2026-08-16

Quality contour: Ruff, Bandit, coverage ratchet, no GitHub Actions.

- `grok_verify` runs Ruff from `ruff.toml` without a packaging marker; skip-if-missing, fail-closed when ruff/bandit/coverage are installed
- Bandit AST next to regex `secret-scan`; excludes `tests/` and `engineering/`
- Coverage.py report in `pr`/`release` after a measured fail-under of 74
- Local `python3 scripts/grok_verify.py --mode pr` was the only gate in this published version
- Optional consumer Semgrep, Trivy config, and npm prettier or format run only when those signals exist

## 2.0.5 — 2026-08-15

After `git pull` on a consumer project, missing or cwd-relative hook scripts no longer lock Grok.

- Root hook files are thin dispatchers into `.grok/hooks/`
- `adaptive.json` commands try `.grok/hooks/`, then the cwd shim, then a fail-open response
- Installer copies those shims so older hook configs keep working
- Toolchain pins live in `.grok-stack/config/toolchain.json`
- `routing.json` is live and still permits exactly one write owner

## 2.0.4 — 2026-08-15

Soft and fail-open hooks so the agent cannot lock itself out.

- `grok_verify` runs unittest when `tests/test*.py` exists without a packaging marker
- `pre_tool_use.py` allows on infrastructure exceptions
- `stop_gate.py` warns about evidence and never blocks stop
- Production policy matches command invocations rather than words inside paths
- One shell `-c` layer is unwrapped before matching
- Follow-up reuse requires the same open session
- `SubagentStop` emits empty JSON and records a stop once
- Prepare-only deploy tooling prints human commands without executing them
- Risk classification matches `прод` as a word, not as part of `продукт`

## 2.0.3 — 2026-08-14

- Renamed remaining Codex branding to Grok
- Added the README complete graph

## 2.0.2 — 2026-08-14

- Versioned ZIPs and checksums are tracked under `packages/`
- GitHub Release `v2.0.2` ships ZIP, SHA-256, and source archive

## 2.0.1 — 2026-08-14

- `VERSION` is the package-name source of truth
- Prepared `dist/adaptive-grok-build-pro-v2.0.1.zip`

## 2.0.0 — 2026-08-14

First working Adaptive Grok Build Pro release.

- Task routing, quality profiles, change packages, and fingerprint-bound receipts
- Domain skills under `.grok/skills/` with a mirror in `.agents/skills/`
- Managed agents under `.grok/agents/`
- Grok lifecycle hooks for route, policy, stop, and evidence invalidation
- Installer copies the stack without deleting unrelated agent files
- Local verification through Make and unittest
- Packaging excludes `.env`, `.env.*`, and private-key files
