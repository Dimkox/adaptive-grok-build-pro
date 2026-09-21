# Recovery plan — issue #155

> Typed authority: [`change-spec.yaml`](change-spec.yaml). Strategy: `forward_fix`,
> at most one corrective release. This plan authorizes no production operation.

## Trigger conditions

Hold delivery and prepare a corrective release if a refusal is attributed to the wrong
condition, accept/reject behavior differs from the preserved `018` function, an error
message consumer breaks, or applying `021` fails.

## Preserve the applied history

A database that recorded migration `021` must continue receiving a package containing
byte-identical resources `001`–`021`. `plan_migrations()` rejects a package shorter than
its applied history with `applied migration is missing from package`; already-applied
`018` is never replayed. Reverting the source commit and deploying its shorter migration
inventory therefore neither restores the function nor provides a working normal upgrade.

Do not remove row 21 from `schema_migrations`, edit a shipped resource, drop the function,
or restore a database snapshot solely to undo this diagnostic change. The migration
performs no row backfill and changes no table or index: recovery concerns the function
body and compatible application handling.

## One corrective release

1. Retain all shipped migration bytes and the request/server-clock test corrections.
2. If the SQL body must change, add the next unused versioned resource (expected `022`,
   after checking the current inventory). Use `CREATE OR REPLACE FUNCTION` on the same
   `(char,text) -> jsonb` signature, retain `SECURITY DEFINER`, the fixed search path and
   coordinator-only grant, and restore either the exact intended pre-`021` guard/body
   behavior or a reviewed corrected reason mapping. Never claim that replaying `018`
   will perform this replacement.
3. Ship compatible Python handling in the same release. It must refuse both fixed-code
   rejection envelopes and legacy SQL NULL without treating a refusal as malformed
   binding data. If only an application message needs correction, retain `021` and fix
   that handling without changing database history or implying the SQL body was undone.
4. Apply the corrective release through the ordinary migrator under its existing
   transaction, advisory lock and bounded statement/lock timeouts, after the separate
   operational authorization. No manual history edits or timeout widening are part of
   this procedure.

If `021` itself fails, verify its transaction left the migration prefix unchanged and
stop the upgrade. Diagnose the concrete failure before a bounded retry; do not mark it
applied or attempt to skip directly over it to a corrective resource.

## Required recovery evidence

Before approving a corrective release, prepare a disposable database with `001`–`021`
already recorded, apply the proposed correction, and prove the original prefix hashes
are unchanged and only the expected new version is appended. A fresh empty-database
run alone cannot prove this recovery path.

Exercise accepted binding, exact replay, and refused binding on that upgraded database;
check the expected reason (or the explicit `store_returned_null` compatibility result)
and unchanged role isolation. Run the focused migration tests, the mandatory disposable
PostgreSQL tier and `python3 scripts/grok_verify.py --mode pr` for the correction. Recovery
is accepted only after these observations and its separately required delivery approval;
this source change does not claim that the future corrective migration has been exercised.
