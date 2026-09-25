# Rollback plan — Reclaim leaked disposable PostgreSQL runs at harness start (issue 128)

## Trigger conditions

- Any , , or a  reason naming a container this repository
  believes it minted: the predicate or the ownership proof is wrong.
- A gate run reports a PostgreSQL connection failure while a sibling contour's harness was reclaimed
  mid-run (the age bound or the nonce exclusion failed).
- CONTAINER ID   IMAGE                COMMAND                  CREATED             STATUS             PORTS                       NAMES
8a4c7c60c98c   postgres:17-alpine   "docker-entrypoint.s…"   5 minutes ago       Up 5 minutes       127.0.0.1:33433->5432/tcp   adaptive-factory-exit-806ac6b7042c
9d25fe816b91   postgres:17-alpine   "docker-entrypoint.s…"   5 minutes ago       Up 5 minutes       127.0.0.1:33432->5432/tcp   adaptive-factory-exit-4de1aec81a16
17f3fba4773e   postgres:17-alpine   "docker-entrypoint.s…"   33 minutes ago      Up 33 minutes      127.0.0.1:33415->5432/tcp   adaptive-factory-exit-9fa62ab18bdf
18caa4c2d12c   postgres:17-alpine   "docker-entrypoint.s…"   About an hour ago   Up About an hour   127.0.0.1:33368->5432/tcp   adaptive-factory-exit-ee2bf93bf79d shrinking across unrelated runs, i.e.
  reclaim deleting more than the orphans it can name.

## Application rollback

Single forward-fixable commit set; reverting the harness file restores the previous behavior with no
migration and no schema, contract or digest change. Reverting the  flag alone is NOT a valid
partial rollback: it re-opens the volume half of the leak this change closes, and anonymous PGDATA
volumes would again accumulate per interrupted run.

## Data recovery / forward-fix

- A mis-reclaimed disposable database is recreateable by re-running the gate (~5–10 min of harness
  time and one fresh cluster). Nothing in the reclaim path can reach a named volume: 
  removes only anonymous volumes associated with the container, and the harness never mounts a named
  one.
- The one unrecoverable shape is a *lookalike*: a hand-started container carrying this label and the
  same image. That is why deletion requires the probe's full identity contract (12-hex run name,
  32-hex nonce) and, on the minted path, a daemon that does not contradict the claim. If such an
  event is ever observed, stop the reclaim call in `main()` (one line) — the harness still removes
  its own container at exit, so the gate loses only the orphan sweep, not cleanup.
- Dangling anonymous volumes not attached to any container are outside this change; they remain the
  residual half of the disk cost and are tracked there, not silently "fixed" by a sweeper here.

## Verification after rollback

1. `python3 -m unittest tests.test_disposable_exit_reclaim factory.tests.test_migrations` green.
2. `python3 scripts/grok_verify.py --mode pr` → `RESULT: PASS` with `factory-postgres-exit` and
   `source-stability` passing.
3. `docker ps -a --filter label=adaptive-factory.disposable-exit --format '{{.Names}}'` before and
   after two consecutive gate runs: the count must not fall by anything other than the containers those
   runs created, and each removal must appear as a `RECLAIM` line in the check output.
