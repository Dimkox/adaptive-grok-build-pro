# docs: release-chain landing convention in view of routed agents, and inspected gate failure causes

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260916-docs-state-the-release-chain-landing-convention-627a16`
Route: `627a16845fc4` (intent release, base `83925c12`)
Risk: high (documentation only; no production action)

## Human gates and how they are satisfied here

- `scope_and_design_approval`: the scope of this unit — one convention sentence in `START_HERE.md` plus the three inspected failure causes — was stated to the maintainer in the running report and the standing instruction for this session is to continue; nothing beyond those two prose areas is touched.
- `production_action_approval`: **not consumed by this change.** It tags, releases or installs nothing; it only records text. The gate stays attached to the tag/Release steps of a release chain, each of which was granted separately for v2.0.17 (`--profile release`).

## Problem

Two truths lived where nobody looks. First, the convention that a release chain's own commits (R, A, SR) are recorded through `current_unreleased_change` and `local_candidate` rather than as rows in `delivered_change_history.post_v2_0_16_landing` was written into one `record_scope` prose field, while row #81 — the previous chain's successor — sits in that very ledger, so a routed agent reading only the ledger could conclude either that rows are required or that #81 contradicts the ledger. Second, `work_inventory` still said `not inspected or inferred` for PRs #33, #15 and #21 even though the causes are recoverable verbatim from the retained job records, which is exactly the kind of placeholder a later agent may trust as a boundary of knowledge.

## Outcome

`START_HERE.md` carries the convention in the paragraph that points at the machine-readable handoff, and each of the three entries states the observed failing command with its assertion or error text, while keeping the caveat that the conclusion is a historical observation and not current merge eligibility.

## Scope

### In scope

- one sentence in `START_HERE.md`;
- three `failure_cause` values in `work_inventory` and the two coupled literals in `tests/test_project_state.py`.

### Out of scope

- any release action, tag, artifact or installation;
- `published_release`, `prior_published_releases`, `local_candidate`, milestones and migration records;
- the open pull requests themselves (#33 stays open; this commit only records what its gate failure was).

## Constraints

- Backward compatibility: prose and test literals only.
- Data/privacy: causes quote command and assertion text, no credential or host identity.
- Performance: not applicable.
- Operational: rollback is one revert.
