# Tasks — Repair L5 current landing source binding

- [x] Freeze contracts and expected behavior.
- [x] Add failing test or characterization test.
- [x] Implement the smallest vertical change.
- [x] Run the focused landing quality profile (47 tests).
- [ ] Run the exact-head PR verifier.
- [ ] Complete independent reviews.
- [ ] Bind evidence to the final tree fingerprint.

## Sequential program handoff

This repair is task 1 of the user-approved operationalization sequence. Each
task consumes the prior task's merged exact SHA and must not reopen accepted
minor findings.

1. **Current-source compatibility (this change):** produces an exact-source,
   20-member offline L5 artifact pipeline.
2. **Operational multimodal provider:** consumes task 1 and produces a pinned,
   least-authority provider adapter with real text/image/audio/PDF/DOCX output;
   no publishing authority.
3. **Durable job/artifact runtime:** consumes task 2 and replaces process-local
   job/result state with restart-safe bounded persistence and recovery.
4. **Reversible cPanel/LiteSpeed publisher:** consumes task 3 and produces a
   canary/rollback-capable publisher; credentials and production mutation stay
   behind separate exact grants.
5. **Live dogfood qualification:** consumes task 4 and one user-supplied input,
   then proves input → artifact → canary → live URL → rollback/evidence under
   separately materialized production authority.

The next task starts from this change's accepted merge SHA and its exact
source/artifact contract. Provider credentials or live deployment are not an
implicit output of task 1.
