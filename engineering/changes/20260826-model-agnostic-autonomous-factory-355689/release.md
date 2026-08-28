# Release plan — Model Agnostic Autonomous Factory

## Deployment

Two PR-only stacked source releases: M3 on exact reviewed M2-A, then M4 on reviewed M3. Neither PR installs/activates systemd, invokes providers, deploys the bot, or performs an external write.

## Feature flags / staged rollout

M3 validates source-only governance first. M4 migrates a disposable/staging `factory` schema, starts the API manually on a Unix socket, exercises synthetic intake/claim/reconcile/kill, and remains stopped by default until review. The `baby-bot` adapter/deployment is a separate later slice.

## Metrics and alerts

M3 reports active/expired/conflicting rules and debt. M4 reports queue depth, live reader/writer allocations, reclaims, retries/dead tasks, budget stops, kill state, audit/reconciliation failures, API auth failures, and socket readiness without secret bodies.

## Go/no-go criteria

Go for each stacked PR only with one final verifier, exact route-selected reviews, zero local evidence gaps, clean tree, and the external Trust CI check on exact PR SHA. M4/bot integration is no-go while the exposed Telegram token remains unrotated, Bot API request URLs can be logged, admin-only authorization is unproved, or Unix-socket permission tests fail. Merge/deploy/install/external writes remain separately authorized human operations.
