# Repository exploration — issue #122

## Findings

1. `trust-ci/config/policy.example.json` is a catalog-mode example, not the policy evidenced as deployed in the activation report. It names two real-looking repositories (`Dimkox/adaptive-grok-build-pro`, lines 57–60; `Dimkox/ii-tonya-platform`, lines 132–135), contains executable profile commands (for example lines 60–113 and 135–156), and specifies absolute host/worker holdout paths plus digest-looking values (lines 115–129 and 158–173). The `approval_rules` at lines 20–55 also look operational and define `governance`, `database`, and `production` scopes. These fields are shape-valid configuration, but by themselves do not establish that either profile, command set, approval-scope set, or holdout is installed on the Trust CI host.

2. `trust-ci/README.md:19` already says the example is illustrative, pending separate server-side policy/holdout installation, and does not claim either repository is enabled. However its wording is not sufficient to prevent treating the exact-looking approval rules as deployed policy, and does not identify the authoritative live observation. Narrow correction: explicitly state that all `approval_rules` and profile values in `policy.example.json` are examples only and are not evidence of deployed scopes/enabled repositories; point to the authenticated policy handoff and live health endpoint for the deployed epoch, plus GitHub branch protection / the App-owned Check Run for the required check. Do not rewrite approval scope values or change code/config semantics.

3. The epoch is calculated from the **effective canonical policy**, not the raw example-file bytes. `trust-ci/src/adaptive_trust_ci/policy.py:367–394` constructs each effective profile, hashes each normalized `Policy` (`:256`), and for catalog mode hashes the ordered repository/profile-digest mapping (`:379–394`). `trust-ci/src/adaptive_trust_ci/policy.py:275–278` derives the legacy check name from its digest; `trust-ci/src/adaptive_trust_ci/api.py:74–84` exposes the active `policy_digest` in `/health/ready` for legacy mode and catalog digest/mode/profile count for catalog mode. `trust-ci/README.md:258–284` provides the supported operator procedure: obtain the exact deployed policy via the authenticated human-owned handoff, calculate the canonical digest, compare it to `/health/ready`, and stop if they differ. Raw `sha256sum` is explicitly not equivalent (`README.md:286`).

4. The `engineering/runbooks/trust-ci-activation-report.md` is a dated historical activation record, not a live source: it says “Fill after live M0.2/M0.3” (`:3`), gives report date `2026-08-24` (`:11`), and records digest `6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5` and corresponding check `adaptive-trust-ci/verified@6737355947c2` (`:19–20`). Its opening `:5` calls that the protected-main check at the time. It should be clearly labeled historical/as-of that report date and users should be directed to the current authenticated handoff + `/health/ready` for today's policy digest; the actual required check must be verified in GitHub branch protection and as an App-owned Check Run on the exact PR head. A static report cannot establish the currently deployed epoch.

## Reproduction / consistency check

Loaded the checked-in catalog with `PolicyCatalog.load(trust-ci/config/policy.example.json)`. It is accepted as a catalog and derives catalog digest `607ac23dd0b20339a835738d462ba7efbdf6280b25778a4666ff170238cf17a9` (check suffix `607ac23dd0b2`), with profile check suffixes `3f516cf4a96b` and `965715d8df90`. These do not match the historical activation report’s `6737355947c2`. This confirms the checked-in example is not the policy instance documented as deployed in that report. It does **not** establish whether a later deployed policy epoch exists.

An attempted `Policy.load()` of the catalog file correctly rejected it because `Policy.load()` is for legacy policy shape (`allowed_repositories` and root-level commands/holdout); catalog files must use `PolicyCatalog.load()`. No deployed policy file, live endpoint, host runtime, or GitHub branch-protection state was accessed during this read-only analysis.

## Evidence locations

- Example rules and catalog profiles: `trust-ci/config/policy.example.json:20–55`, `:57–176`.
- Existing “illustrative only” language: `trust-ci/README.md:19`.
- Epoch derivation and naming: `trust-ci/src/adaptive_trust_ci/policy.py:240–278`, `:367–394`.
- Live readiness fields: `trust-ci/src/adaptive_trust_ci/api.py:74–84`.
- Authoritative human handoff and digest comparison: `trust-ci/README.md:256–290`.
- Historical activation values: `engineering/runbooks/trust-ci-activation-report.md:3–24`.

## Uncertainty

The repository evidence only proves what the example and dated report contain. Current deployed policy, current branch-protection check name, and current Check Run ownership/status must be read from the operator’s authenticated handoff, `/health/ready`, and GitHub respectively. They must not be inferred from the checked-in example or the August activation report.
