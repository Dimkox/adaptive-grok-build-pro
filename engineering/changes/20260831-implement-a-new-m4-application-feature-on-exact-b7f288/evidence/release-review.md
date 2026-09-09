# Final exact-head independent release review — M4 durable factory control plane

## Verdict and binding

**PASS — no Critical or Important release-readiness blocker remains.**

- Reviewer role: route-selected read-only `release_reviewer`
- Route: `b7f288f1e81e`
- Accepted M3 base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Exact reviewed evidence HEAD: `9fe779ab9f90719201acfd01160d3452658ff075`
- Exact reviewed evidence tree: `05707b35fb10ab9a29d3be35478faf4ef84789a1`
- Exact reviewed product commit: `4f75558770f2f332b32b4a47fe6afa61fcc524ec`
- Exact reviewed product tree: `5e4a46bab94f4943b6fc698472e309d4ee24fab2`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fe779ab9f90719201acfd01160d3452658ff075`
- Exact-head verifier: PASS, fingerprint `2b9b3ee786663e3adba2e2f85e51e7c752c8e57166a0d7af6e3f62a88f4b45e8`

The prior RR observability blocker and its later consistency, authority, query-bound and startup-readiness issues are closed on the exact product above. No release finding at Critical or Important severity remains. This PASS is local release-review evidence only; it is not permission to push, open/update a PR, merge, migrate, roll out, publish or deploy.

## Critical and Important review

No Critical or Important findings.

### Prior RR metrics blocker — closed

- The authenticated surface now exposes the release plan's bounded intake/queue/transition, retry/dead, live-lease/reclaim/fence-rejection, capacity, budget/accounting, kill and reconciliation values through exactly three fixed-key families. Authentication rejection is a saturating, label-free process-local count whose restart reset is explicit.
- Forward migration `012` replaces runtime-readable/generic counters with one owner-maintained 21-value singleton. Backfill and trigger installation occur atomically under write-conflicting source-table locks; runtime has no counter-table access and can invoke only the fixed snapshot reader and no-argument saturating fence increment. Forged pre-`012` values remain revoked untrusted evidence and are not imported.
- Store-derived values come from one fixed-row statement with transaction-local five-second statement and 500-millisecond lock bounds. Snapshot updates share the authoritative business transactions, so a scrape cannot combine impossible lease/capacity or state/event states and no retained-history scan grows with task history.
- A stale-fence counter failure is best effort after the authoritative decision, bounded by one-second connect / 100-millisecond lock / 250-millisecond statement limits, and cannot replace the identical `409 stale_fence`. Final 401/403 accounting occurs exactly once at the HTTP response boundary without credentials or identities.
- The exact verifier exercised the real PostgreSQL snapshot, upgrade, capability, lock-timeout, deadlock, auth and fence paths. Independent review checks also passed API/server/migration/service 27/27.

### Install, upgrade, bootstrap and startup — ready for a separately approved local rollout

- Installer ownership includes the complete `factory/contracts`, `factory/src` and SQL resource tree, locked dependencies, local examples, API/database tests and the disposable restart harness. It excludes runtime credentials, sockets and database state. Independent installer/structure checks passed 32/32.
- Installation copies source only; it neither applies migrations nor activates a service. `adaptive-factory-admin bootstrap-local` separately requires owner/runtime DSNs, applies checksum-locked migrations under the factory advisory transaction, provisions or validates a `LOGIN NOINHERIT` runtime login, grants only `factory_runtime`, and proves readiness through the runtime DSN.
- Migration `012` is a forward atomic cutover from schema `011`. The migrator's five-second statement/lock bounds make lock or scan failure roll the transaction back to `011`; the release plan requires a reviewed retry window. Non-empty schema-008 upgrade, exact active-generation quarantine, schema-012 readiness, runtime-role denials and empty replay are covered by fresh PostgreSQL evidence.
- The disposable exit runner now refuses the official image's temporary bootstrap postmaster: `postmaster.pid` must identify PID 1 and `pg_isready` must succeed before host TCP is used. The exact verifier then ran all 70 factory tests plus an actual PostgreSQL restart, fresh-store reconnect, one repair, zero-repair replay, higher fence and late-holder rejection.

### Rollback and forward recovery — adequate

- Rollout starts globally killed, verifies a logical backup by restoring it into a separately named comparison database, proves exact-schema readiness/effective-role/capacity/accounting/audit/reconciliation invariants, runs synthetic submit-to-restart evidence, and only then clears kill.
- Before first intake, only the explicitly identified disposable database may be destroyed. After durable intake, recovery is global kill, stop intake/claims and the UDS process, preserve rows/audit/logs/evidence, compare against the verified restore, and use a reviewed forward migration `013+`. Down-migration, evidence deletion and checksum/history override are prohibited.
- Any readiness, fence, capacity, budget, accounting, audit, authentication, restart or reconciliation failure remains a no-go regardless of schedule pressure.

### Documentation, deadline and M4-M9 connectivity — coherent

- `VERSION`, README H1 and current-state identity remain `2.0.12`; factory package identity is separately `0.1.0`. Root/package/roadmap/release/rollback/schedule/tasks documents consistently describe M4 as a local unaccepted source candidate and do not claim push, external check, merge, rollout or deployment.
- The hard deadline is `2026-09-08 00:00 UTC+3`; normal work freezes four hours earlier for exact-state gates. The M4 calendar window ends `2026-09-02 18:00 UTC+3`; this review occurred before it, and every document states that time cannot waive an exit gate.
- M5 branch `milestone/m5-isolated-execution-provisional-m4` / route `37b05f579320` and M6 branch `milestone/m6-semantic-validation-provisional-m4` / route `82aac86a3bf9` remain provisional descendants of M4 anchor `94fc5ad`. They must restack and pass acceptance in order M4 → M5 → M6; M5 retains the suitable rootless-isolation-host blocker.
- The roadmap-only M4→M9 table names each immutable digest/SHA handoff, predecessor and exact-state gate, invalidation trigger, rollback/demotion path and forbidden authority. M7-M9 remain explicitly unimplemented roadmap contracts; M8 is capped at L2 and production promotion remains human-owned.
- README's K22 inventory contains exactly 22 named nodes and all `C(22,2)=231` unique `---` edges, with no missing or extra pair. It is correctly labeled decorative inventory, not architecture, completion or merge evidence.

### External Trust CI boundary — preserved

- M4 is local UDS/PostgreSQL control only. It has no provider execution, repository command, Git/GitHub, systemd, deployment, production or Trust CI mutation path, and no GitHub Actions were added.
- Local verification and review reports are preflight evidence, never merge authority. Even with this PASS, delivery remains **NO-GO** until the final evidence tree is committed/frozen, all route-selected review receipts bind it, an explicitly authorized PR exists, the App-owned policy-epoch `adaptive-trust-ci/verified@<policy-sha12>` check succeeds on that exact PR head, and every independently signed required scope is present. A new commit, base, policy or holdout invalidates the external decision.

## Exact evidence inspected

The fingerprint-bound verifier receipt created at `2026-09-02T00:13:05Z` for exact HEAD `9fe779ab9f90719201acfd01160d3452658ff075` and fingerprint `2b9b3ee786663e3adba2e2f85e51e7c752c8e57166a0d7af6e3f62a88f4b45e8` reports:

```text
14/14 verifier checks: PASS
root python-unittest: 488 tests in 496.646s — OK
factory-unit: 26 tests — OK
factory-postgres-exit: 70 tests in 41.360s — OK
actual restart: one repair; replay no-op; higher fence; late holder rejected — PASS
Bandit / Ruff / secret scan / SQL safety / architecture / governance — PASS
source stability — PASS
```

Independent checks during this review:

- API/server/migration/service: 27/27 PASS.
- Installer and root structure/K22: 32/32 PASS.
- Full-range `git diff --check`: PASS with no output.
- Exact HEAD/tree and product commit/tree: matched the bindings above.

Before this report write the only worktree changes were concurrent route-selected `code-review.md`, `security-review.md` and `test-review.md` writes; no product file differed from the exact committed product. This reviewer changed only `release-review.md`. The report write changes the worktree/evidence fingerprint, so it must be committed and receive fresh fingerprint-bound local receipts before any local-completion claim.
