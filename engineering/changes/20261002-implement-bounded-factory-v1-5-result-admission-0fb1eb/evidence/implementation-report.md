# PR3b bounded result admission contract/API seam

Write owner: route-selected `integration_implementer`, route `0fb1ebee4b9e`. Candidate started at exact PR233 head `55779432d7ff13cc29a2c2cd9c72d69f5d45dda1`. Source `b0579a390` was inspected but not cherry-picked because it depended on absent persistence methods and regressed PR3a hardening.

## Delivered

- Additive immutable `ResultEnvelopeV2` binds repository, task, run, fence, packet, attempt and source identity while delegating payload semantics to unchanged V1 validation.
- `ResultBroker` optionally emits V2 and retains strict duplicate/nonfinite/secret/content-type/unknown-channel/chunk/pre-copy behavior; all seven inspected channels remain unavailable and non-consuming.
- POST and GET routes implement bounded headers/body/media, bearer scopes, repository/worker/grant identity and response correlation.
- The real `FactoryService` intentionally raises `ResultAdmissionUnavailable` after validation and before store access. The stable result is HTTP 503; no persistence, replay, outbox, dispatch or model side effect exists.
- Canonical JSON Schema and OpenAPI use an external schema reference rather than duplicated embedded definitions; architecture assigns V2 to the proposal broker and HTTP to the local API.

## TDD evidence

Initial `factory.tests.test_result_admission_api` failed to import `ResultEnvelopeV2`. After the first green slice, contract parity failed because the V2 schema was absent. A malformed outer JSON regression then reproduced a generic HTTP 500 before the parser mapping was repaired to bounded 422. All final focused regressions pass.

## Verification

- Full Factory discovery: 845 tests; initial run had exactly three inventory/frozen-predecessor failures, all repaired; conditional environment skips remained expected.
- Focused result/broker/OpenAPI suite: 30 tests pass.
- Root V2 schema binding: 1 pytest passes.
- Architecture validate and exact-base fitness: pass, no findings; existing limits remain unchanged.
- Ruff and `git diff --check`: pass.

The controller still owns full PR verification, independent mutation reviews, final receipts and external delivery.

## Review correction

Test review found surviving mutants for run, packet and lease-owner binding. Checked-in API and direct-service regressions now exercise each mismatch with an exploding store, and direct service admission must itself raise `ResultAdmissionUnavailable`; API routes return the service call directly so a future accidental return cannot be hidden by a redundant endpoint-level 503.

## Residual scope and rollback

There is deliberately no durable admission, idempotent replay, concurrency, outbox, transport or live interception evidence. U4/macOS/Apple work is excluded. Rollback is a reviewed revert of this additive slice; no data recovery is necessary because no writes occur.
