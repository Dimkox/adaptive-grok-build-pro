# M9 Deadline Schedule

All times are UTC+3. The hard deadline is **2026-09-08 00:00 UTC+3** (`2026-09-07 21:00 UTC`). It never waives predecessor acceptance, external authority, environment, recovery, verification, review or production gates.

| Window | Locally feasible work | Exit condition |
| --- | --- | --- |
| 2026-09-02 | package/spec/design/connectivity checkpoint | committed documentation on exact provisional M4 base |
| 2026-09-02–2026-09-06 20:00 | implement Tasks 1–4 as separate pure local TDD commits using synthetic opaque identities; independently await dependency-ordered M4→M8 acceptance | focused deterministic source tests pass; factual ledger rows remain blocked |
| 2026-09-06 20:00–2026-09-07 08:00 | restack/reconcile only after exact accepted M8 SHA/profile/cohort are factual | accepted identities recorded, not inferred |
| 2026-09-07 08:00–14:00 | Task 5 schemas/architecture/docs if its gate opens | no external capability; focused integration suite passes |
| 2026-09-07 14:00–20:00 | exact-tree verification and independent route reviews | all required fresh local receipts on one fingerprint |
| 2026-09-07 20:00–2026-09-08 00:00 | protected reserve | exact-state release decision and blocker report |

If accepted M8, signed inputs, nonproduction environment or recovery evidence remains unavailable, the result is a documented `BLOCKED` state, not compressed gates, fabricated evidence or production action.
