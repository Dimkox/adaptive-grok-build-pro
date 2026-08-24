# architect — BINDING: previous claw ruling stands; close-out only

Route `47da9efaec38`. Read-only except this report. No `.env`, keys, push, merge, deploy, compose-up, or M0.1 runtime.

## Ruling

**Previous claw ruling stands.** Host is `claw` (Xeon E5-2680 v4, ~16 GiB ECC). Never call it a laptop. Publish `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080` with compose project `adaptive-trust-ci`. SearXNG keeps host 8080.

This turn is **close-out only**: independent reviews, commit the already-written host-name slice, update draft PR #5. Do **not** compose-up. Do **not** start M0.1 runtime.

Stuck: product is dirty and uncommitted; PR #5 remains `9f84dfd` draft with stale “not this laptop” body. Write owner = `general_implementer`. Keep draft; no ready/merge/webhook/branch-protect.

In: product files already matching the claw ruling + packages `c8e5e5` and `47da9e`. Out: leftovers `33e0c2`/`9d97f8`/`37bf04`; M0.1 compose-up; M1/M2.
