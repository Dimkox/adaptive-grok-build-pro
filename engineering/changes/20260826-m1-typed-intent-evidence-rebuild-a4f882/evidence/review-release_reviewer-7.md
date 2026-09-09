# Release review 7 — M1 typed intent and evidence

## Verdict

**PASS for local source readiness** at exact candidate HEAD `98649e4e1e6a971fb802bc934eb5680de529e18a` (Git tree `a78118c8e420d152add5779046ee257ba02e8203`).

No P0, P1, or P2 release-readiness finding remains. Code review 7, test review 7, and security review 7 all pass the same source commit. The current README, roadmap, and durable package describe the candidate conservatively and do not claim that it is merged, externally attested, deployed, or database-integration-proven.

This PASS authorizes only recording local release-review evidence. It does not authorize a push, PR update, merge, tag, GitHub Release, deployed Trust CI change, or production operation.

## Final local evidence

- `review-code_reviewer-7.md`: **PASS**. Atomic constructor allocation, rollback without exception masking, idempotent cleanup, and the surrounding exact-path/bounded-worker implementation were reviewed on `98649e4e` with no open finding.
- `review-test_reviewer-7.md`: **PASS**. Root suite 223/223; Trust CI suite 200 total with 190 passed and 10 explicitly conditional PostgreSQL skips; focused workspace lifecycle 15/15; two consecutive default Trust CI runs preserved the exact two-file holdout bundle and digest `e2de03333ac37e6478433ad37486f6ee904ae8ba8054c86481c04eb7d56fcd64`; compileall and committed-range whitespace checks passed.
- `review-security_reviewer-7.md`: **PASS**. All four constructor failure boundaries clean their allocated paths and preserve the original exception. Trusted Git configuration isolation, bounded streaming, process-group cleanup, exact protected-path approvals, strict parser/holdout behavior, raw provenance, signature compatibility, and no-follow reads remain passing.
- Independent release preflight run after the three wave-7 reports: `python3 scripts/grok_verify.py --mode pr --no-record --json` exited 0 with `status=pass`, 223 root tests, gate-valid active spec, and 6/6 declaration-mapped acceptance criteria. Its pre-release-report tree fingerprint was `5a2275b9d819942f9cbf29195c7fac9ebe7c40d44e20701902126becc4725873`.
- `git diff --check 0a4dd0a..98649e4` passed. No root packaging marker, GitHub Actions workflow, migration, destructive data operation, or deployment definition was added by M1.

## Readiness truth

- `README.md:10` calls this a locally green remediation candidate and still requires fresh route reviews before `source-ready`. That wording is conservative: the reports now exist outside the reviewed commit, while fingerprint-bound closure has not yet been recorded.
- `DARK_FACTORY_ROADMAP.md:330-343` distinguishes checked source/regression work from release readiness and explicitly leaves deployed Trust CI/holdout proof to a separately authorized rollout.
- `requirements.md` leaves AC-006 unchecked, `tasks.md` leaves Task 6 and the external PR step unchecked, and `state.json` remains `verifying`. Those are truthful pre-closure states, not defects in this release candidate.
- The active red-risk v2 spec is gate-valid, lists forbidden outcomes and `governance` scope, maps all six criteria, and explicitly forbids representing source readiness as deployment.
- `release.md` keeps dual-read legacy compatibility and canonical single-write as the staged migration boundary. `rollback.md` uses a non-destructive PR revert and correctly states that no schema migration or destructive data write is included.

## PostgreSQL and deployed evidence

Ten PostgreSQL integration tests are present but were not executed because `TRUST_CI_TEST_DATABASE_URL` is not configured. Every fresh reviewer reports those skips explicitly; no database-backed pass is claimed. This is not a blocker for local source readiness because M1 does not migrate or deploy PostgreSQL and the trusted service rollout is out of scope.

Before any later worker/attestation rollout, an operator must run the legacy and current signed-payload PostgreSQL round trips against an authorized disposable test database and retain that evidence. The rollout must also bind immutable worker/holdout/policy artifacts, exercise rollback/restart behavior, and prove the deployed reader/emitter on an exact SHA. None of that is inferred from this local PASS.

## Remaining gates after this review

1. Store this report with the three wave-7 reports, record fresh verification plus `code_review`, `test_review`, `security_review`, and `release_review` receipts against one current repository/spec fingerprint, and require `python3 scripts/grok_status.py` to report zero gaps before transitioning the package to `ready`. Any subsequent repository change makes those receipts stale and requires proportionate re-verification/re-review.
2. Do not push or update PR #8 until the user explicitly delegates that external operation.
3. On the exact pushed PR head, require the App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run and the human-signed `governance` scope required by deployed policy. Local reports and receipts cannot create either authority.
4. Merge remains human-owned. Deployment of the new holdout, worker reader, policy epoch, image, or attestation emitter remains a separate operator-controlled change with its own evidence and authorization.

## Conclusion

M1 is suitable for a passing local release-review receipt at `98649e4e1e6a971fb802bc934eb5680de529e18a`. The repository can complete its local evidence/state closure without performing any unauthorized external action. External PR, merge, PostgreSQL, and deployment gates remain explicitly open.
