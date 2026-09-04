# AI architect analysis — bounded M6 semantic validation

## Decision

Canonical head `2d2360cd6f2a19ad3328d468073a52927691b112`
(tree `5ee89e86b7e8f03ff78c644713e449b0fb9064d8`) supplies the complete bounded
semantic-validation and correction core needed for a local M6 source checkpoint.
It is source material rather than a drop-in branch: its merge base predates exact
M5 `85cd4343143915ce9342634e7fe81886b6394871`
(tree `779e0b99a5e489a2c91e866662cc1f31ae73b4c3`), and its semantic migration is
numbered `014` instead of the required additive `018`.

No additional semantic algorithm, provider integration, public repair endpoint,
autonomous recovery daemon, or hardening sweep is required for this checkpoint.

## Confirmed core behavior

- `SemanticSubjectV1` binds a closed requirement set to exact base/head SHAs,
  spec, architecture, authority, diff, deterministic/holdout/review evidence,
  original writer/context, risk, and diff limit. Any relevant mutation changes
  the subject digest and makes prior finding, coverage, verdict, or directive
  stale.
- `ValidatorIdentityV1` is provider-neutral. It records versioned definition,
  model and context digests but no provider-controlled decision. Validators must
  be independent from the original writer and have `repository_read` plus
  `semantic_validate`; `application_write`, adjudication, external write,
  network, and credential access are forbidden.
- Findings and coverage are typed, closed, bounded, digest-bound, and cover the
  exact requirement set. Provider prose cannot supply the final decision.
- `adjudicate()` is deterministic under input permutations. Any conflicting
  coverage status, explicit `contradicted` status, unsupported “proven” claim,
  security/authority/contradiction finding, or unrepairable finding yields
  `needs_human`. Repairable findings or unproven coverage yield `repair`; exact
  evidenced coverage with no findings yields `pass`.
- Duplicate finding identities and multiple typed findings for one requirement
  are exposed as duplicate/correlation evidence. They do not silently override
  one another or grant a pass.
- `plan_repair()` permits only cycles `1`, `2`, and `3`, keeps the exact original
  writer, requires a fresh context, unchanged base/architecture/authority, fresh
  semantic evidence, non-recurrent typed findings, non-increased risk, bounded
  diff, and positive budget/deadline. Cycle `4` (and every out-of-range cycle)
  returns `needs_human` with no directive or child proposal.
- The persisted lifecycle binds each child to the exact parent task/run/fence,
  packet, manifest, workspace result, head, verdict, directive, preceding child,
  writer/context, limits and source digest. A broker failure leaves the one
  persisted child replayable; it does not authorize another child.

## No application-write authority

The canonical separation is sufficient and must survive the port:

1. coordinator, validator, and adjudicator are distinct actor kinds and database
   roles;
2. validator evidence requires its exact assignment and actor identity;
3. the adjudicator recomputes the verdict from persisted evidence;
4. semantic roles have no direct table DML and receive only narrow
   security-definer functions;
5. neither a validator nor an adjudicator receives `task:execute` or workspace,
   provider, Git, credential, network, approval, or external-write authority;
6. correction reaches M5 only through the exact reserved repair-child broker
   identity and digest-bound intake source. M6 never edits application files or
   calls a provider itself.

## Only true remaining core work

1. Copy the final four semantic modules and seven schemas from `2d2360`, then
   graft only their M6 seams into the current M5 service/store/API/models and
   architecture. Current M5 wins every overlapping-file conflict; do not merge
   or cherry-pick the canonical branch wholesale.
2. Port the final `014_semantic_validation_bridge.sql` body as
   `018_semantic_validation_bridge.sql`, update migration inventory/checksums and
   every test/reference, and apply it after unchanged M5 migrations `014`-`017`.
3. Rebind the semantic bridge to the exact M5 `85cd434` packet, manifest,
   proposal, attestation, snapshot and result forms. Preserve exact task/run,
   repository, owner, writer role, live fence, SHA and digest cross-checks.
4. Graft the coordinator/validator/adjudicator stores and service/API operations
   additively, preserving all M5 endpoints and database capabilities. Retain the
   reserved repair-broker source/claim checks from fixes `81cc3c4`, `87897ff`,
   `534b667`, `fc019d4`, and `2d2360`.
5. Run the existing focused semantic contract, bridge, adjudication, persistence,
   service/API and repair-lifecycle tests against the new tree, plus one
   disposable PostgreSQL migration/replay proof. Regenerate evidence for the new
   exact SHA; no receipt from `2d2360` transfers.

## Explicit non-gaps for this local checkpoint

Live provider calls, provider-specific verdict logic, public repair API,
automatic multi-process recovery, additional metrics machinery, application
mutation by a validator, and corporate approval automation are not needed for
the bounded source result. Existing immutable persistence and exact idempotent
replay support the agreed semi-manual coordinator flow; those extensions can be
handled after the sequential MVP milestones without reopening M6.
