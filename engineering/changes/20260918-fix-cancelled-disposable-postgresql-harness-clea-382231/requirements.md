# Requirements — Fix cancelled disposable PostgreSQL harness cleanup, orphan recovery, and timeout reporting (#128)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given a previous labelled container+volume older than the documented TTL and exactly matching harness ownership metadata, when the next runner starts, then it reclaims those resources and reports full identities before creating its own.
- [ ] Given fresh, current, malformed, foreign, partially bound, or ambiguous resources, when startup reclamation evaluates them, then it preserves them and does not delete by name/prefix alone.
- [ ] Given SIGTERM or SIGINT during a running test phase, when the verifier cancels the exit check, then descendants are stopped/reaped before the harness removes its exact container and volume; cancellation remains a non-pass outcome.
- [ ] Given a timed-out verifier command with descendants, when its timeout expires, then its isolated process group receives bounded TERM then KILL escalation and no descendant remains when the command result is returned.
- [ ] Given delayed Docker name visibility after container creation, when cleanup starts without a bound ID, then it retries name-to-ID lookup and exact binding only within the strict lookup deadline before deleting the exact full ID and matching volume.
- [ ] Given more labelled resources than the per-run recovery budget, when startup lists candidates, then Docker output bytes and inspected row count are capped, backlog is reported, and only exact stale bindings can be removed.
- [ ] The single per-run recovery candidate budget is shared across stale container+volume bundles and detached volumes; a bundle consumes one candidate and prevents an additional detached-volume reclaim in the same invocation.
- [ ] Given a bounded Docker listing exceeds its output byte cap, when startup recovery handles the result, then it reports an output-limit backlog distinctly from a Docker/list command failure and skips the incomplete snapshot without deleting from it.
- [ ] Given KeyboardInterrupt during a generic verifier command or bounded Docker listing, when the operation unwinds, then its isolated process group receives bounded TERM→KILL and is reaped before cancellation is re-raised.
- [ ] Given a nested Trust CLI launched from a test-worker process, when its environment is prepared, then `_GROK_TEST_CHILD` is removed and inherited pinned tool paths are retained after Trust suite paths so its explicit worker configuration is evaluated independently.
- [ ] Given an inner or outer budget expiry, when the check reports, then the failing result identifies phase, elapsed time, and budget; ordinary assertion failure remains distinguishable.
- [ ] Given missing repository-sandbox capability, when the gate runs, then the existing explicit skip/remedy remains visible.

## Failure and edge cases

- Docker inspect/list/remove failure, malformed labels, wrong mount, volume-only partial creation, delayed name visibility, oversized listings, concurrent fresh run, timeout during each phase, repeated signal during cleanup.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: exact full IDs and nonce/label/mount checks before deletion; unknown ownership fails closed.
- Reliability: SIGKILL/host loss is recovered only by later TTL sweep; no claim of immediate cleanup in that case.
- Performance: all subprocesses and sweeps remain bounded within the 600s outer limit.
- Observability: report reclaimed count and identities, phase outcome, elapsed/budget, and preserved ambiguous resource identity.
