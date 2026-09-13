# Review — successor commit a1e977e (release-record v2.0.16), read-only

**Verdict: PASS with 1 must-fix before merge** (hygiene only — every recorded identity verified true).

## 1. Identity vs reality — all spot-checks match
- `gh api check-runs/103797448701` → head `2b1517986b9b5b83a95b1286baac161074c58175`, conclusion `success`, name `adaptive-trust-ci/verified@06ecf1c875bc` = PROJECT_STATE `checked_head`/`conclusion`/`name`. ✔
- `gh release view v2.0.16` → `targetCommitish 969c4f65…` (= `merge_commit`), `publishedAt 2026-09-13T22:04:08Z` (= `published_at`/`local_candidate.published_at`), asset digests `sha256:71f63a10…c746d7` + `14e3753a…b254fb8`. ✔
- `git ls-remote --tags` → `v2.0.16` object `8486ddb648f97e79a5f3a81d9b539378d2d4b301` → `969c4f65…` = `tag_object`/`merge_commit`. ✔
- Local `sha256sum`: zip `71f63a1089f4009cc65ed0afb5b755418fa5a8bf1dd4ce2aebae2f1b8cc746d7`, sidecar `14e3753aadf21f29119fdc059d4c65791833144d8de1ece0b7d83adf1b254fb8`; sidecar text binds the same zip digest. Matches state, README and l5 ledger. ✔
- PR number 79, signer `0519cf1d47436f2e`, app 4694114, attestation `90cb34aa-6eb5-49ca-a0ec-104e11c5e722`, GitGuardian `SUCCESS` (no check_run_id claimed → nothing falsifiable). `observed_main_sha` = the tag target. ✔

## 2. Tests
`python3 -m unittest tests.test_project_state tests.test_manifest_package tests.test_structure -q` →
`Ran 89 tests in 21.805s` / `OK` (stray `/tmp/tmpnhuzpc0g/publish/project.zip` + digest line is test stdout, not a failure).

## 3. Historical no-churn (tests/test_project_state.py)
- 49 removed vs 61 added lines. Removed asserts: 24 `assertEqual` + 2 `assertFalse` + 7 `assertIsNone`; added: 41 `assertEqual` + 2 `assertTrue`.
- All 7 dropped `assertIsNone` are the pending-null invariants (`route_id`,`branch`,`change_package`,`checked_head`,`merge_commit`,`tree`,`pull_request`) that became positive identity asserts — upgrade, not loss. `published`/`external_effect` assertFalse→assertTrue is the correct semantic flip.
- v2.0.15 demotion is asserted, not dropped: `prior[0]` tag + `checked_head`/`merge_commit`/`tree`/`artifact.sha256` via named constants, `len(prior)==3`, `prior[1]` still v2.0.14. v2.0.15 block in PROJECT_STATE is byte-for-byte the old published block.
- Minor coverage delta: per-test asserts on `source_parent`/`source_parent_tree`/`reviewed_product_*` were removed without direct replacements (values unchanged, still null/287b27a; `test_manifest_package` still binds the digest). Not a blocker.

## 4. Ledger / timestamp walk
- `17:33:28` survives only in two intentional historical mentions (the successor tasks.md instruction and the ledger sentence explaining the correction); the gate value itself is now `17:33:02 UTC` in `l5-delivery-stack.json` and `check_completed_at: 2026-09-13T17:33:02Z` in PROJECT_STATE. Zero stale literal left.
- `engineering/reviews/l5-delivery-stack.json` parses; `release_v2_0_16` record carries tag object, merge, PR 79, checked head, run, attestation, signer, zip+sidecar sha and the "activation separate" note — all consistent with reality above. PROJECT_STATE parses; prior list length 3; `local_candidate.status=published`, `published=true`, `operational_activation=false`, scope `github_repository_delivery_and_release_only` (no overclaim). README/START_HERE/CHANGELOG/ROADMAP/VERSION(2.0.16) align; docs keep the repository-release-only caveat.

## Must-fix
1. New root file `implementing` (1 line, literal `states-`) is committed in this successor and would land on `main` permanently. It is absent from `969c4f6`/main, not ignored by `.gitignore`, not part of the shipped ZIP, and is unrelated to the commit's stated scope ("milestones/inventory/immutable objects byte-unchanged"). `git rm implementing` before opening/updating the successor PR — nothing in the test suite guards root-level file hygiene, so no test catches it.
