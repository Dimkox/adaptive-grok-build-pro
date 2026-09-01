# M4 security review — FAIL

## Reviewed identity

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Exact base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Exact product HEAD: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Exact Git tree: `d497c897e3875dd52f788c10bbb1f7ed19e3942f`
- Full reviewed range:
  `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Reviewer: route-selected read-only `security_reviewer`

## Verdict

**FAIL**

- Critical findings: **0**
- Important findings: **2**
- Moderate findings: **2**

The current exact tree must not receive a passing `security_review` receipt.
Local verification and older review reports do not waive the authorization and
authority-provenance defects below, and none of them is external merge authority.

## Severity-ordered findings

### Important I-1 — Persisted M0 authority is not bound to repository or policy and is checked outside intake's transaction

The trusted observation table stores `observed_at`, policy-epoch-shaped
`check_name`, `exact_head_sha`, issuer and evidence digest, but no repository
identity or full deployed-policy digest
(`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:1-10`).
Bootstrap exceptions likewise have a free-form scope but no enforced repository,
action or policy subject (`005_security_accounting_commands.sql:12-19`).

`TaskIntakeV1` accepts the caller's `repository_id` and `policy_digest`, but its
cross-authority checks only compare the M2/M3 architecture fields and M0 head to
the governance head (`factory/src/adaptive_factory/contracts.py:227-263`). The
store lookup then checks only the caller-repeated timestamp/check-name/head tuple,
or the caller-repeated exception fields
(`factory/src/adaptive_factory/store.py:134-149`). It does not bind the row to
`intake.repository_id`, `intake.policy_digest`, the expected policy SHA prefix,
or a repository-scoped exception subject.

The checked-in nominal fixture demonstrates the gap: it accepts
`policy_digest=999999...` with check suffix `06ecf1c875bc`. An independent
reproduction on exact HEAD printed:

```text
policy_prefix 999999999999
check_suffix 06ecf1c875bc
mismatch_accepted True
```

Consequently one legitimate observation can be replayed for another configured
repository that contains the same commit (including a fork), while an arbitrary
policy digest is frozen into an accepted intent as though it were validated.
The bootstrap path has the same cross-repository problem because its `scope`
string is matched for equality but never interpreted against the requested
repository/action.

There is also a revocation race: `FactoryService.intake()` calls
`verify_m0_authority()` on one connection and only afterwards opens the separate
intake transaction (`factory/src/adaptive_factory/service.py:43-49`,
`factory/src/adaptive_factory/store.py:134-149,234-243`). A trusted operator can
revoke the observation between those operations and the intake will still commit.

Required remediation:

1. Add a forward migration that binds every M0 observation/exception to an exact
   repository subject and full policy identity (and, for an exception, a closed
   action/scope that is actually evaluated).
2. Require the check-name suffix to match the trusted full policy digest and
   compare that trusted tuple with the intake values.
3. Perform the non-revoked, unexpired authority lookup in the same transaction
   that inserts the accepted intent, or consume an unforgeable transaction-bound
   authority handle.
4. Add cross-repository, wrong-policy, wrong-scope and concurrent-revocation
   regressions. Caller JSON must remain a lookup request, never authority.

### Important I-2 — Repository-scoped operators can run the global reconciler and mutate other repositories

Repository authorization is enforced for submit/read/list/cancel, worker grants
and repository kill switches. Reconcile is the exception:

- `FactoryService.reconcile()` checks only the `factory:reconcile` scope, operator
  kind and limit; it neither requires wildcard authority nor passes allowed
  repositories to the store (`factory/src/adaptive_factory/service.py:148-152`).
- `PostgresFactoryStore.reconcile()` selects every expired live allocation and
  has no repository predicate (`factory/src/adaptive_factory/store.py:914-955`).
  It can release capacity and move another repository's task to retry,
  needs-human or dead while writing audit/events as the unauthorized operator.

An independent service-boundary reproduction on exact HEAD used an operator with
only `repositories={"repo/a"}` and reached the unfiltered store reconciler:

```text
global_reconcile_reached True
repo_scoped_result mutated-all-repositories
```

This violates the stated fail-closed unauthorized-repository contract. The kill
path already demonstrates the appropriate pattern by requiring `"*"` for a
global operation or checking one repository explicitly
(`factory/src/adaptive_factory/service.py:138-146`).

Required remediation: either require wildcard repository authority for the
global reconcile endpoint, or pass the actor's closed repository set through the
service and apply it to candidate selection, mutation, cursor and idempotency
identity. Add unit, API and real-PostgreSQL tests proving a repo-A operator cannot
observe or repair repo-B work.

### Moderate M-1 — Actor and token file checks do not secure path ancestry or ownership

Actor configuration and bearer-token readers use `O_NOFOLLOW` only on the final
pathname and validate regular-file mode `0600`
(`factory/src/adaptive_factory/server.py:22-37`,
`factory/src/adaptive_factory/settings.py:13-31`). They do not require an absolute
path, verify the file owner, pin repository/root identity, or walk every ancestor
with no-follow directory descriptors. `getattr(..., 0)` also silently removes the
no-follow property on a platform without that capability.

A mode-`0600` leaf therefore does not by itself prove operator ownership. In a
renameable or symlinked ancestor (especially when the service runs with elevated
read authority), a local attacker can substitute an attacker-owned actor file or
token before startup and choose credentials/scopes. The socket path has an
explicit owned/private-parent check, but the more sensitive authentication files
do not (`factory/src/adaptive_factory/server.py:73-93`).

Required remediation: require absolute paths; fail if required descriptor
capabilities are unavailable; open and pin every ancestor without following
links; require an explicit trusted owner policy for both actor and token files;
and test ancestor symlink/replacement, foreign ownership and unsupported
capability cases.

### Moderate M-2 — The advertised audit hash chain does not authenticate all stored audit evidence

Audit rows store `task_id`, `run_id` and `correlation_id`, but `_audit()` excludes
all three from `current_digest` (`factory/src/adaptive_factory/store.py:185-230`).
`verify_audit_chain()` does not even select them and can therefore return true
after those fields change (`factory/src/adaptive_factory/store.py:376-408`).

Runtime UPDATE/DELETE denial on `audit_log` is a valuable primary control, but it
does not make a partial hash an integrity proof. A privileged repair, accidental
owner mutation or future grant regression can alter run attribution or request
correlation without detection while the product reports a valid chain. These are
security-relevant evidence fields used for fencing and incident reconstruction.

Required remediation: version the canonical audit envelope and bind at least
task, run, correlation, actor, action, resource, reason, timestamp and canonical
metadata into each digest. Add fault-injection tests that mutate each stored
semantic field with migration-owner authority and require chain verification to
fail. Keep runtime audit UPDATE/DELETE revocations.

## Security controls that remain sound

- Migrations are contiguous/checksummed and factory-only. Runtime has no Trust-CI
  schema authority in the tested role model.
- Capacity functions are static, parameterized `SECURITY DEFINER` routines with
  fixed `search_path=pg_catalog,factory`, schema-qualified objects, PUBLIC
  execution revoked, canonical 20/10/1 ceilings and ordered locks. Migration 008
  removes direct runtime allocation-release mutation.
- Lease mutation binds task, run, authenticated owner, fence, packet, live
  allocation, lease/deadline and current task projection. Capacity drift makes
  readiness and reconciliation fail closed.
- The API cumulatively caps streamed bodies at 1 MiB, uses bounded generic errors,
  constant-time bearer comparison and disables access logging. The composition
  exposes an owned Unix socket only; no TCP listener is configured.
- No provider, shell, repository command, Git/GitHub, systemd, deployment or
  external-write capability exists under `factory/src/adaptive_factory`; the CLI
  uses only HTTP over an explicit Unix-domain socket.
- The verifier capability hotfix is narrowly implemented: only exact
  `GROK_VERIFY_CAPABILITY=repository-sandbox` skips only
  `factory-postgres-exit`; absent, malformed and suffixed values execute the
  runner and propagate failure. That environment declaration is not
  authentication or merge authority, so the external runner/policy must remain
  responsible for setting it.

## Verification evidence

Static inspection covered the complete base-to-head diff, all eight SQL
migrations, contracts, store/service/API/server/settings/CLI, tests, change
package and verifier hotfix. `git diff --check` passed and the changed-tree secret
scan found no committed credential/private-key pattern.

Focused exact-head tests passed:

```text
Ran 25 tests in 9.094s
OK
```

This set covered contracts, service authorization currently under test,
migrations, state/retry policy and all four verifier capability cases. The
existing exact-head verification receipt also records the broader API/database
exit suites as passing, but it is currently stale after evidence refresh and in
all cases does not detect or waive the findings above.

No `.env`, token, private key, credential store, production dump, Trust-CI state,
shared database or external system was read or mutated. This review performed no
push, merge, release, deployment or database write. The only repository write is
this requested report.

## Residual trust boundary

This report is local review evidence for exact product HEAD
`cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`; it is not merge authority. After
the findings are repaired by the route's single write owner, rerun full
verification and all affected independent reviews on one stable fingerprint.
The final pull-request SHA still requires the App-owned policy-epoch Check Run
and every required independently signed approval scope.
