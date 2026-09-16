# Architecture — Release sync 2.0.16 to 2.0.17: identity bump R, artifact child A, tag release and successor SR per pinned doctrine

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`VERSION` and `adaptive_grok.__version__` read `2.0.16`; README, CHANGELOG, ROADMAP, `START_HERE.md` and `GROK_BUILD_HANDOFF.md` present `2.0.16` as both the product identity and the final state ("no release preparation remains"). `PROJECT_STATE.json` mirrors that: `product_version` `2.0.16`, `latest_published_release` `v2.0.16`, `current_unreleased_change.status` `no_new_release_candidate`, and `local_candidate` closed as `published`. Ten pull requests have merged since publication, so the identity no longer describes the tree a reader gets.

## Proposed behavior

`R` (this commit) moves the *candidate* identity to `2.0.17` and opens the pending slot; the *published* identity stays `v2.0.16`. The distinction is enforced structurally, not by prose: `published_release`/`prior_published_releases` remain the only records that assert existing artifact bytes, while `local_candidate` asserts their absence. `A` later adds exactly two tracked files (`packages/adaptive-grok-build-pro-v2.0.17.zip` + `.sha256`) and flips `local_candidate` to `artifact_bytes_delivered`; the tag and GitHub Release then bind to `A`'s merged commit; `SR` records the final publication facts.

## Components and boundaries

- Identity surface: `VERSION`, `.grok-stack/adaptive_grok/__init__.py`, `README.md`, `CHANGELOG.md`, `DARK_FACTORY_ROADMAP.md`, `START_HERE.md`, `GROK_BUILD_HANDOFF.md`.
- Machine-readable state: `PROJECT_STATE.json` (`product_version`, `observed_at`, `observed_main_sha`, `current_unreleased_change`, `local_candidate`, `delivered_change_history`).
- Lockstep consumers: `tests/test_structure.py`, `tests/test_project_state.py`, `tests/test_manifest_package.py`.
- Unchanged: `published_release`, `prior_published_releases`, `milestones`, `operational_qualification`, packaging scripts, `packages/` bytes, PostgreSQL migrations 001-018.
- Re-pointed currency pointers (not historical assertions): `work_inventory.open_pull_requests` (closed PRs removed, their records preserved byte-identical for the two that stay open), `trust_ci.last_success` (the "latest observed success" pointer moves to PR #94), `runtime_observations.evidence`/`observed_at`, and `active_delivery`'s route/branch/change_package/next_action mirror.

## Data flow

`git log`/GitHub API + the Trust CI store → this package's landing record and `PROJECT_STATE.json` → README/START_HERE/ROADMAP/CHANGELOG wording → test literals in the same commit. Verification rederives the facts from the frozen tree; nothing flows back from the docs into the release identifiers.

## API and event contracts

No HTTP, event or schema contract changes. `engineering/contracts/openapi` is untouched; the `contracts` block in the typed spec is empty by design.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: release-governance and documentation-currency rules as exercised by the `v2.0.15`/`v2.0.16` release-sync precedents.
- Applicable canonical example IDs/versions: none introduced.
- Open or overdue debt IDs: none created by this change.
- Expected governance handoff or receipt impact: `verification`, `security_review` and `release_review` receipts under `.grok-stack/runtime/receipts/` bound to the final tree fingerprint.

## Bitrix-specific impact

- Modules/events/agents/components affected: none (this repository is generic, not a Bitrix tree).
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: none; no installer or service file changes.
- Core modification: forbidden unless explicitly approved. Not applicable here.

## Decisions

- Candidate-vs-published split is proven by tests (absence assertion in `test_manifest_package.py`), not by a documentation caveat, following the `v2.0.16` precedent.
- Historical records are appended, never repointed: the post-publication landing facts go into a new `delivered_change_history` entry instead of editing the `v2.0.16` publication record.
- `R` deliberately carries no artifact bytes, so the release-sync commit can be reviewed and reverted without touching anything published.

## Risks and mitigations

- Stale literal in one of the three coupled test modules → run the trio plus `grok_verify --mode pr` on the frozen tree before opening the pull request.
- A merged pull request between `R` and `A` would ship outside the tagged ZIP → freeze the content PRs (#64 restack merged) before authoring `R`, and re-derive `observed_main_sha` at freeze time.
- Overstating release state in prose → `release_review` checks every `v2.0.17` sentence against the tree, and `FORBID-001` makes a premature publication claim a spec violation rather than a wording slip.
