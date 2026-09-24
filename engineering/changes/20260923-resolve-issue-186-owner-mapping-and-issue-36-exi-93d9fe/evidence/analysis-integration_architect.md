# Integration architect analysis — issues #186 and #36

## Source identity

- Repository: `/tmp/agbp-issues-186-36`
- Route: `93d9feecc1dc`
- Change package: `engineering/changes/20260923-resolve-issue-186-owner-mapping-and-issue-36-exi-93d9fe`
- HEAD inspected: `130ce4a42d9f9bbd1b56772d40b19ae530283205`
- Product tree was not modified; this report is the only intended write.

This is historical/base analysis of the implementation tree, not a claim that
the evidence package has the same HEAD. Candidate package identity is recorded
separately in owner-mapping.md and the review reports.

## Commands and findings

1. `rg -n -i --hidden --glob '!*.pyc' '(#186|#36|exit.?status|exit.?code|command result|command_result|returncode|return_code|owner mapping|owner)' .`
   - Found the prior backlog disposition in `engineering/changes/20260921-research-open-backlog-map-each-item-to-its-sourc-d54d3a/evidence/analysis-docs_researcher.md` and `evidence/external-blockers.md`.
   - That evidence states that #36’s `if ! cmd; then code=$?` recorder is from another gate, with no matching recorder in this checkout. The issue queue records #36 as `external_owner_or_target_required`.
   - No repository source, command, contract, or issue mapping for #186 was found by the same search; the current change package is the repository-local place to bind the disposition.

2. `sed -n '353,362p' .grok-stack/adaptive_grok/verification.py`
   - `_command_check` calls the Python `run(...)` helper and sets `status='pass'` only when `proc.returncode == 0`; its summary contains the exact `exit=<returncode>` value. This path cannot reproduce the shell negation-status bug described by #36.

3. `sed -n '100,220p' trust-ci/src/adaptive_trust_ci/sandbox.py`
   - Trust CI sandbox execution reads `process.returncode` directly. Timeout is explicitly normalized to `124`; launch/runtime failures are explicitly normalized to `127`; otherwise the child return code is converted to `int` and passed to `_command_result`.
   - `_command_result` derives `status` from `exit_code == 0` and stores the exact `exit_code`, bounded output tails, duration, and output digest.

4. `sed -n '382,405p' trust-ci/src/adaptive_trust_ci/models.py` and `sed -n '1,95p' engineering/contracts/schemas/trust-ci-attestation-envelope.v1.json`
   - `CommandResult` requires an integer `exit_code`; `attestation_dict()` emits it.
   - The v1 signed attestation schema requires `name`, `status`, `exit_code`, `duration_seconds`, and `output_sha256`, with no additional command-result properties.

5. `sed -n '220,265p' trust-ci/src/adaptive_trust_ci/api.py`
   - The public Trust CI result projection already preserves `name`, `status`, `exit_code`, `duration_seconds`, and `output_sha256` for every command.

6. `rg -n -C 8 'command_results|exit_code|_run_bounded|subprocess\\.run|Popen|CompletedProcess|CommandResult' trust-ci factory delivery engineering/contracts schemas`
   - Trust CI tests exercise passing and failing command results, including nonzero exit code `96` in `trust-ci/tests/test_postgres_integration.py` and runner result construction in `trust-ci/tests/test_runner.py`.
   - The bounded process helper in `trust-ci/src/adaptive_trust_ci/workspace.py` returns the process return code to its callers; it is not a result-schema boundary and does not erase the code.

## Contract and integration impact

No API, event, JSON-schema, database, or Trust CI deployed-policy change is justified for either issue on this tree.

- Producers: `.grok-stack/adaptive_grok/verification.py` and Trust CI sandbox/runner code already produce explicit exit status.
- Consumers: Trust CI runner, API projection, signed attestation model, v1 attestation JSON schema, and PostgreSQL integration tests already consume/persist the status and exit code.
- Compatibility: changing the existing `exit_code` field would be an unnecessary breaking or semantic change. Adding another status field would duplicate an existing contract and create reconciliation risk.
- Trust boundary: repository contracts and local tests do not modify or replace the deployed Trust CI policy, GitHub App check, external holdout, or signed approvals.

## Recommendation

Disposition #36 as an external-owner/external-target issue for the absent shell gate. Preserve its regression pattern for any future shell gate, using `cmd || code=$?` (or equivalent direct status capture), and require a focused failing-command regression test if that gate is introduced. Do not add speculative shell code or a compatibility schema change here.

Use this report as the binding repository evidence for #186’s owner mapping: the current repository owns Python verification and Trust CI command-result handling, and those paths already preserve exit codes. Update/close #186 as a repository-no-change disposition, while linking #36 separately to its external owner/target. Any future implementation of the absent shell recorder must be routed as a separate change with its concrete source owner, contract impact, and regression test.

## Limitations

The GitHub issue bodies and external owner metadata were not changed or queried in this read-only wave. The recommendation is limited to current-tree and repository-history evidence; it does not claim that an external shell gate is healthy or that deployed Trust CI differs from the repository source.
