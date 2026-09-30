# Rollback plan — Реализовать Factory v1.5 FPF U7 runtime: applicability selector, progressive dependency-complete reader, context budgeter, URI resolver, semantic projection, decision invalidation, adapter, offline snapshots, security boundary, A/B/C evaluation, upgrade fallback and deterministic tests

## Trigger conditions

Semantic regression, boundary failure, incompatible exact profile, missing offline
bytes or failed protected A/B/C criterion.

## Application rollback

Disable the optional profile and select the current qualified native path for the
next attempt; never mutate an in-flight attempt.

## Data recovery / forward-fix

Preserve snapshots, selections, delivery captures and decisions for audit/replay.

## Verification after rollback

Mandatory project rules are current and the selected native profile is qualified.
