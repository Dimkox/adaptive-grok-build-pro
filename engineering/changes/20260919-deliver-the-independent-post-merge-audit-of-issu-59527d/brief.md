# Deliver the independent post-merge audit of issue #104 composition analysis as durable change-package evidence, plus the two agent-behavior lessons it produced

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260919-deliver-the-independent-post-merge-audit-of-issu-59527d`
Created: 2026-09-19T04:34:18+00:00
Risk: medium (yellow)
Complexity: standard
Domains: api

## Problem

Issue #104 was closed by merging PR #133 (`d871ea6d5d654406281dd65626a3dce61bf933fa`) on 2026-09-19. The wave that was
supposed to implement the same task turned into an independent post-merge audit of it, and that audit — plus three
measurement corrections and eight agent-behavior lessons — existed only in untracked working trees and in chat. This
repository's own contract forbids that: durable designs, verdicts and lessons must live in Git or the active pull
request, because chat is the lowest-priority source of truth and a fresh agent must be able to continue from GitHub
alone.

Separately, six lesson entries in `mistakes.md` were **committed nowhere**: they lived only as an uncommitted tail of
the primary working tree, while a `git log --all -S` search for their headings returned zero refs and no open pull
request touched the file. That is precisely the failure class already recorded in this document as
*"a stale checkout can commit a whole-file rewrite of the append-only shared docs"* — unrecoverable if any session had
restored the file. The maintainer directed that they be preserved.

## Outcome

A reader of `main` can see, without this session: what #133 actually changed in the comparator's coverage (measured
before/after on the declared 50-record inventory), what it deliberately left unverified (residuals R1–R5, each
reproducible by command), which of the wave's own intermediate conclusions were wrong and why, and the two new
durable rules that came out of those errors — alongside the six recovered lessons, which now have a commit that
protects them.

## Scope

### In scope

- `engineering/changes/<this package>/evidence/` — the route-selected analysis reports (repo explorer, architecture,
  documentation research, integration, AI/contract domain) and the controller's re-measured verdict tables.
- `mistakes.md` — eight insertions: six recovered orphan entries placed in chronological position, two new entries
  from this wave. No existing line is modified or removed.
- Package paperwork for this documentation change.

### Out of scope

- Any product, contract, rules, schema, governance or test change. The composition residuals and the closure defect
  are tracked as issue #146 and R1–R5; fixing them belongs to their own routes.
- Reopening, re-scoping or re-closing issue #104, and any edit to another change package's records.
- The other sessions' in-flight pull requests (#137, #138 and the rest), including their files and their claims.

## Constraints

- Backward compatibility: append-only for shared documents — `git diff --numstat` for `mistakes.md` must show zero
  deletions; the analysis text of already-merged packages is never rewritten.
- Data/privacy: the repository is public, so machine-local absolute paths, host names, key material and operator
  endpoints are replaced with placeholders (`<worktree>`, `<private-scratch>`) in every committed evidence file.
- Performance: not applicable — no runtime surface is touched.
- Operational: no network write other than this pull request; no push to a protected branch, no merge, no tag, no
  release. Local verification and review receipts are preflight evidence only, never merge authority.
