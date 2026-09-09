# Code review 4 — M1 exact Git path remediation

## Verdict: PASS

Reviewed exact commit `ee9ed6ada12f78f808a12df311a41d7888ca9d30` (tree `43f387cb85453a9e9e69665e33c03b14139b8925`, verification fingerprint `8e38706ed5ccdc2345ac40deb64df5b83440e692adabce5330825ae67cf1c64c`) against `1e3c5ce3cde0f60a65343e7df1764ced4e56c290`, the prior code-review blocker, and the active M1 package. No blocking or non-blocking code findings remain in the remediation diff or the relevant surrounding trust path.

## Prior blocker closure

- `trust-ci/src/adaptive_trust_ci/workspace.py:97-128,172-184` now reads changed paths as bytes from `git diff --name-only -z --no-renames <base> <head> --`, requires a terminating NUL, rejects empty/malformed/oversized records, strictly decodes each record as UTF-8, and preserves the decoded path without stripping or slash/backslash rewriting.
- Exact identity is propagated from the checked-out job SHAs (`workspace.py:73-81`) into `Checkout.changed_files`; `trust-ci/src/adaptive_trust_ci/policy.py:277-283`, `runner.py:215-251`, and `models.py:304-308` preserve those strings through approval-scope matching, spec selection/digest/coverage, and signed attestation serialization.
- `workspace.py:83-95` applies the same NUL-delimited byte treatment to mutation status. Error rendering uses `repr`, so embedded controls do not forge line-oriented diagnostics.
- The real-repository regression at `trust-ci/tests/test_runner.py:278-364` proves exact Unicode, LF, tab, and backslash identities, governance-scope binding, deterministic four-spec provenance, signed-attestation round-trip, nonexistent SHA rejection, and invalid UTF-8 failure.
- Independent probing confirmed `--no-renames` retains the intended delete+add identity for a rename (`('new.txt', 'old.txt')`), unusual mutation status returns the exact LF-containing path, invalid UTF-8 status fails closed, and unterminated/empty NUL records are rejected.

## Surrogate and holdout correctness

- Local, trusted-runner, and independent-holdout structural walkers reject unpaired surrogate code points in both values and keys before UTF-8 canonicalization (`.grok-stack/adaptive_grok/spec.py:417-433,740`; `trust-ci/src/adaptive_trust_ci/runner.py:58-74`; `trust-ci/holdout.example/change_spec_validate.py:51-67,227-228`). Valid JSON surrogate pairs decode to a Unicode scalar and remain accepted.
- Raw spec bytes are still hashed before parsing (`runner.py:224-250`), so a surrogate failure retains the deterministic raw provenance digest and becomes a signed zero-coverage failure without executing holdout or product commands.
- The holdout test loader now compiles source in memory. On a clean archived exact HEAD, the default Trust CI suite left the holdout file set unchanged and the bundle digest stable at `e2de03333ac37e6478433ad37486f6ee904ae8ba8054c86481c04eb7d56fcd64`, matching `trust-ci/config/policy.example.json`.

## Verification evidence

- `git diff --check 1e3c5ce..ee9ed6a`: PASS.
- Focused Trust CI path/surrogate/scope/holdout-loader tests: 5 passed.
- Additional rename, mutation-status, malformed-NUL, and invalid-UTF-8 probes: PASS.
- Clean archived exact-HEAD Trust CI suite with its default environment: 182 passed, 10 PostgreSQL integration tests skipped because `TRUST_CI_TEST_DATABASE_URL` was not configured.
- Focused local surrogate test: 1 passed.
- `python3 scripts/grok_verify.py --mode pr --no-record --json`: PASS; 223 root tests passed, current typed spec coverage is 6/6, and ruff/bandit/diff/schema checks passed.

This is local, exact-tree review evidence only; it does not substitute for the App-owned policy-epoch Trust CI check or required external approvals.
