# Fix issue #167: select focused static SEO landing verification for landing-only changes while retaining full PR verification for runtime, contract, Trust CI, package, architecture, or workflow changes, with regression tests.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260922-fix-issue-167-select-focused-static-seo-landing-757d30`
Created: 2026-09-22T19:14:43+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

The repository's normal PR verifier runs broad runtime, contract, architecture, governance, factory/PostgreSQL, and Python checks even for a standalone static SEO landing. Issue #167 requires a bounded landing contract path without weakening verification for any mixed, unknown, or infrastructure-adjacent diff.

## Outcome

For a diff containing exactly one static landing directory under `side-projects/seo-landings/**` and exactly one explicitly named focused landing test, maintainers can run `python3 scripts/grok_verify.py --mode focused-static-seo-landing --no-record --json` and receive only scope, diff-integrity, source-stability, and that contract-test result. Any other path, missing/ambiguous inventory, or multiple landing directories is rejected by the focused mode; the operator then uses full `--mode pr`.

## Scope

### In scope

- Fail-closed changed-file classification for one landing directory plus one focused test, with trusted Git status/rename/copy provenance.
- Explicit `focused-static-seo-landing` CLI mode and workflow-command allowlisting.
- Regression coverage for accepted scope, mixed/excluded/unknown paths, malformed inventory, missing or multiple tests, multiple landing directories, unsafe file statuses, PR no-downgrade, and rejected-scope subprocess suppression.
- Documentation of the safe default and Trust CI boundary.

### Out of scope

- Automatic route-time guessing, an `auto` mode, or changes to prompt routing.
- Changes to landing content, the SEO skill, showcase, runtime, contracts, Trust CI, packages, architecture, workflow policy, factory, PostgreSQL, or full PR verification behavior.
- Replacing or weakening the App-owned exact-SHA Trust CI merge check.

## Constraints

- Backward compatibility: `--mode pr` remains the full verifier and never silently downgrades.
- Data/privacy: no data, credentials, services, or external systems are touched.
- Performance: focused mode runs one explicitly named landing contract and bounded Git checks.
- Operational: focused mode is the safe default only after changed-file classification proves landing-only scope; otherwise use full PR verification.

## Evidence status

- RED baseline: the analysis report recorded that no landing-specific mode existed, `--mode fast` still ran common/full checks, and the workflow allowlist accepted only `fast` and `pr` (`evidence/analysis-repo_explorer.md`).
- GREEN repair evidence: 17 focused verifier cases, 2 Git-status cases, and 1 workflow allowlist case passed, including status provenance, PR no-downgrade, rejected-scope suppression, selector normalization, landing/test binding, unittest-contract validation, focused execution, and workflow allowlist coverage.
- Focused CLI smoke: `python3 scripts/grok_verify.py --mode focused-static-seo-landing --no-record --json` exited `1`, passed `git-diff-check`, failed `scope-selection` with `out-of-scope or invalid changed paths are present`, and did not run the landing contract or broad suite; this is expected for the current mixed implementation/documentation tree.
- The prior full verifier PASS is stale after this repair and package edit. Full `python3 scripts/grok_verify.py --mode pr`, fresh independent reviews, and final fingerprint-bound evidence remain pending.
