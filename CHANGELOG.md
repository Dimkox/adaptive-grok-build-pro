# Changelog

## 2.0.14 — 2026-09-04

Published repository release for the offline L5 multimodal landing dogfood vertical.

- Adds six closed landing records, bounded private text/audio/image/PDF/DOCX intake, a fixed command-provider boundary with an unavailable default and sealed fixture, exact-SHA deterministic rendering/evaluation with a three-attempt ceiling, and a deterministic 19-member site artifact
- Adds four authenticated local landing operations with a route-specific bounded streaming body path; the existing 1 MiB JSON limit and all M0-M9 contracts/migrations remain unchanged
- Adds only a transport-free `UnavailableLandingPublisher`; no operational provider, network path, credentials, target mutation, live/indexed result, hosting action, or production authority is present
- PR #24 checked head `66a7fe5c4a59b3ea7e1350b34e0a547faf5a9f57` passed App-owned `adaptive-trust-ci/verified@06ecf1c875bc` (`SUCCESS`, check run `101099224099`, attestation `9defb556-f703-4a13-b20a-8b88aa6781b4`, signer `0519cf1d47436f2e`) and GitGuardian (`SUCCESS`), then merged at `2026-09-04T16:56:37Z` as `1751b5855e46782b9a1bfceb6e1ab0102cba03b0`, preserving reviewed tree `618df086920c92179aa0e22a8c8d4ad30ebd9230`
- GitHub Release `v2.0.14` was published at `2026-09-04T16:58:48Z`; `packages/adaptive-grok-build-pro-v2.0.14.zip` has SHA-256 `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`, and its sidecar file has SHA-256 `1a961c35b8f12fa02579ec7888c889f0ae7ca8656b158eb731681ef8357caf3c`
- Published `v2.0.13`, PR #22, merge `8599d45f4f28285381b05a53feb3059de92eb2a8`, and their artifact remain immutable historical facts; repository publication does not establish an operational provider, hosting, M8 cohort/activation, or production authority

## 2.0.13 — 2026-09-02

Published M4-M9 repository product release.

- Product identity **2.0.13** across `VERSION`, repository documentation, and the tracked `adaptive_grok` runtime; Trust CI service identity remains separately **2.1.0**
- Integrates the M4 durable control plane, M5 bounded execution, M6 semantic validation, M7 shadow handoff, M8 earned-autonomy evaluation, and M9 local staged-delivery/recovery source while preserving migrations `001`-`018`
- M9 is deliberately local-only: it provides immutable delivery records, deterministic preview/staging/bounded-canary decisions, a sealed in-memory environment, and least-authority recovery without an operational adapter, persistence, credentials, provider access, or production authority
- Repairs roadmap/state parity, claim-terminal lease races, all-runtime database bounds/typed availability, fail-closed role bootstrap, and persisted accepted retry limits through additive migration `013`
- Audits legacy schema-12 retry exhaustion without advancing a fence or creating a lease, and makes release packaging derive inventory and bytes from filtered, clean, exact Git `HEAD` while independent shipped-artifact tests reject ambient ignored/untracked members
- PR #22 checked head `b5eba759c309a92f92f4d4003d025795c7f8a1f9` passed App-owned `adaptive-trust-ci/verified@06ecf1c875bc` (`SUCCESS`, check run `100955508827`, attestation `74f1bbb2-3098-4d35-a42f-d49351d81c4a`) and merged to `main` as `8599d45f4f28285381b05a53feb3059de92eb2a8`, tree `03e122a30fb2dbb59907f4c4c28e17f93cbf0751`
- GitHub Release `v2.0.13` was published at `2026-09-04T08:33:19Z`; `packages/adaptive-grok-build-pro-v2.0.13.zip` has SHA-256 `3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c`
- Binds sensitive hook policy and denial evidence to the unique effective repository root, including nested workdir aliases and literal `cd`/`git -C` shell overrides, without recording raw commands
- Preserves the M4 repair source and integrates M5-M9 additively as the delivered repository product; factual M8 cohort/activation and real signed M9 environment/provider deployment remain operational gaps
- The intermediate `aa12e7c` verifier receipt and earlier candidate artifacts remain historical evidence superseded by the exact PR #22 checked head and published tag; later documentation-only commits do not restack `v2.0.13`

## 2.0.12 — 2026-08-23

Self-hosted Trust CI control plane in-tree, K16 README graph, optional docker/syft/trivy/cosign toolchain pins.

- Product identity **2.0.12**; Trust CI service identity stays **2.1.0**
- PR-only delivery; rebase-merge of draft PR #2 is a bootstrap exception because the App-owned check is not live yet
- Example image pins stay placeholders; live registry pins stay untracked
- Still no GitHub Actions

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
- Coverage.py report in `pr`/`release` after a measured fail-under of 74 (ratchet, not a guessed 90)
- No GitHub Actions / Dependabot; local `python3 scripts/grok_verify.py --mode pr` is the only gate. `--with-ci` is forbidden.
- Optional consumer Semgrep / Trivy config / npm prettier|format when those signals exist; not enabled on this tree

## 2.0.5 — 2026-08-15

After `git pull` on a consumer project, missing or cwd-relative hook scripts no longer lock Grok.

- Root hook files are thin dispatchers into `.grok/hooks/` (no root `_lib.py`)
- `adaptive.json` commands try `.grok/hooks/…` then the cwd shim, then print `{}` / allow
- Installer copies those shims so older `python3 pre_tool_use.py` configs keep working
- Toolchain pins (built / minimum / fallback) in `.grok-stack/config/toolchain.json`; doctor offers install of the fallback or a newer version
- `install_into.py` pulls missing required toolchain tools by default (`--no-deps` to skip, `--all-deps` for optional PHP/Node/gh)
- `routing.json` is live: analysis floor is `repo_explorer` / `task_analyst` / `architect` / `docs_researcher` on non-micro work; `max_parallel_analysis` (default 10) is a ceiling, not a quota; still exactly one write owner

## 2.0.4 — 2026-08-15

Soft / fail-open hooks so the agent cannot lock itself out.

- `grok_verify` runs `python-unittest` when `tests/test*.py` exist, even without `pyproject.toml` / `requirements.txt` / `setup.py`
- `pre_tool_use.py`: on any exception or import failure → **allow** (was hard deny via exit 2)
- `stop_gate.py`: missing/stale evidence → **warn only**, never block stop; missing route → allow
- Policy still blocks truly destructive/secret paths when it runs successfully
- Docs: how to disable hooks entirely if needed
- Production policy matches command invocations (`git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`), not bare words in paths or arguments
- One-layer `bash`/`sh`/`zsh`/`dash`/`ksh -c`/`-lc` payloads are unwrapped before production-invocation matching
- Follow-up reuse (`делай`, `continue`) requires the leftover route to be the same session and not closed
- `_python` unittest discovery matches top-level `tests/test*.py` (not nested rglob); pytest-wins is characterized
- `SubagentStop` emits `{}` and records a stop once; extra host retries no longer append history or feed `additionalContext`
- UserPromptSubmit rematches any non-follow-up request (including `repair yourself`) and ignores child-agent briefs
- `.grok/hooks/adaptive.json` commands are path-qualified so Grok does not load stray root hook copies
- Prepare-only `scripts/grok_deploy.py`: dry-run prints human publish commands; `--record` requires production approval and writes receipt `deploy`/`prepared`
- This-repo GitHub Actions: verify plus a conditional package job (no publish)
- README: commercial-grade product that is free, public, and MIT (no EULA, no paid tier)
- Risk classifier matches `прод` as a word, not as a substring of `продукт`

## 2.0.3 — 2026-08-14

- Rename remaining Codex branding to Grok (`ADAPTIVE GROK ROUTE`, zip prefix, installer markers)
- README complete-graph of the stack

## 2.0.2 — 2026-08-14

Full git + release artifacts.

- Versioned zips and checksums are tracked under `packages/`
- GitHub Release `v2.0.2` ships zip, sha256, and source tar.gz

## 2.0.1 — 2026-08-14

Patch after 2.0.0 for a clean human-owned tag.

- Version source of truth is `VERSION`; packager default output follows it
- Ready-to-publish zip: `dist/adaptive-grok-build-pro-v2.0.1.zip`

## 2.0.0 — 2026-08-14

First working Adaptive Grok Build Pro release.

- Task routing, quality profiles, change packages, and fingerprint-bound receipts
- Domain skills under `.grok/skills/` with a mirror in `.agents/skills/`
- 21 managed agents under `.grok/agents/`
- Grok lifecycle hooks (route, policy, stop gate, evidence invalidation)
- Installer copies `.grok`, `.agents`, and `.grok-stack` without deleting unrelated agent files
- Local verification: `make doctor` / `make verify` / `python3 -m unittest discover -s tests`
- Packaging excludes `.env`, `.env.*`, and private-key files from the zip/manifest
