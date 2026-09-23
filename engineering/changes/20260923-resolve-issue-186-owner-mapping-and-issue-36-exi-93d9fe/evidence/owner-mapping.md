# Owner mapping evidence — issues #186 and #36

Audit source identity: repository `/tmp/agbp-issues-186-36`, route `93d9feecc1dc`, audited `origin/main` `130ce4a42d9f9bbd1b56772d40b19ae530283205`, tree `3b51c9d21550627bb35fdb06753d2bedd5cf97ff`.
Candidate identity: committed HEAD `8dac90df509bd197ca14c670c30b5fc2ab5e73c2`, candidate tree `355d42f9f2d7f1b4ca3406bd2c01825b14c1bdf43eeb9c9505b3a9935df4efd6`.

## Audit commands

```text
git fetch --all --prune
git ls-tree -r --name-only origin/main
git grep -n -E 'if !|\$\?|exit_code|exit status|status_file|status.*file|write.*status' origin/main -- 'scripts/**' 'trust-ci/**' '*.sh' 'tests/**' 'delivery/**'
git grep -n -i -E 'issue.?36|#36|issue.?186|#186' origin/main
git log --all --oneline -G 'if !.*cmd|code=\$\?|exit[_ -]status.*(file|record)|record.*exit'
git log --all --oneline -S'if ! ' -- scripts trust-ci factory tests
git log --all --oneline -S'code=$?' -- scripts trust-ci factory tests
```

## Result

No tracked source, command, shell recorder, or reachable product-history implementation owns the reported `if ! cmd; then code=$?; fi` pattern. The safe characterization reproduced the mechanism: `if ! bash -c "exit 7"; then code=$?; ...` reports `0`, while direct/`else` capture reports `7`. Existing owners preserve status through `.grok-stack/adaptive_grok/verification.py`, `.grok-stack/adaptive_grok/python_test_runner.py`, and `trust-ci/src/adaptive_trust_ci/sandbox.py`; this is not evidence of the absent shell defect.

## Issue mapping and disposition

- **#186:** repository audit complete; disposition is “no local owner / no speculative fix.” No issue closure is claimed here.
- **#35:** reported `verify:deploy` multi-file shell syntax target is absent; no `package.json` or matching gate exists.
- **#36:** reported shell recorder is external/misrouted to this tree. No external repository, exact path, command, maintainer, or closure is asserted. Residual blocker: an authoritative external owner/link and reproduction were not supplied.
- **#39:** ESLint/worktree report targets a distinct JavaScript repository; this tree has no tracked `package.json` or ESLint config.
- **#48:** CLI guard/gist report targets an external installed CLI, not a file installed by this repository.

This characterization/source audit is the regression evidence for an absent owner. No product code, test, OpenAPI/event/SQL contract, verifier semantics, or Trust CI deployed behavior changed. A future fix requires a separate change after an external owner link identifies the actual source.
