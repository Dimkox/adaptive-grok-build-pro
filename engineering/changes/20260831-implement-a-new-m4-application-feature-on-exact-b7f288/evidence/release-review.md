# Independent release review — M4 durable factory control plane

## Verdict and binding

**FAIL — Important finding present.**

- Route: `b7f288f1e81e`
- Base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed product HEAD: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Existing exact-head local verification receipt: PASS, fingerprint `13363f4e7d5b058ae864ca54c165bb671e6355c2d7082f60c023a01154347df3`; it includes `factory-postgres-exit=pass` and source stability PASS.

I inspected the full committed range, active route/package state, release/rollback/schedule documents, README/roadmap, installer inventory, all eight migrations, the UDS server/settings/store paths, disposable exit/restart probes, current local receipts, and the exact-head verifier changes. `git diff --check` over the reviewed range is clean.

## Important finding

### RR-001 — The shipped local rollout cannot provision or connect its required database roles

`factory/compose.yaml` creates just the PostgreSQL bootstrap owner named by `FACTORY_POSTGRES_USER`; the supplied `.env.example` then points `FACTORY_DATABASE_URL` at a different, nonexistent `factory_service` login. The migration SQL creates `factory_migrator` and `factory_runtime` as `NOLOGIN NOINHERIT` roles, but neither creates a service login nor grants that login membership in `factory_runtime` (`factory/compose.yaml:4-7`, `factory/.env.example:2-5`, `factory/src/adaptive_factory/resources/001_initial.sql:1-5`).

This is not only a documentation mismatch. Every store connection unconditionally executes `SET ROLE factory_runtime` (`factory/src/adaptive_factory/store.py:50-59`), so the documented `adaptive-factory-server` composition cannot connect with the supplied example or with a separately created login unless an unprovided privileged provisioning step grants role membership. The release plan and factory README require a distinct migrator connection through schema 008, but expose neither a migration command nor a bounded role/bootstrap procedure for that connection (`release.md:5`, `factory/README.md:18,22,34`). The installer faithfully transfers the incomplete package, so it does not close this gap.

Impact: an otherwise authorized local rollout has no reproducible, least-privilege bootstrap path and will fail before readiness. An operator could manually improvise role/login grants, but that is exactly the undocumented security-sensitive database mutation this release plan is meant to constrain. This blocks release readiness.

Required repair: provide an explicit, separately authorized local bootstrap/migration interface or a complete operator runbook that names the migrator and runtime login creation, ownership, membership, credential inputs, and validation/rollback boundaries. Make the compose/example settings internally consistent, add a disposable integration test that starts from those shipped inputs and reaches authenticated UDS readiness under the effective runtime role, then rerun exact-tree verification and all selected reviews.

## Release controls that are otherwise correctly represented

- Migrations are contiguous checksum-bound `001..008`, applied under an advisory lock, and recovery documentation consistently requires forward migration `009+` after durable intake; destructive down-migration and audit deletion are prohibited.
- Rollout begins killed and calls for restore-to-separate-database, schema/readiness/capacity checks, redacted metrics, synthetic accounting flow, actual restart, and two-pass reconciliation. Rollback preserves rows, audit, logs, and evidence before forward recovery.
- The executable service binds only an absolute owned `AF_UNIX` socket at mode `0660`; its CLI uses HTTP-over-UDS. Static inspection found no product provider execution, shell/repository/GitHub operation, TCP listener, deployment/systemd action, Trust CI mutation, or external-write path. Docker use is confined to the named disposable test runner.
- The installer includes factory source, migrations, lockfile, contract, examples, and the disposable verification harness, and excludes runtime state, sockets, databases, and credentials. The inventory is complete for source transfer, but cannot make the missing rollout bootstrap executable.
- The recent verifier change permits `factory-postgres-exit` to be skipped only for the explicit `repository-sandbox` capability. The supplied exact-head local receipt records this gate as **pass**, not skip. This preserves local PostgreSQL/restart evidence; it does not itself establish external merge authority.

## Evidence and delivery boundary

The package correctly distinguishes local preflight from delivery authority. The exact product head has a passing local verification receipt, but the worktree presently contains uncommitted reviewer-report rewrites, including this report; that receipt cannot bind the final evidence tree. `requirements.md` also leaves AC-014 unchecked. Therefore neither this review nor the existing receipt may be described as final route closure, PR approval, merge eligibility, migration approval, deployment authorization, tag/release authority, or service activation.

After RR-001 is repaired and the evidence tree is frozen, local closure still requires a fresh fingerprint-bound verifier run and all route-selected review receipts on that same tree. PR delivery remains separately authorized, and merge requires the GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run plus all required signed scopes on the exact PR head. No local receipt, Markdown report, delegated grant, or state value substitutes for that external gate.
