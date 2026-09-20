# Rollback plan — Fix issue #155: semantic_bind_repair_child guard rejections and PostgreSQL tier determinism

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes. Strategy: `forward_fix`, at most one step (typed in `change-spec.yaml`).

## Trigger conditions

Roll forward (revert the commit) rather than roll back the database if any of these is observed after merge:

- A bind is refused with a reason that does not match the guard that should have fired — i.e. the re-grouped `OR` blocks disagree with `018`'s accept/reject set on real data. This is the only *behavioural* risk the change carries.
- A consumer's code matches on the old message text `semantic repair child binding rejected` exactly and breaks on the appended `: <reason>` suffix.
- `021` fails to apply on a cluster that already has `001-020` (drift or timeout), which would stop every migration for that database, not just this feature.

## Application rollback

`git revert` the merge commit and ship the result as an ordinary update. `018` still contains the complete pre-fix function body, so re-applying the older source restores the previous behaviour through the same migration mechanism — the rollback is a source operation, not a SQL operation.

The Python allowlist and the strict envelope reader revert with the same commit; nothing outside the commit needs coordination, and no other component was taught to emit or expect the envelope.

## Data recovery / forward-fix

No data was written, rewritten, deleted, or re-encoded, and no index, constraint, table, view, type, or privilege was added. `021` changes only the body of one function plus its grants on an unchanged signature. Therefore:

- **There is no destructive step to undo, and there must not be one.** Deleting `schema_migrations` row 21, `DROP FUNCTION`, or editing `018` in place are all forbidden here: rewriting a shipped resource makes the recorded `(version, name, sha256)` prefix diverge and fails every existing database with `migration drift at version N`.
- Forward-fix instead: if a reason is wrong, a new resource `022_…` replaces the function again. History stays append-only, which is exactly the rule this change was written under.
- A reverted deployment leaves `021` applied and harmless: the function keeps the same accept/reject decisions, and the pre-fix Python simply never reads the envelope key — it treats the returned document as it always did.

## Verification after rollback

1. `python3 -m unittest -q factory.tests.test_migrations` — the vocabulary/equality assertions revert with the tree, so this must be green on the reverted source, not on the fix.
2. `python3 -u factory/tests/run_disposable_exit.py` — one pass on the reverted tree; the tier must not need the fix to be green, and this is also how the `stale_m0` fixture coupling is checked independently (a reverted tree reproduces `422 != 201` only in runs longer than 300 s).
3. `python3 scripts/grok_verify.py --mode pr` on the clean reverted tree.
4. Read one real rejection from the reverted cluster and confirm it is the pre-fix anonymous `semantic repair child binding rejected` — proof the rollback restored the known shape rather than a third state.
