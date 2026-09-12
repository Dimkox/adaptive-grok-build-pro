# Requirements — Fix Trust CI human approval CLI: approval-create and approval-submit must run from a source checkout on a human-controlled host without importing API, worker, PostgreSQL, or other server-only dependencies; add regression tests and reproducible operator setup documentation without weakening signature verification or exposing private keys

## Acceptance criteria

- [x] Given a source checkout with Python and `cryptography` but without FastAPI,
  psycopg or uvicorn, when the operator invokes `approval-create`, then a mode-0600
  signed envelope is created with the same exact policy/SHA/scope binding as before.
- [x] Given the same checkout without server dependencies, when the operator invokes
  `approval-submit --help`, then argument parsing succeeds without importing server code.
- [x] Existing API approval acceptance, signature rejection, replay protection and
  exact-SHA requeue tests remain green without contract changes.
- [x] The operator documentation shows the source-checkout command and states that
  the key must remain on a human-controlled machine unreadable by agents/services.

## Failure and edge cases

- Missing `cryptography` fails only when a cryptographic human command executes and
  produces an actionable dependency error; help and submit remain stdlib-only.
- An unknown scope, excessive TTL, stale policy, wrong SHA, expired approval,
  tampered signature or replay remains rejected by existing validation.
- No approval is created or submitted during automated verification.

## Non-functional requirements

- Security: no private-key discovery, logging, copying or server-side signing.
- Reliability: command-specific imports are covered in isolated subprocess tests.
- Performance: human-command startup does not initialize API, worker or database modules.
- Observability: CLI retains explicit non-zero exits and API response/error output.
