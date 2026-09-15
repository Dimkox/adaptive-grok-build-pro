# Release sync 2.0.16 to 2.0.17: identity bump R, artifact child A, tag release and successor SR per pinned doctrine

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260915-release-sync-2-0-16-to-2-0-17-identity-bump-r-ar-f98796`
Created: 2026-09-15T20:24:34+00:00
Risk: high
Complexity: high-risk
Domains: release-governance, documentation, test-infra

## Problem

Twelve pull requests merged after the immutable `v2.0.16` publication (`2026-09-13T22:04:08Z`): #81 the release-record successor, #82 draft-decode canonicalization, #83 offline recovery tests, #85 runtime-closure docs, #88 Grok reasoning usage, #89 current-state reconciliation, #90 README focus, #91 durable provider failover, #93 workflow artifact adapters with the pinned upstream component contract, #13 repository-scoped immutable Trust CI profiles, #64 the Caroline cross-project confirmation and #94 the `ctime`-granularity repair that made the mandatory gate command deterministic. The tree still announces `2.0.16` as both the product identity and the released state, and `PROJECT_STATE.json` asserts that no release preparation remains. Both statements are now false: readers cannot tell what the next release will contain, and the packaging tests pin an identity that no longer matches the source.

## Outcome

`main` carries a truthful `2.0.17` **candidate** identity: every human-readable surface and every coupled test literal names 2.0.17 as the in-preparation product, while `published_release` continues to describe only the real, immutable `v2.0.16`. A reader of a fresh clone can see exactly which merged work the next release will ship and that no `v2.0.17` artifact, tag or activation exists yet.

## Scope

### In scope

- `VERSION`, `adaptive_grok.__version__`, README title and identity line, CHANGELOG `2.0.17` section, ROADMAP identity lines, `START_HERE.md` and `GROK_BUILD_HANDOFF.md` current-state wording.
- `PROJECT_STATE.json`: `product_version`, `observed_at`/`observed_main_sha`, `current_unreleased_change` opened as the 2.0.17 record, `local_candidate` opened as a pending 2.0.17 slot with the ZIP pair asserted absent, and `delivered_change_history` carrying the post-publication landing record.
- Lockstep test anchors in `tests/test_structure.py`, `tests/test_project_state.py` and `tests/test_manifest_package.py`.

### Out of scope

- Building or committing the `v2.0.17` ZIP+sidecar (artifact child `A`), pushing the tag, publishing the GitHub Release, and the post-publication documentation successor `SR`.
- Any provider installation, host mutation, service restart or operational activation.
- The published `v2.0.13`-`v2.0.16` records and the frozen PostgreSQL migration range 001-018.

## Constraints

- Backward compatibility: additive only; released artifact digests and historical milestone records are byte-unchanged.
- Data/privacy: no credential, private key, host identity or machine-local runtime state may enter the diff.
- Performance: not applicable (identity and documentation surface only).
- Operational: the release sequence is `R -> merge -> A -> merge -> tag + GitHub Release -> SR`; each step needs its own exact delegated grant, and `A` cannot self-record its own merge identity.
