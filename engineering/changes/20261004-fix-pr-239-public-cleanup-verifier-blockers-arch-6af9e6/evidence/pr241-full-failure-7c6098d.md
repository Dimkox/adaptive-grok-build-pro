# Historical full-gate refusal — PR241 head 7c6098d

This is a compact diagnostic record, not a complete report, successful receipt, external approval or current qualification.

- Historical candidate: `7c6098d791912fd6039c931c0f90878e32451167`.
- Historical fingerprint: `dc849ec3f3aa0bfe492ee046a5262e997f282f73484e62813a011ae04c8d1dee`.
- Actual agreed comparison base: `6dbbc7dbe81812d919851c2300db6f4917033d43`.
- Local command: `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack GROK_TEST_WORKERS=12 taskset -c 0-27 python3 -B scripts/grok_verify.py --mode pr`.
- Started 2026-10-04T17:51Z; observed completed 2026-10-04T18:04Z. Exit1, report status fail, terminal completed, evidence recorded.
- Selector: full-pr-suite, unsafe-file-status, changed paths1453, no selector skips. The separately unconfigured workflow-artifacts check was skipped, not passed.
- Core: 4 failed, 1185 passed, 2058 subtests passed in123.67s. Runner exit1 /124.166s.
- Coverage measured81.66%, above configured74%, but failed qualification because the test invocation failed. It is not a passing coverage gate.
- Other local checks passed, including architecture, governance, Factory unit/PostgreSQL, source stability and QG-01. These are historical scoped observations, never authorization to skip checks for the repair head.
- Complete original479036-byte report remains in ignored local runtime under `receipts/6af9e6eed1d8/reports/4cba0fe57454c835f88b41c68e146491c8e07399f7ab1d21aa084256b9d26fab.json`, SHA256`4cba0fe57454c835f88b41c68e146491c8e07399f7ab1d21aa084256b9d26fab`. It is private and not publicly dereferenceable. This Markdown does not modify, replace or pretend to expose the original report.

## Four failures and root causes

1. `StructureTests.test_repository_root_holds_only_canonical_entries`: closed ROOT_ENTRIES omitted the nine deliberately retained compatibility launchers. Its git ls-tree HEAD assertion had passed before commit because that earlier HEAD did not yet contain the restored files.
2. `FocusedPythonExecutionTests.test_admitted_inventory_never_executes_full_suite_discovery`.
3. `FocusedPythonEmptyTargetTests.test_the_replaced_runner_is_named_by_the_caller_not_assumed`.
4. `VerifyDocsStateScopeEndToEndTests.test_verify_selects_and_runs_the_focused_profile_for_a_docs_only_successor`.

The latter three temporary fixtures lacked tests/__init__.py. Under the Core runner's inherited candidate/candidate-tests/candidate-stack PYTHONPATH, Python selected the real candidate's regular tests package instead of the fixture namespace. Each nested invocation ran the real152 focused tests, propagating the root-inventory failure. A green status after updating the root list could still conceal wrong-tree execution; the repair additionally asserts that exactly five fixture tests execute.

The selected architect independently reproduced plain-unit pass, selected-pytest pass and Core-style inherited-path failure on exact7c in private scratch. Diagnosis was read-only. Repair`a83d4e5c28b097bcc00147bd255c55d07701e595` adds only the nine exact canonical names, three empty fixture package markers and three execution-count assertions; production runner, environment, selector and gates are unchanged. Targeted12 controls passed19.539s; the four original failures passed1.026s AFTER COMMIT under the inherited Core-style path. These targeted results do not replace a fresh full gate.

## External failure

App-owned check`111494300960`, name`adaptive-trust-ci/verified@06ecf1c875bc`, exact historical7c head:

- Started2026-10-04T17:51:14Z; completed2026-10-04T18:03:47Z.
- Conclusion FAILURE; title Exact SHA failed independent Trust CI.
- Reported results: holdout-bundle-integrity pass(exit0); external-holdout pass(exit0); root-unittest fail(exit1).
- Later pipeline checks were not reported as executed; do not label them passes.
- Attestation identifier`d62170ba-f640-48bf-aced-f1f6f7373c82` is an observed public identifier only; no cryptographic envelope or human approval was generated or verified here.

The failed check barred merge. It was not overridden, relabelled, administratively merged or retried unchanged. A real test repair and new exact-head local/external gates are required.
