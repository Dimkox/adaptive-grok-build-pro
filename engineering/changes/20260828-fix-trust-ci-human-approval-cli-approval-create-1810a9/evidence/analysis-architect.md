# Architecture analysis — human approval CLI startup

Route: `1810a99eee3c`
Role: `architect` (read-only product analysis)
Base: `1c06299894279a88b881defa3f19b004fa742223`

## Verdict

The failure is deterministic and precedes argument parsing or signing. `adaptive_trust_ci.cli` eagerly imports every server command implementation at module import time, so a human workstation cannot even reach `--help`, `approval-create`, or `approval-submit` unless FastAPI, PostgreSQL, worker, backup, and GitHub-side dependencies are all importable.

The smallest safe repair is command-local lazy imports in `cli.py`, plus an isolated import-boundary regression test and a source-checkout operator recipe. Do not change the approval envelope, signature algorithm, policy digest calculation, `POST /approvals`, trust store, database schema, required scopes, or deployed policy.

## Root-cause evidence

Reproduction from this clean source worktree:

```text
$ PYTHONPATH=trust-ci/src python3 -m adaptive_trust_ci.cli --help
Traceback (most recent call last):
  ...
  File "trust-ci/src/adaptive_trust_ci/cli.py", line 11, in <module>
    from .api import create_app
  File "trust-ci/src/adaptive_trust_ci/api.py", line 6, in <module>
    from fastapi import Depends, FastAPI, Header, HTTPException, Request
ModuleNotFoundError: No module named 'fastapi'
```

`git blame` shows that the eager `.api`, `.settings`, `.store`, and `.worker` imports entered with the original operational/human CLI commit `59e50cd3`; later commits added backup, migrations, GitHub App, and holdout imports to the same startup fan-out. Thus the first incorrect state is the CLI module boundary, not the Ed25519 signer, policy binding, approval API, PostgreSQL requeue, or current M3 signature.

The safe approval-side dependency chain is already isolated in the source:

```text
approval-create -> policy + models + signing -> stdlib + cryptography
approval-submit -> pathlib + urllib (stdlib only)
```

`policy.py` and `models.py` do not import API/worker/store/PostgreSQL code. `signing.py` imports `cryptography` and `models`, which is appropriate on the human-controlled signing host.

## Smallest safe implementation

Keep only standard-library imports at `cli.py` module scope: `argparse`, `json`, `os`, `sys`, `urllib`, and `Path`. Import project/server modules inside the command branch that actually uses them.

Required command boundaries:

| Command family | Imports allowed after dispatch |
| --- | --- |
| `approval-create` | `Policy`, `ApprovalPayload`, `Signer`, `sign_approval` |
| `approval-submit` | No adaptive server module; stdlib `urllib` only |
| `approval-verify`, `attestation-verify`, `keygen`, `trust-store-validate` | Local models/signing/policy primitives as required |
| `api` | `uvicorn`, `create_app`, `ApiSettings` |
| `worker` | `Worker`, `install_signal_handlers`, `WorkerSettings` |
| migrations/database/backup/doctor | PostgreSQL, backup, settings, and server operations only in their own branches/helpers |
| GitHub/holdout/branch protection | Their adapters only in the selected branch |

Two implementation shapes are possible:

1. **Recommended: local imports in the existing branches and `_doctor()`.** This is the minimum diff, preserves every CLI spelling and output, and has no new package/module surface.
2. Split human commands into a new `operator_cli.py` dispatcher. This gives a stronger physical boundary but duplicates parser/dispatch concerns and is unnecessary for this incident.

Do not reclassify packaging dependencies in this hotfix. The source-checkout path can install only the pinned signing dependency and invoke `python -m` with `PYTHONPATH`; changing project extras would also require Dockerfile/install changes and expands rollback risk without fixing the import defect more directly.

## Trust-boundary invariants

- The private Ed25519 key is read only by `Signer.from_private_file()` in `approval-create` on the human-controlled host. It is never passed to `approval-submit`, the API, an agent, a container, logs, or the repository.
- The output remains a newly created JSON envelope with mode `0600`; `_write_new_json()` continues to refuse overwrite.
- The signed payload remains bound to `repository`, PR number, exact base SHA, exact head SHA, canonical deployed-policy digest, scope, actor/key ID, nonce, issue time, and expiry.
- The server remains authoritative: it independently resolves the matching job, verifies key/actor/scope/signature/exact-SHA/policy/TTL, rejects replay, persists the approval, and only then requeues.
- A local CLI success is not merge authority. Only the App-owned exact-policy/exact-SHA Check Run remains authoritative.
- No automated or synthetic human approval is introduced. Tests may use an explicitly ephemeral test signer, as existing signing tests already do; that fixture is not an operational human key and must never target the deployed API.

## API and data contracts

Compatibility classification: internal implementation-only change.

- `POST /approvals` request and response are unchanged.
- `ApprovalPayload` and `ApprovalEnvelope` schema version 1 are unchanged.
- Canonical JSON, Ed25519 signing/verification, policy digest, TTL, replay protection, and error status codes are unchanged.
- No producer/consumer migration is required. The CLI continues to produce the same envelope consumed by the API.
- No SQL, migration, index, durable-state, requeue, or backup change is required.

Adding a public policy-download endpoint is explicitly out of scope. The human should receive an operator-reviewed copy of the deployed policy through an operator-controlled channel and compare the envelope policy digest with `/health/ready`; exposing the complete server policy is neither necessary nor justified by this startup bug.

## Regression test design

Add `trust-ci/tests/test_cli.py` and make the pre-fix tree fail for the observed reason.

P0 import-boundary test:

1. Start a fresh Python subprocess with `trust-ci/src` on `PYTHONPATH`.
2. Install a meta-path guard that fails if any of these are imported: `adaptive_trust_ci.api`, `worker`, `store`, `migrations`, `backup`, `settings`, `github`, `github_app`, `holdout`, or top-level `fastapi`, `uvicorn`, `psycopg`.
3. Import `adaptive_trust_ci.cli` and exercise `--help`. The current tree fails at `.api`; the repaired tree must exit 0.
4. Exercise `approval-submit` against a mocked/local in-process HTTP endpoint with a non-secret fixture envelope and assert the same guard never fires.
5. Exercise `approval-create` with an ephemeral test-only Ed25519 key and a temporary policy, then assert: exit 0, output mode excludes group/world access, envelope parses, exact repository/PR/base/head/scope/policy digest are present, and no forbidden server import occurred.

P1 compatibility tests:

- Existing signing verification tests still accept the created envelope and reject wrong base/head/policy/scope/TTL.
- Existing API approval test still records and requeues only the matching waiting job.
- Existing server commands at least parse; focused API/worker/database suites and full `grok_verify --mode pr` catch missing command-local imports.
- A source-checkout smoke test follows the documented operator command with only pinned `cryptography==46.0.4` present, not FastAPI/psycopg/uvicorn.

The import test must run in a fresh subprocess so earlier test imports cannot hide an eager dependency through `sys.modules`.

## Operator documentation

Document a source-checkout workflow rather than assuming a globally installed `adaptive-trust-ci` executable:

```bash
python3 -m venv .venv-approval
. .venv-approval/bin/activate
python -m pip install 'cryptography==46.0.4'
export PYTHONPATH="$PWD/trust-ci/src"
python -m adaptive_trust_ci.cli approval-create ...
python -m adaptive_trust_ci.cli approval-submit ...
```

The documentation must also state:

- use a reviewed copy of the deployed policy and compare its resulting digest with the server readiness digest;
- inspect the exact PR base/head SHA immediately before signing;
- keep the key outside the checkout and agent environment;
- submit only `approval.json`; delete it after its short TTL if operator policy requires;
- a new commit/base/policy epoch requires a new approval;
- never use `keygen` or an agent to create an operational human approval key as part of this repair.

Do not print or document real paths, key contents, tokens, `.env` values, or trust-store material.

## Rollout and rollback

Rollout is code/docs only: merge through the existing Trust CI gate, then use the reviewed source checkout on the human workstation. No database migration, API contract rollout, server policy mutation, trust-store rotation, or service-state reset is needed. Existing API/worker images may continue running; a later normal image rebuild should run the server command smoke tests because command-local imports also cover those entrypoints.

Bootstrap caveat: this hotfix must not approve itself. A human may use the released full-dependency CLI on a human-controlled workstation, or personally review and run the minimal source repair there, but the agent/server must never receive the private key or manufacture the required approval.

Rollback is one commit revert of CLI/tests/docs. Since no schema, envelope, policy, or durable state changes, rollback requires no data recovery and old envelopes remain verifiable. Roll back if any server command fails to import after its branch is selected or if the output envelope differs from the frozen schema/signature contract.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| A moved import is omitted for a server command | Parser smoke plus focused API/worker/database tests and full verification |
| Lazy imports accidentally alter exception timing | Freeze command exit/output behavior; only dependency loading time may change |
| Test passes because server modules were already loaded | Fresh subprocess plus explicit import guard |
| Docs encourage key exposure | Human-host-only recipe; key outside checkout; envelope-only submission |
| Fix broadens into policy/API/package redesign | Explicit non-goals and unchanged contract assertions |
| Hotfix is treated as authority for its own merge | Existing external exact-SHA App check and human signature remain mandatory |

## Acceptance recommendation

Accept the implementation only when all of the following are evidenced on the final fingerprint:

1. The original `--help` reproduction succeeds without FastAPI/psycopg/uvicorn available.
2. `approval-create` and `approval-submit` pass under the server-import guard.
3. The created envelope verifies through the unchanged signing verifier and remains exact-SHA/policy/scope bound.
4. The unchanged API test proves matching-job requeue and replay rejection.
5. No policy, trust-store, database schema, approval API, protected-branch, or secret file changed.
6. Operator docs are reproducible from a source checkout and contain no real secret material.
