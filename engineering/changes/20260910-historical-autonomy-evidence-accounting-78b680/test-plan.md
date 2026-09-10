# Verification plan

Baseline: python3 -m unittest tests.test_structure tests.test_repo_router passed 45 tests before product changes. The baseline log is private scratch, not an authoritative receipt.

Focused tests must prove behavior: duplicate/conflicting observations, partial pagination, boolean-as-integer rejection, unknown interventions, missing acceptance, changed repository/profile separation, and 30 synthetic records granting no authority. Exercise CLI only with synthetic temporary input; no provider/GitHub request.

Run the CLI on private source observations and reconcile counts independently. Preserve unknown task qualification and intervention measures. Check public diff for private identifiers.

Run python3 scripts/grok_verify.py --mode pr for base/contracts/AI, then code/test/security reviewers on the same final tree. Preserve environmental failures honestly and resolve within authorized scope.

## Preflight repair verification

The first full preflight passed 624 root tests, coverage (80% overall, 95% history module), pilot/unit, lint, architecture, governance, secret and contract checks. The disposable factory suite ran 546 tests with three landing composition failures and one existing skip. All factory files were identical to the base before repair; the failures were separately reproduced as blob_expired. After the two fixture-clock injections, rerun the affected tests and the full disposable factory suite. Review the corrected candidate, then bind the final full preflight and review receipts to the committed candidate. Preserve the initial failed result as history.
