# Verification plan — not executed

- Resolve canonical producer records; reject substituted repository/task/run/head/spec/verdict/attestation/profile.
- Verify idempotent retries and rejection of conflicting same-key writes, stale observation replay and cross-repository swaps.
- Missing verifier/observer, absent explicit human outcome, digest-only claims or invalid provenance remain unavailable/rejected.
- Base/head/policy/holdout/check/App mismatch, expiry or invalidation revoke currentness while preserving history.
- Use real disposable PostgreSQL restart and independent process reopen; interrupted transactions must expose no partially accepted record.
- Prove reader/runtime capabilities cannot originate acceptance or mutate immutable evidence.
- Run existing shadow/autonomy/delivery V1 tests unchanged, including M9's rejection of true V1 availability.

After product implementation, run `python3 scripts/grok_verify.py --mode pr` and the implementation route's independent reviews. Bind receipts to the final fingerprint. This design-only tree has no product change, so AGENTS.md's no-op rule applies: no full verifier or implementation review now.
