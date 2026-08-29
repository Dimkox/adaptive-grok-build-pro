# Release plan — Fix Trust CI human approval CLI: approval-create and approval-submit must run from a source checkout on a human-controlled host without importing API, worker, PostgreSQL, or other server-only dependencies; add regression tests and reproducible operator setup documentation without weakening signature verification or exposing private keys

## Deployment

Deliver through a dedicated PR. After merge, an operator uses the documented
minimal-dependency source-checkout invocation on the human-controlled workstation.
Installing the complete service package remains supported but unnecessarily expands
the workstation dependency boundary. No API, worker, database or policy rollout is
required for the CLI-only recovery.

## Feature flags / staged rollout

None. First run `--help`, then create an envelope only after a human reviews the exact
policy and PR SHA context.

## Metrics and alerts

No server metric changes. Operational evidence is the local CLI exit status, API
acceptance response and the existing App-owned Check Run transition.

## Go/no-go criteria

Go only with focused and full tests passing, unchanged contracts/data, independent
reviews and no private-key access by an agent or service.
