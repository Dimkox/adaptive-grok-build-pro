# Issue #155 continuation — 2026-09-21

Continue branch `fix/issue-155-repair-binding-rejections` from implementation commit
`6b13806d454cada0c63520129baf09056db46408`, based on
`90078959ff816068af374ad42f4bb80fdbaec866`. The existing approved route is
`c4e47ea3ced7`; the implementation owner is `frontend_implementer` as selected by that
route. The misleading role name is tracked separately in issue #156.

## Recovered state

- GitHub PR #151 merged on 2026-09-19 at 20:27:56 UTC as `90078959ff816068af374ad42f4bb80fdbaec866`.
- The #155 implementation is local and has no pull request at this observation.
- The last full verifier failed: a committed trailing blank line, unowned `.qwen/tmp`
  helpers, and `python-unittest` exit 1. Its summary preserved no test traceback, and
  failing architecture/governance prevented creation of a verification receipt.
- On resumption the helpers are already outside the checkout and the EOF fix is staged.
  Neither observation proves the remaining checks pass.
- Historical four-pass PostgreSQL streaks cover the earlier trees described in
  `evidence/postgres-evidence.md`; the final test-file refinement postdates them.
  Do not label those streaks as four passes on the final product contents.

## Continuation procedure

1. Recover the root-test diagnostic using the verifier's exact command, retaining full
   stdout/stderr outside the source checkout. Make a minimal regression-proven repair
   only if the failure persists.
2. Freeze the product and test contents. Record a content manifest, and satisfy AC-005
   with four consecutive disposable PostgreSQL tier passes on those contents, retaining
   each command, exit status, duration and host load. Documentation-only changes do not
   establish a new product test result; record full-tree and product identities separately.
3. Run `python3 scripts/grok_verify.py --mode pr --json`, retain its detailed output,
   and inspect every failure instead of inferring a cause from an exit status.
4. Obtain independent `code_review`, `test_review`, `security_review` and `data_review`
   reports for the final diff. Record receipts only after reports and delivery documents
   have their final contents; recheck any subsequent product change.
5. Commit the local handoff and prepare a concrete PR. Branch push/PR creation require
   the named external operation's authority; merge additionally requires fresh
   App-owned exact-head Trust CI and any deployed-policy approval scopes.

The migration remains additive (`021`); resources `001`–`020`, contracts, deployed
runtime and published artifacts remain outside this continuation's edits. Follow-up
issues #162, #163, #166 and the broader queue are not part of this repair.

## Independent review correction

The first September 21 full verifier and four-pass product streak passed; their raw
results are retained in `evidence/continuation-20260921/`. Independent review then found
a legacy NULL refusal still chained the parser's `invalid_object` exception despite its
correct outer message, and a source-revert recovery plan incompatible with applied
migration `021`. The writer added a red/green regression for the exception chain and moved
NULL classification before parsing; recovery now preserves the migration prefix and
requires a reviewed forward correction. The first streak is historical after this
production-code correction; final verification and four-pass evidence must cover the
corrected product bytes before delivery.

The correction is frozen at product digest `7bc1176912c7468329d825a1b5f1ef74b0025cc862505f04003050bca1aeac25`. Its focused red/green logs and report are in `evidence/null-cause-review-fix/`; SQL resources are unchanged. The corrected full verifier passed, and four new PostgreSQL attempts passed on these exact product bytes. The independently checked raw results are in [the final archive](evidence/final-20260921/README.md).

## Reviewed local handoff

All four selected independent reviews now pass: [code](evidence/continuation-code-review.md),
[test/evidence](evidence/continuation-test-review.md), [security](evidence/continuation-security-review.md)
and [data](evidence/continuation-data-review.md). The reports retain the initial failures
and their resolutions. The final test review independently checked the four new logs,
manifest and hashes; review completion does not substitute for the current local receipts.

Commit the frozen handoff, run the full verifier on that clean HEAD, then record the
four review receipts with the report paths above and require zero `grok_status` gaps.
The archive's d659558 full-verifier checkpoint predates the final documentation commit;
a fresh clone must not reuse it as a current whole-tree receipt. No product change is
needed for closure, and no repeat analysis/review wave is needed for this paperwork.

The [PR description](pull-request.md) is prepared. Branch push and PR creation remain
pending their exact operational delegation; merge still requires the App-owned check
on the resulting current head and any separately required signed approval scopes.
Main was re-observed at `90078959ff816068af374ad42f4bb80fdbaec866` on September 21;
no PR exists for this branch at the local handoff observation.

The user's request to advance more factory work also produced a [concrete next-pilot
investigation and unposted issue draft](next-pilot/README.md). Its missing Russian-page
audit coverage was independently reproduced against the current target. Route that
successor separately; neither this investigation nor the old closed PR is a real
provider run, maintainer acceptance, or M8 qualification.
