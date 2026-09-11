# code_reviewer — M0.2 backup/restore/restart drill (POST-implementation)

Route: `249c12b20197`. Change: `20260824-m0-2-backup-restore-restart-drill-on-claw-d5291e`. Read-only. No secrets. No push/merge/deploy.

**Verdict: pass**

Reviewed commit `92ddbd9f69c5c560f257fd61fa9c902f43f67e50` vs parent `ce03c87b3d9b8767105c01270869e33b50af56df`, plus `evidence/drill-report.md` and `evidence/implementation.md`.

## Checklist

| Gate | Result |
| --- | --- |
| Tracked `trust-ci/compose.yaml` unchanged | **pass** — not in the 28-file commit; `git diff ce03c87..92ddbd9f -- trust-ci/compose.yaml` empty |
| No PEM / DSN / dump bytes in the commit | **pass** — activation report still forbids PEM/JWT/webhook secret; dump only size 26496 and sha256 prefix `c46da2cb9754`; no `postgresql://` / `BEGIN … PRIVATE KEY` in product docs |
| Live volume not restore TARGET | **pass** — drill: throwaway tmpfs `adaptive-trust-ci-restore-throwaway-*`, dbname `trust_ci_restore`, mounts excluded `adaptive-trust-ci_trust-ci-postgres`; `docker rm -f` throwaway only |
| Restore `restored-and-verified` | **pass** — drill-report |
| Restart without `-v` | **pass** — `docker compose --project-name adaptive-trust-ci restart postgres` |
| Jobs 2=2 | **pass** |
| GET `/health/ready` 200 | **pass** |
| No `git push` this slice | **pass** — brief/implementation; origin remains `ce03c87` until a later push |
| `main` unprotected | **pass** — report `main` protected = false; plan still `[ ] **Do not protect main**` |
| M0.2 not claimed complete | **pass** — plan: backup/restore/restart `[x]` with “Not M0.2 complete”; webhook, Ed25519, source-mutation, policy retitle remain open |

## Product delta

- `engineering/runbooks/trust-ci-activation-report.md`: backup cell dated 2026-08-24 pass; Check Run id remains `97390635614`; SHA-change history notes `97406973020` / `ce03c87` in prose only.
- Plan splits backup/restore/restart from source-mutation.
- `decisions.md`: live volume is dump source + restart subject only.
- `trust-ci/tests/test_m0_invariants.py`: when the backup cell is a dated pass, require `2026-` and `pass` (tautological once the `if` matches; still does not weaken PEM / Check Run / local HMAC / no public HTTPS).

## Residual (not fail)

- Backup-cell unit assert does not check CLI names or “throwaway”; those live in the report text and drill evidence.
- Change-package YAML still has template placeholders; workflow paperwork, not a compose/runtime risk.

Independent of the implementer. Do not treat this file as merge authority.
