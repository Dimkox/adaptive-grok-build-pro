# Release v2.0.19 with fail-closed factory issue fixes

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260923-release-v2-0-19-with-fail-closed-factory-issue-f-4317e6`
Created: 2026-09-23T03:02:16+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Prepare the next repository-owned release v2.0.19 from origin/main with bounded local guards related to #35/#39/#48 and owned fail-closed fixes for #73/#167, retain the #35/#36/#39/#48 external-owner disposition through #186, and exclude unrelated M8/DEV work; update release metadata only after the bugfix tree is verified.

## Outcome

The next release candidate contains bounded local fail-closed guards related to #35/#39/#48
and repository-owned fixes for #73/#167, with regression evidence retained. The original
#35/#39/#48 reports and #36 remain explicitly dispositioned through #186 where their external
owners or source seams are absent; this release makes no broad closure claim. No M8/DEV
observation work is included.

## Scope

### In scope

- #35-related local guard: parse each changed shell file with an independent `bash -n` invocation
  and reject an empty selection; the external `verify:deploy` report remains through #186.
- #39-related local guard: pass bounded repository-owned Python file lists to Ruff/Bandit and
  report the selected scope; the filed JavaScript/ESLint report remains through #186.
- #48-related local guard: make the repository-owned Trust CI smoke checks reject empty
  observations and unsafe producer/grep patterns, with executable fake-runtime tests; remaining
  external guard traps remain through #186.
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
  in this repository; the delivery PR may use `Fixes #73` and `Fixes #167` only, with `Refs #35,
  #36, #39, #48, #186` for the bounded/external dispositions.

## Constraints

- Backward compatibility: legacy `tree_fingerprint` grants remain readable during the migration
  window; historical evidence is not rewritten.
- Data/privacy: no new data source or secret is introduced; only opaque local evidence fields are
  renamed.
- Performance: focused static checks are cheaper only for an unambiguous landing-only diff; the
  release candidate itself still runs the full PR verifier.
- Operational: delivery remains PR-only and exact-SHA Trust CI-gated.
