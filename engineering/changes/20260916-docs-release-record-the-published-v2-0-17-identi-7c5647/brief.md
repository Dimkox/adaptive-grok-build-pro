# docs(release): record the published v2.0.17 identity, tag object and artifact digests (SR)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260916-docs-release-record-the-published-v2-0-17-identi-7c5647`
Route: `7c56479f61d3` (base the artifact-child merge `c86b1a1`)
Risk: high

## Problem

Tag `v2.0.17` (object `5c6687ed…`) binds the merged artifact-child commit `c86b1a1…` and the GitHub Release ships the ZIP+sidecar, but the tree still described that release as an unpublished candidate: `published_release` named `v2.0.16`, `local_candidate.published` was false and `current_unreleased_change` still asked the reader to tag and publish. A clean clone would contradict the repository's own release.

## Outcome

`SR` closes the chain: the record states the published release with recomputable evidence, `v2.0.16` is archived as history rather than rewritten, the delivery pointers follow the published chain, and `operational_activation` remains false because publication is repository delivery only.

## Scope

### In scope

- `published_release`, `prior_published_releases`, `latest_published_release`, `local_candidate`, `current_unreleased_change`, `active_delivery` pointers and a fresh dated runtime observation dossier bound to this base;
- README, START_HERE, ROADMAP, CHANGELOG, GROK_BUILD_HANDOFF, `packages/README.md`;
- the coupled literals in `tests/test_structure.py`, `tests/test_project_state.py` and `tests/test_manifest_package.py`;
- `mistakes.md`: the recorded process defects of this release cycle.

### Out of scope

- any product code, packaging script or artifact byte;
- installation, restart, activation or deployment of the L5 services;
- the immutable bytes of every earlier release.
