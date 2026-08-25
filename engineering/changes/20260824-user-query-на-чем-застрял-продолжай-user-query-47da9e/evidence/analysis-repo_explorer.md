# repo_explorer — uncommitted product vs leftovers

HEAD `milestone/m0-live-trust-authority` @ `9f84dfd`. No push.

## Product dirty (exclude leftover 20260817 / 9d97f8 / 37bf04)

Modified: `QUICKSTART.md`, `decisions.md`, `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`, `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`, `engineering/runbooks/trust-ci-activation-report.md`, `engineering/runbooks/trust-ci-rollout.md`, `trust-ci/README.md`, `trust-ci/compose.yaml`, `trust-ci/scripts/smoke.sh`, `trust-ci/tests/test_m0_invariants.py`.

Untracked product/workflow: `engineering/changes/20260824-user-query-какой-нахуй-ноут-ты-работаешь-на-xeon-c8e5e5/`, this package `…-47da9e/`.

Leftovers (ignore): `…-33e0c2/` (20260817), `…-9d97f8/state.json`, `…-37bf04/`.

## Compose + spec

`trust-ci/compose.yaml` line 1 `name: adaptive-trust-ci`; api ports `"127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080"` (in-container still 8080). Spec `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` Host: **claw** (Xeon E5-2680 v4, ~16 GiB ECC); not a laptop; 8080=SearXNG; compose-up needs `migration_or_external_write_approval`. Plan/activation agree. `decisions.md` 2026-08-24 M0 CI host is claw.

Stuck: M0.0 host-name slice is on-disk, not committed; M0.1 compose-up not this turn.
