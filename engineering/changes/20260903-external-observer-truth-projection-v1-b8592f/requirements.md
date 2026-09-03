# Requirements — External Observer truth projection v1

## Acceptance criteria

- **EO-001 — Closed subject/config.** Exactly one operator-configured repository, default branch, numbered candidate PR, expected Check Run name and GitHub App ID; repository ships only a closed schema and placeholder example, with no committed mutable “current PR”, credential or arbitrary URL.
- **EO-002 — Typed claims.** `PROJECT_STATE.json`, a closed evidence manifest and local receipts are normalized as claims with SHA/digest/freshness; malformed, contradictory or unstructured claims never become observed facts. README/START_HERE are links/run instructions, not parsed authority, and PROJECT_STATE identifies itself as a historical claim/snapshot.
- **EO-003 — Canonical projection.** Same normalized inputs and observation time produce byte-identical closed `PUBLIC_STATUS.v1` JSON/digest and deterministic human rendering with independent implemented, reviewed, check-verified, delivered, released and attestation states.
- **EO-004 — Coherent freshness.** Opening/closing main and exact configured PR reads must match; every positive claim uses exact SHA/fingerprint equality and a configured freshness ceiling. Movement, mismatch or partial data never produces fresh consistency.
- **EO-005 — Check identity.** A successful check requires exact PR head, exact configured Check Run name, exact configured App ID and completed/success; missing, duplicate, conflicting, queued or foreign-app records fail closed.
- **EO-006 — Release proof.** Newest qualifying stable release tag resolves through a bounded direct/annotated chain. `release_behind` requires a structurally consistent compare from release commit to main; inequality alone, divergence or rewind proves nothing.
- **EO-007 — Delivery proof.** Only the configured exact PR can establish current delivery; merged status plus merge-commit ancestry/equality to current main is required. Optional lists are discovery-only partial data and historical M0-M9 remain evidence claims unless individually validated.
- **EO-008 — Bounded read-only transport.** Fixed HTTPS `api.github.com` GET paths, no auth/cookies/proxy/redirect/retry/write/git, strict UTF-8/JSON/types, bounded body/cardinality/tag depth, 10-second request and 90-second aggregate deadlines.
- **EO-009 — Fail-closed persistence.** First failure is unavailable/unknown; later failure is stale with last valid normalized snapshot. One lock, safe regular/no-follow paths, canonical atomic writes, corruption rejection, contention without I/O and fixed redacted errors are required.
- **EO-010 — Authority isolation.** A separate operator-owned nonprivileged observer service/domain has only local claim/runtime reads and allowlisted public GitHub reads; it is not part of the controller and has no Factory/M5, Trust CI, human approval, signing, release, production or external-write authority. Check `details_url` is never followed; `REFERENCED_NOT_VERIFIED` and `ATTESTATION_UNOBSERVABLE` remain explicit without a separately reviewed redacted signed public endpoint.

Canonical change-spec v1 requires `AC-*` IDs, so `AC-001..AC-010` map positionally and verbatim to `EO-001..EO-010`; EO IDs remain the feature-facing stable names.

## Invariants and edge cases

Positive facts bind exact lowercase 40-hex SHA and canonical digest; no stage implies another; current observation never rewrites claim sources. Missing release, closed/draft PR, base mismatch, moving main/head, stale receipt, malformed compare, tag cycle, duplicate check, rate limit, timeout, redirect, oversize or corrupt cache yields bounded false/unknown/stale output.

No network appears in tests. No version/package bump, schema/data migration or backfill is included.
