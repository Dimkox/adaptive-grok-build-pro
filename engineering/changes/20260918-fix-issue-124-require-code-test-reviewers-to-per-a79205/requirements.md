# Requirements — Fix issue #124: require code/test reviewers to perform mutation testing in a private scratch copy outside the reviewed worktree, preserve the reviewed tree as read-only, and report which claims were executed with commands/output plus reviewed-tree-modified:no and scratch path. Update reviewer briefs/templates and tests.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Code and test reviewer instructions explicitly prohibit source mutation in the reviewed worktree and require private scratch for mutation testing.
- [ ] Scratch is a private directory with restrictive permissions below a trusted, non-sticky parent; mutations and generated artifacts remain outside the reviewed tree.
- [ ] Scratch contents represent the exact reviewed candidate snapshot, including relevant dirty changes, and reports bind to HEAD plus the candidate tree fingerprint.
- [ ] The candidate tree is checked before and after review; a changed candidate invalidates/stales the review result.
- [ ] Review reports state `reviewed tree modified: no`, the scratch path, source identity, and the exact executed claims, commands, and observed results; unexecuted claims are identified as unexecuted.
- [ ] Structural tests enforce required reviewer brief/config/report text while leaving reviewer sandbox mode read-only.
- [ ] Reviewers return reports out-of-band without modifying the candidate; after all reviews finish, the coordinator persists reports and reruns final verification for the report-containing tree.

## Failure and edge cases

- Scratch directory creation fails closed for writable/sticky/untrusted ancestry or permissions other than the required private mode.
- Missing candidate fingerprint, source mutation during review, or snapshot mismatch prevents a clean review claim.
- Static review claims with no executable probe remain explicitly unexecuted rather than represented as mutation-test evidence.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security:
- Reliability:
- Performance:
- Observability:
