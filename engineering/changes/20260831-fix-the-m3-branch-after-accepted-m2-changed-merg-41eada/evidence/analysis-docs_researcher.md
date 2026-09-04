# Documentation and evidence analysis — M3 restack on accepted M2

**Route:** `41eadaeae674`
**Change:** `20260831-fix-the-m3-branch-after-accepted-m2-changed-merg-41eada`
**Mode:** repository-local analysis; no product edits.

## Exact restack fact and authority boundary

- The required predecessor is the exact accepted M2 merge commit `022411b05924618cfde0cb97b8c8aff4955e6013` (`Merge pull request #16`, subject `fix(trust-ci): classify bounded zombie-only process groups`). It is a merge of previous M2 head `9493741…` and M2 hotfix parent `5b2a259…`.
- Current M3 head `d4cc01f` does **not** contain `022411b` (`git merge-base --is-ancestor 022411b d4cc01f` exits 1). The restack must therefore create a new M3 integration head; all M3 exact-head evidence becomes historical after that source change.
- The authoritative operating rule is already recorded in `decisions.md`: a stacked milestone binds verification to its immediate reviewed predecessor, not the program inception base. This restack applies that rule to the new accepted M2 head. The accompanying `mistakes.md` entry about carrying a program base into an M3 verifier remains historically true and must not be rewritten.
- The merge/rebase/resulting local commit is not merge authority. It requires fresh local verification/route reviews on its final fingerprint, then a PR exact-head App-owned `adaptive-trust-ci/verified@<policy-sha12>` check and any external signed scopes before merge. No deployed policy, holdout, image, key, PostgreSQL state, or branch protection fact may be changed or claimed by this source-only restack.

## What must be preserved as historical evidence

Do **not** rewrite or “refresh” historical artifacts to pretend they prove the restacked head:

- `engineering/changes/20260826-m3-m9-production-delivery-continuation-355689/evidence/m3-task-evidence.md` correctly binds Tasks 1–7 to product head `73a45d1…`, review-only `e7c903d…`, and its then-derived digest set. Those identities prove checkpoints only, not the later restacked candidate.
- M3 package prose currently says its Tasks 1–7 were reviewed through those old checkpoints and final Task 8 verifier/reviews are open. Retain the old commit/digest statements as dated historical facts; add a clear supersession/restack note rather than replacing them with an unverified new SHA.
- Existing M2/M3 receipts, review reports, governance handoffs, architecture evidence, and change-package state are fingerprint/exact-SHA bound. They are invalid for the new product tree but remain audit evidence. Never modify a receipt’s embedded fingerprint, route base, review identity, or claimed command result.
- Historical M2 package evidence similarly remains historical. The accepted M2 commit is the base to consume, not a license to copy its local receipts into M3 or claim its review/Trust-CI proof on a descendant.

## Required active-package content

The new restack package is an unscoped generated draft. Before closure it needs the following exact, bounded claims:

1. **Typed spec.** Replace `UNKNOWN` objective fields and empty criterion/invariant/forbidden/observability sections. Acceptance must require (a) `022411b…` is an ancestor of the final M3 head, (b) M3 governance behavior/requirements are preserved, (c) final architecture/governance evidence is rederived for the exact base/head and final fingerprint, and (d) selected verifier/reviews are fresh. Map criteria to real test files and final receipt evidence; no nonexistent Trust-CI result may be listed as passed.
2. **Brief/requirements.** State the in-scope operation precisely: integrate exact M2 accepted head into M3, resolve conflicts without semantic M3 weakening, and retain M2 zombie-only process-cleanup behavior. Explicit non-goals: no M4 implementation, governance-rule activation, deployed Trust CI change, external write, merge, publish, or production action.
3. **Architecture.** Record that the architecture model/rules and M3 governance handoff are rederived because their evidence binds base/head and tree state. This is not a new component, API, data flow, or runtime topology. Preserve the M1 → M2 → M3 authority ordering and the fact that canonical governance JSON—not Markdown—is M3 authority.
4. **Test plan.** Include ancestry/provenance check; M2 zombie regression retention; M2 model/rules validation, deterministic diagrams/fitness; governance schema/loader/lifecycle/handoff/receipt/installer tests; final `grok_verify --mode pr`; and code/test/security reviews on the one final tree. If integration conflicts change a behavior, add the focused regression before its repair.
5. **Release/rollback.** Release is a stacked source PR only. Go requires a final exact M3 head that contains `022411b…`, current exact inputs/evidence, fresh local receipts, and the later external PR check. Rollback before merge is closing/reverting the restack branch; after merge, use a reviewed forward-fix/revert PR, preserve evidence, and renew all affected exact-state checks. Never rewrite protected history or revive a previous handoff/receipt after a new source commit.
6. **Tasks/state/evidence.** Keep old M3 state/evidence separate. Record this package’s own analysis, final verifier and reviews under its `evidence/` directory; transition only after the current package is complete. The target PR preparation remains pending until a final head exists.

## README, decisions, and mistakes

### README requires a current-state correction after the restack

The current README says M2-A is merely a local candidate with PR/external check pending, while the route identifies accepted M2 head `022411b…`. After the integration commit and its local evidence, update the M2 current-state sentence to describe only the accepted M2 source fact supported by the tree (without asserting deployment/merge authority beyond what is independently evidenced). Update M3 wording to say it is restacked on that accepted M2 head and that its final verifier/reviews/PR exact-SHA check are pending until actually recorded.

Keep these statements unchanged:

- M1 is local/source evidence, not deployed proof.
- The M3 registries are empty; repository-authored approval-looking fields are untrusted; no active rule/example or closed debt is fabricated.
- M4 remains pending and needs current exact M1/M2/M3 handoffs and external authority in its own PR.
- Architecture model/rules are authority; Mermaid and `decisions.md`/`mistakes.md` are projections/explanations, not overrides; local receipts are preflight only.
- README version remains `2.0.12` unless a separately approved version change exists, and its complete K16 graph must not be disturbed by a restack that adds no node.

### Decisions/mistakes update rule

Add one concise `decisions.md` entry only if the restack establishes the concrete integration decision: “M3 consumes accepted M2 `022411b…` as its immediate predecessor; all architecture/governance handoff and receipt evidence is regenerated for the resulting exact head.” This is a useful operational fact and follows the AGENTS self-learning rule. Do not add a `mistakes.md` entry unless an actual restack error occurs; the already-recorded base-selection root cause is sufficient and must remain intact.

## Observability and contract implications

No API/event version, OpenAPI document, database, queue, external adapter, or metric contract should change merely to restack. Preserve `engineering/contracts/openapi/**`, Trust CI package boundary, and all external authority wording unless the actual conflict resolution changes them; such a change would be out of this route’s “without changing M3 requirements” constraint and needs an explicit documented compatibility/risk decision.

The observable proof for this change is exact provenance and reproducible local validation: final head ancestry, clean exact base/head architecture evidence, current governance digest/evidence digest, final tree fingerprint, and review/verification results. Do not publish old digest values as current, and do not create high-cardinality or secret-bearing telemetry merely to record restack status.
