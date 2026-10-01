# Implementation report — workflow upstream refresh

Route: `8ba78f913978`. Sole write owner: `general_implementer`. Isolated branch: `chore/update-workflow-upstreams-20260930`. Comparison base: `5713b407818dbb6c2d1acfcb0b0d9661c32e1153`.

Source implementation commit: `a02af4d4fe2c14620c96b866658328f8ab602a0d` (`chore: refresh advisory workflow upstream pins and provenance`). This report is a later evidence-only commit; use the final branch HEAD for review and final verification, not this source commit or historical receipts.

## Delivered changes

- Config and README now agree on Superpowers 6.4.2, BMAD stable 6.12.0 and Spec Kit 1.0.13, each peeled stable commit and its separately observed main commit on 2026-09-30.
- The workflow-source contract binds those exact observations and all eight README columns. Named existing tests remain alongside the current samples.
- Four compact exact-revision samples characterize Superpowers Spec/Interfaces opacity, Spec Kit phase/parallel dependencies, stable BMAD nested tasks and BMAD main's advisory ticket context. Their separately stored bytes and closed fixture manifest bind SHA-256, repository, revision, source path, adapter identity and source version; mutation regressions fail on changed bytes or version before parser assertions. See `upstream-provenance.md` for immutable source URLs and excerpt/instantiation details.
- Runtime parsers, source-manifest bounds, installer behavior, product VERSION, package bytes and authority boundaries are unchanged. No upstream framework is installed or vendored.
- Change requirements, architecture, test plan, rollback and shared learning records document the bounded decisions and observed mistakes.

## Verification evidence

1. Red provenance contract: `python3 -m unittest tests.test_workflow_sources.WorkflowSourceContractTests.test_stable_release_and_observed_main_have_separate_exact_provenance -v` failed with three expected stale/missing-metadata assertions before the config update (old Superpowers 6.3.0, absent BMAD exact commit, old Spec Kit 1.0.7).
2. Green focused run after review repair: `python3 -m unittest tests.test_workflow_sources tests.test_workflow_artifacts tests.test_workflow_artifacts_adversarial -q` passed **65 tests**. New parser samples are characterization tests of the existing implementation, which required no runtime repair. The first BMAD main fixture exceeded the unchanged 32-character `source_version` bound; it was corrected to `main@1cbcfa272fe6` with full SHA retained in the frozen identity manifest and provenance.
3. Exploratory full run: `taskset -c 0-27 python3 scripts/grok_verify.py --mode pr` selected **full-pr-suite**, evidence kind `verification:full-pr-suite`, reason `out-of-scope-or-invalid-paths`, 18 changed paths, no scope skips. Actual suite/check results were PASS for `change-spec`, `architecture`, `governance`, `secret-scan`, `contract-structure`, `sql-safety`, `ruff`, `bandit`, `pilot-unittest`, `python-unittest`, `coverage`, `factory-unit`, `factory-postgres-exit` and `source-stability`; `workflow-artifacts` was explicitly SKIP because workflow artifacts are not configured.
4. That exploratory verifier's **overall result was FAIL**, solely because `git-diff-check` checked the earlier package HEAD `41d1a41756277ba91a5cc13eb4cf1049719616a3` against the comparison base and found two whitespace defects in package templates. The same run held the candidate tree stable. Its working-tree fixes were already present but were not part of the exact Git range.
5. After committing those repairs with the implementation, `git diff --check 5713b407818dbb6c2d1acfcb0b0d9661c32e1153..HEAD` passed at source commit `a02af4d4fe2c14620c96b866658328f8ab602a0d`.

The exploratory full result is historical suite evidence, **not a passing current receipt**. The coordinator explicitly chose a final integrated exact-tree verifier after collecting independent review reports rather than another identical implementation-phase full run. Final verification, review receipts, PR delivery and the App-owned exact-head Trust CI check remain required. No merge, publication, deployment, tag or push was performed by this write owner.

## Residual risks and recovery

Main observations may move after this date; immutable commit IDs preserve what was observed and are never install or stable-release targets. Compact samples prove the accepted subset, not execution of all upstream templates. BMAD main has no new native-task/status contract; Superpowers pointers are intentionally opaque. A successor PR can forward-fix metadata or samples with a new dated observation and rerun focused/full verification; no operational data recovery or runtime rollback is needed.
