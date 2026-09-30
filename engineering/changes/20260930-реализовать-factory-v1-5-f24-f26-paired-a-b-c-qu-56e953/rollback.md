# Rollback plan — Реализовать Factory v1.5 F24 F26 paired A/B/C qualification harness: frozen 12-case corpus, Pump Selector fixtures/oracle, behavior impact selector, immutable baseline, thresholds, budgets and deterministic tests

## Trigger conditions

Resource digest instability, false comparative pass, or regression in existing factory tests.

## Application rollback

Revert the additive module, resources and tests. No runtime profile is activated by this change.

## Data recovery / forward-fix

No database mutation or external effect exists. Preserve generated reports as historical failed evidence.

## Verification after rollback

Run the existing factory unit suite and confirm the optional harness import is absent.
