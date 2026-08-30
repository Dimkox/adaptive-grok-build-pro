# Code review — production-only human approvals

## Verdict

**FAIL**

Reviewed route `75aa6daa89b1` at HEAD `25a4d65` with tree fingerprint
`483f117dcfa1185e817ef8e584506627786565853debb2988821d65c0a6cc03e`.
The production composition cannot create the protected-branch evidence required
by `POST /promotions`, so the requested end-to-end promotion gate is not
deployable from the shipped entrypoints.

## Areas checked

- Production CLI entrypoints, API construction, settings and Compose wiring.
- HMAC merge ingress, durable merge-fact claiming, GitHub App corroboration,
  exact-commit runner and protected-branch attestation persistence.
- Promotion envelope validation, provenance binding, idempotency/replay and
  consume-once paths.
- Automated-only `approval_rules: []` behavior and preservation of the sole
  `promotion:production` human-signature boundary.
- PostgreSQL migration/API/store composition, observability and rollback docs.
- Surrounding unit/E2E tests for merge provenance, runner and promotion flow.

## Findings

### BLOCKER — merge provenance is implemented only as disconnected library code

Files/lines:

- `trust-ci/src/adaptive_trust_ci/cli.py:187-197`
- `trust-ci/src/adaptive_trust_ci/api.py:53-60,152-170`
- `trust-ci/src/adaptive_trust_ci/settings.py:88-102,137-167,170-205`
- `trust-ci/src/adaptive_trust_ci/worker.py:163-203,218-247,247-281`

The deployed `api` entrypoint calls `create_app(settings)` without a
`protected_ref`. `ApiSettings` has no protected-ref setting, so every genuine
`closed+merged` delivery reaches `ingest_merged_pull_request` with
`protected_ref=None` and is rejected as a misconfigured server before the merge
fact can be persisted.

The deployed `worker` entrypoint similarly calls `Worker.build(...)` with its
default `protected_ref=None` and `supply_chain_verifier=None`. More importantly,
`Worker.run()` only claims legacy PR jobs; it never invokes
`process_next_merge_fact`, has no production `ProtectedBranchJobRequest`
factory, and never runs reconciliation. The tests construct a specially wired
`Worker` and call `process_next_merge_fact` directly, so they prove the isolated
method but not the real process entrypoint.

Impact: no merge fact is accepted by the normal API process; even a manually
inserted fact is never consumed by the normal worker process; therefore no
protected-branch attestation can be recorded and promotion acceptance must
fail provenance matching. AC-002, AC-007 and AC-008 are unmet. This is
fail-closed, so it does not weaken security, but it makes the primary feature
inoperable.

Required repair: add validated immutable protected-ref and supply-chain inputs
to runtime settings/Compose, pass them through both entrypoints, construct the
exact protected-job request from controlled configuration, and schedule merge
fact processing plus bounded reconciliation in the worker loop. Add a
production-composition regression test that starts through `cli.main`/settings
and proves `merged webhook -> durable fact -> worker evidence -> promotion`.

### HIGH — reconciliation can advance past an incomplete GitHub search result

Files/lines:

- `trust-ci/src/adaptive_trust_ci/github_app.py:190-218`
- `trust-ci/src/adaptive_trust_ci/worker.py:87-151`

`GitHubAppClient.list_closed_pulls` extracts only `items` from the Search API
response and discards the `incomplete_results` signal. `MergeReconciler.run`
then treats any short page as a complete interval and advances the durable
watermark per returned candidate. If GitHub reports an incomplete result set,
an omitted merged PR can fall behind the saved watermark and be skipped
permanently.

Impact: after the production wiring is added, a missed webhook can remain
unrepaired despite the claimed bounded reconciliation guarantee, violating the
loss-recovery part of AC-002/AC-007. Fail the reconciliation interval without
advancing its watermark whenever the API marks results incomplete; cover this
with a regression test.

## Verification notes

- `python3 -m py_compile trust-ci/src/adaptive_trust_ci/api.py
  trust-ci/src/adaptive_trust_ci/worker.py`: pass.
- `git diff --check`: pass.
- A focused test invocation from the system Python could not run because that
  interpreter lacks the repository test dependencies (`pytest`, `fastapi`). No
  passing claim is made from that invocation. The code findings above are
  established directly from the shipped runtime call graph.

## Residual risks

- No external policy, branch protection, migration, service, merge or production
  action was performed during this read-only review.
- The review does not approve the tree after fixes. Any product-code change
  requires fresh verification and a fresh independent code review.
- The repository correctly documents that development/PR/merge is signature-free
  under `approval_rules: []` and that exactly one human signature belongs only
  to final production promotion; the failure is operational composition, not a
  reintroduction of intermediate human gates.
