# Rollback plan — Implement new Factory runtime behavior for bounded pre-model result envelopes and deterministic result-channel sanitization, based on source commit aa53f300d and stacked on PR2c; add the closed schemas, Python feature modules and regression tests, excluding persistence and dispatch from this slice

## Trigger conditions

Secret/ambiguous input is admitted, boundedness regresses, or additive contracts break existing discovery.

## Application rollback

Forward-fix or reviewed revert of the offline modules, schemas and bindings. Never replace absence with raw passthrough.

## Data recovery / forward-fix

No migration or durable state is introduced; no data recovery is needed.

## Verification after rollback

Run focused result suites and full PR verification, confirming channels remain unavailable.
