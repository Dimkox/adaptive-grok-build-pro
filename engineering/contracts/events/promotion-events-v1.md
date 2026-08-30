# Promotion events V1

The machine-readable authority is [`promotion-event-v1.schema.json`](../schemas/promotion-event-v1.schema.json). Events are append-only completed facts ordered by the database-owned `event_sequence`; producers must not change V1 meanings in place.

| Event | Producer | Required meaning |
| --- | --- | --- |
| `promotion.accepted` | promotion API acceptance transaction | The exact signed envelope and exact protected evidence joined and committed. |
| `promotion.rejected` | promotion API rejection-audit transaction | A request was denied with a stable reason code; no promotion authority was created. |
| `promotion.consumed` | deployer consume transaction | The exact tuple was consumed once immediately before production effects. |
| `deployment.completed` / `deployment.failed` / `deployment.reconciled` | deployer reconciliation | Terminal or repaired facts for the unique operation ID. |

Rejected events always have `promotion_id: null` because an unaccepted caller-supplied ID is not authority. They may copy only already-validated bounded identity and digest fields. `details` is exactly `{"http_status": <400..599>}` at the database boundary. Raw request bytes, envelope signatures, bearer tokens, private material and the human `reason` are forbidden in rejection events, logs and metrics.

Acceptance and its accepted event share one transaction. A rejection is stored in its own bounded transaction; failure to store it cannot turn denial into authority and increments the low-cardinality audit-failure signal. Duplicate idempotent retrieval creates no second accepted event. Stable rejection codes are those frozen by the OpenAPI contract.

Retention is at least 400 days and never shorter than the restorable backup horizon. V1 has no delete, truncate, mutation or unconsume interface.
