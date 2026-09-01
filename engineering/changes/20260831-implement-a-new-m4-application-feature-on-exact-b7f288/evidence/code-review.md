# Code review — M4 durable factory control plane

## Verdict

**FAIL**

No Critical findings were found. Three Important findings remain in the exact reviewed product tree, so AC-014 and local code-review completion are not satisfied.

## Review binding

- Route: `b7f288f1e81e`
- Product base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed HEAD: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Merge base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1` (exact route base)
- Reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Latest verifier range inspected separately: `8e6504168462bbabad359fec3d23838c87f5ba22..cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Verification evidence inspected: receipt created `2026-09-01T14:59:00+00:00`, fingerprint `13363f4e7d5b058ae864ca54c165bb671e6355c2d7082f60c023a01154347df3`, with 43 disposable-PostgreSQL/API tests and actual restart/reconciliation passing. Subsequent evidence-file changes make that receipt stale for the current worktree; they do not alter the reviewed product HEAD.

## Findings

### Important — CR-001: changed frozen producer authority is returned as a duplicate instead of superseding the active task

`TaskIntakeV1.intent_digest` binds the complete normalized intake, including producer exact heads/evidence, M0 authority, route/change IDs, acceptance IDs and limits (`factory/src/adaptive_factory/contracts.py:249-267`). Its separate `idempotency_key`, however, omits those fields and binds only a subset of source/base and M1/M2/M3/policy digests (`factory/src/adaptive_factory/contracts.py:268-281`). Intake then looks up that subset key and immediately returns the old task without comparing `intent_digest` (`factory/src/adaptive_factory/store.py:246-251`).

This violates AC-002 and the architecture statement that only exact duplicates are returned while changed frozen authority creates a new generation. A valid second intake with matching repository/source/digests but different, mutually consistent M2/M3/M0 `exact_head_sha` values produces the same idempotency key and a different intent digest; the reviewer reproduced `same_key=True` and `same_intent=False`. The store therefore preserves neither the new accepted authority nor the required supersession event/audit. The existing PostgreSQL test changes only `source_digest`, which is included in the subset key, so it does not cover this case (`factory/tests/test_postgres_integration.py:66-77`).

Required repair: define duplicate identity from the complete frozen intent (or compare the located row's `intent_digest` before returning), then add real PostgreSQL regressions for changed producer exact head/evidence, M0 authority and another accepted frozen field such as limits. Exact replay must return the same task; any changed frozen intent for the same source identity must atomically supersede eligible nonterminal work.

### Important — CR-002: repository-limited reconcile credentials can mutate every repository

`FactoryService.reconcile` checks only the `factory:reconcile` scope and `operator` kind; it never requires wildcard repository authority or passes an authorized repository filter (`factory/src/adaptive_factory/service.py:148-152`). `PostgresFactoryStore.reconcile` then selects expired runs globally and releases/retries/dead-letters or repairs them regardless of repository (`factory/src/adaptive_factory/store.py:914-962`).

Consequently an actor configured with `repositories={"repo/a"}` and the reconcile scope can change tasks and capacity owned by `repo/b`. This breaks the scoped API/repository-isolation contract and is inconsistent with the explicit wildcard requirement already used for global kill (`factory/src/adaptive_factory/service.py:141-145`). Metrics has the same unfiltered cross-repository shape (`factory/src/adaptive_factory/service.py:30-34`, `factory/src/adaptive_factory/store.py:87-107`), although the mutation path is the release blocker.

Required repair: either require `"*"` for global reconcile/metrics, or make reconcile repository-scoped end to end and constrain every candidate query and cursor to the authorized repository set. Add a service/API and disposable-PostgreSQL regression proving a repository-limited operator cannot observe or repair another repository.

### Important — CR-003: malformed closed API commands escape as internal errors instead of bounded client failures

The API declares raw `dict` bodies and converts untrusted members with constructors or Python coercions outside a validation/error boundary. Examples include `RunRole(payload["role"])` on claim (`factory/src/adaptive_factory/api.py:213-236`), `FailureClass(outcome)` through proposal/release (`factory/src/adaptive_factory/service.py:91-95`), and `int(payload.get("limit", 100))` on reconcile (`factory/src/adaptive_factory/api.py:345-365`). Invalid enum/type values raise uncaught `ValueError`/`TypeError`; only contract, authorization, fence, budget and store errors have handlers (`factory/src/adaptive_factory/api.py:88-106`). Cancel also stringifies arbitrary JSON as a reason and has no reason bound before database event/audit insertion (`factory/src/adaptive_factory/api.py:191-211`, `factory/src/adaptive_factory/store.py:965-983`).

These are ordinary untrusted client inputs to a closed versioned API, but they can produce `500` responses and transaction-level database exceptions instead of deterministic `400/422` errors. That is incompatible with AC-010's closed, bounded API semantics and obscures operational failures.

Required repair: parse each command into a closed typed request contract with explicit enum, scalar, UUID/digest, collection and byte-length bounds; translate all validation failures to the documented bounded `4xx` envelope. Add API tests for invalid role/outcome, non-integer reconcile limit, wrong claim collection/scalar types, malformed cursor/UUID and oversized/non-string reasons.

## Reviewed behavior without blocking findings

- The schema and store use PostgreSQL transactions, database time, `FOR UPDATE SKIP LOCKED`, monotonically increasing per-task fences and live allocation validation. Release/cancel/supersede/reconcile paths close runs, attempts and database-owned capacity through fixed-search-path security-definer functions.
- Migrations are contiguous through `008`, checksum checked, factory-scoped, forward-only after intake, and the final migration removes runtime direct allocation-release authority. Counter ceilings and canonical scope identities are database constrained.
- Command replay is serialized by an advisory transaction lock and checks actor, action and request digest before returning a stored result. Claim null results, heartbeat/release and accounting commands have durable replay paths before mutable fence validation.
- Budget/cost/token/output and completion accounting fail closed; retry classification is restricted to the four declared infrastructure classes and attempt three becomes terminal.
- The server pre-binds an absolute owned Unix socket, validates its parent, disables access logs, and has no TCP/provider/Git/GitHub/deploy/systemd execution surface. Actor/token files use no-follow file opens and exact mode checks.
- Rollback is evidence-preserving: global kill, stop local intake/claims, retain audit/state, restore into a separate comparison database and forward-fix with migration `009+`; no down migration is proposed.

## Latest verifier capability hotfix

The `7520b33` production change and `cf0219b` test-isolation follow-up do not add a separate blocking finding. The skip is confined to the pre-existing `factory-postgres-exit` check in PR/release mode and requires exact equality with `GROK_VERIFY_CAPABILITY=repository-sandbox` (`.grok-stack/adaptive_grok/verification.py:590-608`). Unset or look-alike values execute the unchanged 600-second runner, and a runner failure remains a verifier failure. The local-success test now removes inherited capability state, so the four capability matrix tests are order/environment isolated (`tests/test_verification_doctor.py:715-776`).

The variable is a runner capability declaration, not authentication or merge authority. The sandbox skip remains acceptable only alongside immutable-runner provenance and separate exact-head evidence where `factory-postgres-exit` actually passed; the inspected receipt contains that passing 43-test/restart evidence. It does not replace the App-owned exact-SHA Trust CI check.

## Reviewer verification

- `git merge-base <base> HEAD` — exact route base returned.
- `git diff --check <base>..<head>` — PASS.
- Four focused verifier-capability tests — PASS, 4/4.
- Dependency-free factory contract/state/migration/service tests — PASS, 21/21. API/server imports in the host interpreter were unavailable because FastAPI/Uvicorn are intentionally package-local; the exact-head disposable exit receipt supplies those dependency-backed results.
- Frozen-intent classifier probe — reproduced same idempotency key with different full intent digests after a mutually consistent producer/M0 exact-head change.
- Existing exact-head disposable exit evidence — PASS, 43/43 plus actual PostgreSQL restart, one repair, replay no-op, higher fence and late-holder rejection.

## Residual risks after required repairs

The reconciliation path is intentionally globally serialized through capacity locks and bounded by a five-second transaction timeout; high contention can fail a reconcile invocation even when state remains safe, so operations should monitor and retry with the same command key. The effective runtime role still has broad insert privileges needed by the current direct-SQL store design, so a future hardening iteration should move immutable intake/event/audit creation behind narrower database functions; this review did not classify that architectural residual as a new blocker because the supported API/service boundary enforces those writes and direct runtime tampering is outside the declared credential boundary.
