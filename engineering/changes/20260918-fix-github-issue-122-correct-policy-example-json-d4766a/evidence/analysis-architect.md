# Architecture analysis — issue #122

## Finding

The issue concerns an authority-labeling gap around a checked-in example, not a demonstrated defect in Trust CI policy execution. `trust-ci/config/policy.example.json` currently has three `approval_rules` (`governance`, `database`, `production`); its governance globs include `trust-ci/**`, workflow and governance paths (file lines 20–55). A reader can mistake these suggested rollout inputs for the active server-side rules. The report in issue #122 provides observed examples (PR #113 and PR #13) and historical merges, but these precedents alone do not reveal the current deployed policy and must not be presented as the source of authority.

The repository already gives a correct high-level distinction in `trust-ci/README.md:19`: the example is illustrative only, the second profile digest is a shape-valid placeholder, and the example does not enable either repository. The deployment runbook, however, copies that file to `runtime/policy.json` at `engineering/runbooks/trust-ci-rollout.md:30` without a nearby qualification. Its exact active-policy proof process is split across later steps and says to inspect the generated `adaptive-trust-ci/verified@<policy-sha12>` check (`:52–63`). The documentation fix should make the caveat visible at the point of use and identify operator-verifiable active-epoch observations.

## Authority boundary and evidence

- `AGENTS.md:17–21` establishes that only the exact-head App-owned Check Run from deployed Trust CI is merge authority, that human approvals are signed outside the repository, and that repository changes cannot alter deployed policy, holdout, images, keys, trust stores, database state, or branch protection.
- `trust-ci/src/adaptive_trust_ci/policy.py:236–256, 275–278` derives the policy digest from canonical effective configuration and forms the check name as `<status_context>@<first 12 digest hex>`; therefore an example JSON’s configured scope globs do not prove that those scopes are deployed.
- `trust-ci/src/adaptive_trust_ci/api.py:60–84, 187–199` exposes health readiness and active digest metadata and emits `check_name`/`policy_epoch` metrics. In legacy mode `/health/ready` has `policy_digest`; catalog mode has `catalog_digest` plus mode/profile count, so documentation must not imply one universal health response field without accounting for catalog mode.
- `trust-ci/README.md:7–19` describes the epoch-named App check and explicitly marks the example illustrative. `trust-ci/README.md:265–283` demonstrates comparing an operator-controlled, reviewed policy digest with `/health/ready`’s active digest; this is stronger than inferring deployed rules from repository history.
- Current checked-in handoff records the required check `adaptive-trust-ci/verified@06ecf1c875bc` in `START_HERE.md:13`, `PROJECT_STATE.json` and `README.md:21`; this is a dated/current-tree observation, not a promise that the deployed epoch will remain unchanged.

## Recommended narrow change

Documentation-only. Add an explicit short warning immediately before or after the example-to-runtime copy command in `engineering/runbooks/trust-ci-rollout.md`: the checked-in JSON is a starting template, its `approval_rules` are illustrative configuration, and they are neither evidence of the active server policy nor a repository-side override of it. Point operators to the externally reviewed policy handoff and `/health/ready` comparison already documented in `trust-ci/README.md:265–283`, then require the exact Check Run on the exact PR head and GitHub App owner as the merge-gate observation. Qualify that catalog deployments expose per-profile active epochs/check names; the current API reports `catalog_digest` for catalog mode, while check names are derived from the resolved profile digest.

Consider one sentence in the example JSON itself only if it can be done without invalidating strict schema parsing (JSON has no comments). Prefer the runbook and existing README prose; do not add custom metadata keys to the policy JSON, because that changes its schema/digest inputs or risks suggesting the service consumes the annotation.

Do not edit or narrow the actual example `approval_rules` merely to fit recent precedent. Those rules are example content and may guide future deployment; the current deployed policy is external. Do not state that `governance` is never required, that the example is guaranteed to differ, or that prior green checks establish current policy. Do not inspect or mutate host-local deployed files or policy state as part of this repository change.

## Acceptance criteria and verification

1. The deployment instructions state next to the copy command that `policy.example.json` and its approval globs are illustrative; copying it is an operator deployment step, not evidence that the live service uses those exact rules.
2. The instructions name a reproducible active-epoch observation: compare the operator-reviewed external policy digest with the ready endpoint’s active digest (or catalog digest as applicable), and verify GitHub’s exact-head Check Run name/owner. The documented source for merge authority remains the deployed service, not commit history or local verification.
3. No policy JSON values, policy parser/runtime code, Trust CI deployment inputs, holdout, App configuration, or branch protection changes occur. No policy digest/check name behavior is changed.
4. Validate JSON syntax and schema of `trust-ci/config/policy.example.json` unchanged; run `git diff --check`; inspect the final diff to ensure it is docs-only and contains no new claims about live state. There is no need to run the full unit suite for a prose-only edit unless a documentation contract test is added or affected.

## Open implementation detail

The issue suggests documenting in the activation report or README. Since `trust-ci/README.md:19` already carries a sound caveat and `trust-ci/README.md:265–283` already contains the operational digest comparison, the smallest useful repair is to surface that caveat in `engineering/runbooks/trust-ci-rollout.md` at the copy/deploy sequence, optionally with links to those README sections. Avoid duplicating or contradicting the README’s catalog-mode distinctions.
