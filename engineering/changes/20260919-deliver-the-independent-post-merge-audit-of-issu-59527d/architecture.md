# Architecture — durable delivery of the #104 post-merge audit

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Repository knowledge about the #104 composition work stops at what merged PR #133 asserted. There is no independent
record of: how much of the declared contract fleet that merge actually unlocked, which edit classes still return no
verdict, or which intermediate conclusions of the follow-up wave were wrong and why. Separately, six lesson entries
exist only as an uncommitted tail of the primary working tree, reachable from no ref.

## Proposed behavior

The audit becomes repository content under this package: **five** analysis reports, the controller's re-measured
verdict tables (with each superseded table marked superseded and its cause named), a reproduction harness holding the
copy-pasteable command behind every number, and eight `mistakes.md` entries placed without touching a single existing
line.

Lane provenance is stated because it is not uniform: four of the five lanes (`repo_explorer`, `architect`,
`docs_researcher`, `integration_architect`) are the analysis agents this change's route `59527d5a28f8` selects; the
fifth, `ai_architect`, is not in that route's `allowed_agents` at all — it is one of the five analysis agents of route
`4c524b83df59`, the #133 delivery wave whose evidence scaffold was carried into this package and expanded
post-merge. The earlier wording ("six route-selected analysis reports") described neither route: there are five
reports, and one of them was never selected here.

## Components and boundaries

| Artifact | Role |
| --- | --- |
| `evidence/analysis-repo_explorer.md` | which comparator sites handle each composition keyword at the merged head; the `_event_meaning` gap (CAR-4) |
| `evidence/analysis-architect.md` | adversarial soundness hunt against #133's union logic — **returned**: it found the measured false `compatible` (CAR-5, issue #147) and the `incompatible (changed_constraint)` verdict for a novel scalar widening that this file's earlier table had recorded as a non-verdict |
| `evidence/analysis-docs_researcher.md` | primary-source rules for `anyOf`/`oneOf`/`allOf`, dedup asymmetry, empty-list and `format` semantics |
| `evidence/analysis-integration_architect.md` | propagation of `unsupported` to a failed run, digest/freeze exposure, the locally failed PostgreSQL tier |
| `evidence/analysis-ai_architect.md` | measured end-state on the real landing/AI closure at the merged head; its `R1 … R5` are its own rejection-branch mechanisms, not this package's residual list |
| `evidence/controller-declared-inventory-table.md` | the authoritative before/after tables, computed on the declared 50-record inventory from a pristine tree, each table citing the harness block that recomputes it; CAR-1…CAR-5 defined and mapped against the agent's `R-n` list |
| `evidence/measurement-harness.md` | blocks A–H: the stdlib-only scripts, the exact invocations, and the printed result lines for every number committed here, including the one-process-per-tree rule |

No comparator, contract, rules or policy file is in this change's boundary.

## Data flow

Not applicable — static documentation. `evidence/measurement-harness.md` carries the reproduction commands, so the
flow is `reader → block → same verdict`, with no runtime component; each table in the controller file names its block.

## API and event contracts

No contract is added, changed or deprecated. Contracts are *discussed* (their verdicts are recorded), which does not
touch `architecture/system.yaml` inventory digests, `contract_inventory_digest()` or `architecture_digests()`.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: `FIT-DECLARED-NETWORK-ONLY` (why no evidence script in this package imports a network family —
  reproduction commands are shell lines inside `.md`, not `.py` files under `engineering/changes/**`).
- Applicable canonical example IDs/versions: none.
- Open or overdue debt IDs: CAR-1 … CAR-4 (comparator incompleteness, fail-closed, documented here, fixed elsewhere),
  CAR-5 (latent **soundness** defect, filed as issue #147), and issue #146 (closure reverse edges). All are out of
  this change's scope by design. Note the identifier: `analysis-ai_architect.md` also uses `R1 … R5`, for its own
  rejection-branch mechanisms — the mapping table in the controller file disambiguates the two lists.
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
  mechanically before the commit, including inside quoted command output.
- **One process per tree, always.** `sys.modules` caches `adaptive_grok.architecture`, so importing a second tree's
  module in the same process returns the first tree's object and the "A/B compare" silently compares a tree with
  itself; this is the mechanism behind two wrong numbers in this package's first revision, and the harness records
  the proof line.
- **Every committed table names its unit and its reproducing block.** The 38-file glob and the 38-record declared
  `json_schema` unit are equal counts over different sets, so a count alone cannot detect a swapped denominator.
- **Rename an ambiguous identifier instead of annotating around it.** Two different five-item lists were numbered
  R1–R5; the controller's became CAR-1…CAR-5 and the agent's stayed as it was written, with a mapping table, because
  a durable audit record cannot contain an id whose referent depends on which file you are reading.

## Risks and mitigations

- **Losing the primary tree's uncommitted tail while it stays uncommitted.** Mitigated by committing copies; the
  original file is untouched, so a concurrent owner can still commit their own version and Git will surface the
  overlap rather than hide it.
- **Audit content aging against the next comparator change.** Mitigated by binding every claim to a commit SHA
  (`2f66ba6`, `d871ea6`) plus a re-run command, so staleness is detectable rather than persuasive.
- **Readers mistaking this package for the fix.** The brief, requirements and this file each name #146, #147 and
  CAR-1…CAR-5 as the places where work actually happens.
- **A correction introducing a new wrong number.** Mitigated by `measurement-harness.md`: the number and the command
  that prints it are committed together, so the next reviewer re-runs rather than re-reads.
