# Architecture — Fix the M3 branch after accepted M2 changed: merge exact M2 head 022411b05924618cfde0cb97b8c8aff4955e6013 into M3, resolve integration conflicts without changing M3 requirements, add or update regression tests if needed, run verification and reviews, and prepare PR #11 for fresh exact-SHA Trust CI; no external writes without exact delegated grants.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

M3 head `d4cc01fe8d6ec82cce93106191774fc32e8dbb46` diverged before accepted M2
head `022411b05924618cfde0cb97b8c8aff4955e6013`; neither contains the other.
Consequently old M3 handoffs, receipts, reviews, and external checks do not bind
the accepted predecessor.

## Proposed behavior

Create a normal two-parent merge with M3 as first parent and exact accepted M2
as second parent. Resolve only four content conflicts, preserving both histories
and contracts. Recompute any exact-state architecture/governance evidence for the
merged tree instead of loosening schemas or editing historical evidence.

## Components and boundaries

- M2 architecture/package/Trust-CI workspace code is inherited unchanged.
- M3 canonical governance JSON and closed schemas remain authority; Markdown is explanatory.
- Architecture rules semantically union governance coverage with the finite M2 budget.
- Local evidence remains preflight only; App-owned exact-SHA Trust CI remains merge authority.

## Data flow

Exact M2 parent + M3 parent -> conflict-resolved source tree -> focused tests ->
architecture/governance derivation -> full verifier -> independent receipts.
No runtime, database, queue, or external-system data flow changes.

## API and event contracts

No OpenAPI, HTTP, webhook, queue, event, database, or external-adapter contract changes.
Existing contract inventory is validated unchanged.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: all currently applicable entries in canonical governance registries.
- Applicable canonical example IDs/versions: none added or changed.
- Open or overdue debt IDs: none added or changed.
- Expected governance handoff or receipt impact: old exact-state artifacts are stale; fresh evidence must bind the resulting head and exact accepted-M2 base.

## Bitrix-specific impact

- Modules/events/agents/components affected: none; repository is not a Bitrix implementation.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: installer regression coverage only; no lifecycle change.
- Core modification: forbidden unless explicitly approved.

## Decisions

- Use a true merge, not rebase/cherry-pick, to preserve exact accepted M2 lineage.
- Treat existing characterization tests as the RED contract; add behavior only if a focused compatibility test exposes a genuine regression.
- Resolve append-only history by retaining both sides and resolve tests by invariant semantics, never wholesale side selection.

## Risks and mitigations

- Lost milestone regression: combine both conflicting test suites and run both cohorts.
- Stale exact-state proof: derive fresh evidence after the final source commit.
- Architecture-policy weakening: retain `10820` exactly and preserve governance separation/handoff rules.
- External authority confusion: do no external write and make no merge-eligibility claim from local evidence.
