# Final release/readiness review — M2-A executable architecture

## Exact identity and verdict

- Route: `0156034c05bd`
- Adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8` (tree `b6bb74f00fba7fd194ac1da01a00cca7aea89bf5`)
- Reviewed HEAD: `99de2f9757400f7394b7a9e2c46b3ebce939e438` (tree `bae34faabdf968396e393d40f7219d3bbf5a60b5`)
- Packaged diff: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-25bfbe5..99de2f9.diff`
- Packaged diff SHA-256: `385aef31d68d78ce9f68b824900bba01d9980e66bf5370897cda77b2dac49a01`
- Verdict: **BLOCKED**

Finding count: zero Critical, six Important, two Minor. PASS requires zero Critical and Important findings.

The candidate has a coherent source/deployment split, exact adoption baseline, reproducible architecture projections, and truthful open M2-B/external gates. It is not locally source-ready because five independently reproduced defects invalidate mandatory fitness, durable adoption, bounded execution, and installer ownership, and the required route evidence is therefore not green.

## Important findings

### REL-FINAL-I1 — real new queue jobs can be classified `not_applicable` and pass without risk escalation

The exact-head test review reproduces three queue-rooted forms that lose provenance in `.grok-stack/adaptive_grok/architecture_fitness.py:994-1068`: `from celery import *` followed by `@shared_task`, tuple/list unpacking of a queue-derived object, and a queue-derived indexed container. Each exact base/head probe returned `background=not_applicable`, `overall=pass`, and no `new_queue` trigger, while the supported direct-assignment control correctly failed as `unsupported`.

This contradicts the frozen fail-closed package-aware provenance design, AC-004, FORBID-002, README's claim that package-aware fail-closed queue provenance is implemented (`README.md:11`), and the roadmap's checked background-job fitness item. It can hide the exact new asynchronous work whose idempotency, correlation, bounded retries, terminal failure, and dead-letter behavior M2-A is supposed to gate.

Required repair: treat wildcard queue imports as unsupported when a changed operation may depend on their exports; either resolve bounded structured assignment/subscript provenance or conservatively return unsupported. Add exact base/head Celery and RQ tests for wildcard imports, tuple/list and annotated/chained assignments, indexed containers, malformed/ambiguous forms, negative controls, category result, overall status, `new_queue`, scanned scope, and monotonic post-risk. Both background fitness and risk must consume the same repaired result.

### REL-FINAL-I2 — installer can overwrite target-owned authority through symlink aliases

The installer excludes the three literal target-owned paths (`scripts/install_into.py:45-49,64-75`), but its managed-file boundary uses following checks and then `dst.parent.mkdir(...)` plus `shutil.copy2(src, dst)` (`scripts/install_into.py:79-82,123-140`). An existing managed destination symlink can target `architecture/system.yaml`, `architecture/rules.yaml`, or `architecture/adoption.json`; `--force` follows that alias and overwrites target-owned authority. A symlinked ancestor can redirect a managed write outside the target repository.

This makes the unconditional operator claims in `README.md:257` and `QUICKSTART.md:20` false and violates AC-006, FORBID-004, the design's explicit ownership boundary, and the release plan's installer statement. Direct-path exclusion and the current ordinary-file force test do not protect the filesystem write boundary.

Required repair: make every installer-managed destination operation repository-contained, regular-file-only, descriptor-relative/no-follow, and race-safe across all ancestors and the final entry. Add final-symlink, ancestor-symlink, special-file, and relocation tests under `--force`, proving target authority and outside-target bytes remain unchanged. Apply the same boundary to `AGENTS.md`, Bitrix-local guidance, and ensured directories where relevant rather than repairing only one copy loop.

### REL-FINAL-I3 — adopted architecture deletion becomes `not_configured` after one later commit

The exact-head code review reproduces a normal sequence in which architecture authority is adopted, all three authority files are deleted in the next commit, and an unrelated later commit follows. `_active_architecture_binding()` checks only the current tree, route base, and current commit's direct parents (`.grok-stack/adaptive_grok/receipts.py:148-188`), so the adoption history moves out of view and verification returns `status=pass` with architecture `not_configured`.

This violates the durable-adoption contract, AC-005, and the requirement that deleting adopted authority fails closed. Persist or derive a bounded durable adoption decision that cannot disappear after one descendant commit, while retaining legacy unconfigured compatibility; add ordinary-history, merge, shallow, deletion-commit, and post-deletion-descendant regressions.

### REL-FINAL-I4 — unknown line statistics silently become zero and pass code budgets

`_line_stats()` returns `(None, None)` for NUL-bearing or invalid-UTF-8 files (`architecture_diff.py:659-670`), while `_code_budget()` converts either unknown value to zero with `or 0` (`architecture_fitness.py:950-976`). The code reviewer reproduced an applicable one-line budget with a new NUL-bearing `src/app.js`; line statistics were unknown, but the category and overall fitness both passed.

This violates AC-004's rule that unsupported applicable analysis fails. Any unknown required metric in an applicable budget must return `unsupported` or fail; add NUL, invalid-UTF-8, non-Python, and mixed-file exact base/head regressions.

### REL-FINAL-I5 — process setup exceptions leak the already-started Git process group

`_run_capped()` starts the subprocess before selector construction/registration, but its cleanup `try/finally` begins only after those setup calls (`architecture_diff.py:82-101`). The code reviewer forced `os.set_blocking` to fail and observed the sleeping child still alive after the raw `OSError` escaped.

This violates the bounded-execution requirement. Process ownership and cleanup must begin immediately after successful `Popen`; normalize selector/setup failures to structured fail-closed architecture errors, terminate/reap the whole process group, and cover every setup stage with real-process regressions.

### REL-FINAL-I6 — required final review and receipt gate is not satisfied

The actual exact-head reports are not the passing wave described in the assignment: `final-code-review.md`, `final-test-review.md`, and `final-security-review.md` all say **BLOCKED** and contain the Important findings above. `python3 scripts/grok_status.py` reports all six required receipts missing: verification, code, test, security, data, and release. The route and durable package correctly remain `reviewing`; Task 6 review closure and M2-B remain unchecked (`tasks.md:12-13`).

No passing local completion claim or `ready` transition is valid for this tree. Return both defects to the same route-selected writer, rerun full exact-head verification and all affected code/test/security/data/release reviews, record every receipt against one current repository/spec/architecture fingerprint, and require zero status gaps. Any repair or documentation change invalidates prior fingerprint-bound evidence.

## Minor findings

### REL-FINAL-M1 — schema mutation regression breadth remains incomplete

The SDD ledger records this deferred limitation at `progress.md:74`, and `final-test-review.md` confirms that the required/unknown-field mutation matrix does not cover every trust-domain, classification, secret, signal, contract, and individual rule-record shape. Spot probes reject representative malformed records and the schemas are closed, so no parser acceptance defect was reproduced. Expand the matrix to prevent future per-definition schema weakening.

### REL-FINAL-M2 — SDD recovery/final-review pointers are stale

`.superpowers/sdd/2026-08-26-m2a-executable-architecture/progress.md:10` still says Task 6 is the next task even though lines 64-72 record it complete. `final-review-brief.md:5,9` points reviewers to superseded head `b995fae...` and the older packaged diff instead of `99de2f9...`. The assigned exact diff is valid and independently identified, so this did not conceal the current findings, but the durable review entrypoint should be updated before the next review wave.

## Evidence and readiness checks

- The exact review package contains 77 changed files, 16,401 insertions, and 28 deletions. Applying it to the adoption base was independently reported to produce a byte-identical exact-head tree.
- `git diff --check 25bfbe59..99de2f9` passes.
- The exact range under `trust-ci/**` and `.github/workflows/**` is empty. No root packaging marker, service, database, migration, queue/runtime, provider integration, or external action was introduced.
- README's K16 block contains exactly 120 unique `---` edges and labels the clique decorative-only. The linked system/rules/adoption files, schemas, CLI, and five generated views exist.
- `VERSION` and the README H1/current published identity consistently remain `2.0.12`. README accurately calls M2-A a local source candidate and does not present it as the published `v2.0.12` artifact.
- Installer/package manifests include the architecture modules, CLI, strict schemas, and non-authoritative examples while excluding direct installation of the target marker/model/rules. The direct inventory is correct; REL-FINAL-I2 is a write-boundary alias bypass.
- Root discovery reports 331/331 passing, diagrams render/check without repository mutation, the exact diff package is reproducible, and the active red spec maps 7/7 criteria. Those green checks do not cover or override the independently reproduced queue and installer failures.
- `state.json` remains `reviewing`; `requirements`, `tasks`, `release`, and `rollback` do not claim `ready`, merge, deployment, or independent M2-B enforcement. Rollback is source-only and non-destructive, with forward-fix/versioning after adoption.

## Pending gates and disclaimer

After local repair and zero-gap receipt closure, M2-A still requires separately authorized branch push/PR delivery. Merge eligibility then requires the App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run on the exact PR head plus all externally required signed approval scopes. Local source, tests, SDD ledgers, reports, and receipts cannot create that authority.

M2-B remains a separate route/package/branch implementing independent holdout/server-policy enforcement. Deployment of a new policy epoch, holdout, image, trust material, branch protection, database state, or external service is outside this review and requires separate operator authorization, immutable artifact evidence, rollout/rollback proof, and exact-SHA validation. No external action is required to repair or re-review the local source, and none was performed by this review.
