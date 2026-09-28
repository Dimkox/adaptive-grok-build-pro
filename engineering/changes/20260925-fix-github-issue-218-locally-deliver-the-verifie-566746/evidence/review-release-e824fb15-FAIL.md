# Independent release review — issue #218, e824fb15

Verdict: FAIL — one Important package-contract inconsistency and one Minor dated-state inconsistency. The exercised product regressions pass; this report does not identify a new product-code blocker. External delivery remains outside the authorized scope.

## Source identity and isolation

- Candidate: `/home/pall/grok-projects/adaptive-grok-build-issue218-delivery`.
- Route: `566746aef130`.
- Package: `engineering/changes/20260925-fix-github-issue-218-locally-deliver-the-verifie-566746` (abbreviated `PACKAGE` below).
- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`.
- HEAD before and after: `e824fb1551ff37ab647c52b00a1fce38ede79213`.
- Git tree before and after: `0e1c4b188503793d48d61ded35afedf109170e3d`.
- Candidate fingerprint before and after: `4e84b701ed15ca39741205a37517b18306ef5a7708ccfd0d5e83ad7e945f2104`.
- Development source: `68dfc70c5f58adcc927f731c5d88de09a1b4b242`, tree `0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66`.
- Scratch: `/home/pall/issue218-release-review-fWpN8ZEO`, mode `0700`, owned by `pall`, beneath `/home/pall` (mode `0750`, non-sticky, owned by `pall`). Exact snapshot is its `repo/` directory.
- reviewed-tree-modified: no

The candidate had exactly one existing unstaged path, `PACKAGE/state.json`; no staged or untracked paths were reported. The scratch uses a local `git clone --no-hardlinks --no-checkout`, checks out the exact HEAD, and copies that dirty state file. Its fingerprint matched the candidate before and after probes. State-file SHA-256 is `2d3fc4a00febbf08c7a1735a598c5001c42c610f2f1aabec297cf19c08a78e73`. Only the non-secret runtime route and active-change pointers were copied for status diagnostics. No receipts or grants were copied. The first scratch status lacked its active-change pointer and correctly reported a missing package; after copying that pointer, the actual diagnostic below succeeded. That setup result is not a candidate defect.

## Findings

### Important I-1 — authoritative scope and delivery documentation contradict the repairs

`PACKAGE/change-spec.yaml:18` still says: “Do not modify product behavior beyond the exact recorded generated-template compatibility repair.” This contradicts its own AC-007 through AC-010 and the authorized, implemented post-source changes in `util.py` and `verification.py`. The objective at line 30 likewise describes only the compatibility repair. This is not a request to remove the security fixes: the typed constraint needs to describe their actual bounded scope.

Supporting contradictions remain in `PACKAGE/requirements.md` AC-003 (the only post-source behavior change is empty-bullet whitespace), `PACKAGE/architecture.md:26` (verifier code “copied exactly from source, not modified here”), and its six-path diagram. `PACKAGE/release.md:6-8` still describes a package-only delta and a commit-before-reviews sequence without the required reports/ready/final-recording tail. The implementation report accurately records the later repairs, but it cannot override the typed forbidden outcome.

Correct the active contract and current architecture/release description to include the exact eleven non-package paths, fail-closed security repairs, budgeted maximum-monotone-anchor algorithm, and mandatory completion sequence. Distinguish historical construction evidence from current assertions. Reconcile evidence-accounting reasons currently saying “implementation not started” before final `ready`. Any scope-file correction changes the gate digest; materialize the already authorized bounded consent against that corrected scope using the repository workflow, without broadening authorization. Persist reports, preserve the one-direct-child topology, and regenerate final verification and receipts afterward.

### Minor M-1 — current release wording conflicts with an available local tag

`README.md:7` says v2.0.19 tag publication remains pending; `START_HERE.md` says the tag remains absent. The local repository contains annotated tag object `4e5d1505433f7a2d5faa71db31c0b4d964f77897`, peeling to `cb9af4073ba6c3d515145164d771c75ebdfa3224`. These inherited dated descriptions should explicitly identify their observation date and distinguish a locally present tag from unverified remote publication. No network lookup was authorized, so this report does not claim the remote tag or GitHub Release exists, nor that v2.0.18 is or is not the latest published release.

README's product version matches `VERSION` (2.0.19), its updated worker/verifier/receipt sections reflect the cumulative implementation, and its architecture model/rules/generated-view targets exist. A release or push proposal must reconcile the current-state wording with then-current authorized observations. No artifact rebuild or version bump is requested here.

## Executed checks and observations

All executable probes ran in scratch unless explicitly identified as read-only candidate identity checks.

1. `git rev-list --count cb9af4073ba6c3d515145164d771c75ebdfa3224..HEAD` returned `1`. `git rev-list --parents -n 1 HEAD` returned exactly the reviewed HEAD and declared base. This is one non-merge direct child.
2. `git diff --check cb9af4073ba6c3d515145164d771c75ebdfa3224 HEAD` exited 0 with no output. Base-to-HEAD inventory contains 211 paths.
3. `git diff --name-only 68dfc70c5f58adcc927f731c5d88de09a1b4b242 HEAD`, checked against the exact package plus declared path allowlist, produced 33 paths: 22 package paths and 11 non-package paths, with `out_of_scope=[]`.
4. `git diff --name-only cb9af4073ba6c3d515145164d771c75ebdfa3224 HEAD -- trust-ci .github/workflows packages VERSION architecture` returned no paths. A separate query for `engineering/changes/*219*` also returned none. The candidate does not modify Trust CI, GitHub Actions, immutable release artifacts, version identity, or architecture authority.
5. `PYTHONDONTWRITEBYTECODE=1 python3 scripts/grok_gate.py status` reported `scope_and_design_approval=approved`, digest `2ba6e2e67943b3ca4f6144ef9b4f5af7194f6f7a56157623c989eaea6c1d1dfa`. This is local workflow evidence only.
6. `PYTHONDONTWRITEBYTECODE=1 python3 scripts/grok_status.py` reported package `complete`, stage `reviewing`, clean product state, and expected gaps: dirty completion tree plus missing verification/code/test/security/release receipts. Missing final receipts are expected at this review stage and are not a separate defect.
7. `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_architecture_model_preflight` passed: 26 tests in 3.947s.
8. The following exact command passed six tests in 1.591s:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_verification_doctor.VerificationTests.test_added_whitespace_classifier_tracks_duplicate_occurrences_and_order \
  tests.test_verification_doctor.VerificationTests.test_chain_whitespace_uses_longest_stable_clean_order \
  tests.test_verification_doctor.VerificationTests.test_chain_whitespace_budget_exhaustion_is_structured_incomplete \
  tests.test_verification_doctor.VerificationTests.test_chain_wires_one_aggregate_whitespace_budget_across_edges \
  tests.test_verification_doctor.VerificationTests.test_endpoint_wires_one_budget_across_worktree_and_index \
  tests.test_verification_doctor.VerificationTests.test_endpoint_whitespace_rejects_moved_and_duplicated_bad_occurrences
```

9. Read-only candidate and scratch identity checks used `git rev-parse HEAD HEAD^{tree}`, `git status --porcelain=v1 --untracked-files=all`, and:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack python3 -c 'from pathlib import Path; from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'
```

Both fingerprints remained equal to the recorded value. Candidate identity and dirty-state inventory were unchanged.

## Compatibility, other lanes, and recovery

The cumulative candidate includes the #227/#226/#224/#222/#220/performance stack plus #218. It is not a standalone two-commit #218 backport. The existing #222 package documents the two original #221 commits, `fc89a341...` and `4200289a...`, and their restacked provenance. Current architecture/doctor/tests include subsequent integration repairs; they are not byte-identical to the old #221 tip. The 26-test architecture run supports retention of that path-shape behavior, including the #50 diagnostic work. A future delivery should identify the #221 overlap explicitly and coordinate supersession or refreshed integration; this local review neither closes #50 nor changes #221. Current remote PR/issue state was not queried.

#219 remains a separate Trust CI runner/holdout/digest lane. Absence of a `trust-ci/**` diff proves this candidate does not deliver that lane; local scanner success does not establish deployed holdout parity. A future base change requires fresh verification and an external check.

The scan report contract remains `adaptive-grok.verification-scan/v1` within schema-v2 completion receipts. Incomplete or old scanless receipts must be regenerated; a one-commit squash changes identity, so stacked-source receipts cannot be reused. No production schema, service deployment, persistent migration, or feature flag is introduced by this delivery. Observability remains exact source/base/head identity, scan completeness/findings, dependency-barrier output, check durations, receipt status, and later external attestation.

Rollback is suitable for this source-only candidate: preserve the development branches; abandon the isolated local delivery branch before external delivery, or use a reviewed revert of the single squash after delivery. No database down-migration, secret recovery, deployed-policy edit, or production cleanup is required. Rollback execution was not authorized or performed.

## Mutants, unexecuted claims, and authority

- Mutants executed by this release reviewer: none; no killed/survived score is claimed. Mutation probes are mandatory for code/test reviewers, whose independent reports remain required. Historical mutant results in the implementation report were read as history, not promoted into current reviewer evidence.
- The coordinator reported a fresh full `grok_verify.py --mode pr --no-record` PASS for this HEAD. This reviewer did not rerun the full Core/Factory verifier or inspect its full raw log; the focused runs above are independently observed.
- The historical exact pre-package `git write-tree` projection was not reenacted. The source object, one-commit topology, final inventory, and preserved construction report were inspected.
- External PR status, remote releases/tags, deployed policy, external holdout, branch protection, signed approvals, and exact-head App check were not queried. No fetch was performed because the task explicitly forbids network access.
- Documentation statements about production rollback, full platform support, Docker cleanup, and immutable published artifacts were statically reviewed; no production/platform/Docker/rollback or publication probe was executed by this reviewer.
- No candidate files, source branches, grants, receipts, issue states, PRs, tags, releases, deployment systems, or approval keys were changed or accessed for mutation. The only writes were in private scratch.

Final local release-review verdict: FAIL, with 0 Critical, 1 Important, and 1 Minor finding. Repair the documentary contradiction, finish the committed-tail workflow, and obtain fresh final verification and routed receipts before local completion. Any eventual PR merge still requires the App-owned policy-epoch check on the exact PR head and separately required approvals. This report authorizes no external action.
