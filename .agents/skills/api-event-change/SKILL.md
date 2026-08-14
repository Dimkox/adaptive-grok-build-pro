---
name: api-event-change
description: Use when changing REST/HTTP APIs, webhooks, events, queues, schemas, producers, consumers, or event-driven workflows.
---

# API and Event Change

1. Freeze current and proposed contracts.
2. Identify every producer, consumer, adapter, and owner.
3. Classify compatibility and versioning impact.
4. Define validation, authentication, errors, idempotency, retries, duplicate delivery, ordering, correlation, retention, and PII.
5. Use an outbox or equivalent consistency mechanism when transactional state and publication must align.
6. Add contract and replay/retry tests.
7. Plan staged rollout, consumer migration, and deprecation.

Events represent completed business facts, not internal implementation steps. Do not silently change payload meaning under an existing version.
