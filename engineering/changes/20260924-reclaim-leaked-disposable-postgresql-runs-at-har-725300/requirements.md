# Requirements — Reclaim leaked disposable PostgreSQL runs at harness start (issue 128)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Given labelled disposable runs exist on the host, when the harness starts, then it reclaims the ones older than the documented bound whose nonce is not its own, before it creates its own container.
- [x] Given a reclaim decision was made, when the check output is read, then each container appears as `RECLAIM reclaimed|leaked|skipped|skipped-limit` with name, age, running state and removal observation; nothing is deleted silently.
- [x] Given another worktree's harness is running right now, when this harness reclaims, then the in-flight sibling (younger than the bound) and the current run's own nonce are never removed.
- [x] Given the gate is cancelled by SIGTERM, when the process dies, then the cleanup `finally` still runs because the signal surfaced as an exception, and the run still exits non-zero.
- [x] Given `docker run` returned a container id whose binding later fails to verify, when the harness exits, then that container is reclaimed rather than leaked.

## Failure and edge cases

- A container that cannot be inspected, has an identity mismatch, an unparsable creation timestamp, a foreign image or a name outside the harness prefix is skipped and reported, never deleted.
- A removal whose post-check still inspects successfully is reported `leaked`; the harness does not claim a reclaim it cannot observe.
- The reclaim budget bounds one invocation; the remainder is reported `skipped-limit` for a later run instead of turning startup into an unbounded cleanup loop.
- Signal handlers are installed only on the main thread and are always restored, so an importing caller keeps its own disposition.
- No host cron or global prune is added: cleanup authority stays with the harness that mints the label.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: containers leaked before this change are reclaimed by age on the next gate run rather than by a one-off migration, and a bound that must exceed a live sibling is a heuristic, not a lease. Accepted: the harness cannot see another worktree's process, and #52 shows where an ownerless sweeper ends up.

## Non-functional requirements

- Security: removals are constrained to an exact label, name prefix, image and 64-hex id; no credential, volume outside the container's own anonymous volume, or foreign resource is touched.
- Reliability: bounded timeouts on every docker call; fail-closed on any ambiguity; a cancelled run can never be mistaken for a pass.
- Performance: one `docker ps` plus one `docker inspect` per candidate before the suite starts, bounded by the reclaim budget.
- Observability: the `RECLAIM` lines land inside the `factory-postgres-exit` check output that the verification receipt already stores.
