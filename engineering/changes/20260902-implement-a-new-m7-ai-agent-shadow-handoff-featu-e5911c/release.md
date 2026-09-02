# Release plan — M7 local shadow handoff

Current delivery is local provisional pure library/schema source plus factual documentation. It has no runtime/store/service registration and its only bundle state is `blocked_pending_durable_lookup`. No push, PR, check publication, merge, tag, package, release, deploy or external write is in scope.

Future dependency order: finish/accept the factual M4 integration successor; finalize M5 from provisional reference `cbfca655…`; restack/finalize M6 from provisional reference `534b667…`; restack M7, add durable canonical producer lookup and reconcile schemas; declare architecture ownership; rerun focused/full verification and route-selected reviews. Only an external ledger may mark exact dependency commits accepted, and only a separately authorized operator may push/open a PR; human review and merge remain mandatory.

No-go while a predecessor is provisional, schemas differ, receipts are stale/missing or the tree changes. Deadline pressure cannot convert no-go to go.
