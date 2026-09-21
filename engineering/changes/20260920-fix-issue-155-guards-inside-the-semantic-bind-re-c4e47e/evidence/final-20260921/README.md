# Corrected product verification — 2026-09-21

Product SHA-256: `7bc1176912c7468329d825a1b5f1ef74b0025cc862505f04003050bca1aeac25`. All four sequential disposable PostgreSQL attempts
passed with that identical content-sensitive digest before and after each attempt.
The 3,283-file manifest includes source, tests, contracts, configuration and all other
tracked/nonignored files except the explicit bootstrap/memory documents, active
change package and local runtime evidence. It is not a whole-tree receipt. Driver
source is retained as inert text; its negative control is in the historical
`../continuation-20260921/manifest-control.json` record.

| Attempt | Wall seconds | Exit | Started UTC |
|---|---:|---:|---|
| 1 | 358.330 | 0 | 2026-09-21T05:10:03.197945+00:00 |
| 2 | 375.076 | 0 | 2026-09-21T05:16:02.022929+00:00 |
| 3 | 378.336 | 0 | 2026-09-21T05:22:17.629325+00:00 |
| 4 | 366.498 | 0 | 2026-09-21T05:28:36.457871+00:00 |

Each run reports 779 tests and two conditional skips, followed by actual PostgreSQL
restart/reconciliation and effective runtime/attestor-role checks. This corrects
the evidence boundary after the NULL-before-parser source repair; prior streaks
are preserved separately and do not establish these corrected product results.

The two conditional skips are the dedicated empty-cluster role-creation scenario
and the absent-PDF-parser scenario (the pinned parser is installed). The ordinary
disposable cluster does not exercise those optional environments. No production
authority window, timeout, skip condition or runner was relaxed.

`verify-initial.json` is the complete corrected-product full-verifier checkpoint:
PASS on `d6595584649827baff78c2be46f978473d4b0465`, whole-tree fingerprint
`b77fcdb933fc0b74524929a3c25e49de3f3df09c121d2a3a7029ea957785fa4c`, with source stability confirmed.
It used `GROK_TEST_WORKERS=8 python3 -u scripts/grok_verify.py --mode pr --json`:
785 root tests and 1,098 subtests passed, measured coverage was 80% against the
unchanged 74% requirement, 56 selected factory unit tests passed, and the mandatory
PostgreSQL tier also passed. The pilot suite has its existing pinned-local-Codex
sandbox case skipped; workflow artifacts are not configured. Read the report for
the exact command, output, profiles and other checks.

An earlier verifier was deliberately cancelled to repair whitespace in raw evidence
packaging; `verification-cancelled.json` records that exit 143 and cleanup. It is
neither a passing run nor an observed test failure. The next complete verifier above
passed after the lossless evidence-wrapper correction.

This checkpoint predates the final review reports and handoff commit. Final local
completion additionally requires fresh full verification and all four independent
review receipts on the clean delivery HEAD. Those machine-local receipts are kept
outside Git; use `python3 scripts/grok_status.py` to check their current binding.
Neither this archive nor local receipts authorize a push, merge or deployment.

`index.json` binds each archived byte sequence. Files ending in `.log.json` are
lossless base64 envelopes only when raw diagnostic whitespace would fail the
repository whitespace gate; verify both wrapper and decoded hashes before reading
the original bytes. Unwrapped files are verbatim. No log output is trimmed.
