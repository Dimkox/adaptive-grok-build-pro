# Fix issue157 repository language classifier: bounded Swift and other language signal detection, symlink-safe manifests, truncation and unknown reporting without suppressing detected signals.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261002-fix-issue157-repository-language-classifier-boun-628083`
Created: 2026-10-02T22:27:56+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Fix issue157 repository language classifier: bounded Swift and other language signal detection, symlink-safe manifests, truncation and unknown reporting without suppressing detected signals.

## Outcome

Repository profiles retain confirmed routing languages and separately disclose recognized source/manifest languages. Swift has bounded positive evidence; scan exhaustion, unknown candidates, unreadability and unsafe filesystem paths have explicit outcomes.

## Scope

### In scope

- `.grok-stack/adaptive_grok/repo.py`, `tests/test_repo_language_disclosure.py`, and this contour-local package.
- Reconstruct approved design contour C on actual baseline `e5856acfd4bc7a186f40a740b54ec86459462db5`, then integrate actual fetched main before coordinator verification.

### Out of scope

- Router precedence (owned by B), version/state/release aggregates, macOS/U4 qualification, deployment, publication and historical evidence imports.
- Existing dirty worktrees are read-only source references and remain untouched.

## Constraints

- Backward compatibility: keep kind/languages/domains/signals/bitrix_modules/package_scripts, including legacy canonical manifest language ordering. Add detected_languages and language_scan; non-Swift extension-only evidence does not create a specialist route.
- Data/privacy: no network, provider, credential or production reads. Hidden files and dependency/generated directories are excluded from source scanning.
- Performance: shared 4000-file, 8 MiB-read, depth-16, 1024-directory, 20000-entry, 4000-entry-per-directory and 64 KiB-per-file bounds. Overflow discards a partial directory instead of accepting filesystem-order-dependent evidence.
- Operational: source-only; full verification and route-selected independent reviews belong to the coordinator and do not confer external merge authority.
