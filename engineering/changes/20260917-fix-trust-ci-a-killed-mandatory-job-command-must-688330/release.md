# Release plan — interrupted Trust CI commands (#103)

## Deployment

**Source-only. This commit does not change the running Trust CI service.**

- What ships: Python source under `trust-ci/src/adaptive_trust_ci/` (`sandbox.py`, `runner.py`, `api.py`) plus
  tests. No SQL, no migration, no config, no Dockerfile, no compose, no systemd unit, no policy file.
- The deployed worker on the CI host (`claw`) keeps running its current image, so **jobs gated after this
  merge still record `verification-failed` for a kill** until a maintainer rebuilds/relaunches the worker from
  a commit containing this change and restarts the service. That step is outside the pull request's trust
  domain (`AGENTS.md`: repository changes cannot modify deployed Trust CI policy, deployed images or
  PostgreSQL state) and requires its own exact delegated authority.
- Frozen schema respected: `status` is still written from the `001_schema.sql` CHECK list; the new values live
  in the unconstrained `failure_code text` column and as an additive member of `result jsonb`. No SQL file is
  changed by this branch — prove it with `git diff --name-only 2f66ba6 -- '*.sql'` (empty). The tree holds
  exactly three numbered-`.sql` sets, all untouched: the **three** deployment files
  `trust-ci/sql/001_schema.sql`, `002_operational_indexes.sql`, `003_database_roles.sql`; the three packaged
  copies that `test_packaged_migrations_match_deployment_migrations` keeps byte-equal to them; and
  `factory/src/adaptive_factory/resources/` (20 files today, last `020_execution_v2_priced_usage.sql`;
  **18 at tag `v2.0.13`**, last `018_semantic_validation_bridge.sql` —
  `git ls-tree -r --name-only v2.0.13 | grep -c 'factory/src/adaptive_factory/resources/.*\.sql'` → `18`).
  That factory set is what the `"001-018"` string counts, and it appears in `PROJECT_STATE.json`
  (`current_unreleased_change.frozen.postgresql_migrations`, two archived copies,
  `active_delivery.integrated_stack.migrations`), `README.md:32`, `START_HERE.md:57` and `CHANGELOG.md:75`.
  It is **not** in `AGENTS.md` (`grep -c "018" AGENTS.md` → `0`; its data rule at line 130 says only "All
  schema changes use versioned migrations") — an earlier revision of this package attributed it there and was
  corrected after review round 2.
- **No backfill and no rewrite**: the durable record of PR #102 head `123ac93c…` job
  `47d397ab-9b58-463e-a01e-7bdd33897725` stays `failed/verification-failed` exactly as observed. Correcting a
  stored row would be a destructive mutation of the trust record and is deliberately not attempted here; the
  head can be re-gated with a fresh exact-SHA job instead.
- Rollout order: merge to `main` after the App-owned exact-SHA check is green (which will likely also need a
  human-signed `governance` approval because `trust-ci/**` is in that approval-rule glob) → any later,
  separately authorized image rebuild picks the behavior up.

## Feature flags / staged rollout

No flag and no staging is needed: the change only adds cause precision on a path that already ends
non-success. Both new `failure_code` values are strictly more informative than the value they replace, the
`status` vocabulary is unchanged, and an older API client ignores the new `result.abort` member.

## Metrics and alerts

- New operator signal (`SIG-001`): terminal rows per cause become separable —
  `select failure_code, count(*) from trust_ci_jobs where status = 'failed' group by failure_code;` now yields
  `aborted-by-signal`, `aborted-by-timeout` and `verification-failed` apart.
- Recommended operator reading of the new cause, once the image is updated: `aborted-by-signal` means **the
  command reached no verdict**, not "this is not a code problem". Who sent the signal is not in the record
  (the class deliberately never claims it). The next step is to look at `result.abort.signal` together with the
  container/daemon logs and the job duration: a `SIGKILL` from an outside `kill -9` or a host cleanup is an
  infrastructure event to re-gate, while a `SIGKILL` that the kernel delivered because the PR's own tests
  exhausted the sandbox memory (`137` is also how an in-container OOM renders — see `brief.md`) is a defect in
  the pull request that must be fixed, not re-gated away. `aborted-by-timeout` is a capacity or hang question:
  compare the command's `timeout_seconds` in the policy against the stored duration and output tail.
- Unchanged: the Prometheus `adaptive_trust_ci_jobs{status=…}` labels (no new status), the check name and the
  App-owned policy-epoch check.

## Go/no-go criteria

- Go: `make trust-ci-test` green (269 OK, 10 postgres-integration skipped), `ruff check` clean on the six
  changed files, `compileall` clean, root suite green, typed spec `grok_spec.py validate --gate` `ok: true`,
  independent code and test reviews recorded, and the exact-SHA App check green.
- No-go: any diff under `trust-ci/sql/`, `trust-ci/src/adaptive_trust_ci/resources/`, `trust-ci/config/`,
  `trust-ci/systemd/`, `.github/`, or any identity file (`VERSION`, `README.md`, `CHANGELOG.md`,
  `PROJECT_STATE.json`, `START_HERE.md`).
