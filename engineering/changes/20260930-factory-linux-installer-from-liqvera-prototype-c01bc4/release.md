# Release plan — Factory Linux installer from Liqvera prototype

## Deployment

Deliver this additive source through the isolated installer branch/PR. No live
adapter, host mutation, dependency installation, push/tag/Release is performed.
Contracts and exact provenance: `factory/runtime/SETUP_MANAGER.md`.

## Feature flags / staged rollout

CLI defaults to no runtime adapter. Qualify an explicitly authorized adapter on a
disposable Linux root before separately authorizing host activation. No existing
source ZIP or Factory/L5/Trust-CI configuration is implicitly adopted.

## Metrics and alerts

Observe phase/generation/current/previous/observed running and closed error codes.
Nonterminal journals need reconciliation; integrity, health, schema/backup, and
confirmation failures block effects. Logs have finite limits and redaction.

## Go/no-go criteria

Require focused contracts, full PR preflight, independent code/test review, and
external exact-HEAD Trust CI. Offline tests prove no live/restore acceptance.
Runtime reversal requires checked retained backup and the same schema, never a
down migration. Source rollback removes this additive module.
