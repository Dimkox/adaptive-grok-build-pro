# Tasks — Fix issue #73: rename current evidence fingerprint fields that trigger GitGuardian secret heuristics while preserving historical evidence immutability and schema/test compatibility.

- [x] Inventory current and historical evidence fields.
- [x] Preserve immutable historical artifacts.
- [x] Record bounded design and external GitGuardian boundary.
- [x] Record the user's explicit `scope_and_design_approval` for this bounded bugfix.
- [x] Add RED/GREEN regressions for current writes, legacy reads, dual-field rejection, and historical bytes.
- [x] Implement the single-producer/single-reader compatibility change.
- [x] Run focused policy/history and landing-consumer suites (76 tests passed); adjacent grant-consumer suites also passed (21 tests).
- [ ] Run route verification (first run was harness-interrupted; see `evidence/verification-interrupted.md`).
- [ ] Run security/code/test/release reviews and bind evidence after approval.
