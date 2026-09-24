# Repository analysis — issue #73

Route: `147e6461d649`  
Worktree: `/tmp/agbp-issue73-evidence-digest`  
HEAD: `130ce4a42d9f9bbd1b56772d40b19ae530283205`  
Scope: read-only analysis; no product implementation, no full `grok_verify`, and no secrets/private keys read.

## Finding

The rename can be bounded only to newly authored/current evidence. The current HEAD has no product schema or producer for `authorization_tree_fingerprint`; that exact key occurs only in these two source-bound historical records:

- `engineering/changes/20260913-l5-split-g-current-base-offline-recovery-and-com-352913/evidence/historical-qwen-probe.json:14`
- `engineering/changes/20260913-l5-split-g-final-base-offline-recovery-and-assem-2a890b/evidence/historical-qwen-probe.json:14`

Both records were introduced as L5 evidence by `e737dd5c`/the assembled L5 history and carry the same recorded authorization ID and digest. They are historical evidence, not runtime input. Do not rename those keys in place: doing so changes an immutable observation and its source-bound bytes. The unmerged candidate commit `5b8acee6` demonstrates the tempting two-file `authorization_tree_fingerprint` → `grant_binding_digest` edit, but it is not an ancestor of this worktree and should not be ported as-is.

The false-positive disposition is already recorded at `engineering/reviews/l5-split-delivery.md:29` and `engineering/reviews/l5-delivery-stack.json:469`. The backlog analysis also explicitly says to preserve the frozen evidence and use a neutral name only for new evidence (`engineering/changes/20260921-research-open-backlog-map-each-item-to-its-sourc-d54d3a/evidence/analysis-docs_researcher.md:15`).

## Current contracts and consumers inspected

- Current local grants are emitted and matched as schema-v2 records with `tree_fingerprint` in `.grok-stack/adaptive_grok/state.py:242-257,292-317`; `scripts/grok_landing_publish.py:51-76` also requires that exact current grant field. These are live authorization bindings, not the archived evidence key.
- The pilot authority model and fixtures use `tree_fingerprint` (`pilot/authority.py:24-58,109-147`, `pilot/tests/test_authority.py:15-40`, `pilot/tests/test_runtime_authority.py:54-70`). Renaming this field would be a broad authority-contract migration with fail-closed compatibility risk.
- Current local receipt/report envelopes use `tree_fingerprint` in `.grok-stack/adaptive_grok/receipts.py:541-567,643-703`; stale-receipt behavior is covered by `tests/test_verification_doctor.py:758-787` and receipt tests. Do not globally rename it for this issue.
- Current provider-evidence schemas are closed (`additionalProperties: false`) and use `provider_evidence_digest`: `factory/contracts/jsonschema/landing-provider-evidence.v1.schema.json` and `landing-provider-evidence.v2.schema.json`. `factory/tests/test_landing_contracts.py:170-195,344-390` freezes the v1 digest/schema behavior and v2 compatibility boundary.
- Current pilot evidence schemas use neutral `*_digest` names and `head_tree`, for example `pilot/contracts/jsonschema/candidate-change.v1.schema.json` and `pull-request-proposal.v1.schema.json`; their tests cover `push_grant_digest`/`proposal_grant_digest`. No current schema or loader references `authorization_tree_fingerprint`.
- Historical state fixtures still intentionally contain `tree_fingerprint` at `tests/test_project_state.py:289-303`; those are also not rename targets.

## Compatibility and secret-scan risks

1. The old flagged name is not a current API contract. A new evidence record may use `grant_binding_digest` (or another neutral, semantically precise name), but it must be introduced in the actual current producer/consumer contract rather than by changing unrelated runtime grant fields.
2. Because the current JSON schemas are closed, adding a field requires a versioned schema/fixture/test change; silently accepting both names would weaken the contract. Historical records should remain readable as historical bytes by path/version if a reader is ever added.
3. The local `_secret_scan` does not match this field name (as recorded in the backlog analysis), so local verification cannot prove that GitGuardian will clear the historical detector result. Renaming current fields will not erase the old name from Git history. Do not globally suppress 64-hex values; keep the existing targeted GitGuardian disposition/allow-list with its service owner.
4. A broad `tree_fingerprint` rename would touch authorization, receipt freshness, pilot, factory publication fixtures, and many tests, creating a needless compatibility and fail-closed risk without addressing the specifically observed `authorization_tree_fingerprint` false positive.

## Minimal TDD recommendation for the write owner

First add a focused regression/characterization test (new `tests/test_issue_73_evidence.py`, or the closest existing evidence-contract test) that:

- asserts both archived historical JSON paths retain `authorization_tree_fingerprint` and their bytes/digests;
- asserts any newly introduced current evidence fixture uses `grant_binding_digest` and rejects the old key under its closed schema; and
- proves no runtime authorization/receipt contract is changed by the evidence-only rename.

Then make the smallest current-evidence-only rename at the real producer, schema, and fixture paths discovered by that failing test. On this HEAD, no such current producer exists, so a test/documentation guard is the minimal repository fix; do not invent a new runtime schema solely to remove the historical false positive. Independent security and release review remain required after any product change.

## Rollback and release implications

- A guard/documentation-only change is a one-commit revert with no data migration, deployment, VERSION bump, or release rebuild. It must not rewrite either historical JSON record.
- If a real current contract is added, preserve existing v1 contracts and use an additive/versioned forward fix; rollback must leave readers able to consume already-emitted new records. Do not retag or rebuild immutable releases.
- Any product/schema change proceeds through the pending `scope_and_design_approval`, one write owner, focused TDD evidence, route verification/reviews, PR delivery, and the exact-head App-owned Trust CI check. No external write or release action is authorized by this analysis.

