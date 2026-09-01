# M4 final security review — FAIL

## Reviewed identity

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head: `01643c6594947535e690c5722f710081c9b9db9f`
- Reviewed diff: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..01643c6594947535e690c5722f710081c9b9db9f`
- Reviewer: route-selected read-only `security_reviewer`
- Verdict: **FAIL**
- Critical findings: **0**
- Important findings: **5**
- Moderate findings: **2**

PASS requires zero Critical/Important findings. This report is local review evidence only; it is not merge authority and cannot create the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check.

## Important findings

### I-1 — Caller assertions are accepted as M0 trust authority

`M0AuthorityV1.from_dict()` accepts any fresh caller-supplied `observed_at`, any regex-shaped `check_name`, and a matching caller-supplied head SHA (`factory/src/adaptive_factory/contracts.py:145-160`). Its alternate form accepts any named bootstrap exception, issuer, scope, and future expiration (`factory/src/adaptive_factory/contracts.py:161-170`). Intake only cross-compares those fields with the other caller-supplied handoffs (`factory/src/adaptive_factory/contracts.py:227-237`); it does not bind the observation to the deployed policy epoch/App identity or bind an exception to a trusted, persisted operator decision. This remains reachable to every token with `task:submit` (`factory/src/adaptive_factory/api.py:119-131`).

A focused production-code probe accepted both:

```text
accepted_authority ... check_name='caller-asserted-not-trust-ci' ...
accepted_authority ... bootstrap_exception='fabricated', issuer='untrusted-caller', scope='anything' ...
```

An authenticated submitter can therefore manufacture the authority that is supposed to gate dispatch. This contradicts the requirement that M4 consume frozen authority and not infer permission from caller claims. Require a verifier-produced, integrity-protected observation bound to the exact head, deployed check name/policy epoch and trusted issuer; remove the revoked bootstrap form or require a separately persisted and authenticated operator exception with an allowlisted scope and bounded TTL.

### I-2 — Worker mutations are not bound to actor identity or repository authorization

Claim accepts an arbitrary caller-provided `owner` (`factory/src/adaptive_factory/api.py:184-204`, `factory/src/adaptive_factory/service.py:49-60`) instead of binding the lease owner to `actor.actor_id`. Heartbeat, release, budget reservation, and usage observation check only a coarse scope (`factory/src/adaptive_factory/service.py:62-101`); unlike read/cancel/claim, they never enforce `actor.repositories`. The SQL fence validates the owner string embedded in the caller-supplied grant but does not compare it with the authenticated actor or that actor's repository set (`factory/src/adaptive_factory/store.py:424-440`).

A focused service-boundary probe showed actor `worker-B`, authorized only for `repo/B`, successfully invoking heartbeat and completed release for a grant owned by `worker-A`:

```text
heartbeat worker-B frozenset({'repo/B'}) worker-A
release worker-B frozenset({'repo/B'}) worker-A completed
```

Possession or forwarding of a grant therefore bypasses the token's actor/repository boundary. Bind claim owner to the authenticated actor (or an explicit server-side worker identity), and enforce actor ID plus repository authorization inside the same transaction that locks every grant mutation. Add cross-actor and cross-repository heartbeat/release/budget regression tests.

### I-3 — Budget enforcement can be bypassed by the normal API completion path

The API exposes claim, heartbeat and proposal/release, but no budget reservation or usage-observation endpoint (`factory/src/adaptive_factory/api.py:184-237`, `factory/contracts/openapi/factory-control.v1.json:10-14`). A worker can directly propose `completed`; release checks the live fence but does not require accounting evidence, inspect `accounting_blocked`, settle a reservation, or compare observed usage with reserved usage (`factory/src/adaptive_factory/store.py:424-440`, `factory/src/adaptive_factory/store.py:454-510`). `accounting_blocked` only affects future claims and reservations (`factory/src/adaptive_factory/store.py:353-357`, `factory/src/adaptive_factory/store.py:524-535`), so even a currently blocked lease can complete. The stored `wall_seconds` reservation is never included in any limit calculation (`factory/src/adaptive_factory/store.py:512-547`).

Consequently, missing accounting fails closed only if a caller voluntarily invokes the non-API service method that detects it. Require server-side accounting state for every completion/release, reject release while accounting is absent or blocked, expose a closed authenticated accounting protocol if workers need it, and enforce/settle wall, cost, token and output reservations atomically.

### I-4 — The claimed Unix-socket-only server boundary is not implemented

The package has only a CLI entry point (`factory/pyproject.toml:11-12`). `FactorySettings` is not wired to an application bootstrap, and the tree contains no Uvicorn server construction, Unix-socket bind, socket-parent ownership validation, stale-socket handling, or `0660` permission enforcement. `create_app()` returns a transport-agnostic ASGI app (`factory/src/adaptive_factory/api.py:81-82`), so nothing in product code prevents an integrator from binding it to TCP. The CLI's use of `httpx.HTTPTransport(uds=...)` (`factory/src/adaptive_factory/cli.py:61-66`) constrains only that client, not the server.

This leaves the primary local trust boundary asserted by AC-010 and `factory/README.md:20-24` unenforced and provides no runnable authenticated API composition from settings, store, service and tokens. Add a dedicated server entry point that can only bind an operator-owned Unix socket, validates/no-follows its parent and existing path, applies `0660` under a controlled umask, refuses TCP configuration, wires `read_token_file()` and repository-scoped actors, and has an end-to-end socket-mode/no-TCP test.

### I-5 — Runtime database grants permit mutation of records described as immutable/append-only

Migration `003` grants `factory_runtime` `UPDATE` on every operational table except `audit_log`, including `accepted_intents`, `task_events`, `usage_observations`, `budget_reservations`, and `kill_switches` (`factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql:48-53`). Those tables are described as immutable or append-only evidence, yet a runtime credential can rewrite accepted bodies/digests, event actors/actions/metadata, usage, or the current kill state without producing a new row. The audit chain covers only `audit_log`; it does not detect these rewrites (`factory/src/adaptive_factory/store.py:278-310`). The runtime connection also accepts an arbitrary database URL without checking/setting the intended role (`factory/src/adaptive_factory/store.py:44-53`).

The audit-log-specific no-update/no-delete test is positive but too narrow (`factory/tests/test_postgres_integration.py:266-287`). Replace the blanket grant with per-table least privilege (for example INSERT-only immutable facts, narrowly necessary UPDATE columns/tables), ensure the service actually operates under the runtime role, and add negative privilege tests for every immutable/evidence table.

## Moderate findings

### M-1 — The 1 MiB body limit is Content-Length-only and runs before authentication

Middleware rejects only when a parseable `Content-Length` is present (`factory/src/adaptive_factory/api.py:104-109`). A streaming/chunked ASGI body has no content length and is fully consumed by FastAPI's JSON parser before endpoint authentication. Malformed `Content-Length` also reaches an unhandled `int()` conversion. A local peer with socket access can therefore bypass the documented 1 MiB memory bound without a valid token. Enforce a cumulative receive limit at the ASGI boundary and return a bounded 400/413 for malformed or oversized framing; test chunked, missing, conflicting and malformed lengths.

### M-2 — Mutation correlation and kill idempotency do not preserve reliable operator evidence

The API validates `X-Correlation-ID` but drops it before service/store calls; store audit instead uses request IDs or synthesized digests (`factory/src/adaptive_factory/api.py:119-279`, `factory/src/adaptive_factory/store.py:229-238`, `factory/src/adaptive_factory/store.py:417-419`, `factory/src/adaptive_factory/store.py:491-505`). Kill changes are not added to the hash-chained audit, and conflicting reuse of an idempotency key returns the caller's newly requested `enabled` value when the insert did nothing (`factory/src/adaptive_factory/store.py:639-650`). This can falsely report an unkill/kill while durable state remains opposite. Persist the authenticated correlation ID, action digest and actual prior result; reject an idempotency key reused with different scope/enabled/reason; preserve kill evidence in an append-only protected record/audit chain.

## Positive controls observed

- Bearer token digests are compared with `hmac.compare_digest`, and the token-file reader uses `O_NOFOLLOW`, verifies a regular `0600` file, bounds length and closes the descriptor (`factory/src/adaptive_factory/api.py:35-53`, `factory/src/adaptive_factory/settings.py:13-31`). No token or database secret was read or logged during this review.
- Application SQL values are parameterized; the only executed raw SQL is packaged, checksum-bound migration text (`factory/src/adaptive_factory/migrations.py:33-64`, `factory/src/adaptive_factory/store.py`). No SQL-injection path was found in the reviewed surface.
- Claims use ordered capacity locks plus `FOR UPDATE SKIP LOCKED`, monotonic per-task fences, database time, live-run/state/deadline checks and transaction-scoped updates (`factory/src/adaptive_factory/store.py:320-440`). These controls reject stale/expired grants when the authenticated resource boundary is otherwise correct.
- Global/repository kill state blocks new claims as specified (`factory/src/adaptive_factory/store.py:312-324`), and reconciliation is page-bounded to 100 by the service with a five-second statement timeout (`factory/src/adaptive_factory/service.py:112-116`, `factory/src/adaptive_factory/store.py:652-687`).
- `audit_log` itself is insert/select-only for the runtime role and is hash chained; verification recalculates the chain and head (`factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql:52-54`, `factory/src/adaptive_factory/store.py:89-136`, `factory/src/adaptive_factory/store.py:278-310`).
- No provider, shell, repository, Git/GitHub, deploy, systemd, connector or production-write execution path was found under `factory/src/adaptive_factory`.

## Commands and evidence

```text
git rev-parse HEAD
01643c6594947535e690c5722f710081c9b9db9f

git diff --name-status 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..01643c6594947535e690c5722f710081c9b9db9f
72 changed paths inspected; factory package, contracts, SQL, tests and surrounding change documents reviewed.

PYTHONPATH=factory/src:. python3 <focused authority/authorization probe>
Both fabricated M0 forms accepted; cross-repository/cross-owner heartbeat and release reached the store.

python3 -m compileall -q factory/src factory/tests
PASS

rg -n "uvicorn.run|Config\\(|Server\\(|chmod\\(.*0660|chmod\\(.*0o660|create_unix|bind.*unix|\\[project.scripts\\]" factory -S
Only `[project.scripts]` matched; it defines the CLI, not a server.

python3 -m unittest discover -s factory/tests -p 'test_*.py' -v
NOT RUNNABLE in the reviewer base environment: `fastapi` and the installed `adaptive_factory` package were absent. This is not represented as passing evidence. The independent route verification receipt must remain the source for the full test result on the exact fingerprint.
```

No `.env`, private key, credential store, production dump, Trust CI secret/state, or human approval material was read. No database, network, push, merge, release, deployment or other external mutation was performed. The only repository write by this reviewer is this requested report.

## Required disposition

**FAIL.** Return I-1 through I-5 to the single route write owner, add adversarial regressions, rerun exact-tree verification, and repeat every affected independent review. Do not record a passing `security_review` receipt for head `01643c6594947535e690c5722f710081c9b9db9f`.
