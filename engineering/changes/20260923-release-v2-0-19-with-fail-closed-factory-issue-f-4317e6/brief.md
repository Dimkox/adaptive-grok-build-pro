# Release v2.0.19 with fail-closed factory issue fixes

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260923-release-v2-0-19-with-fail-closed-factory-issue-f-4317e6`
Created: 2026-09-23T03:02:16+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Prepare the next repository-owned release v2.0.19 from origin/main with fail-closed bug fixes for issues #35, #36, #39, #48, #73, and #167, keeping each issue implementation independently reviewable and excluding unrelated M8/DEV work; update release metadata only after the bugfix tree is verified.

## Outcome

The next release candidate contains repository-owned, fail-closed verification fixes for
#35, #39, #48, #73, and #167, with each issue's regression evidence retained. Issue #36
remains explicitly dispositioned as external/unowned through #186 because this repository
contains no shell recorder with the reported `if ! cmd; then code=$?` seam. No M8/DEV
observation work is included.

## Scope

### In scope

- #35: parse each changed shell file with an independent `bash -n` invocation.
- #39: pass bounded repository-owned file lists to Ruff/Bandit and report the selected scope.
- #48: make the repository-owned Trust CI smoke checks reject empty observations and unsafe
  producer/grep patterns, with executable fake-runtime tests.
- #73: emit neutral current grant-binding field names, preserve legacy reads, reject conflicting
  dual fields, and keep historical evidence byte-identical.
- #167: add an explicit fail-closed focused static SEO-landing verifier while retaining full PR
  verification for mixed or runtime-affecting changes.
- Release metadata update only after the combined fix tree passes focused checks and full PR
  verification.

### Out of scope

- Creating a new shell recorder for #36 without an owned source path; that disposition remains
  tracked by #186.
- M8/DEV evidence, autonomy activation, production deployment, Trust CI policy/holdout changes,
  GitHub Actions, secrets, private keys, or direct protected-branch writes.
- Closing unrelated backlog issues or claiming that local code fixes an external owner not present
  in this repository.

## Constraints

- Backward compatibility: legacy `tree_fingerprint` grants remain readable during the migration
  window; historical evidence is not rewritten.
- Data/privacy: no new data source or secret is introduced; only opaque local evidence fields are
  renamed.
- Performance: focused static checks are cheaper only for an unambiguous landing-only diff; the
  release candidate itself still runs the full PR verifier.
- Operational: delivery remains PR-only and exact-SHA Trust CI-gated.
