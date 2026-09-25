# Test plan — Reclaim leaked disposable PostgreSQL runs at harness start (issue 128)

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | | |
| P1 | | |

## Automated checks

- Unit:
- Integration:
- Contract:
- E2E:
- Static analysis:

## Manual checks

-

## P0 arms added after the first authoritative gate run

The first `grok_verify --mode pr` on this contour FAILED two checks (`factory-unit`,
`factory-postgres-exit`). Cause: `factory/tests/test_migrations.py` asserted the pre-fix
contract — on a failed binding the harness reports `leaked id=...` and `remove` is **not**
called — so the suite was green precisely because the container was never reclaimed.

| Arm | Pins | Measured |
| --- | --- | --- |
| `test_exit_runner_reclaims_its_own_container_when_binding_fails` (rewritten) | ownership begins at `docker run`: the minted id is reclaimed with `minted=True`, and the suite never runs | was red before this commit (it asserted the opposite), green after |
| `test_exit_runner_container_binding_and_cleanup_are_exact_id_scoped` (updated) | removal argv is `docker rm -f -v <64-hex id>` — `-v` releases the anonymous volume, id-scoping is unchanged | killed when `-v` removed or when a name is used |
| `test_minted_removal_skips_the_binding_check_but_not_the_id_shape_check` (new) | a minted id deletes without re-verifying the label, but a non-64-hex value is refused and no subprocess runs | 2 arms |
| `test_unbound_non_minted_container_is_still_refused` (new) | the pre-existing refusal is intact for non-minted callers | 1 arm |

`tests.test_disposable_exit_reclaim` + `factory.tests.test_migrations`: 49 tests OK; `ruff check tests .grok-stack/adaptive_grok scripts` clean; `git diff --check` clean.
