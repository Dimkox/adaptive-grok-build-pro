# Release inclusion — 2.1.1

The user explicitly requested issue #229 heartbeat/watchdog in release 2.1.1. This branch is an isolated implementation slice. Final VERSION, package bytes, broad PROJECT_STATE and publication belong to the release coordinator.

Ship CLI, additive state/hooks, installer registration, tests and runbook together. Consumer-local runtime state is excluded. This slice has no host activation or native harness adapter; tests do not prove the external hang cause, maintainer pilot acceptance or operational qualification.

Go criteria: full verifier on actual product inventory, route-selected independent reviews, current fingerprint receipts, external exact-head Trust CI and required approval scopes. Local RED/GREEN does not authorize tagging, publication or merge. Rollback follows rollback.md.
