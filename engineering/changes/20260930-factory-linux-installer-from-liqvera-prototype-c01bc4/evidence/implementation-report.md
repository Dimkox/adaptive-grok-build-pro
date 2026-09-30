# Factory installer implementation report

Route `c01bc4b8b498`; sole writer `general_implementer`; isolated branch
`feature/factory-v15-installer`, worktree `.worktrees/v15-installer`.
Initial implementation commit: `4c30bd1ddbcb321cd54a95187129f957553963af`.
The following documentation/default-adapter commit is identified by Git history;
this report deliberately does not embed its own commit identity.

## Delivered source

- `factory/runtime/setup_manager.py`: stdlib ZIP/manifest verifier, Linux preflight,
  UID/private-root confinement, immutable releases, lock/durable state, health-gated
  atomic pointer, status/logs/start/stop, same-schema checked-backup update/reversal,
  interruption reconciliation, preserving removal and exact-target purge confirmation.
- `factory/tests/test_runtime_installer.py`: 31 offline contract tests using real
  filesystem/archive/hash/socket/flock/journal behavior with injected service effects.
- `factory/runtime/SETUP_MANAGER.md`: frozen artifact/state/adapter/CLI contracts,
  provenance, operating limits, supported/unsupported boundaries.
- README and active change-spec/tasks/release/test-plan now reference these paths.

`scripts/install_into.py`, Factory/L5 service and storage implementation, Compose,
Trust CI, runtime credentials and deployment policy were not changed. No live host,
Docker, dependency installation, provider call, push, release, or GitHub Actions.

## Provenance

Owner explicitly authorized transfer from `Dimkox/liqvera` exact commit
`e3df6833e8916d01f55028e63d4db1632a805a75`, independently observed with
`git -C /tmp/liqvera-inspect.ygeanO/repo rev-parse HEAD`. The read-only prototype was
not edited. Selected safety-pattern reference files and captured SHA-256 values:

| Reference | SHA-256 |
| --- | --- |
| `scripts/verify-liqvera-installer.py` | `72e22cda1930d859be8093e3ec875ae5e673c842a41da849644147ae6b9fb207` |
| `installer/lib/runtime.py` | `8ffdc2be7c350fb1d529beeaa9de6326e9942bc9edf520ce194f87372de7a8f4` |
| `installer/lib/lifecycle.py` | `0fb33e0405f02784a871569a785f92e8d7acc2978c2effd400a507ce926d054b` |

`git ls-tree --name-only HEAD` showed no root open-source license. Owner-directed
transfer does not claim upstream open licensing. This is newly written Factory code
adapting safety patterns, without Liqvera service/config/image/migration payload.

## RED/GREEN evidence

1. Before any runtime implementation:
   `python3 -m unittest factory.tests.test_runtime_installer` => RED, 22 failures,
   explicit assertion `Factory setup manager has not been implemented`.
2. First implementation run => 18 passed/4 errors: private-root fixture files
   inherited group-writable modes. Restricting world writes while retaining UID-owned
   `0700` root privacy yielded GREEN, all 22 tests.
3. Added regression probes for foreign occupied roots, extra immutable inventory,
   previous-pointer preservation and interrupted removal => RED, 3 failures/1 error.
   Added preflight ownership check, exact directory inventory, previous preservation,
   and removing/purging journal phases => GREEN, 29 tests.
4. Added runtime-observed status and multiline secret/control probes => RED,
   missing `running` field and leaked PEM-body/control-line content. Implemented
   observed status plus block/control redaction => GREEN, 31 tests.
5. Refactored the missing-adapter sentinel to concrete `UnavailableRuntimeAdapter`;
   existing fail-closed CLI contracts stayed GREEN.

Latest focused command: `python3 -m unittest factory.tests.test_runtime_installer`
=> **31 passed** (3.408 seconds on latest observed run).
`ruff check factory/runtime/setup_manager.py factory/tests/test_runtime_installer.py`
=> **all checks passed**. `bandit -q factory/runtime/setup_manager.py` => exit 0.
`git diff --check` => exit 0.
`python3 scripts/grok_spec.py validate <change>/change-spec.yaml --json` => `ok: true`,
2/2 acceptance criteria and 4/4 total typed criteria mapped.

`taskset -c 0-27 python3 scripts/grok_verify.py --mode pr` was started as an exploratory
full run (tool session `62230`) before final documentation/default-adapter edits.
Its result is not yet available at this report's creation and would be stale for
the final tree. Coordinator must record the eventual result, perform final frozen
verification, and dispatch independent route-selected reviews. No full-suite,
review, merge-eligibility or deployment-completion claim is made here.

## Coverage and outstanding scope

| Requirement | Source status and evidence | External qualification |
| --- | --- | --- |
| Independent archive/manifest pinning; strict extraction | Implemented; tamper/path/link/special/duplicate/extra/missing tests | Trusted release digest distribution remains operator responsibility |
| Read-only host/root/resources/port/capability preflight | Implemented; Linux/resource/port/private-root/missing-capability tests | Live host suitability NOT_RUN |
| Immutable releases; durable lock/journal; atomic health switch | Implemented; real byte/mode/inventory/flock and crash tests | Real filesystem/service-manager qualification NOT_RUN |
| Status, bounded redacted logs, idempotent start/stop | Implemented injected adapter contract; CLI defaults explicitly fail closed | Concrete activated systemd/Docker adapter intentionally absent source, not claimed NOT_RUN |
| Update/reversal backup/schema guard | Implemented exact-binding checked retained backup, same-schema transitions | Snapshot completeness/restore drill NOT_RUN; schema-changing migration/restore intentionally unsupported source |
| Interrupted recovery | Implemented no restart/migration replay; prior/current pointer and removal crash tests | Power-loss durability on actual host NOT_RUN |
| Preserving remove/exact purge token | Implemented retained trees/token generation/inventory tests | Real destructive purge NOT_RUN, not authorized |
| Existing boundaries/source materializer | Additive source; focused scope leaves existing materializer/service/config files unchanged | Full verifier and independent review pending |

## Residual risks and rollout/rollback

The adapter is a trusted boundary: it must honor timeout/byte limits and per-release
service isolation. The manager checks elapsed time after return and cannot cancel
an arbitrary callback. Arbitrary unknown secrets require adapter-side redaction.
Private UID-owned roots exclude hostile same-UID/root processes from the threat
model. Backup hashes prove retained bytes, not application-specific consistency.
Use a local filesystem with atomic rename/flock/fsync semantics. Interrupted purge
requires explicit recovery and never auto-resumes deletion.

Rollout: complete frozen local verification/reviews and external exact-head Trust CI
before PR merge; qualify a separately scoped runtime adapter on disposable roots;
then obtain separate exact host activation authority. Default CLI has no activation
authority. Rollback: remove this additive source module or use exact verified
same-schema reversal with a retained checked backup. Never down-migrate; preserve
persistent trees on ordinary removal and recover an interrupted operation explicitly.
