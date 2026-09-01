# Final exact-head independent release review — M4 durable factory control plane

## Verdict and binding

**FAIL — one Important release-readiness blocker remains.**

- Reviewer role: route-selected read-only `release_reviewer`
- Route: `b7f288f1e81e`
- Accepted M3 base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Exact reviewed product HEAD: `daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Exact reviewed Git tree: `9c93b2ca4fea4f71ab70bbf71bd62ca8df936ad8`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Exact-head verifier receipt: PASS, fingerprint `ad41a13355b097f4be0a3d6c3754b9cc4de8178824e801ac264fad81c852e794`

I inspected the actual cumulative diff, active route and package, install inventory, migrations/bootstrap/readiness, schema-008 upgrade and replay evidence, release/rollback/schedule, README/version/stack graph, runtime metrics/auth path, implementation ledger/report and exact-head verifier receipt. The prior schema-008 forward-recovery blockers are closed, but the release plan's mandatory observability set is not implemented or evidenced. That mismatch prevents a go decision for a durable scheduler/control plane.

## Important finding

### RR-003 — the documented go/no-go observability set cannot be observed

The release plan requires bounded observation of “intake, queue, transitions, leases, capacity, budget, retries/dead, kills, reconciliation and auth failures” and makes any missing go gate a no-go (`release.md:5-7`). The shipped authenticated `/metrics` endpoint returns only:

- accepted and superseded task counts;
- expired-run/reclaimed count;
- current active capacity;
- accounting-blocked task count;
- active kill count;
- cumulative repaired count.

That implementation has no queue depth/state counts, transition counts, current/live lease count, reserved/observed budget signal, retry/dead counts, fence-rejection count despite the family name, or authentication-failure count (`factory/src/adaptive_factory/store.py:112-132`). The endpoint simply authenticates and returns those store values (`factory/src/adaptive_factory/api.py:200-203`). Authentication failures are not persisted or counted, and the shipped server explicitly disables access logging (`factory/src/adaptive_factory/server.py:96-102`), so the missing auth-failure signal cannot be recovered from the documented runtime surface.

The tests prove that the three returned families are authenticated and redacted, but no test asserts the release-plan signal inventory or exercises signal changes for queue, transition, live lease, budget, retry/dead, fence rejection or failed authentication. The implementation report and README therefore overstate rollout observability when they claim the release plan matches the final tree.

Impact: after clearing the initial kill, an operator cannot distinguish a stalled queue, retry/dead escalation, accumulating live leases, budget pressure, repeated fence rejection or authentication attack from healthy operation using the supported surface. Synthetic happy-path and restart smoke tests do not provide ongoing incident visibility. This is an Important release blocker for AC-013 and for the package's own go/no-go contract, not a request for a full dashboard product.

Required repair: either implement the exact bounded, low-cardinality inventory named by the release plan (including a safe authentication-failure signal) or narrow the approved release contract with an explicit operator-visible alternative that actually exists. Add behavioral tests that drive each promised signal, assert exact bounded/redacted output with no task IDs/bodies/reasoning/secrets, and prove unauthorized metrics access increments or emits the documented safe signal without exposing credentials. Re-run the exact-tree verifier and all route-selected reviews on the final evidence tree.

## Release controls assessed as sound

### Install, upgrade and bootstrap

- The installer payload includes package source, OpenAPI, locked dependencies, migrations 001-011, local placeholders and the complete disposable test/restart harness; it excludes runtime credentials, sockets and database state. Installer evidence is 17/17.
- Source installation does not apply migrations or activate a service. The separately invoked admin bootstrap uses distinct owner/runtime DSNs, checksum planning and a factory advisory lock, provisions or validates a `LOGIN NOINHERIT` runtime role, grants only `factory_runtime`, then checks readiness through the runtime DSN.
- Real PostgreSQL evidence builds a non-empty schema-008 database, atomically applies exactly 009-011, proves schema 11 readiness and empty replay, and separately proves the shipped effective-role bootstrap.

### Schema-008 recovery and checksum caveat

- The previous release/data findings for blocked-zero retry and unsafe `ready_for_human` accounting are closed by migration 011. The final same-identity fixture proves generation 1 becomes evidence-preserving `superseded/accounting_blocked`, generation 2 stays queued and is the exact claim target, reservation aggregates remain intact, readiness fails if the quarantine marker is removed, and migration replay is empty.
- Migrations 001-010 remain immutable. Migration 011 was corrected in place only before PR delivery and only after disposable-local use. The README, factory README and ledger explicitly require any database holding the earlier 011 checksum to be discarded and recreated; they prohibit checksum override/history rewrite/shared repair. The reproduced old-checksum rejection caused the exact disposable container to be discarded and rebuilt.

### Rollback and forward recovery

- Rollout starts killed and requires verified backup restoration into a separate comparison database before activation. Failure triggers global kill, stops intake/claims and the socket process, and preserves rows, audit, logs and evidence.
- Before first intake only a specifically identified disposable database may be destroyed. After durable intake there is no down-migration or audit deletion: recovery is comparison restore or reviewed forward migration 012+, with readiness, role-denial, capacity/accounting, audit-chain and two-pass reconciliation checks.

### Documentation, identity, graph and schedule

- `VERSION`, README H1 and current-state identity all remain `2.0.12`; factory service identity is separately `0.1.0`, and Trust CI remains separately identified. README truthfully labels M4 a local source candidate rather than merged/deployed behavior.
- The stack graph contains 17 core nodes and exactly all 136 unique pairwise `---` edges, including Factory-to-every-other-node; no pair is missing.
- The schedule preserves the superseding `2026-09-08 00:00 UTC+3` deadline, reserves the final four hours for exact-state gates and explicitly says schedule pressure cannot waive any gate. At review time the M4 window had not expired.

### External trust boundary

- M4 remains UDS/local and has no provider execution, repository/Git/GitHub/systemd/deploy/production or Trust CI mutation path. No GitHub Actions were introduced.
- Local verifier/reviews are preflight only. Even after RR-003 is repaired, merge/rollout remains **NO-GO** until the evidence tree is frozen, every required review/receipt binds that tree, a separately authorized PR exists, the App-owned policy-epoch `adaptive-trust-ci/verified@<policy-sha12>` check passes on its exact head, and all required independently signed scopes are present. This report authorizes none of those operations.

## Exact evidence

The inspected verifier receipt was created at `2026-09-01T22:11:35Z` for exact HEAD `daa3930cb84ba6547171583e41bcf0dee2ab1314` and fingerprint `ad41a13355b097f4be0a3d6c3754b9cc4de8178824e801ac264fad81c852e794`:

```text
14/14 verifier checks: PASS
root python-unittest: 488 tests in 492.642s — OK
factory-unit: 24 tests in 0.012s — OK
factory-postgres-exit: 63 tests in 51.339s — OK
actual restart: one repair; replay no-op; higher fence; late holder rejected — PASS
source-stability: PASS
```

The ledger also records exact active-generation GREEN at 1/1, upgrade plus bootstrap at 2/2, installer 17/17, fresh PostgreSQL 63/63 plus restart and root 488/488 on product commit `d15302f`, followed by the exact final-tree verifier above. `git diff --check` over the full base-to-head range produced no output.

Before this report write, `git rev-parse HEAD` and `HEAD^{tree}` matched the SHA/tree above. Concurrent final security/test report rewrites were already present in the worktree and were not modified by this reviewer. This review changed only `release-review.md`; it changed the evidence-tree fingerprint, so the existing verifier receipt is not a final worktree receipt and must not be recorded as local closure.
