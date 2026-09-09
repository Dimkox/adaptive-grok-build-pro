# Rollback plan — Add default-off live Grok and live Qwen landing executors plus explicit Python/system requirements for the current host configuration; no live API calls in tests; no landing-repo mutation.

## Trigger conditions

Fitness fail, unexpected httpx import in dogfood files, or default server constructing live executors.

## Application rollback

Restore the predecessor tree (`22c70c3` live composer without Grok/Qwen adapters). Default server path does not load the new module.

## Data recovery / forward-fix

No schema or durable data change.

## Verification after rollback

Existing `test_landing_live.py` RecordingExecutor path and default unavailable server tests stay green.
