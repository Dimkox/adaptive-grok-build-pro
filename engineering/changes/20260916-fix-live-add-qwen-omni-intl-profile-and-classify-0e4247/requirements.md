# Requirements — qwen-omni-intl profile and probe classification

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001: profile exists with the international host, pinned model, streaming and the five media classes, and is accepted by every enumeration that gates selection (host config, settings enum, env composition, probe choices).
- [x] AC-002: probe failure output is exactly four keys with an allowlisted category and a bounded http_status, and never contains the credential, exception text or an upstream body.
- [x] AC-003: existing profile digests and the failover order are unchanged; the mainland omni keeps its endpoint.
- [x] AC-004: the international omni capability is evidenced by a live 200 for a real image and a real audio file, with image/audio token accounting and a correct description of each, plus a 401 mainland control with the same key.

## Failure and edge cases

- A provider error without a computed category must still classify safely (`protocol`), never crash and never echo.
- A numeric http_status outside 100..599 is dropped to null rather than passed through.
- An unknown profile name keeps failing as `landing_provider`, so the widened set does not become a free-form selector.

## Governance context

No governance rule or digest is restated; canonical governance JSON stays separately reviewed authority.

## Non-functional requirements

- Security: closed operator output preserved and narrowed to bounded enums; no credential in diffs, logs or evidence.
- Reliability: default-off live execution unchanged.
- Observability: probe output plus the durable observation category.
