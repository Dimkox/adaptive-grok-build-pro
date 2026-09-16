# Requirements — Release sync 2.0.16 to 2.0.17: identity bump R, artifact child A, tag release and successor SR per pinned doctrine

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001: Given a frozen tree after this commit, when `tests/test_structure.py::test_version_identity_matches_readme` runs, then `VERSION`, the README `# Adaptive Grok Build Pro v2.0.17` H1, `Identity: **2.0.17**`, the CHANGELOG top section `## 2.0.17 — 2026-09-15 (candidate, unpublished)`, the ROADMAP `product version: 2.0.17 candidate (latest published release: v2.0.16; published 2026-09-13T22:04:08Z)` line and `adaptive_grok.__version__` all agree.
- [x] AC-002: Given `PROJECT_STATE.json`, when `tests/test_project_state.py` asserts the release facts, then `product_version` is `2.0.17`, `latest_published_release` and `published_release.tag` remain `v2.0.16`, and the post-publication landing record names each of the twelve merged pull requests with its merge commit, checked head and App-owned check-run identifier.
- [x] AC-003: Given `local_candidate` as a pending 2.0.17 slot, when `tests/test_manifest_package.py` runs, then `published` is false, the identity fields are null, and `packages/adaptive-grok-build-pro-v2.0.17.zip` and its sidecar are asserted **absent** from `packages/`.
- [x] AC-004: Given a clean clone of this commit, when a reader opens `START_HERE.md` or the README current-state section, then the text states that `v2.0.16` is the only published release, that a `2.0.17` candidate is in preparation, and that no `v2.0.17` artifact or tag exists.

## Failure and edge cases

- A test literal left at `2.0.16` while docs say `2.0.17` (or the reverse) breaks lockstep: the trio plus `grok_verify --mode pr` must run on the **frozen** tree, not on a partially edited one.
- Claiming `published: true`, a tag, or artifact bytes in `R` is a forbidden outcome (`FORBID-001`), not a documentation preference.
- `delivered_change_history` must not restate a pre-publication assertion with a repointed value; archived records are copied verbatim and only genuinely new facts are added.
- The candidate ZIP path in the absence assertion must match the packaging script's naming exactly, otherwise `A` would add files that no test pins.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: release-governance (immutable published artifacts, `R -> A -> tag -> SR` sequence), documentation currency (bootstrap truth at clean-clone read).
- Canonical-example deviations and evidence: none; the `v2.0.16` release-sync package `20260913-v2-0-16-release-sync-identity-bump-to-2-0-16-pub-105344` is the followed precedent.
- Intentional debt created, repaid, or accepted: none created. The retained `v2.0.16` "no release preparation remains" wording is removed here rather than left stale.

## Non-functional requirements

- Security: no secret, key, host path beyond established repository patterns, or machine-local runtime state in the diff (`FORBID-002`); route `f98796afe7de` requires a `security_review` receipt.
- Reliability: identity claims must be reproducible from Git, the GitHub API and the tracked `packages/` assets alone.
- Performance: not applicable.
- Observability: the exact-head `adaptive-trust-ci/verified@06ecf1c875bc` check plus the three coupled unittest modules are the success signals.
