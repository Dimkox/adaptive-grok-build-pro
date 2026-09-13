# D independent-review repair handoff

Selected sole writer data_implementer; route bec1fcdde794; reviewed source HEAD d1fdb7aec61b242c1a2fc5fc0ced1809e1b79c76; unchanged genuine route predecessor a75b3cd639a1483533069e8634759cdfc6612310. Only the D checkout was edited. F and E were untouched; parent owns commits, propagation, full verification and renewed independent reviews. Product writes are frozen again.

## Confirmed defects and minimal fixes

1. FactorySettings.validate_landing accepted double-slash anchors. A temporary state=/tmp/.../state and quarantine=//tmp/.../state are different Path objects that resolve to the same inode; direct default-off compose_server_landing accepted them, so its lexical disjointness check failed. settings.py now rejects anchor // in the existing shape-validation loop before disjointness checking or I/O, covering quarantine/state/source/scratch/output for every provider mode. This common validator also serves the existing server entrypoint; no future dedicated-host fixture or loader is involved.

2. Existing server.main's sequential finally block stopped at listener.close failure, skipping owned_landing.close and leaving a real SQLite writer active. An owned-runtime close failure independently skipped socket unlink. server.py now nests independent finally stages for listener close, runtime close and socket cleanup, preserving the guarded app.state lookup and existing missing-socket handling. Errors propagate after all remaining cleanup stages have been attempted. The regression uses a real application/owned temporary SQLite and synthetic listener/socket/uvicorn seams; it opens no listener and contacts no service.

factory/tests/test_landing_server.py adds three regression methods: the actual same-inode default-off alias, thirty bounded shape/no-I/O subcases (five roots × six existing provider/default-off options), and the two teardown-failure cases. Every previously delivered D product hash except settings.py, server.py and this existing test file remains unchanged.

## Evidence

- split-d-alias-red.out:31 failing checks (one actual alias plus30 shape/I/O subcases) and one unittest parent method counted passed against the unfixed shared validator. This is RED, not a passing run.
- split-d-alias-cleanup-red.out: initial teardown failure reproduction; the listener leak also prevented the following case from acquiring its fixture store.
- split-d-alias-cleanup-red-bounded.out: added per-subcase emergency test cleanup, then reproduced both distinct defects: writer remains active after listener error, and unlink is skipped after runtime-close error. Two failed subcases, one unittest parent counted passed.
- split-d-alias-green28.out: **31 tests and59 subtests passed in4.32s** across only the affected direct-runtime and existing-server test files, using28 workers.
- split-d-alias-fitness.json: PASS against actual D route predecessor, including all unchanged code-budget/separation/import/ownership checks.
- split-d-alias-ruff.out: all three changed Python files PASS. git diff --check PASS.

No broad suite was repeated; parent now performs the mandatory full verifier and current-head independent reviews.

## Manifest and disclosed frozen-reference differences

Updated complete24-path manifest: /tmp/agbp-sweep/split-d-source-sha256.json. Identical repair-specific copy: split-d-alias-source-sha256.json. Prior manifest preserved as split-d-source-sha256-before-alias.json. The audit proves only the three named review-repair paths changed from the prior D implementation; the other21 hashes are identical.

New production deviation patches against immutable f31406e970d67f7cd59694da5de88915adb0fa68: split-d-alias-settings-frozen-deviation.patch and split-d-alias-server-frozen-deviation.patch. Preserve these alongside the earlier split-d-sqlite-frozen-deviation.patch. D now has14 whole frozen file selections and these two additional disclosed production repairs; the original implementation report's historical16-whole count predates review.

Suggested shared-memory decision (parent-owned): Validate path shape in the common composition settings boundary, since dedicated-loader checks do not protect direct callers. Teardown resources need independent finally stages so one close error cannot strand SQLite ownership or suppress socket cleanup.

No credentials, environment files, providers, live grants, production resources, Git commits or other worktrees were accessed or changed by this repair. Runtime behavior differs only for unsupported double-slash roots and failure cleanup; persisted schemas, provider behavior and normal successful startup/shutdown remain unchanged.
