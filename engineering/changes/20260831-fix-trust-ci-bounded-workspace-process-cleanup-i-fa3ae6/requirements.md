# Requirements — Fix Trust CI bounded workspace process cleanup in the immutable read-only runner: zombie-only descendants after SIGKILL must not mask the original stdout/stderr/timeout failure, while live or uncertain survivors remain fail-closed. Deliver as an isolated stacked Trust-CI-only bugfix on M2 with regression tests.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given mocked bounded procfs records whose matching target-PGID members are all Z, then direct classifier execution returns `zombie_only`; a bounded command retains its original stdout/stderr/timeout `WorkspaceError`.
- [ ] Given a matching non-Z member (including X), malformed/truncated/oversized stat, vanished/open/read race, unavailable procfs, numeric-entry cap, deadline expiry, or uncertain final group probe, then direct classifier execution returns the fail-closed state.

## Failure and edge cases

- The worker process group remains rejected for both signal and inspection.
- A vanished PID is a normal race; incomplete membership evidence is not zombie proof.
- The direct `Popen` leader is still reaped and selector/stream cleanup remains intact.
- The receipt regression continues to bind frozen adoption base, route base, fingerprint, and evidence fields, but does not claim an arbitrary later stacked worktree has globally passing cumulative fitness.

## Non-functional requirements

- Security: retain TERM/KILL ordering and never signal outside the original PGID.
- Reliability: preserve the original failure only after positive zombie-only proof.
- Performance: bounded procfs entry/read scan and existing finite grace periods.
- Observability: existing redacted bounded workspace failure classifications are sufficient.
