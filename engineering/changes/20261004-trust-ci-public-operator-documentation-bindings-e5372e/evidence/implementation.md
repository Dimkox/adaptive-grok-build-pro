# Test-only public operator documentation compatibility

Writer: integration_implementer. Baseline HEAD: `97a7581238022356b2de8d193a9bd8363fc92dc3`. Exact public-document source: `52e1163da49d80b1ee40210c48e565f2fa3f13e7` (PR #239).

The only executable change is `trust-ci/tests/test_m0_invariants.py`. Positive historical hostname, inbound webhook and App-ID literals are replaced by unique role-bound extraction, syntax validation and cross-document equality. Named public placeholders are alternatives only for their exact roles. Historical/public documentation consistency supplies no live identity or merge authority; App ownership, exact SHA, epoch, protected main, API/worker separation and no-Actions assertions remain unchanged.

Writer-observed red/green: original module 14 tests passed; two new fixture failures preceded implementation; repaired module 20 tests passed. Final module SHA256: `687dd2ae3abb23fcece7867a3723ec66fe7b15ec5058fa04314b40d5c659354f`.

Writer command: `PYTHONPATH=trust-ci/src:trust-ci/tests PYTHONDONTWRITEBYTECODE=1 taskset -c 0-27 python3 -m unittest discover -s trust-ci/tests`. Original documents: 250 discovered, 240 passed, 10 skipped, 6.812 seconds. Exact PR239 public documents in private scratch: same counts, 6.706 seconds. The ten skips require `TRUST_CI_TEST_DATABASE_URL` and are not passes. Public module separately passed 20 tests. Ruff and Git whitespace checks passed.

Scratch is project-contained `.review-scratch/trust-ci-doc-bindings-implementation-eKqNI0`, private mode 0700. It reproduces base plus candidate changes; public spec, plan, activation report, README, decisions and mistakes are verbatim from the exact public source commit. No deployed policy, holdout, human keys, production database or protection was read or changed.

The bounded scope invocation is explicitly cancelled, not completed verification. Full PR verification, independent review and the external exact-head App check remain pending. Branch transport may precede them only as UNVERIFIED transport.
