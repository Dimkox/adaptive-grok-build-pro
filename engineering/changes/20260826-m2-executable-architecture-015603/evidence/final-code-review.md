# Final whole-branch code review — M2-A

## Reviewed identity

- Route: `0156034c05bd`
- Adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`
- Adoption-base tree: `b6bb74f00fba7fd194ac1da01a00cca7aea89bf5`
- Head: `99de2f9757400f7394b7a9e2c46b3ebce939e438`
- Head tree: `bae34faabdf968396e393d40f7219d3bbf5a60b5`
- Clean exact-head tree fingerprint at review start: `ebddb8684a2e35f23df32ad117de016b6bec6c11df8c51bc7444ebe6fd22b603`
- Packaged diff: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-25bfbe5..99de2f9.diff`
- Packaged-diff SHA-256: `385aef31d68d78ce9f68b824900bba01d9980e66bf5370897cda77b2dac49a01`
- Scope inspected: exact `25bfbe59ea188d9687b20a9caad19e7db3d031f8..99de2f9757400f7394b7a9e2c46b3ebce939e438`, 77 files, 16,401 insertions, 28 deletions. The base is an ancestor of the head. The worktree was clean when review began; independent reviewer reports appeared later and were not treated as product inputs.

## Verdict

**BLOCKED** — zero Critical findings, three Important findings, and one Minor finding. The implementation does not yet satisfy the fail-closed fitness, durable-adoption, and bounded-process portions of the approved M2-A contract.

## Important findings

### I1 — A deleted adopted architecture becomes `not_configured` after one later commit

`_active_architecture_binding()` distinguishes a legacy repository from deleted authority by checking only the current tree, the route base, and the current commit's direct parents (`.grok-stack/adaptive_grok/receipts.py:161-188`; parent enumeration is at `:148-158`). That evidence is not durable. On a normal pre-adoption route base, the sequence “commit adoption; commit deletion of `adoption.json`, `system.yaml`, and `rules.yaml`; commit an unrelated file” moves the adoption commit outside every inspected tree.

An end-to-end temporary-repository reproduction using the production `build_route`, `set_active_route`, and `verify` APIs produced:

```text
adopt     90bffc5c9a6544c7124ff3d5a90050612a0a7647
deletion  bb423700b8d2defc98a20b5f0ca7974912113e93
head      bb88ae72075b4204878fa864a614a2483621ed33
status    pass
architecture_meta  {'configured': False, 'status': 'not_configured'}
architecture_check {'name': 'architecture', 'status': 'skip', 'summary': 'architecture is not configured', ...}
```

The existing committed-deletion tests stop at the deletion commit (`tests/test_verification_doctor.py:280-320`). The merge test likewise checks the deletion commit itself (`:401-429`), while the depth-one shallow test supplies the adopted commit as its route base (`:431-462`). None covers a later descendant with the ordinary pre-adoption route base.

Impact: a consumer can remove all target-owned authority, add one later commit, and permanently bypass architecture verification and architecture-bound receipt behavior as a legacy repository. This contradicts the approved rule that after adoption deletion fails closed (`docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:177`) and the package requirement that later absence is invalid (`engineering/changes/20260826-m2-executable-architecture-015603/requirements.md:31-32`). A bounded durable adoption decision and a regression for the post-deletion descendant are required.

### I2 — Unavailable line statistics are counted as zero, so applicable code budgets pass open

For NUL-bearing or invalid-UTF-8 files, `_line_stats()` deliberately returns `(None, None)` (`.grok-stack/adaptive_grok/architecture_diff.py:659-670`). `_code_budget()` then computes changed lines with `(item.added_lines or 0) + (item.deleted_lines or 0)` (`.grok-stack/adaptive_grok/architecture_fitness.py:950-976`). Thus “cannot analyze” is silently converted to zero rather than an `unsupported` applicable result.

An end-to-end temporary Git repository with an applicable `src` budget of one changed line and a new `src/app.js` containing `b'line1\0\nline2\n'` produced:

```text
line_stats None None
code_budget pass () applicable
overall pass
```

The production rule covers `.grok-stack/adaptive_grok`, `architecture`, `engineering/contracts`, and `scripts` (`architecture/rules.yaml:37-49`), so binary/invalid-UTF-8 non-Python files in these paths can bypass `max_changed_lines`. Python decode failure happens to be caught later by AST analysis, but JavaScript, shell, data, and other suffixes are not. Tests cover normal text limits and line-stat ceilings (`tests/test_architecture_fitness.py:1333-1357`, `:1741-1770`) but not unavailable statistics flowing into the budget.

Impact: AC-004's “unsupported applicable analysis fails” requirement is violated, and the exact current fitness report can pass despite a budget metric being unknowable. Any applicable artifact with an unknown required metric must make the category `unsupported` (or otherwise fail closed), with NUL and invalid-UTF-8 regressions.

### I3 — Bounded process setup exceptions leak the started process group

`_run_capped()` starts the subprocess at `.grok-stack/adaptive_grok/architecture_diff.py:82-91`, then constructs/configures/registers the selector at `:95-100`; its cleanup `try/finally` does not begin until `:101`. An exception from `DefaultSelector`, `os.set_blocking`, or `selector.register` therefore escapes without stopping or reaping the already-started process. It also leaks a raw platform exception instead of a structured architecture failure.

With `os.set_blocking` forced to raise after a real sleeping subprocess was captured, the production function returned:

```text
exception OSError forced setup failure
alive_after_return True
review_cleanup_returncode -9
```

The reviewer explicitly killed and reaped that isolated process group after observing the leak. Existing process tests cover output-limit and timeout paths after setup (`tests/test_architecture_fitness.py:1682-1715`) but not setup failure.

Impact: exact Git/diff/line-stat analysis is not bounded on all failure paths and can leave descendants running. Process ownership must enter cleanup immediately after successful `Popen`, selector setup failures must be normalized fail-closed, and focused regressions must prove group termination/reaping for each setup stage.

## Minor finding

### M1 — Deferred closed-schema mutation coverage is still incomplete

The SDD ledger's deferred Task 1 concern remains accurate. `test_every_authoritative_object_is_closed_and_required` mutates the system root, node, runtime, edge, failure behavior, and rules root, and injects unknown keys only into a node, failure behavior, and rules root (`tests/test_architecture_model.py:301-346`). It does not exercise required/unknown-field behavior for system trust-domain, data-classification, secret-class, signal, or contract records, nor for the individual rules record types.

Independent structural inspection found all 10 system object schemas and all 13 rules object schemas currently have `additionalProperties: false` and require every declared property, so this is a test-depth gap rather than a present product defect. It remains Minor and should be expanded to prevent future schema drift.

## Acceptance-contract assessment

- **Strict model/schema parsing and deterministic digests:** no additional Critical/Important defect found. Current `summary --json` succeeded with architecture digest `ca97384dd1ceb33547ef6de0b38fc04a3dcbdb8648ce0a278f764bec11c562bc`; structural schema inspection found no open/incompletely-required object schema.
- **Exact diff, fitness, and monotonic risk:** exact base/head fitness returned `fitness_status=pass`, `risk_pre=red`, `risk_post=red`, `baseline_introduced=true`, exact base/head identities, and evidence digest `56f8b58ce24477dc13bd2399338bc02129b126c9c586f578c524a8f89ef157d8`. I2 shows that the category can nevertheless pass open on an adversarial applicable artifact, so AC-004 is not met.
- **Durable target adoption and architecture-bound receipts:** ordinary current-state and staleness paths are present, and focused M1 compatibility tests passed. I1 is a direct bypass of the durable post-adoption failure contract, so AC-005 is not met.
- **Bounded deterministic execution:** normal exact commands complete and output caps/timeouts are implemented, but I3 leaves a pre-finally process-lifecycle hole.
- **Read-only diagrams:** `architecture_diagrams` publicly exposes render, digest, and compare operations only; no publisher/write API was found. `diagram --check --json` returned `ok=true`, five stable digests, and no mismatches. Focused read-only and no-follow tests passed.
- **Package-aware queue provenance:** the shared queue result feeds fitness and risk, and focused 63/64-root provenance tests passed, including sibling-export negatives and relevant above-limit unsupported behavior. No new Critical/Important queue defect was found.
- **Installer target ownership:** `scripts/install_into.py:45-48,64-74` excludes adoption/model/rules even if they appear in `MANAGED_FILES`; the focused `--force` ownership regression passed. Examples remain under the non-authoritative template path.
- **M1 compatibility:** focused legacy-unconfigured receipt compatibility and route-base/head/contract staleness tests passed. No schema-v1 or criterion-binding regression was found beyond I1's adopted-deletion bypass.
- **Trust boundary and scope:** `git diff --name-only ... -- trust-ci .github/workflows` was empty. No new dependency, service, database, migration, queue, framework, external write, or Trust CI mutation was found.
- **Documentation truth:** README/Quickstart/roadmap describe M2-A as a local source candidate, keep K16's 120-edge graph decorative, state diagrams are read-only projections, preserve target-owned adoption, and explicitly leave final receipts, PR/external exact-SHA trust, M2-B enforcement, and deployment pending. No material overclaim was found.

## Review evidence

- `git diff --check 25bfbe59...99de2f9` — PASS.
- No paths under `trust-ci/**` or `.github/workflows/**` changed across the exact range.
- `grok_architecture summary`, `drift`, `diagram --check`, and exact `fitness` commands — exit 0; drift empty; diagram projections match; exact current fitness reports pass/red-to-red.
- Typed change-spec gate validation — exit 0, `ok=true`.
- Seven focused tests — PASS: diagram repository-read-only; diagram ancestor/final no-follow; both queue root-limit/provenance cases; installer target ownership under `--force`; legacy receipt compatibility; receipt staleness on contract/route-base/head changes.
- Three independent adversarial reproductions were executed against the production APIs for I1-I3; all temporary processes/repositories were cleaned up and no product file was changed.
- Broad verification was intentionally not rerun as part of this independent code review; the current review wave owns fresh exact-fingerprint verification separately.

## Residual risks and cannot-verify items

- The three Important findings require remediation and focused regression evidence before another final review. Current happy-path CLI/test success does not close them.
- This review did not inspect or validate deployed Trust CI policy, holdout content, protected-branch configuration, external Check Runs, signed approvals, or deployment state. Those are outside repository-local code-review authority.
- Parallel final-review evidence files appeared after the clean starting fingerprint. They do not change the exact committed product tree reviewed here, but receipts must bind the coordinator's final unchanged repository fingerprint after all authorized evidence is present.

## Merge-authority disclaimer

This report is local workflow evidence only. It is neither merge authority nor a substitute for the GitHub App-owned policy-epoch `adaptive-trust-ci/verified@<policy-sha12>` Check Run on the exact pull-request head, branch protection, or any required independently signed human approvals.
