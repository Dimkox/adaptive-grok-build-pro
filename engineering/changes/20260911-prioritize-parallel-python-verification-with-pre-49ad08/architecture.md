# Bounded design

Use the architect and docs reports under evidence. Add a small helper inside adaptive_grok, already covered by existing ownership, and a closed root .grok-test-runner.json opt-in with schema_version1/workers auto or0..64. The explicit GROK_TEST_WORKERS override has precedence; auto uses available logical CPUs with a28-worker cap. Absent config and override preserves generic behavior; a private child cap prevents recursive pools without activating unconfigured consumer fixtures.

Parallel Core uses only tests, worksteal and the invoking interpreter with exact development tool pins. Keep existing python-unittest and coverage check identities. Both the new path and nested legacy coverage own unique external temporary data; .coveragerc remains unchanged, and its74 threshold is a branch-aware total, not branch-only coverage. Worker crashes, missing contributions, bounded output/timeout and unavailable tooling cannot become successful coverage.

No HTTP/event/data contract, application authority, deployed runner/policy, PostgreSQL harness or protected branch rule changes. New config stays outside installer MANAGED_FILES so consumers opt in deliberately.

## Trust entrypoint and runner tooling

The user's original two-suite recipe is completed by the existing `make trust-ci-test`: the same module exposes a dedicated Trust CLI, resolves worker configuration at repository root, then launches `trust-ci/tests` from `trust-ci/` with only absolute Trust import roots. Positive workers use loadfile; explicit0 uses full unittest discovery. `make test-python` sequences normal verification and Trust even after a first-command failure, aggregating exit status. Factory orchestration is unchanged.

The existing `trust-ci/runner.Dockerfile` gains three missing exact test pins; its stdlib operations test checks them. This is source preparation only. Two cached runner images lack these tools, but neither is asserted to be currently deployed. Deployment remains outside PR authority; the operator must provision a reviewed immutable image and any changed policy epoch before external acceptance. No implicit serial fallback or skipped new tests substitutes for this prerequisite.

## Delivery split after architecture verification

`FIT-TRUST-CI-SEPARATION` rejects a PR combining local implementation with `trust-ci/**` source mutations. Move the three runner package pins and the existing test_ops pin assertion into a separate bootstrap branch/PR; this acceleration branch has no Trust CI source changes. Its Make target still invokes the existing Trust test suite with loadfile. Companion image deployment remains independently operated, and actual signed scopes come from the external exact-head check.
