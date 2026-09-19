# Requirements — durable delivery of the #104 post-merge audit

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] AC-001 — The **five** analysis reports plus the controller's re-measured tables plus the reproduction harness
      are tracked under `evidence/`, each numeric claim names the block that reproduces it, and the lane provenance
      is stated rather than implied: four of the five lanes (`repo_explorer`, `architect`, `docs_researcher`,
      `integration_architect`) are selected by this change's route `59527d5a28f8`, while the fifth
      (`ai_architect`) is **not** in that route's `allowed_agents` at all — it belongs to route `4c524b83df59`, the
      #133 delivery wave whose scaffold this evidence was carried from. "six route-selected reports" was wrong on
      both counts: there are five, and one of them was never selected by this route.
- [ ] AC-002 — The record says plainly what merged #133 fixed (identity-analyzable json_schema contracts
      **12/38 → 36/38**, i.e. **24 unlocked**; across all declared kinds **21/50 → 46/50**, i.e. **25 unlocked**; the
      `unsupported_openapi_construct` symptom is gone) and what it left: fail-closed residuals **CAR-1 … CAR-4**
      **plus CAR-5, which is not fail-closed** — declared-`$id` resolution taking precedence over the declared-path
      table is a latent false-certification path, filed as issue #147 with a control-flipped reproduction and
      measured unreachable in today's inventory (41 `$id` values, none path-like, 0 of 86 `$ref` bases ambiguous).
      *Superseded:* an earlier revision of this AC carried the base row as `14/38`, which contradicts the 38
      denominator it shared a row with (14 + 26 = 40).
- [ ] AC-003 — Superseded tables are marked superseded with their cause (truncated factory-only inventory; a working
      tree carrying a probe commit; a typed-in base row that was arithmetically impossible; an ablation line that
      mixed the 38-record json_schema unit with the 50-record all-kinds unit; an edit-class cell that named a verdict
      the comparator does not return; placeholder cells in the synthetic table), so nobody re-quotes them.
- [ ] AC-004 — `mistakes.md` gains 8 entries (6 recovered from an uncommitted tail at the maintainer's direction +
      2 from this wave) with **zero deleted lines**; the 8 new entries are ordered among themselves and add no
      out-of-order date pair — the file already carries **12** out-of-order adjacent date pairs at the base and still
      carries **12** at the delivered head (block F prints both), so "stays chronologically ordered" was not a
      checkable predicate and is not what this criterion claims.
- [ ] AC-005 — No machine-local absolute path, host name, key material or credential survives in committed evidence
      (placeholders only), including inside quoted command output.
- [ ] AC-006 — `python3 scripts/grok_verify.py --mode pr` passes on the delivered head with the `verification` and
      `code_review` receipts bound to it. *(Ticked by the receipts, never in advance.)*

## Failure and edge cases

- An analysis agent's report contradicts a controller measurement → the measurement wins and the report is kept with
  the contradiction labelled. This happened three times in this package: the `add-branch → compatible` cell, the
  `add novel branch → unsupported_schema_comparison` cell (which contradicted `analysis-architect.md`'s measured
  `incompatible (changed_constraint)` and was the wrong one — see the CAR-1 supersession note), and
  `analysis-integration_architect.md`'s "baseline 20/50" against the measured 21/50.
- Two different five-item lists were both numbered R1–R5 (the controller's residual work items and the
  `ai_architect` report's rejection-branch mechanisms). The controller's list is renamed **CAR-1 … CAR-5**; the
  agent's `R-n` ids stay unrenamed, and the mapping table in
  `evidence/controller-declared-inventory-table.md` says which list a citation belongs to.
- A report is still being written when the tree is finalized → the file is excluded from this commit rather than
  committed half-written.
- `git diff` shows any deletion in a shared append-only document → the commit is wrong, re-do it as a pure insertion.
- The route-selected reviewer asks for a claim that cannot be reproduced → the claim is removed, not softened. If the
  reproduction needs a heavier tool than this package may commit (the `grok_architecture.py fitness` gate path needs
  throwaway commits), the claim stays attributed to the lane that executed it and says so — see "Gate-path
  corroboration" in the controller table.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none newly. `FIT-DECLARED-NETWORK-ONLY` is the reason this package holds no `.py` that
  imports a network family — evidence scripts stay inside `.md` files, per the recorded trap, which is why
  `evidence/measurement-harness.md` carries stdlib-only blocks instead of a `probe.py`.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: **repaid** — six lessons that existed only in a dirty working tree are
  now in Git. **Accepted/created**: this wave documents but does not fix CAR-1–CAR-5; #146 carries the closure defect
  and #147 carries CAR-5.

## Non-functional requirements

- Security: documentation of a verification gap is not a vulnerability disclosure risk here (repository is public,
  CAR-1..CAR-4 are fail-closed, and CAR-5 is measured unreachable in the shipped inventory), but no credential, key,
  endpoint or operator path is quoted — see AC-005.
- Reliability: every statement is tied to a re-runnable command or a commit SHA; `evidence/measurement-harness.md` is
  the runnable half of that promise.
- Performance: n/a (no runtime surface).
- Observability: `SIG-001` — the numstat shape of the shared-document diff (78 added / 0 deleted) plus the count of
  analysis reports under `evidence/` (5), with the route that owns each lane named.
