# Rollback plan — offline landing backup/restore boundaries without web-stack fixture coupling

## Trigger conditions

- `python3 -m unittest factory.tests.test_landing_backup -v` regresses to a loader error or any previously
  passing boundary test fails.
- `factory.tests.test_landing_host` stops collecting or any host test changes outcome on a host with the
  pinned deps.
- `python3 scripts/grok_verify.py --mode pr` turns red on the committed tree because of this change
  (fitness, discovery, inventory or lint).

## Application rollback

Single forward-fix step (`maximum_steps: 1`, strategy `forward_fix`): revert the merge commit of this PR.
It restores `test_landing_host.py`, `test_landing_backup.py` and deletes `factory/tests/landing_host_fixture.py`;
no product module, migration, configuration, governance artifact or runtime state is involved, so nothing
else needs unwinding.

## Data recovery / forward-fix

None required. The change writes no persistent data: fixtures use throwaway temporary roots and a throwaway
SQLite store that are removed by `addCleanup`. No cache, queue, external system or released artifact is
affected; the installed L5 release is untouched by this change.

## Verification after rollback

1. `python3 -m unittest factory.tests.test_landing_backup` — back to the pre-change state (loader ImportError
   where the web stack is absent, full run where it exists).
2. `python3 scripts/grok_verify.py --mode pr` green for the reverted tree.
3. Re-record `verification`, `code_review`, `test_review` receipts against the new fingerprint; the revert is
   itself PR-delivered and needs a fresh App-owned exact-head check.
