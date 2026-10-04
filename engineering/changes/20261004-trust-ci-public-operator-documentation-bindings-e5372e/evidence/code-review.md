# Independent code review: PASS

Route: e5372ed69c31. Base: 97a7581238022356b2de8d193a9bd8363fc92dc3. Candidate HEAD before/after: ee3a970ffa5e481a81de10def538670a3eaf080e. Candidate fingerprint before/after: 81cb9328950acb91d9da386718f43471c3d36d627cf6e7cf32b8a0efea8288f5. Candidate Git status remained clean. Reviewer: code_reviewer, independent of the integration writer.

Scratch relative to candidate: ../../.review-scratch/companion-code-I1GcAs/snapshot, under reviewer-owned non-sticky mode 0700 parents. Exact clean committed snapshot reproduced with a local shared clone and restored to its clean fingerprint afterward.

reviewed-tree-modified: no

Inspected active route, brief, requirements, verification plan, implementation evidence and actual base-to-HEAD diff. The only executable change is trust-ci/tests/test_m0_invariants.py. Public placeholders preserve uniquely named document roles and consistency but supply no live identity or merge authority. Existing protected-main, epoch, exact-SHA, App authentication, API/worker separation, loopback and no-Actions assertions remain.

Baseline commands from scratch:

    GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack:trust-ci/src taskset -c 0-3 python3 -B -m unittest discover -s trust-ci/tests -p test_m0_invariants.py -v
    ruff check trust-ci/tests/test_m0_invariants.py
    GIT_OPTIONAL_LOCKS=0 git diff --check

Original documents: 20 tests passed, 0.031 seconds. Ruff: All checks passed! Whitespace check passed. Exact public projection from PR239 commit 52e1163da49d80b1ee40210c48e565f2fa3f13e7 also passed 20 tests in 0.037 seconds. Public spec, plan, report, README, decisions and mistakes were reproduced by exact git-show reads and apply_patch in scratch only.

Each mutation used this command prefix:

    GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack:trust-ci/src:trust-ci/tests taskset -c 0-3 python3 -B -m unittest -v

Append the exact fully qualified targets below:

- Allow duplicate declarations: test_m0_invariants.OperatorDocumentBindingTests.test_rejects_missing_duplicate_and_decoy_report_fields and test_m0_invariants.OperatorDocumentBindingTests.test_rejects_missing_duplicate_and_wrong_section_role_declarations. Killed: seven failures.
- Disable consistency: test_m0_invariants.OperatorDocumentBindingTests.test_rejects_mismatched_declarations_in_every_document. Killed: eleven failures.
- Public protected-main=false: test_m0_invariants.M0InvariantTests.test_m0_3_main_is_app_bound. Killed: one retained protected-main assertion failure.
- Replace dated App binding's protected-main role: test_m0_invariants.M0InvariantTests.test_operator_docs_name_funnel_app_webhook_url. Killed: one failure, expected one dated main App binding, found zero.
- Alter exact spec SHA and dated epoch: test_m0_invariants.M0InvariantTests.test_m0_spec_and_plan_exist and test_m0_invariants.M0InvariantTests.test_m0_3_main_is_app_bound. Killed: two retained identity assertion failures.

No surviving/inconclusive probes. Fixture tests additionally exercise missing/duplicate sections, wrong roles, mismatches, malformed syntax, wrong placeholders and endpoints. Mutations and public substitutions were restored in scratch only.

Unexecuted: complete PR verifier, full Trust CI suite, PostgreSQL and external exact-head CI. Coordinator/writer suites are separately attributed; cancelled scope is not a pass. Live deployment, keys, policy and branch protection were not accessed or changed.
