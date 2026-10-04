# Independent test review: PASS

Route: e5372ed69c31. Base: 97a7581238022356b2de8d193a9bd8363fc92dc3. Candidate HEAD before/after: ee3a970ffa5e481a81de10def538670a3eaf080e. Fingerprint before/after: 81cb9328950acb91d9da386718f43471c3d36d627cf6e7cf32b8a0efea8288f5. Candidate status remained clean. Reviewer: test_reviewer, independent of integration writer.

Scratch relative to candidate: ../../.review-scratch/test-review-docbind-hXxj7M/repo. Reviewer scratch and trusted non-sticky parent were mode 0700. A clone without hardlinks reproduced exact HEAD/fingerprint; restored scratch matched again. Candidate Git calls used GIT_OPTIONAL_LOCKS=0.

reviewed-tree-modified: no

Capacity remeasured 2026-10-04T14:15:42Z: 14 physical/28 online logical CPUs, default affinity22, cpuset0-27, no finite ancestor quota. Child-only widening succeeded; at most four CPUs used.

Inspected exact diff and surrounding tests. Only executable delta: trust-ci/tests/test_m0_invariants.py. Role bindings reject misplaced fields and inconsistent identities. App ownership, recorded SHA, policy epoch, protected main, API/worker separation, loopback and absence of Actions assertions remain.

Commands ran from scratch repo, with GIT_OPTIONAL_LOCKS=0, PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=trust-ci/src:trust-ci/tests, and TMPDIR set to its private sibling tmp.

    taskset -c 0-3 python3 -m unittest -v test_m0_invariants

Observed: 20 tests passed, 0.037 seconds, zero skips. Concrete/public placeholders, malformed syntax, missing/duplicate/decoy report fields, misplaced sections, mismatches in each document and retained M0 invariants exercised.

Mutation commands under the same environment:

    taskset -c 0 python3 -m unittest -v test_m0_invariants.OperatorDocumentBindingTests.test_rejects_invalid_host_webhook_and_app_identity_syntax

Disable App-ID validation: killed, exit1, six subtest failures including accepting an installation placeholder as App ID.

    taskset -c 0 python3 -m unittest -v test_m0_invariants.OperatorDocumentBindingTests.test_rejects_missing_duplicate_and_wrong_section_role_declarations

Allow section extraction into unrelated sections: killed, exit1, three wrong-section failures.

    taskset -c 0 python3 -m unittest -v test_m0_invariants.OperatorDocumentBindingTests.test_rejects_mismatched_declarations_in_every_document

Disable consistency: killed, exit1, eleven mismatch failures.

    taskset -c 0 python3 -m unittest -v test_m0_invariants.M0InvariantTests.test_api_cannot_hold_github_app_or_client test_m0_invariants.M0InvariantTests.test_m0_3_main_is_app_bound

Combined private mutants: GitHubAppAuth marker in API source and protected-main=false in report. Both killed: two tests, two failures, exit1. Static assertion preservation is tested, not deployed credentials/protection.

No surviving/inconclusive mutants. Full Trust CI250 suite was not repeated by reviewer; coordinator's ten PostgreSQL skips remain unexecuted, not passes, requiring TRUST_CI_TEST_DATABASE_URL. Writer public projection is separate, not fresh execution by this reviewer. Full PR, unrelated discovery, PostgreSQL and external CI/approvals unexecuted. Cancelled startup scope is not completed verification. This is independent test-review evidence only.
