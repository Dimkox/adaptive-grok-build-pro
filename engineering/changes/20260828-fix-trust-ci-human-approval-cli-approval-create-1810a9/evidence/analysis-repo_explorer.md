# Repository analysis — human approval CLI source-checkout failure

Route `1810a99eee3c`; role `repo_explorer`; analysis only. No product code, deployed service, policy, trust store, database, approval envelope, or private key was read or changed.

## Finding

**Confirmed root cause:** `adaptive_trust_ci.cli` is an aggregate server/operator module. Lines 11–22 import API, backup, GitHub, holdout, migration, settings, store, and worker components unconditionally before `argparse` can select `approval-create` or `approval-submit`. The first import, `.api`, immediately imports `fastapi`; therefore a human host with the intended cryptographic dependency but without the server stack cannot even display either approval command's help.

This is a pre-dispatch import-boundary defect, not a signing, signature-verification, HTTP, PostgreSQL, or Trust CI job-state defect. `git blame` traces the eager `.api`, `.store`, and `.worker` imports to the original human CLI commit `59e50cd3` (`trust-ci: add operational and human approval CLI`, 2026-08-23); later operational commands widened the same aggregate import surface.

There is a second operator-path gap: `trust-ci/README.md:215-234` invokes an installed `adaptive-trust-ci` executable but documents no source-checkout setup. On this host `command -v adaptive-trust-ci` returns no path. Thus the documented command is unavailable, while the natural source fallback is deterministically broken by the eager FastAPI import.

## Deterministic reproduction

Host dependency state was inspected by module availability only; no environment or credential file was read:

```text
cryptography: available
fastapi: missing
psycopg: missing
uvicorn: missing
adaptive-trust-ci executable: absent
Python 3.12.3
```

Both operator commands fail before argument parsing:

```bash
PYTHONPATH=trust-ci/src python3 -m adaptive_trust_ci.cli approval-submit --help
PYTHONPATH=trust-ci/src python3 -m adaptive_trust_ci.cli approval-create --help
```

Both exit `1` with the same traceback:

```text
adaptive_trust_ci/cli.py:11  from .api import create_app
adaptive_trust_ci/api.py:6  from fastapi import ...
ModuleNotFoundError: No module named 'fastapi'
```

The required dependency slices themselves load successfully on this host:

```bash
PYTHONPATH=trust-ci/src python3 - <<'PY'
from adaptive_trust_ci.models import ApprovalPayload
from adaptive_trust_ci.policy import Policy
from adaptive_trust_ci.signing import Signer, sign_approval
print('approval-create dependency slice imports: PASS')
PY
```

Result: `PASS`, with none of `adaptive_trust_ci.api`, `adaptive_trust_ci.worker`, `adaptive_trust_ci.store`, `adaptive_trust_ci.migrations`, `fastapi`, `psycopg`, or `uvicorn` present in `sys.modules`. `approval-submit` uses only `argparse`, `pathlib`, `urllib`, `sys`, and the JSON envelope bytes.

## Exact source map

| Location | Current behavior | Relevance |
| --- | --- | --- |
| `trust-ci/src/adaptive_trust_ci/cli.py:11-22` | Imports all operator and server components at module import time. | Root cause. |
| `trust-ci/src/adaptive_trust_ci/api.py:6-7` | Imports FastAPI eagerly. | First observed failure on the human host. |
| `trust-ci/src/adaptive_trust_ci/cli.py:163-185` | Creates the exact-SHA payload and signs it. | Needs only `Policy`, `ApprovalPayload`, `Signer`, and `sign_approval`. |
| `trust-ci/src/adaptive_trust_ci/cli.py:204-219` | Posts the existing envelope bytes to `/approvals`. | Needs no Trust CI server module and no cryptography. |
| `trust-ci/src/adaptive_trust_ci/store.py:273-285` | Defines `PostgresStore`; imports `psycopg` only when connecting. | Not needed by either human command; must remain outside their import path. |
| `trust-ci/pyproject.toml:12-17` | Full service distribution depends on cryptography, FastAPI, psycopg, and uvicorn. | Do not use `pip install .` as the lightweight source-checkout setup. |
| `trust-ci/README.md:215-234` | Assumes the console script already exists. | Reproducible human-host setup is missing. |

## Minimal compatible repair

Keep `cli.py` as the public entry point and move product imports to the command branches that consume them. This is smaller and safer than changing packaging, creating a second distribution, changing the entry point, or altering approval semantics.

Required command-local import ownership:

| Command/helper | Imports it alone should own |
| --- | --- |
| `api` | `uvicorn`, `create_app`, `ApiSettings` |
| `worker` | `Worker`, `install_signal_handlers`, `WorkerSettings` |
| `migrate`, `migration-status` | `CommonSettings`, `PostgresMigrator` |
| `policy-digest` | `CommonSettings`, `Policy` |
| `holdout-digest` | `bundle_digest` |
| `keygen` | `Signer` |
| `trust-store-validate` | `TrustStore`, `utc_now` |
| `approval-create` | `ApprovalPayload`, `Policy`, `Signer`, `sign_approval` |
| `approval-verify` | `ApprovalEnvelope`, `Policy`, `TrustStore`, `verify_approval`, `utc_now` |
| `approval-submit` | no package-local imports; standard library only |
| `attestation-verify` | `AttestationEnvelope`, `verify_attestation` |
| `branch-protect` | `GitHubClient`, `Policy` |
| backup/restore branches | the selected backup function and `CommonSettings` only where used |
| `kill-switch` | `CommonSettings`, `utc_now` |
| `_doctor` | all server/holdout/database/signing imports inside `_doctor`, because it intentionally validates the server contour |

Do **not** solve this by installing FastAPI/PostgreSQL on the human workstation: that masks the import-boundary bug and preserves unnecessary server code execution in the private-key process. Do not split the existing mandatory dependencies in `pyproject.toml` in this hotfix; API and worker Dockerfiles currently use `pip install .`, so a dependency split expands deployment scope. For the explicitly requested source-checkout path, document a dedicated venv outside the repository with pinned `cryptography==46.0.4`, then run:

```bash
PYTHONPATH="$CHECKOUT/trust-ci/src" "$OPERATOR_VENV/bin/python" -m adaptive_trust_ci.cli approval-create ...
PYTHONPATH="$CHECKOUT/trust-ci/src" "$OPERATOR_VENV/bin/python" -m adaptive_trust_ci.cli approval-submit ...
```

The documentation must state that the real human private key remains outside the checkout and is never copied into the venv, service containers, agent workspace, or repository. The policy argument must be an operator-reviewed copy of the deployed policy; its digest should be checked against `/health/ready` before signing. No new public policy endpoint is needed for this repair.

## Fail-first regression tests

Add `trust-ci/tests/test_cli.py` and make the tests launch a fresh Python subprocess from the source checkout. A subprocess is important: importing `cli` in the test runner can hide an eager-import regression through `sys.modules` or because the full test image has FastAPI installed.

1. Create a temporary `sitecustomize.py` import guard that raises on `adaptive_trust_ci.api`, `.worker`, `.store`, `.migrations`, `fastapi`, `psycopg`, and `uvicorn` (optionally all other server-only package modules). Prepend the guard directory and `trust-ci/src` to `PYTHONPATH`.
2. `approval-create` end to end: generate an **ephemeral test-only** Ed25519 key, write a temporary fixture policy, invoke the subprocess with exact test SHAs/scope, assert exit `0`, output mode `0600`, parse the envelope, and verify it with the test public key and policy digest. This fails on the current tree at `fastapi` and proves signing semantics remain intact after the repair.
3. `approval-submit` end to end: serve a loopback-only standard-library `HTTPServer`, invoke the guarded subprocess, and assert `POST /approvals`, `Content-Type: application/json`, exact envelope bytes, successful response, and exit `0`. This fails on the current tree at `fastapi` and proves no FastAPI client/server dependency is used.
4. Keep existing `test_signing.py` tamper, exact base/head/policy, TTL, actor, scope, and replay tests, plus `test_api.py::test_signed_approval_requeues_matching_waiting_job`, as the unchanged trust-boundary regression set.
5. Run the full Trust CI suite and route-selected verification; server command smoke/import coverage is required because every previous top-level import will move to an execution branch.

Testing only `--help` is insufficient for final evidence: it proves import isolation but not envelope generation or HTTP submission. The actual-command subprocess tests provide both.

## API, event, and data impact

- **HTTP contract:** none. `POST /approvals`, request bytes, `Content-Type`, user agent, response/error handling remain unchanged.
- **Envelope contract:** none. `ApprovalPayload` fields, canonical JSON, Ed25519 signature, TTL, scope, exact repository/PR/base/head SHA, and policy digest remain unchanged.
- **Server authorization:** none. `api.py:111-143` continues to load the server trust store, verify the exact job identity/policy/signature, reject replay, persist the approval, and requeue only the matching job.
- **Database:** none. No schema, migration, query, index, lock, backfill, row semantics, or PostgreSQL deployment change is needed.
- **Trust boundary:** improved by reducing the code imported into the human private-key process. The API retains public keys only; the human private key remains human-host-only.
- **Rollout:** source-only CLI fix plus docs/tests. Existing API/worker images need no live mutation to validate the operator CLI; deployment of a new service image follows the normal separate Trust CI policy-epoch process if/when server code is upgraded.
- **Rollback:** revert the lazy-import/docs/tests commit. No data recovery or API consumer migration is required.

## Adjacent risk, explicitly out of scope

The README names `policy.downloaded-from-server.json` but does not define a retrieval channel. The API exposes the authoritative digest through `/health/ready`, not the policy document. The hotfix documentation should require a human/operator-controlled reviewed copy and digest comparison; adding a policy-download endpoint would be a separate security-reviewed API feature, not part of this minimal CLI repair.
