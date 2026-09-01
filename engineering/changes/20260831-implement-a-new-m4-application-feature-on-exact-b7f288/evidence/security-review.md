# M4 security re-review — FAIL

## Reviewed identity

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Exact base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior failing product HEAD: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Exact re-reviewed product HEAD: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Exact Git tree: `663de1bc25b9aee4da419b93a59ec2c98304ac4c`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Remediation range: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06..4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Verification receipt: PASS, exact HEAD `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`, fingerprint `0092b4cd8152eb7919c94c610e66c7a4d71ad46382f1c5db852df41af0ac8789`
- Reviewer: route-selected read-only `security_reviewer`

## Verdict

**FAIL**

- Critical findings: **0**
- Important findings: **1**
- Moderate findings: **0**

The fix wave closes repository/full-policy binding, global-control authorization,
private-file ancestry and audit-envelope integrity, but its M0 revocation lock does
not conflict with the supported revocation update. The exact tree must not receive
a passing security-review receipt.

## Severity-ordered finding

### Important I-1 — `FOR KEY SHARE` does not serialize `revoked_at` updates, so M0 can be revoked while intake still commits

Migration `009` now correctly binds an observation or exception to the requested
repository and full policy digest, enforces the policy-epoch check-name relation,
and restricts bootstrap authority to `action='task:intake'`
(`factory/src/adaptive_factory/resources/009_authority_audit_and_history_indexes.sql:1-19,39-42,55-58`).
The store also invokes that validation from the same database transaction that
creates the accepted intent (`factory/src/adaptive_factory/store.py:254-264`).

The remaining concurrency control is nevertheless insufficient. Both
`m0_observation_valid` and `m0_exception_valid` select the authority row with
`FOR KEY SHARE` (`009_authority_audit_and_history_indexes.sql:39-43,55-59`). In
PostgreSQL, a key-share row lock conflicts with deletion and key-changing updates,
but not with a `FOR NO KEY UPDATE` lock. The supported revocation statement changes
only non-key `revoked_at`, so it can commit after the validator has observed
`revoked_at IS NULL` and before the intake transaction commits. Under the store's
default `READ COMMITTED` transaction, no later authority read detects that change.
The result is an accepted intent whose authority was already revoked when intake
committed.

The regression does not exercise this interleaving. It first blocks intake on the
source advisory lock, commits the revocation, and only then lets intake perform its
first authority read (`factory/tests/test_postgres_integration.py:165-179`). It
proves revoke-before-validation rejection, not validation-before-revoke commit
serialization; its claim that `FOR KEY SHARE` protects concurrent revocation is
therefore false.

Required remediation:

1. Lock the matching authority row with a mode that conflicts with a non-key
   revocation update, for example `FOR SHARE` or `FOR UPDATE`, while retaining the
   validation and accepted-intent insert in the same transaction. Apply the same
   repair to observations and bootstrap exceptions.
2. Add a two-connection regression that pauses intake *after* authority validation
   and before accepted-intent commit, starts `UPDATE ... SET revoked_at=...` on the
   second connection, and proves a serial order: either intake commits before the
   revocation can commit, or intake observes the completed revocation and rejects.
   It must never allow revocation to commit first followed by successful intake.

## Prior findings re-evaluated

- **Repository/full-policy/action M0 binding:** closed apart from the revocation
  serialization defect above. Legacy nullable rows fail equality matching; new
  calls compare repository and all 64 policy hex characters, and the authoritative
  check name is recomputed from that digest.
- **Scoped reconciliation and metrics:** closed by requiring operator kind, the
  explicit scope, and wildcard repository authority before either global store
  operation (`factory/src/adaptive_factory/service.py:30-34,145-149`). A
  repository-scoped actor no longer reaches global reconciliation.
- **Private actor/token packaging:** closed. The shared reader requires absolute
  normalized paths, fails if no-follow/directory capabilities are absent, walks
  ancestry by held directory descriptors with no-follow, enforces trusted owners,
  requires an effective-UID-owned non-writable final parent, and requires an
  effective-UID-owned regular mode-`0600` leaf
  (`factory/src/adaptive_factory/settings.py:13-57`). Actor configuration and token
  files use the same reader.
- **Audit identity integrity:** closed. New version-2 digests include task, run and
  correlation identity, and verification reselects and recomputes those fields;
  version-1 rows remain verifiable without rewriting prior immutable audit
  (`factory/src/adaptive_factory/store.py:201-252,398-438`).

## Other security controls checked

- Migration `009` does not broaden table privileges. Its two `SECURITY DEFINER`
  functions use fixed `search_path=pg_catalog,factory`, schema-qualified static SQL,
  revoke PUBLIC execution and grant only EXECUTE to `factory_runtime`
  (`009_authority_audit_and_history_indexes.sql:32-67`). Existing capacity routines
  retain the same fixed-search-path/PUBLIC-revoked boundary, and migrations `007`
  and `008` continue to deny raw capacity/allocation authority.
- Closed M2/M3 handoffs still require matching architecture digest and exact
  base/head pairs; M0 exact head still matches the governance head. M4 records
  producer provenance rather than deriving or claiming Trust-CI authority.
- Actor/repository checks, constant-time bearer comparison, cumulative 1 MiB body
  cap, bounded parsing, owned UDS-only listener, generic errors and access-log
  suppression remain present. No provider, shell, repository, Git/GitHub, deploy,
  systemd or other external execution/write path was found under the product
  runtime.
- No repository change adds GitHub Actions or changes deployed Trust-CI policy,
  holdout, keys, PostgreSQL state, GitHub App configuration, human approval stores
  or branch protection. The repository-local verifier/receipt remains preflight
  evidence only.

## Verification evidence

- Inspected the active route, requirements, architecture, test plan, prior FAIL
  report, implementation ledger/report, the full base-to-head diff and the complete
  remediation diff.
- `git diff --check 67714a1...4230dc8` passed.
- Focused dependency-free contracts/service/migrations tests: 18 passed; the first
  combined command had one import error solely because system Python lacked
  `uvicorn`. Running the four server/UDS/private-file tests in the locked project
  environment passed 4/4. The generated ignored `.venv` was moved to trash after
  the run.
- The exact final verification receipt reports PASS for HEAD `4230dc8...` and tree
  fingerprint `0092b4cd...`; a passing local verifier does not detect or waive the
  row-lock semantics finding.

No `.env`, token, private key, credential store, production dump, Trust-CI state,
shared database or external system was read or mutated. No product source, commit,
receipt, database, push, merge, release or deployment was changed by this review;
the only retained repository write is this requested report.

## Residual trust boundary

After I-1 is repaired by the route's single write owner, rerun exact-head
verification and the affected independent reviews on one stable fingerprint. A
local PASS still would not authorize merge: the final PR SHA requires the
GitHub-App-owned policy-epoch Check Run and every independently signed approval
scope required by deployed policy.
