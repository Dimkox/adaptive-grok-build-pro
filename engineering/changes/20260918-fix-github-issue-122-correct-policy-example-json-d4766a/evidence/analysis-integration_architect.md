# Integration and Trust CI boundary analysis — issue #122

## Finding

This issue needs documentation-only clarification. `trust-ci/config/policy.example.json` contains example approval scopes and repository profiles, but it cannot establish what the deployed service currently enforces. The safe authoritative observation is a two-part operator handoff:

1. A Trust CI service administrator exports the exact deployed policy through the organization's authenticated, human-owned transfer channel. The human computes the normalized policy digest using the documented `Policy.load(...).digest` command in `trust-ci/README.md` and compares it with the live `/health/ready` response's `policy_digest`. Raw `sha256sum` of the JSON file is explicitly not equivalent.
2. The exact required check name is derived as `adaptive-trust-ci/verified@<first-12-hex-of-policy-sha256>` from that confirmed digest. The protected repository's branch-protection configuration identifies the required check and App ID; an App-owned Check Run on the exact PR head confirms it actually ran. `trust-ci/README.md` documents the format, and `engineering/runbooks/trust-ci-rollout.md` documents the protection procedure.

The relevant operator-safe command is already documented in `trust-ci/README.md`, “Verify the policy epoch and exact review target” (around lines 256–289): the administrator supplies an authenticated handoff file outside the checkout, then the operator compares its normalized digest with `GET $TRUST_CI_URL/health/ready`. This does not disclose policy through a new API and does not read local secrets or host state.

## Does README already provide the safe handoff?

Partially. `trust-ci/README.md` already labels the example policy illustrative (line 19), explains the policy-epoch check format (lines 8–11), and provides the authenticated handoff plus health endpoint digest comparison. It does not say plainly enough that the example's `approval_rules` are not evidence of live required scopes. Root `README.md` also contains a literal historical check `adaptive-trust-ci/verified@06ecf1c875bc` at line 21, while its later workflow description uses `<policy-sha12>`. The literal may become stale when deployed policy changes and should be replaced by the epoch placeholder with a link to the operator procedure. The historical deployment facts remain available in `engineering/runbooks/trust-ci-activation-report.md`; do not present them as current without fresh observation.

## Minimal documentation-only recommendation

- In `trust-ci/README.md`, explicitly state adjacent to the example-policy section: every repository profile and every `approval_rules` entry in `config/policy.example.json` is illustrative; neither the file nor its values establish the currently deployed repositories, commands, holdout, scopes, or required check.
- Link that statement to the existing “Verify the policy epoch and exact review target” procedure rather than copying policy data into the example or adding a new endpoint/tool.
- In root `README.md`, replace the literal check suffix with `adaptive-trust-ci/verified@<policy-sha12>` and link to `trust-ci/README.md` for current live verification.
- Preserve the existing example JSON and deployed policy untouched. A prose-only docs change needs diff/JSON syntax checks and any relevant documentation contract tests; no Trust CI source, deployed policy, branch protection, keys, or runtime state should be changed.

## No-go language

Do not claim the example's scopes are active, that historical check suffixes prove the current epoch, or that a successful local verifier/check text from a non-App actor establishes merge authority. Do not infer the deployed policy from checked-in source, the example digest, a historical activation report, or a check on a different repository/SHA. The exact App-owned policy-epoch check and separately required signed approval scopes remain the external authority. This analysis made no Trust CI/deployment changes and performed no production reads.
