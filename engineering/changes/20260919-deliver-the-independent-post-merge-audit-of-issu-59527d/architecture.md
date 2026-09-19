# Architecture — durable delivery of the #104 post-merge audit

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Repository knowledge about the #104 composition work stops at what merged PR #133 asserted. There is no independent
record of: how much of the declared contract fleet that merge actually unlocked, which edit classes still return no
verdict, or which intermediate conclusions of the follow-up wave were wrong and why. Separately, six lesson entries
exist only as an uncommitted tail of the primary working tree, reachable from no ref.

## Proposed behavior

The audit becomes repository content under this package: six route-selected analysis reports, the controller's
re-measured verdict tables (with each superseded table marked superseded and its cause named), and eight
`mistakes.md` entries placed without touching a single existing line.

## Components and boundaries

| Artifact | Role |
| --- | --- |
| `evidence/analysis-repo_explorer.md` | which comparator sites handle each composition keyword at the merged head; the `_event_meaning` gap (residual R4) |
| `evidence/analysis-architect.md` | adversarial soundness hunt against #133's union logic (pending this wave's final return) |
| `evidence/analysis-docs_researcher.md` | primary-source rules for `anyOf`/`oneOf`/`allOf`, dedup asymmetry, empty-list and `format` semantics |
| `evidence/analysis-integration_architect.md` | propagation of `unsupported` to a failed run, digest/freeze exposure, the locally failed PostgreSQL tier |
| `evidence/analysis-ai_architect.md` | measured end-state on the real landing/AI closure at the merged head |
| `evidence/controller-declared-inventory-table.md` | the authoritative before/after tables, computed on the declared 50-record inventory from a pristine tree |

No comparator, contract, rules or policy file is in this change's boundary.

## Data flow

Not applicable — static documentation. The evidence files themselves carry the reproduction commands, so the flow is
`reader → command → same verdict`, with no runtime component.

## API and event contracts

No contract is added, changed or deprecated. Contracts are *discussed* (their verdicts are recorded), which does not
touch `architecture/system.yaml` inventory digests, `contract_inventory_digest()` or `architecture_digests()`.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: `FIT-DECLARED-NETWORK-ONLY` (why no evidence script in this package imports a network family —
  reproduction commands are shell lines inside `.md`, not `.py` files under `engineering/changes/**`).
- Applicable canonical example IDs/versions: none.
- Open or overdue debt IDs: R1–R5 (comparator incompleteness, documented here, fixed elsewhere) and issue #146
  (closure reverse edges), both out of this change's scope by design.
- Expected governance handoff or receipt impact: none. No governance JSON, digest or policy file moves; the gate
  still requires the App-owned exact-SHA check for merge.

## Bitrix-specific impact

- Not applicable — no Bitrix surface in this route (`domains=api`, docs intent).

## Decisions

- **Preserve the six orphan entries by insertion, not by adopting the dirty file.** Copying the whole dirty
  `mistakes.md` from the primary tree would have silently rewritten shared history (the recorded #84 failure); instead
  the block was inserted at its chronological position, verified by `git diff --numstat` showing zero deletions.
- **Keep wrong measurements in the record, labelled.** Superseding them silently would destroy the reason the rules
  exist; each wrong table stays with its cause.
- **No `.py` in this package.** Reproduction commands are quoted inside Markdown so the fitness gate's evidence-node
  network policy cannot be tripped.
- **Scrub paths at copy time, not at review time.** Placeholders `<worktree>` / `<private-scratch>` are applied
  mechanically before the commit.

## Risks and mitigations

- **Losing the primary tree's uncommitted tail while it stays uncommitted.** Mitigated by committing copies; the
  original file is untouched, so a concurrent owner can still commit their own version and Git will surface the
  overlap rather than hide it.
- **Audit content aging against the next comparator change.** Mitigated by binding every claim to a commit SHA
  (`2f66ba6`, `d871ea6`) plus a re-run command, so staleness is detectable rather than persuasive.
- **Readers mistaking this package for the fix.** The brief, requirements and this file each name #146 and R1–R5 as
  the places where work actually happens.
