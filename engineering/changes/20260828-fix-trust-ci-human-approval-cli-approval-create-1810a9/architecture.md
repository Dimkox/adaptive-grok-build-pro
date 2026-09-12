# Architecture — Fix Trust CI human approval CLI: approval-create and approval-submit must run from a source checkout on a human-controlled host without importing API, worker, PostgreSQL, or other server-only dependencies; add regression tests and reproducible operator setup documentation without weakening signature verification or exposing private keys

## Current behavior

`adaptive_trust_ci.cli` imports every command implementation at module import time.
Consequently even `approval-create --help` requires FastAPI, psycopg and worker
dependencies. On the current host it fails with `ModuleNotFoundError: fastapi` before
the parser can select the human command.

## Proposed behavior

Keep the public parser and command surface unchanged, but import each implementation
inside its selected command branch. Human commands load only their actual dependencies;
server and database commands continue to load their existing modules on demand.

## Components and boundaries

- `cli.py`: dependency routing only; no validation semantics change.
- `policy.py`, `models.py`, `signing.py`: unchanged source of approval construction and verification.
- `api.py`, `store.py`, migrations: unchanged.
- `trust-ci/README.md`: operator preflight and source-checkout invocation.

## Data flow

Human reviews exact context -> local CLI loads policy and human-owned key -> local
signed JSON envelope -> operator submits envelope -> existing API verifies public-key,
policy/SHA/scope/TTL/replay invariants -> existing store requeues the matching job.

## API and event contracts

No endpoint, request, response, event, authentication, retry, idempotency or ordering
contract changes. `POST /approvals` remains the existing consumer. The signed envelope
schema remains byte-for-byte compatible.

## Bitrix-specific impact

- Modules/events/agents/components affected: none.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: none.
- Core modification: forbidden unless explicitly approved.

## Decisions

- Repair import boundaries rather than installing the server stack on the human host.
- Preserve the full policy document requirement; signing only a digest without review
  would weaken the human approval model.
- Do not create, locate or submit any production approval in agent-controlled tests.

## Risks and mitigations

- Missed command dependency: run every CLI help path plus focused command tests.
- Circular/local import regression: keep imports at branch entry and run the full suite.
- Security-boundary regression: unchanged signing/API tests and independent review.
- Existing approval-record/requeue transaction and same-head lookup races are documented
  in the data/integration evidence. They are not the observed startup failure and require
  a separate atomicity hardening change rather than being mixed into this CLI hotfix.
