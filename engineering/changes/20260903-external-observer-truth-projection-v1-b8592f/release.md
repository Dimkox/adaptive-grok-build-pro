# Release plan — External Observer truth projection v1

## Rollout boundary

Phase 1 delivers only reviewed documentation on an isolated branch. Future implementation is source-first: fake tests, manual local CLI, optional inert service source, then a separately authorized operator installation. No automatic install/enable, external write, PR/push/merge/release, Factory/M5 activation, Trust CI or production action is included.

V1 anonymous GitHub reads are best-effort and not enterprise-reliable: the shared-IP quota is currently exhausted at 60/60, so rate limiting must emit `rate_limited` plus unavailable/stale truth. A future authenticated adapter is Phase 2+ and requires separate security review: only a separately provisioned Observer read-only credential/App with metadata/contents/pull_requests/checks read scopes, server-mounted outside the repository. It must never reuse the Trust CI checks-write token or gain write scopes.

## Signals

Fixed-cardinality signals: runs by `fresh_consistent|mismatch|stale|unavailable`, endpoint failure code, snapshot age, claim mismatch count, check identity state, release relation, lock contention, state corruption and attestation visibility. No repository/PR/SHA/token/error-text label and no raw response logging.

## Go/no-go

Go requires EO-001..EO-010 tests, closed contract parity, deterministic output, fake-only transport transcript, no tracked mutation, architecture isolation, root verification, exact-fingerprint code/test/security reviews and separately authorized rollout. No-go for any false-positive truth, unresolved security finding, missing gate, stale receipt, absent external Trust CI on a future PR SHA or attempted credential/remote mutation. Observer source-complete, locally reviewed, externally accepted and operationally activated are separate states.

Hard whole-program deadline: `2026-09-04 23:59 UTC+3`. Observer must close before accepted M5; accepted M4 remains M5's dependency. External quota, Trust CI, isolation, human cohort and production authority are blockers, not schedule waivers.
