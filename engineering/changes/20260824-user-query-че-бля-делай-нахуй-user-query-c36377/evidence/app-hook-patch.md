# GitHub App hook PATCH (worker JWT; PEM unread by agent)

| Field | Result |
| --- | --- |
| PATCH `/app/hook/config` | 200 |
| url | `https://claw.taild9f611.ts.net/webhooks/github` |
| content_type | json |
| insecure_ssl | 0 |
| secret_set | true |
| ping delivery `3838809548922028032` | 502 (immediate after PATCH) |
| redeliver ping `3838817352380579840` | **200 OK** duration 0.8s |
| GET `/app` events | `[]` (no REST to subscribe `pull_request`) |
| GET `/app` permissions | checks write, contents read, pull_requests read |

No repository webhook created. PEM and webhook secret were not printed.
