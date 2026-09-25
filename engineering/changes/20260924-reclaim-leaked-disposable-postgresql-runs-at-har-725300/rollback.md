# Rollback plan — Reclaim leaked disposable PostgreSQL runs at harness start (issue 128)

## Trigger conditions

- Any `RECLAIM refused` or `RECLAIM leaked` line, or a `skipped` reason naming a container this
  repository believes it minted: the predicate or the ownership proof is wrong.
- A gate run reporting a PostgreSQL connection failure while a sibling contour's harness container was
  reclaimed mid-run: the age bound or the nonce exclusion failed.
- The labelled container set shrinking across unrelated runs, i.e. reclaim deleting more than the
  orphans it can name.

## Application rollback

One forward-fixable commit set. Reverting the harness file restores prior behavior with no migration
and no schema, contract or digest change. Reverting the `-v` flag alone is NOT a valid partial
rollback: it re-opens the volume half of the leak this change closes, because anonymous PGDATA
volumes would again accumulate one per interrupted run.

## Data recovery / forward-fix

- A mis-reclaimed disposable database is recreateable by re-running the gate (roughly 5-10 minutes of
  harness time and one fresh cluster). Nothing in the reclaim path can reach a named volume: docker
  removes only anonymous volumes associated with the container, and this harness never mounts a named
  one.
- The one unrecoverable shape is a lookalike: a hand-started container carrying this label and the same
  image. That is why deletion requires the probe's full identity contract (a 12-hex run name and a
  32-hex nonce) and, on the minted path, a daemon that does not contradict the claim. If such an event
  is ever observed, stop the reclaim call in `main()` — a one-line change. The harness still removes
  its own container at exit, so the gate loses only the orphan sweep, not cleanup.
- Dangling anonymous volumes attached to no container are outside this change. They remain the
  residual half of the disk cost and are tracked there rather than silently "fixed" by a sweeper here.

## Verification after rollback

1. `python3 -m unittest tests.test_disposable_exit_reclaim factory.tests.test_migrations` green.
2. `python3 scripts/grok_verify.py --mode pr` reports `RESULT: PASS` with `factory-postgres-exit` and
   `source-stability` passing.
3. Compare `docker ps -a --filter label=adaptive-factory.disposable-exit --format "{{.Names}}"` before
   and after two consecutive gate runs: the set must not lose anything other than the containers those
   runs created, and every removal must appear as a `RECLAIM` line in the check output.
