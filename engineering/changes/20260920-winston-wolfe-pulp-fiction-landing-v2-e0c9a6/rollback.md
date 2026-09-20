# Rollback plan — Winston Wolfe Pulp Fiction landing v2

## Trigger conditions

Missing assets, accidental indexability, actor likeness, invented prices/origin, form/iframe/third-party, skill/showcase/Trust CI drift, verifier red.

## Application rollback

Delete `side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/` and `tests/test_winston_wolfe_seo_landing_v2.py` (plus any optional README bullet) in one revert. No database, no host, no package rebuild.

## Data recovery / forward-fix

Replace a single image family + hashes + HTML references in the same commit when the defect is local.

## Verification after rollback

Path absent, showcase/skill tests pass, `python3 scripts/grok_verify.py --mode pr` green.
