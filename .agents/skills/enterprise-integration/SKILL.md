---
name: enterprise-integration
description: Use for 1C, Bitrix24, SAP, ERP, WMS, BI, payment, CRM, or other external-system adapters and synchronization.
---

# Enterprise Integration

Use an anti-corruption layer and canonical internal model. Define:

- external/internal ID mapping;
- authentication and secret ownership;
- request limits, timeouts, retry/backoff, and circuit breaking;
- idempotency and deduplication;
- partial failure and reconciliation;
- DLQ/manual recovery;
- correlation and audit logging without sensitive payload leakage;
- sandbox/fixture strategy;
- production write approval.

Do not infer undocumented external behavior. Do not perform real external writes during development or review.
