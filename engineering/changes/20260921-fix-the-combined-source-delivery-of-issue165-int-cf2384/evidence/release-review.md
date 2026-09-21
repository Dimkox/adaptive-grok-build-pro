# Independent release review — factory and tooling source delivery

Status: **PASS for the bounded local/source release review.** Final frozen-tree verification, all current review receipts and external delivery remain required. This report does not authorize merge, installation, migration execution, deployment, tagging or publication.

- Role: `release_reviewer`; route `cf23849faca6`.
- Repository: `/home/pall/grok-projects/adaptive-grok-build-factory-tooling`.
- Reviewed branch: `fix/factory-tooling-batch-20260921`.
- Reviewed HEAD: `c8ed34d0731e12e65f75f568d8fb3e9f0f64b2d5`.
- Reviewed Git tree: `5f481c6555b22df363f14d5d2d96d6d03a2c624c`.
- Actual delivered base: `5674c369c4a427d42bde2a5fb3a3e2f73c853cd0`.
- Scope: issue #165 diagnostics, issue #163 semantic-plan refusals and additive migration 022, issue #118 platform fallback, and only the worker-capacity subset of #62.

I read the engineering contract, adaptive-delivery, verification-evidence and release-readiness skills, route and required domain skills, current package, README, START_HERE and relevant PROJECT_STATE records. I inspected the actual base-to-HEAD diff, changed source and surrounding transaction/readiness/runner behavior, tests, recorded initial verification and historical failures. The worktree was clean before this report, and the reviewed HEAD remained unchanged. Review execution was limited to read-only source, Git identity, JSON and SHA-256 checks; no behavioral suite, Docker or PostgreSQL execution was repeated in this lane.

## Provenance and immutable boundaries

Independent checks confirmed all **19** manifest paths have the exact candidate bytes, SHA-256 values and Git modes: nine from #165 head `163847842ccddacd6f179c7a3ea082765530bb84`, seven from #163 head `d80c5c8d8e5afe938d195401715daf5e69192a81`, and three from #62/#118 head `08dd467d0dc9c173af01f3b47876a9a3fa1ca639`. The #165 Stop hook is included. The complete execution-persistence test file is candidate blob `069af430af09598fe70d81a17e64a20a0bd74369`, retaining separate historical 020→021 and current 021→022 upgrade tests. See `candidates.json` and `evidence/integration-source-identity.json`.

The delivered base is an actual HEAD ancestor. Its tree equals the tested PR #173 parent tree, `e5a5cb6b563e92fd234126acca9fc6c2eb1beb5f`; local source identity therefore does not depend on an assumed or unmerged prerequisite. All **21** historical SQL resources 001–021 match that delivered base. No diff touches `trust-ci/`, `architecture/`, `governance/`, `packages/`, `VERSION` or GitHub Actions. Outside the nineteen paths and durable change packages, the only changes are README, START_HERE, PROJECT_STATE, decisions and mistakes.

All **107** files in `evidence/imported-candidate-evidence.json` match their recorded source commits and hashes. The five adopted static analyses also match their original reports and hashes. These checks preserve provenance; they do not turn historical analyses or reviews into current receipts. The original eighteen-path omission and corrected nineteen-path scope remain recorded in the prior scoping package.

## Evidence status and historical failures

The initial combined full result belongs to head `4bc43cb7876d92b11efb289a121dcfef0a0355ac`, using `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json`, exit 0. I independently matched its raw report SHA-256 `d797b047c16090a7b4869a30d27edc3b5a2b2a5cf6936bcfd9b82164b779d32f` and recorded fingerprint `9e1ba0dfac35f1d09d6473a7b5bdcae1f0547cc32d0ec5f83c0df5c1d72c10c9` to the summary and inspected the recorded command outputs:

- Root suite: 877 passed, 1,426 subtests passed; measured coverage 81%.
- Pilot: 44 tests, one explicitly conditional sandbox skip.
- Factory unit tier: 60 tests.
- Disposable factory/PostgreSQL tier: 804 tests, two conditional skips.
- Workflow artifacts: explicitly skipped because unconfigured. Contract structure reports zero contracts checked; that check is not extra API contract coverage.

Commit `c8ed34d0` adds only six evidence/handoff files after that run. It does not change the nineteen source candidates. This supports reviewing the verified implementation, but the earlier receipt is not fresh for the reviewed repository tree. My read-only `grok_status.py` observation reported stale verification/spec/architecture/governance bindings and five missing review receipts, while package completeness was `complete` with all review obligations honestly `not_run`. No genuine initial checkpoint exists for this package; its route-base diagnostic fallback is documented rather than fabricated.

The archived #165 first code review still says FAIL for the raw-byte filename checkpoint defect, alongside the preserved correction and later results. The #165 initial full failure is not rewritten as success. The archived #163 historical-base full run still has exit 1 and failed architecture fitness/dependent governance. The #62/#118 measured RED, 38-test focused GREEN, scoped Ruff result and interpreter/platform limitations remain separate candidate evidence. None of these counts was summed to manufacture the integrated result.

## Recovery, compatibility and observable outcomes

Migration 022 is an additive, separately numbered replacement of `factory.semantic_plan_repair`; it retains the existing function signature, `SECURITY DEFINER`/fixed search path and coordinator-only execution grant. The inspected tests explicitly compare its replacement body with the immutable original after reversing only the named-refusal substitutions, and exercise populated-prefix ledger/data/function/ACL preservation. No table rebuild, data backfill, dependency or service is introduced.

Planning refusals become a separate closed `repair_plan_rejection` envelope. The Python parser accepts only that exact envelope, bounds unknown values to `planning_rejected`, identifies legacy SQL NULL as `store_returned_null`, and keeps malformed successful results distinguishable as corruption. The store raises the named refusal only after its transaction context exits. This preserves the commit boundary for deadline/escalation work, successful lifecycle results and replay; arbitrary database text is not exposed as a refusal reason. This supplies useful failure visibility without claiming operational rollout.

The recovery plan is appropriate: before installation, use a reviewed corrective source PR or independent non-data revert. After 022 has been applied, never remove/rewrite 001–022 or edit the ledger; restore behavior through a separately reviewed additive forward migration and compatible application code. Store readiness explicitly requires the installed migration count to equal the packaged count, so an eventual operation must coordinate drain/rollout and verify readiness, role/schema identity, successful replay and named refusal behavior. Neither old-package/new-database nor new-package/old-database mixed readiness is promised. This source review approves no database operation or downtime plan.

The runner remains optional. No opt-in preserves the previous path; explicit counts and child suppression remain distinct from automatic capacity selection. Linux `auto` conservatively intersects the existing cap and affinity/count fallback with finite quotas found through bounded visible membership, mounts and ancestors; unknown inputs select one worker. Missing parallel capability selects `unittest-degraded` before execution, strict supported pins remain enforced, measured serial coverage remains pinned, and an executed parallel failure is not retried as success. The new behavior does not establish native Windows execution, older-Python qualification, hidden ancestor limits, CPU reservation, PID headroom or memory capacity. README records those limits and the sequential recovery setting.

The diagnostic feature exposes additive fields and explicit unknown/not-run states, bounded lossless path identities and warning-only Stop output. The package guide distinguishes accounting completeness from passing execution/fresh receipts and documents canonical-state-before-mirror recovery. Existing external merge authority is not replaced by these observations.

## Handoff and delivery conditions

VERSION and README remain at product `2.0.18`; immutable published artifact identity is distinct from this unreleased source branch and dated installed runtime identities. README links to the architecture model, rules and all generated views resolve to existing unchanged files. START_HERE and PROJECT_STATE identify the actual delivered base, active branch/package, initial full PASS and outstanding reviews/receipts/external delivery. They retain the unproven pilot, M8 and M9 outcomes and separate #158 work.

One nonblocking documentation clarification is required during the already planned final handoff freeze: README's current-state paragraph still says “Fresh integrated verification ... remain pending,” while START_HERE/PROJECT_STATE distinguish the initial full PASS from final frozen-tree verification. State those two phases explicitly using their actual results. The coordinator acknowledged this correction; it needs no product change, but the final frozen-tree verifier must follow it.

Before claiming local completion, freeze the reports and handoff, run the complete final verifier, record all five selected current review receipts, and confirm zero evidence gaps. A product change requires renewed affected review and verification. Historical result adoption or this report alone cannot satisfy those steps.

Before merge, use the delegated exact branch/PR/merge operations and require `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App **4694114** on the actual final up-to-date head/base, with any required external signed approval scopes. Recheck the deployed policy epoch if it changes. The PR #173 check establishes only the delivered prerequisite; it grants no authority to this successor. Deployed policy, holdout, signing material, trust stores and branch protection remain outside this PR.

After actual successor delivery, closure is limited to **#165, #163 and #118**. **#62 remains open** for bounded failing-command output in App Check Runs; #158 and trusted-validator seven-kind compatibility remain separate. Retained **PR #135 closes only after its successor merges**. PRs #171/#172 are already recorded as closed after PR #173 delivery. No tag, GitHub Release, provider call, live service change or migration execution is implied.

No blocking source-delivery finding was identified within this review scope. Only this report was written; no receipt, source/shared-state edit, commit, push, external write, secret access or additional agent was used. Shared-memory fact for the coordinator: exact candidate/archive preservation and truthful initial-versus-final evidence status are established independently, while eventual migration readiness requires coordinated application/database rollout.
