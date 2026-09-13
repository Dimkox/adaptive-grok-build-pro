# F2 conflict-policy independent-review repair

Selected same sole writer data_implementer; routea15f467e4575; reviewed HEAD5a2ead6e6e1eff5c5df28a8d4bcb91a209975187; genuine unchanged route base d33e8d8b2aa06a76f32724d08d79a21f3604ce42. Only F2 delivery/src/adaptive_delivery/landing_publication.py and factory/tests/test_landing_publication_cli.py were edited. Product writes are frozen again. Root owns documentation, commit, full verification and renewed reviews; G was untouched.

Security/data reviewers independently confirmed that PRAGMA column/index checks do not expose SQLite constraint conflict algorithms. A matching supported-shape schema with request_id UNIQUE ON CONFLICT REPLACE was accepted, and preparing a changed request under the same ID removed the earlier intent. IGNORE also changed the expected collision failure. This was a blocking immutable-intent defect, not a waived schema detail.

Both reviewers agreed to the bounded compatibility decision: the supported format is the actual app-created version1 _SCHEMA declaration, allowing whitespace/case variation. Arbitrarily hand-authored quoted/commented/extra-clause equivalents are not a supported schema format. The validator now compares the complete stored CREATE TABLE declaration to _SCHEMA after only whitespace collapse and case folding, retaining comments/quotes/extra tokens as significant differences; the existing logical PRAGMA/object checks remain. It does not use substring policy matching, strip comments, or introduce a general SQL parser. prepare now explicitly uses INSERT OR ABORT, making its immutable collision behavior independent of a table's default algorithm.

Creation SQL bytes, application ID, user_version, schemas, authority callbacks and all coordinator/effect/reconciliation behavior remain unchanged. Valid generated databases and the existing URI/read-only/idempotency/restart tests continue to pass; unsupported declarations fail publication_state_schema before reading/mutating intent records through the store.

## Evidence

Three new regression methods cover UNIQUE and PRIMARY KEY REPLACE/IGNORE in writer and readonly modes; block/line-comment and quoted/bracketed identifier variants; supported lowercase/indentation compatibility; and preservation of a preseeded original intent when a changed request reuses its ID under an altered UNIQUE policy.

- split-f2-conflict-red.out:18 failing subcases before the repair, three parent methods counted passed and two positive formatting subcases passed. This is a failed RED run; parent-method counts do not erase failures.
- split-f2-conflict-green28.out: **20 tests+88 subtests PASS in8.21s** across the full affected publication suite using28workers.
- split-f2-conflict-fitness.json: actual-base fitness PASS with unchanged budgets and boundary checks.
- split-f2-conflict-ruff.out: both changed Python files PASS. git diff --check PASS.

No unrelated broad suite was repeated; prior full reports remain archived by root and are not relabeled current.

## Exact handoff

Refreshed complete eleven-path manifest: /tmp/agbp-sweep/split-f2-source-sha256.json. Identical repair copy: split-f2-conflict-source-sha256.json. Prior manifest preserved as split-f2-source-sha256-before-conflict.json. Exactly two hashes changed and the other nine F component paths remain identical; archive_equivalent is now false with the exact two exceptions recorded.

Cumulative production deviation against immutable f31406e: split-f2-conflict-frozen-deviation.patch. Narrow two-file review repair against reviewed HEAD: split-f2-conflict-repair.patch. Keep the earlier F schema-validation history and RED outputs as historical evidence.

The root may commit F2, rerun its mandatory verifier/current-head reviews and reconstruct G on that genuine repaired predecessor. No other worktree, grants, credentials, operator database, provider, network or real publication operation was accessed or modified. The added databases and persisted intent rows are synthetic temporary fixtures.
