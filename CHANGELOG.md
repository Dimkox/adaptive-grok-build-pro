# Changelog

## 2.0.19 — 2026-09-22 (candidate, unpublished)

Fifteen pull requests merged after `v2.0.18` are recorded in the candidate state. This section names the next product identity; the ZIP, sidecar, tag and GitHub Release remain pending the exact artifact-child delivery.

- Carries the release-successor, architecture, verification, installer, landing, routing, evidence, schema, package-diagnostics and merge-gate repairs through PRs #111, #112, #113, #114, #115, #116, #149, #150, #151, #154, #170, #173, #174, #184 and #185.
- Binds candidate identity and source provenance to `130ce4a42d9f9bbd1b56772d40b19ae530283205` and the isolated `v2.0.19` release-sync tree.
- Keeps published `v2.0.18` bytes immutable and preserves the separate artifact-child/package and no-deployment boundaries.

## 2.0.18 — 2026-09-16

Four pull requests merged after `v2.0.17` was published. This section records the landed source on `main` and its publication: that source was archived by the artifact child and shipped through tag `v2.0.18`.

- Streams oversized tracked binaries from a bounded 64 KiB reader that hashes while reading and re-checks the dev/ino/size/mtime identity afterwards, so a 10.9 MB tracked artifact no longer refuses architecture analysis (PR #101, checked head `b40fd1a4`, App check `104681990219`, merged `2026-09-16T06:14:17Z` as `83925c1`)
- Puts the release-chain landing convention in view and records the inspected failure causes behind closed pull requests #15, #21 and #33 in the work inventory (PR #102, checked head `3f93e7bd`, App check `104704114422`, merged `2026-09-16T07:52:29Z` as `98b7769`)
- Adds the `qwen-omni-intl` profile — capability proven live (HTTP 200 with image and audio token accounting on the international endpoint; mainland control 401 with the same key) — and classifies operator probe failures through the shared executor taxonomy; closes issue #87, advances #86 for the product half, and files the frozen-contract defect #104 (PR #105, checked head `30fea4e3`, App check `104740673782`, merged `2026-09-16T09:51:33Z` as `ad4d636`)
- Closes the omni change package on its exact delivery evidence (`draft→ready` with per-transition reasons, tasks carrying head-SHA facts) (PR #106, checked head `0a99a4d6`, App check `104754117579`, merged `2026-09-16T10:34:51Z` as `d146ca4`)

## 2.0.17 — 2026-09-16

Twelve pull requests merged after `v2.0.16` was published. This section records the landed source on `main` and its publication: that source was archived by the artifact child and shipped through tag `v2.0.17`.

- Records the published v2.0.16 release identity in the documentation successor, so the release record and the tag agree (PR #81, checked head `26e08254`, merged `2026-09-14T00:11:30Z` as `6d8f6ab`, App check `103814853460`)
- Fixes the L5 draft decode path so model section-item order is canonicalized before validation, closing a live-path bug where an equivalent ordering failed repair (PR #82, checked head `6bd86207`, merged `2026-09-14T02:16:49Z` as `5f6f6ce`, App check `103833535728`)
- Executes the offline backup/restore boundaries as real factory tests instead of relying on the web-stack fixture coupling (PR #83, checked head `77debe55`, merged `2026-09-14T06:13:25Z` as `31725f1`, App check `103872943772`)
- Records the PR #82 runtime closure and the landing-preservation decision in project memory (PR #85, checked head `9c147455`, merged `2026-09-14T06:49:45Z` as `e7e8ad1`, App check `103880103525`)
- Reconciles Grok reasoning-token usage so separately reported reasoning tokens are accounted instead of dropped (PR #88, checked head `4e94f7a9`, merged `2026-09-15T08:00:34Z` as `61a05da`, App check `104295309671`)
- Reconciles the published release record with the observed live Qwen and Grok runtime state (PR #89, checked head `5b03c1f1`, merged `2026-09-15T10:30:55Z` as `02ac8c3`, App check `104339301084`)
- Removes the decorative README graph and clarifies the package guidance (PR #90, checked head `af8419e6`, merged `2026-09-15T11:30:57Z` as `7b14736`, App check `104356296867`)
- Adds the durable Qwen → Grok → OpenAI → Claude → OpenRouter landing failover with capability/attempt APIs and atomic SQLite observations (PR #91, checked head `55deafba`, merged `2026-09-15T16:00:39Z` as `b6fe340`, App check `104440253101`)
- Lands the workflow artifact adapters that compile Spec Kit, BMAD and Superpowers artifacts into the advisory model, with ADR-0001 and the `workflow_sources` upstream version contract pinning superpowers 6.3.0, BMAD 6.12.0 and spec-kit 1.0.7 (PR #93, checked head `9086f2bc`, merged `2026-09-15T20:03:41Z` as `280cbff`, App check `104536573008`)
- Adds repository-scoped immutable Trust CI profiles: commands and external holdouts are selected by exact repository, jobs, approvals, checks, replays and attestations bind to the selected policy digest, and catalog holdouts stay confined to paired server-owned trusted roots while legacy schema-v1 behavior is preserved (PR #13, checked head `6130fbb8`, merged `2026-09-15T21:03:37Z` as `4383115`, App check `104552079057`). The capability is source-only: the deployed policy, holdout bundle and branch protection are unchanged
- Records the Caroline cross-project confirmation as dated, source-pinned observation material with an explicit zero M8 qualifying-task contribution and no activation (PR #64, checked head `45ccb04f2e524d27f97a1b49cb89db65294e891e`, App check `104567389767`, merged `2026-09-15T21:42:34Z` as `01d64e5`)
- Makes the serialized-CAS adversarial preconditions independent of filesystem `ctime` granularity, removing an intermittent failure of the mandatory `root-unittest` gate command (PR #94, checked head `9437efed`, App check `104591923631`, merged `2026-09-15T22:58:12Z` as `7bbf425`)
- Delivers the `v2.0.17` ZIP and sidecar as tracked bytes built twice byte-identically from the merged release-sync tree, and publishes them through tag `v2.0.17` and the GitHub Release with both assets (PR #99, checked head `bbc5cdd9`, merged `2026-09-16T01:14:19Z` as `c86b1a1`, App check `104621989321`)

## 2.0.16 — 2026-09-13

Assembled L5 production runtime source landed on `main` as the attested tree-identical union of seven delivery slices.

- Lands the seven-slice L5 delivery stack as one union commit `eb9df64bca333f30ec58f8c725a021360e22ed92` (PR #75, checked head `ac7ae2def67a267c227ab5703843337d4bb6f4be`, merged `2026-09-13T17:35:51Z`) whose tree is byte-identical to the externally attested G head `e6a813e4c16543f262ced2d9ea353caaad9452d1`, tree `1c8d72a50c0631c0222d111de1403ace4347aab2`
- Adds complete landing import boundaries with exact module-level exceptions covering every landing module and a forbidden network/store/trust check (slice A #65, head `450d62d41ab5f94b72217a1e18f9f60231d6af6f`, check run `103739437925`, merged `2026-09-13T17:07:11Z` as `ede6686`)
- Advances the sealed landing source epoch to `fde60e040167c10975b00d11f578c4da6763069a` / tree `21817e70e079b772e1f3114a80dfc0320d1ada91` with the 22-member deterministic deploy inventory, which excludes the source-only documents `ASSETS.md` and `SERVER-SETUP.md`, while retained readers keep the historical 19- and 20-member layouts (slice B #66, head `d4d070a2defd9d0f8921331e38fb746fc95f38fe`, check run `103741784270`)
- Adds the independently versioned provider-evidence v2 contract, retained-envelope reader and mixed-version persistence, rejecting crossed versions and tampered evidence before any HTTP producer exists (slice C #67, head `9ce156e0128b4f18b3fccfeca9a8edc7175da090`, check run `103744221871`)
- Adds bounded HTTP/Qwen/Grok models and the durable landing runtime: strict media/SSE decoding, isolated PDF worker, explicit live composition and lifetime-owned landing SQLite, with validation and ownership preceding credential acquisition and default-off unavailable behavior preserved (slice D #68, head `bb93885034e52b80653efd96602fec182f7db10a`, check run `103746737270`; security, data and release reviews additionally passed)
- Adds closed private host configuration and the dedicated authenticated Unix landing host with the `adaptive-landing-server` entrypoint, which composes landing SQLite without constructing the broader Factory PostgreSQL store (slice E #69, head `d33e8d8b2aa06a76f32724d08d79a21f3604ce42`, check run `103749191245`)
- Adds authorized filesystem publication with immutable staging, explicit activation and predecessor restoration, durable SQLite intent and observation-only reconciliation after uncertain effects (slice F #70, head `c3f60f09b819c1a246f7af2dcd6664cf3be52dd6`, check run `103751615594`; security, data and release reviews additionally passed)
- Adds bounded offline snapshot/restore and the complete inactive runtime, including the unexecuted installer, service and configuration templates and the final mixed v1/v2 recovery and publication-bundle integration (slice G #71, head `e6a813e4c16543f262ced2d9ea353caaad9452d1`, check run `103754091998`)
- Carries the per-slice App-owned `adaptive-trust-ci/verified@06ecf1c875bc` attestation on each exact head, serially from `14:36:58Z` to `16:46:55Z`; the union head carries its own attestation (`SUCCESS`, check run `103760385178`) and its own GitGuardian `SUCCESS` (`103760298185`). GitGuardian passed on A-F; its `failure` `103749698672` on the G head is the dispositioned generic-detector false positive on a 64-hex grant digest (issue #73), not a credential and not a merge gate
- Closes #66-#71 as landed-by-content with pointers to #75 (the ledger records G as superseded-by-union) rather than rebasing six slices with six fresh serial verifications; the union adds no new product logic, and the full Git union audit against the frozen monolith `f31406e970d67f7cd59694da5de88915adb0fa68` leaves exactly ten product/test differences with explicit dispositions
- Ships the seven change packages under `engineering/changes/20260913-l5-split-*` with the landed source; the machine-readable ledger `engineering/reviews/l5-delivery-stack.json`, the delivery and evidence summaries, the defensive case map, the two current-head delegated local run records, the per-slice final verifier results, independent review reports and fingerprint-bound local receipts arrived with PR #72, merged at `2026-09-13T18:26:32Z` as `e737dd5`, and are immutable history
- Records the two delegated local runs on the G head: one fixed synthetic provider probe closed `normalized` in 3,352 ms, and one disposable private-clone Unix-socket host run that first failed closed on a trusted-ancestry violation before credential acquisition and then closed `needs_human`/`http_outcome_unusable` with an unauthenticated 401, no artifact and no service persistence. Neither is Omni/multimodal, hosting or production acceptance
- Lands the post-landing hardening (PR #77): the contract-inventory exact-count pin becomes a derived set-equality with duplicate guard and seed floor (issue #60), `PROHIBITED_DEPLOY_MEMBERS` moves into production with an import-time self-check and a per-epoch path-component guard that names the offending member (issue #61), and the digest-pinned PDF worker now executes as the real isolated child in factory tests (issue #63 residual)
- The ZIP+sidecar artifact child, tag `v2.0.16` and GitHub Release are published (2026-09-13T22:04:08Z, targeting the protected merge of the artifact-child commit). Still pending: operational activation. No installation, service creation or hosting publication occurred

## 2.0.15 — 2026-09-05 (published 2026-09-05T20:17:20Z)

Local PR candidate for the disabled-by-default single-operator design-partner pilot.

- Adds five closed digest-linked pilot outputs, one exact landing target/base profile, a private restart-safe SQLite ledger, and exact writer/evaluator workspace boundaries
- Pins one Codex start, one credential-free unittest command, deterministic version/status/CSP semantics, and terminal no-retry recovery
- Adds literal operation-digest grants, one non-force branch ref and one draft PR command boundary with observation-only recovery after ambiguity
- Adds built-in default-off `prepare`, `publish-branch`, `publish-proposal` and read-only `status` phases, one bounded Codex app-server `gpt-6-astra` path using opaque host ChatGPT auth, pinned narrow `gh`/Git adapters, current-control grant rebinding and exact private-workspace recovery; no live model, target mutation, push, PR, merge, deployment, tag or release occurred while preparing this source
- Preserves published `v2.0.14` and `v2.0.13` artifacts byte-for-byte; final local `2.0.15` packaging uses source parent `R` plus a ZIP+sidecar-only unpublished artifact child `A`

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
