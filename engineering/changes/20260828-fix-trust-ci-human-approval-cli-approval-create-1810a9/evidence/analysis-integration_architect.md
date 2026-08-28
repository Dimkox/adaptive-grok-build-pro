# Integration contract review — human approval CLI

Route: `1810a99eee3c`
Base commit: `1c06299894279a88b881defa3f19b004fa742223`
Role: `integration_architect` (read-only product review; no operational key, envelope, API mutation, or product-code edit)

## Verdict

The reproduced failure is before signing or HTTP delivery: both
`approval-create --help` and `approval-submit --help` exit `1` because importing
`adaptive_trust_ci.cli` immediately imports FastAPI. The approval producer and
`POST /approvals` consumer otherwise share the same schema-v1 model and signing
implementation. The minimal compatible fix is therefore command-local imports plus
operator/subprocess regression coverage; it must not change the envelope, signature,
endpoint, policy, trust store, database, or requeue semantics.

Reproduction from this checkout:

```text
PYTHONPATH=trust-ci/src python3 -m adaptive_trust_ci.cli approval-create --help
PYTHONPATH=trust-ci/src python3 -m adaptive_trust_ci.cli approval-submit --help
-> ModuleNotFoundError: No module named 'fastapi'
```

## Frozen producer-to-consumer contract

### Producer: `approval-create`

- Inputs remain `--private-key`, `--policy`, `--actor`, `--repository`,
  `--pr-number`, `--base-sha`, `--head-sha`, `--scope`, `--reason`, `--ttl`, and
  `--output` with their current names and meanings.
- The local policy must still authorize the scope and cap the requested TTL.
- The payload remains schema version 1 with exactly these signed fields:
  `schema_version`, `approval_id`, `nonce`, `actor`, `key_id`, `repository`,
  `pr_number`, `base_sha`, `head_sha`, `policy_digest`, `scope`, `reason`,
  `issued_at`, and `expires_at`.
- The envelope remains `{ "payload": <payload>, "signature": <base64> }`.
  Ed25519 still signs `canonical_json(payload.to_dict())`; pretty-printing the
  envelope file therefore does not alter signature semantics.
- Every invocation creates a fresh UUID and strong nonce and writes a new mode-0600
  file with exclusive-create semantics. Existing output files are not overwritten.

The README's current abbreviated binding list should be corrected while documenting
the operator flow: it says `pull_request` but the wire field is `pr_number`, and it
omits signed `schema_version`, `approval_id`, and `reason`.

### Transport producer: `approval-submit`

- The CLI reads the envelope bytes and sends them unchanged with
  `POST <base-url-without-trailing-slash>/approvals`.
- Request headers remain `Content-Type: application/json` and the current human CLI
  user agent. The request timeout remains 30 seconds.
- A 2xx response is printed to stdout and exits `0`; an HTTP error body is printed to
  stderr and exits nonzero. This hotfix should not introduce implicit resubmission.

### Consumer: `POST /approvals`

- No endpoint or authentication-boundary change. Possession of an envelope is not
  authority by itself; the API verifies it against the server-mounted public trust
  store and the durable job.
- Server checks remain: kill switch; parseable envelope; configured scope; an
  existing repository/head job; trusted key; actor and key scope; exact repository,
  PR, base SHA, head SHA and job policy digest; key lifecycle; maximum TTL; issue and
  expiry times; Ed25519 signature; approval-ID/nonce replay.
- Success remains HTTP 200 with `accepted`, `approval_id`, `scope`,
  `requeued_jobs`, and `status_publisher`.
- Existing failure classes remain 400 for malformed/unconfigured scope, 403 for
  failed trust/exact-target/signature/TTL validation, 404 for no job, 409 for replay,
  and 503 for the kill switch. Server/store failures are not to be translated into
  success by the CLI.

Compatibility classification: internal dependency-routing repair, wire-compatible,
no schema or endpoint version change. Server commands may keep their existing
dependencies, but neither human help path nor `approval-submit` may import API,
worker, PostgreSQL, migrations, backup, GitHub App, or cryptography code.
`approval-create` execution may import only the local policy/model/signing chain and
its cryptography dependency.

## Multiple approval scopes

An envelope authorizes exactly one scope. For `database` plus `governance`, the human
must create and submit two independent envelopes with the same reviewed repository,
PR, base/head and policy epoch, but distinct output files, approval IDs and nonces.
The same signed envelope must never be edited into another scope.

The first accepted scope normally changes a `needs_approval` job to `queued` and
returns `requeued_jobs: 1`. A second valid scope submitted while the job is already
queued or running is still stored and can legitimately return `requeued_jobs: 0`;
zero is not rejection. The worker recalculates the full required-scope set before
running checks. If only one scope is present, it returns to `needs_approval` listing
the remainder; when both exact approvals are valid, the same durable Check Run can
continue.

## Retries and error handling

- Do not automatically retry POSTs: a timeout or connection loss after the server
  commits is ambiguous. Reusing an already accepted envelope correctly returns 409
  because its ID/nonce is single-use.
- For 400/403/404, correct the reviewed context or configuration and create a fresh
  envelope only after the cause is understood. For 503, wait for the control plane;
  the request is rejected before approval recording. For 409, treat the envelope as
  previously consumed and verify the exact App-owned check/job state rather than
  manufacturing a replacement blindly.
- Documentation should state that HTTP acceptance is not merge eligibility: the
  operator verifies the App owner, exact head SHA, policy-epoch check name, and final
  check conclusion after all scopes are present.

There is a pre-existing atomicity residual outside this import-boundary hotfix:
PostgreSQL approval insertion and job requeue are separate transactions. If insertion
commits and requeue then fails, replay protection prevents the same envelope from
re-triggering requeue. Do not broaden this repair silently; track a follow-up for an
atomic store operation or an idempotent already-recorded response/requeue design.

There is also a pre-existing availability edge: `api.py` selects a job by
repository/head only even though `lookup.py::get_job_for_exact` exists. Two PR jobs
sharing one head commit can cause a valid older-PR approval to be compared with the
newest job and fail closed, while requeue targets every waiting job for that head.
This does not enable unauthorized execution, but it deserves a separate exact-target
fix and regression rather than being bundled into the CLI import repair.

## Minimal regression set

1. **Import boundary (P0):** in a subprocess whose import guard rejects FastAPI,
   Psycopg, Uvicorn and server modules, assert top-level help,
   `approval-create --help`, and `approval-submit --help` exit `0`. A second guard
   without cryptography should prove help and submit remain stdlib-only.
2. **Create compatibility (P0):** use only an ephemeral test Ed25519 key and temporary
   policy; invoke the real source-checkout CLI, assert exit `0`, new-file mode `0600`,
   all exact payload values and policy digest, fresh ID/nonce, and successful offline
   verification. Also retain rejection tests for unknown scope, excessive TTL, and
   existing output.
3. **Submit contract (P0):** post a non-secret fixture envelope to a loopback stdlib
   HTTP server; assert exact `/approvals` path, method, content type, user agent and
   byte-identical body, plus stdout/exit behavior for 200 and stderr/nonzero behavior
   for an HTTP error. Do not contact the deployed API.
4. **Existing server boundary (P0):** retain API acceptance/requeue, tampering,
   untrusted key/actor/scope, exact repository/PR/base/head/policy, expiry/excessive
   TTL and ID/nonce replay coverage.
5. **Two-scope behavior (P1):** create disposable `database` and `governance`
   envelopes for one waiting test job, submit both, assert both are persisted and
   accepted, allow the documented `requeued_jobs` sequence `1` then `0`, and assert
   the runner proceeds only when both remain valid.
6. **Retry characterization (P1):** submit one fixture twice and assert the first is
   accepted and the second is 409 without duplicate persistence. Characterize a
   post-commit/requeue failure in a separate follow-up before changing idempotency.

## Rollout boundary

The safe rollout is documentation and CLI import routing only, verified from a clean
source checkout with the minimal operator dependency set. Rollback is reverting the
CLI/doc/test commit; approval schema v1 and deployed services require no migration.
The hotfix cannot approve itself, and agents/services must never locate, read, copy,
generate, or submit an operational human private key or approval.
