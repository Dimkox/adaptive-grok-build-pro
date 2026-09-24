# Resolve issue #186 owner mapping and issue #36 exit-status disposition

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260923-resolve-issue-186-owner-mapping-and-issue-36-exi-93d9fe`
Created: 2026-09-23T17:06:25+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Fix GitHub issues #186 and #36. Establish the exact repository-owned source/command owner for the reported exit-status recorder; if a live owner exists, add a failing regression test and minimal fix for #36, then update #186 with the binding evidence. If no owner exists after complete current-tree and history audit, produce a durable repository-local disposition for #186 and an explicit external-owner linkage for #36 without speculative code. Preserve separate issue scope and do not mix Trust CI deployed authority.

## Outcome

At audited commit `130ce4a42d9f9bbd1b56772d40b19ae530283205`, the repository has a durable, source-bound disposition for #186: no repository-owned implementation of the reported shell exit-status recorder exists in the current tree or reachable history. Issue #36 is explicitly external/misrouted pending an authoritative owner link. No product code changed and no issue closure is claimed without that external link.

## Scope

### In scope

- Record exact current-tree and history audit evidence.
- Map #186's related findings: #35 and #36 have no corresponding shell gate here; #39 targets a distinct JavaScript/ESLint repository; #48 targets an external installed CLI guard.
- Preserve the existing Python/Trust CI return-code behavior as characterization evidence.
- Record the external-owner blocker for #36.

### Out of scope

- Any shell helper, verifier semantic change, regression for absent code, API/event/SQL change, Trust CI deployed behavior, or GitHub edit.

## Constraints

- Backward compatibility: no runtime behavior changes.
- Data/privacy: no data or credentials touched.
- Performance: no production path changed.
- Operational: repository-local evidence only; external issue updates require an owner link supplied outside this change.
