# Final data-review repair evidence

Date: 2026-08-28

Scope: the three Important findings from the data review on
`4206166576ad271f693efb65eb80db4c13ef9a24`, plus the release-review chronology
Minor. No `trust-ci/**` or `.github/workflows/**` file changed.

## Root causes and bounded design

1. System semantic validation resolved `allowed_data` IDs but did not derive the
   set whose `contains_secret` flag is true. A secret-bearing classification
   could therefore be attached to any edge. The bounded invariant now requires
   every such edge to be an authenticated `secret_flow`; it adds no schema field
   or runtime capability.
2. Migration applicability matched only declared primary prefixes. Derived
   package-resource mirrors were compared only after a primary artifact was
   already applicable, so mirror-only drift returned N/A. One deterministic
   primary-plus-mirror root set now drives changed-path matching and applicability
   inventory. An unpaired mirror change fails, while a paired change retains the
   existing byte comparison against its primary.
3. The seed assigned `runner.py` to the secretless isolated runner even though
   `worker.py` constructs `JobRunner` with the database, signer, GitHub client,
   and token provider. `JobRunner` reads approvals and attestations and writes
   signed attestations. Ownership now belongs to the trusted worker; both real
   PostgreSQL edges declare the approval, attestation, and job-state data they
   use. Canonical digests and the data-flow projection were regenerated.
4. `release.md` described an obsolete Task 3/review-clean checkpoint. It now
   states only that source repairs are implemented and keeps verification, all
   five reviews/receipts, M2-B, PR, Trust CI, and deployment pending.

## RED

```text
python3 -m unittest -v \
  tests.test_architecture_model.ArchitectureModelTests.test_secret_bearing_data_requires_authenticated_secret_flow \
  tests.test_architecture_model.ArchitectureModelTests.test_seed_architecture_models_current_boundaries_and_real_contracts \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_mirror_only_change_is_applicable_and_fails_drift

Ran 3 tests in 0.231s
FAILED (failures=4)

- deployment and unauthenticated secret_flow accepted DATA-TRUST-MATERIAL
- runner.py owner was NODE-ISOLATED-RUNNER
- mirror-only SQL mutation returned not_applicable instead of fail
```

The first complete fitness run after the canonical model edit also found a
fixture error: an exact-HEAD diff was evaluated against the mutable worktree
snapshot. It correctly raised `fitness snapshot does not match the diff head`.
The test now evaluates the immutable `diff._head_state.snapshot` it claims to
cover.

## GREEN

```text
Focused architecture-model, mirror, and frozen-digest checks
Ran 45 tests in 1.195s
OK

python3 -m unittest -q tests.test_architecture_fitness
Ran 74 tests in 79.560s
OK
elapsed=79.74 exit=0

python3 -m unittest discover -s tests -p 'test_*.py' -q
Ran 369 tests in 189.433s
OK
elapsed=189.63 exit=0
```

Ruff, configured Bandit, compileall, typed spec 7/7, architecture validate,
repository drift, deterministic diagram check, frozen digest structure check,
README K16, exact worktree diff/fitness/change separation, and diff whitespace
all pass. Exact fitness reports `green -> red` monotonic risk and code budget
`10000/10000`. The current summary binds:

- architecture digest: `5ab48dfaac3b649b82c364f05351266979a104ef8420f58e62533d1322805290`
- system digest: `da6453d9bbb291b297a393ff3d63fb68a0f3ec120107b6ed2cac4ee5a2d6e72b`
- data-flow diagram digest: `1e0ad51b8bd1474306f2d63dfce5cc36c1d516e630ec82e222b95ceedefeecb1`

## Files, rollout, and rollback

Changed application/model files are `architecture.py`,
`architecture_fitness.py`, `architecture/system.yaml`, and the generated
data-flow projection. Tests cover secret semantics, mirror-only applicability,
exact snapshot binding, source ownership, real edge data, and frozen digests.
The package requirements, release chronology, and decision ledger carry the
updated evidence.

Rollout remains source-only through the existing PR and external Trust CI path.
Rollback is one revert of the eventual repair commit, which restores the prior
model, digests, projection, and conservative fitness behavior together. The
residual boundary is intentional: secret-bearing data on untyped or
unauthenticated edges and unpaired package-mirror changes fail closed.

The exact no-record verifier result and commit SHA follow after the final gate.

## Tenant and migration aggregate rereview

The tenant category previously took applicability from repository rules and a
closed edge-type subset. That allowed rules to hide declared tenant data and
made deployment or secret-flow edges carrying it return N/A. Applicability now
comes directly from `tenant_scoped: true` classifications and every edge that
carries them. Missing rule coverage and required tenant-filter evidence are
typed unsupported; unauthenticated tenant edges fail. A non-tenant model remains
true N/A.

Migration evaluation previously recomputed derived roots within nested loops and
used one Git blob subprocess for each primary/mirror comparison. One bounded
rule/root/mirror table and root-to-plan index now drive applicability. Aggregate
root, changed-artifact, inventory, rule, and blob work is capped; required blobs
are read in deterministic eight-path batches, and published findings have a
stable ceiling. Mirror-only drift and every existing phase/version/source safety
check remain enforced in exact and worktree modes.

RED evidence:

```text
tenant edge/policy matrix: 5 expected failures; affected cases returned N/A
migration aggregate selectors: 2 expected failures in 0.564s
- primary/mirror comparison invoked forbidden singleton read_diff_file
- low work ceiling returned fail instead of typed unsupported
```

GREEN evidence:

```text
focused tenant and migration methods
Ran 8 tests in 5.235s
OK

python3 -m unittest tests.test_architecture_fitness
Ran 77 tests in 81.915s
OK

python3 -m unittest discover -s tests
Ran 372 tests in 192.014s
OK
```

Exact worktree fitness passes with `code_budget=pass` at exactly
`10000/10000`, `change_separation=pass`, and monotonic risk `green -> red`.
Ruff, configured Bandit, compileall, typed spec 7/7, architecture validation,
drift, deterministic diagram check, summary/digests, README K16, documentation
structure, diff whitespace, and protected-path checks pass. `release.md` already
describes the current final-repair state and keeps independent reviews,
receipts, PR, Trust CI, M2-B, and deployment pending, so no chronology edit was
needed in this rereview.

The exact no-record verifier result and commit SHA follow after the final gate.

## Tenant precedence and bounded migration consumption rereview

The final test and code rereviews identified four related gaps in the aggregate
migration repair. The batch oracle did not require a positive read count or a
content-sensitive mismatch, mirror-only coverage omitted worktree and unchanged
N/A evidence, migration blob bytes/statements/findings were not stopped before
their limits, and mixed unauthenticated plus tenant-filter-unknown edges
published `fail` instead of the more conservative `unsupported` result.

RED evidence was captured before the replacement. The mixed tenant case
returned `fail`; patched byte and statement ceilings returned `pass`; and a
three-finding ceiling still invoked the bounded-predicate analyzer six times.
The strengthened exact/worktree inventory and paired-content controls already
passed, proving that the remaining defect was bounded consumption rather than
applicability.

One named `_MigrationAnalysis` now owns the prepared rule/root index, bounded
issues, statement work, and deterministic eight-path reads. A conservative
pre-analysis work ceiling is checked before semantic traversal. Aggregate blob
bytes stop between batches, statement/finding ceilings stop before predicate or
finding generation, and mirror copies are prepared once for both read inventory
and byte comparison. Any limit becomes typed unsupported. Tenant unsupported
evidence takes precedence while retaining the simultaneous unauthenticated
finding.

```text
focused tenant, batching, mirror exact/worktree, and limit methods
Ran 4 tests in 2.748s
OK

python3 -m unittest tests.test_architecture_fitness
Ran 78 tests in 82.681s
OK
real 82.86

python3 -m unittest discover
Ran 373 tests in 191.487s
OK
real 191.72
```

Ruff, configured Bandit, compileall, typed spec 7/7, architecture validate,
repository drift, deterministic diagram check, exact architecture diff, README
K16, and diff whitespace all pass. Both the frozen-adoption and task-base
protected-path queries are empty. Exact worktree fitness passes with code budget
`9999/10000`, change separation pass, and monotonic risk `green -> red`.
Unchanged exact and worktree migration evaluation is specifically N/A with
`no_matching_sql_change` and audited primary-plus-mirror inventory; mirror-only
drift fails in both modes.

The final verifier and exact commit SHA follow after the evidence-bound gate.

## Final migration early-stop rereview

The final test and code reviews found that the migration work ceiling was
checked only after derived-root, path-matching, and repository-inventory work,
and that SQL analysis eagerly materialized every semicolon-delimited statement.
The original mutation oracle also proved only the typed result, not that blob
reads and SQL analysis were skipped after the aggregate limit.

RED evidence:

```text
focused migration work/scanner selectors
Ran 2 tests in 0.829s
FAILED (failures=2)
- zero work still called _migration_roots
- the 8 MiB separator fixture reached the prohibited eager split

mutation proof with both work checks disabled
Ran 1 test in 0.232s
FAILED: blob read after work limit
```

One staged `_MigrationAnalysis` work counter now rejects a cheap schema-count
upper bound before root discovery, charges the derived-root index before SQL
matching, charges changed SQL against the root index before matching, and
charges inventory, semantic-plan, and blob-read work before the corresponding
downstream operations. SQL statements are consumed incrementally with bounded
comment-aware matching; statement and finding limits stop before the next
predicate evaluation or finding publication. Every ceiling remains typed
unsupported.

GREEN evidence on the final tracked tree:

```text
focused final-review selectors
Ran 2 tests in 1.244s
OK

focused migration regression matrix
Ran 4 tests in 2.210s
OK

python3 -m unittest -q tests.test_architecture_fitness
Ran 78 tests in 82.514s
OK
elapsed=82.69 exit=0

python3 -m unittest discover -s tests -p 'test_*.py' -q
Ran 373 tests in 192.841s
OK
elapsed=193.07 exit=0
```

Exact worktree fitness passes with `code_budget=pass` at `10000/10000`,
`change_separation=pass`, and monotonic risk `green -> red`. The repair adds no
runtime dependency, migration artifact, service, external action, or Trust CI
source change.

## Shared migration-root membership rereview

The final security review found that matching work used the number of distinct
root keys even though each root can map to every migration policy. A valid
256-policy model sharing one root and 3,328 changed SQL artifacts therefore
reached match-set construction after charging only 3,328 units for 851,968
policy memberships.

RED and GREEN evidence:

```text
shared-root membership selector before repair
Ran 1 test in 0.234s
FAILED: matching after membership limit

shared-root membership and prior work-limit selectors after repair
Ran 2 tests in 0.957s
OK

python3 -m unittest -q tests.test_architecture_fitness
Ran 79 tests in 83.002s
OK
elapsed=83.17 exit=0

python3 -m unittest discover -s tests -p 'test_*.py' -q
Ran 374 tests in 193.376s
OK
elapsed=193.59 exit=0
```

Migration matching now charges the sum of policy memberships across every root
before constructing match sets and reuses that actual cardinality for later
plan work. The cheap node traversal factor also charges a minimum unit for each
declared node rather than only for the aggregate path total. The production
replacement is line-neutral, exact worktree fitness passes at `10000/10000`,
and no authority, migration, runtime, dependency, or Trust CI source changed.

## Empty migration-selector defense-in-depth rereview

The final security rereview found that schema-valid empty migration
`path_prefixes` could amplify the later per-policy plan loop while contributing
no root membership to the earlier charge. The canonical loader also accepted
that selector even though it cannot govern an artifact.

RED and GREEN evidence:

```text
semantic loader and bypassed-fitness selectors before repair
Ran 2 tests in 0.182s
FAILED (failures=2)
- empty path_prefixes loaded successfully
- bypassed fitness reached repository inventory before its work ceiling

semantic, bypass, shared-root, and prior work-limit selectors after repair
Ran 4 tests in 1.130s
OK

python3 -m unittest -q tests.test_architecture_fitness
Ran 80 tests in 83.882s
OK
elapsed=84.05 exit=0

python3 -m unittest discover -s tests -p 'test_*.py' -q
Ran 376 tests in 195.386s
OK
elapsed=195.62 exit=0
```

Semantic validation now rejects a migration policy without path prefixes.
Fitness independently charges applicable artifacts across every declared policy
before inventory and charges inventory across every policy before semantic plan
traversal, so bypassed validation still fails closed. The product replacement
is net-negative by one line, exact worktree fitness passes at `9999/10000`, and
no schema, authority, migration, runtime, dependency, or Trust CI source was
changed.

## Inventory fanout mutation oracle

The final test review found that the empty-selector regression exhausted the
applicable-artifact fanout before repository inventory, so it could not detect
removal of the separate inventory-by-policy charge. The strengthened case keeps
one applicable artifact, supplies sixteen inventory entries across 256 bypassed
policies, and forbids plan construction, blob reads, and SQL source analysis.

Mutation-sensitive evidence:

```text
inventory multiplier temporarily removed
Ran 1 test in 0.179s
FAILED: plan after inventory limit

production restored byte-for-byte
Ran 1 test in 0.177s
OK

focused semantic and migration-limit matrix
Ran 4 tests in 1.076s
OK

python3 -m unittest -q tests.test_architecture_model tests.test_architecture_fitness
Ran 124 tests in 84.660s
OK
elapsed=84.84 exit=0

python3 -m unittest discover -s tests -p 'test_*.py' -q
Ran 376 tests in 192.596s
OK
elapsed=192.84 exit=0
```

This wave changes tests and evidence only: production is identical to
`13022f2b85ea2b5be056ea7c8337780e4bfa3fef`, including the 9,999/10,000
architecture budget and both staged fanout charges.

## Canonical migration version-history repair

The exact data review found that history parsing recognized only phased names,
so it omitted the immutable canonical seeds `001_schema.sql`,
`002_operational_indexes.sql`, and `003_database_roles.sql`. As a result, a
proper mirrored phased version 004 appeared non-contiguous, while a phased
artifact could reuse canonical versions 001–003 without a duplicate finding.

RED and GREEN evidence:

```text
python3 -m unittest \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_canonical_migrations_seed_phased_version_history -v
Ran 1 test in 0.997s
FAILED (failures=4)
- mirrored phased version 004: false non-contiguous finding
- phased versions 001, 002, and 003: absent or incorrect duplicate findings

same selector after repair
Ran 1 test in 1.126s
OK

python3 -m unittest tests.test_architecture_fitness -k migration -v
Ran 11 tests in 6.901s
OK

python3 -m unittest tests.test_architecture_model tests.test_architecture_fitness
Ran 125 tests in 86.041s
OK

python3 -m unittest discover
Ran 377 tests in 194.763s
OK
```

The repair uses an exact closed matcher for the three established canonical
names and feeds those names into the existing logical-version inventory as
legacy history. The expand/migrate/contract parser and SQL safety semantics are
unchanged and continue to apply only to new phased artifacts. Table coverage
proves the mirrored 004 successor passes, each canonical version reuse fails,
and the existing mirror, immutable-history, phase-order, statement, byte,
finding, and aggregate-work tests remain green.

Ruff, configured Bandit, compileall, typed spec 7/7, architecture validate,
drift, deterministic diagram check, README K16, exact-range whitespace, and
protected-path checks pass. Exact worktree fitness passes with code budget
`10000/10000`, migration `not_applicable` evidence for the unchanged real
repository, change separation, and monotonic risk `green -> red`. Changed files
are `architecture_fitness.py`, `test_architecture_fitness.py`, this evidence
ledger, and `decisions.md`; no migration bytes, runtime behavior, dependency,
Trust CI source, or workflow changed. Rollback is a normal revert of this source
commit; rollout is the standard exact-head review and external Trust CI path.
