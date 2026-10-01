# Test review — PASS with aggregate gate retained

Reviewed exact head `35b90f296befff5ba2a2ca21951dde172ffd4508` and fingerprint `c5495b8d3529b94e88e8ca0ff2423a00cf9269904ab24b753ac1d6945bbf8e42`.

The exact-head verifier executed the full profile. Root tests, coverage, static checks, contracts and SQL checks passed. The disposable PostgreSQL suite passed `1005/1005` tests with two declared capability skips and completed three real PostgreSQL restarts. Migration036 tests execute pinned historical SQL bytes, verify SHA-256 identities, fresh/pre-035/legacy-035/current-035 upgrades, ACL and behavior before/after, rollback, concurrency, drift rejection and second-apply no-op.

External/provider/installed-host cases remain `NOT_RUN`; U4/macOS is excluded. Architecture fails only the aggregate code-budget view, and governance depends on that result. Therefore the tests support the source and proposed split, but do not make this monolithic preview merge-ready.
