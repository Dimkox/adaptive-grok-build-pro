# Documentation/operator-flow audit — Trust CI human approvals

Route: `1810a99eee3c`
Role: `docs_researcher` (read-only analysis; no production key, approval, API mutation, or product-code edit)
Repository state inspected: route base `1c06299894279a88b881defa3f19b004fa742223`

## Finding

The documented human-approval flow is not executable from the current source checkout on a human-controlled workstation. This is a product/package defect plus a documentation defect, not a signature-verification or Trust CI API failure.

Deterministic reproduction from the repository root on the current host:

```text
$ command -v adaptive-trust-ci
# no output; exit 1

$ PYTHONPATH=trust-ci/src python3 -m adaptive_trust_ci.cli approval-create --help
ModuleNotFoundError: No module named 'fastapi'
# exit 1

$ PYTHONPATH=trust-ci/src python3 -m adaptive_trust_ci.cli approval-submit --help
ModuleNotFoundError: No module named 'fastapi'
# exit 1
```

The environment had `cryptography` available but did not have `fastapi`, `psycopg`, or `uvicorn`. That is a valid minimal human-workstation shape: `approval-create` needs local policy/model/signing code plus Ed25519 support; `approval-submit` needs only the envelope and HTTPS client. Neither operation needs the API server, worker, PostgreSQL, migrations, Docker, or GitHub App code.

## Root cause evidence

1. `trust-ci/src/adaptive_trust_ci/cli.py:11-22` eagerly imports API, backup, migrations, PostgreSQL store, settings, GitHub App, and worker modules before `argparse` selects a command. The first absent server dependency (`fastapi`) prevents even `approval-create --help` and `approval-submit --help`.
2. `trust-ci/pyproject.toml:12-17` puts `fastapi`, `psycopg[binary]`, and `uvicorn` in the same mandatory dependency set as `cryptography`. A normal `pip install ./trust-ci` therefore installs the server/database stack on the human signing workstation even if eager imports are repaired.
3. `trust-ci/README.md:138-146` and `:215-234` invoke a global `adaptive-trust-ci` executable, but the README contains no human-workstation installation or source-checkout invocation step. The only source-checkout `PYTHONPATH` example is for the full test suite at `:254-260`.
4. `trust-ci/README.md:220` names `./policy.downloaded-from-server.json`, but no documentation defines how that exact deployed policy is transferred to the workstation. Repository search found no policy download endpoint or operator transfer runbook. `/health/ready` exposes only the canonical `policy_digest` (`trust-ci/src/adaptive_trust_ci/api.py:55-73`), not the policy document.
5. The docs show only one `governance` approval. The service accepts exactly one scope per envelope (`cli.py:163-184`; `api.py:120-148`), while a PR may require multiple scopes. There is no instruction to create a fresh envelope/output file and submit it once per missing scope.

## Concrete missing or false operator steps

| Current text/behavior | Problem | Required correction |
| --- | --- | --- |
| Bare `adaptive-trust-ci ...` commands | No install step; executable is absent in a clean checkout. | Add a copy/paste human-workstation setup from an exact reviewed checkout/version and an explicit invocation path. |
| Installable package has all server dependencies mandatory | Installing the CLI brings API/PostgreSQL/worker dependencies into the human trust boundary. | Define and document an operator-only dependency/install path. It may include `cryptography`; it must not require or import FastAPI, Psycopg, Uvicorn, API, worker, migrations, backup, Docker, or GitHub App modules for approval commands. Keep server images installing their explicit server dependency set. |
| `policy.downloaded-from-server.json` | Placeholder describes no real transfer mechanism and can tempt use of the untrusted repository example policy. | Document an authenticated, human-owned handoff of the exact deployed policy to a workstation path outside the repository/agent workspace, plus canonical digest comparison with `/health/ready.policy_digest`. Do not expose or copy server keys, trust-store private material, environment files, or database state. |
| Placeholder PR/base/head values only | No reliable step binds the human review to the values that will be signed. | Document how the human obtains and independently checks repository, PR number, exact base SHA, exact head SHA, current policy digest, and missing scopes before signing. A changed base/head/policy requires a new envelope. |
| One `governance` example | Multi-scope gates such as `database` + `governance` remain blocked after only one approval. | State that each scope is a distinct approval: repeat create and submit for every missing scope, using a fresh nonce/approval ID and distinct output file. Never edit or reuse a signed envelope. |
| Output `approval.json` in the current directory | In a source checkout this can place a signed artifact in the repository; the writer also intentionally refuses overwrite (`cli.py:406-417`). | Use an operator-controlled directory outside the checkout, set restrictive permissions/`umask`, and use a scope-specific unique filename. Explain safe deletion/retention according to the operator's audit policy. |
| No response/troubleshooting contract | A nonzero submit currently prints an API body without operator guidance. | Document success JSON (`accepted`, `approval_id`, `scope`, `requeued_jobs`, `status_publisher`) and actionable meanings for HTTP 400/403/404/409/503. Do not advise bypassing policy, trust-store, TTL, or exact-SHA validation. |
| “requeues only the matching exact SHA” with no final check | Operator cannot tell whether all scopes were accepted or the correct App check resumed. | Require post-submit verification that the same durable Check Run on the exact head SHA resumes and is owned by the configured GitHub App. Submission is not equivalent to approval success or merge eligibility. |

## Exact documentation acceptance criteria

The corrected `trust-ci/README.md` (or a directly linked operator runbook) should satisfy all of the following:

1. **Executable setup.** Starting from a clean human-controlled host with Python `>=3.11` and an exact reviewed source checkout, one documented command sequence creates/activates an isolated operator environment and makes the CLI callable. The commands are explicit about the repository-root working directory and are tested verbatim.
2. **Minimal trust boundary.** In that operator environment, `adaptive-trust-ci approval-create --help` and `approval-submit --help` exit `0` while `fastapi`, `psycopg`, and `uvicorn` are not installed. Import tracing or a regression test proves these commands do not import `adaptive_trust_ci.api`, `.worker`, `.store`, `.migrations`, `.backup`, or GitHub App/server settings modules.
3. **Service packaging remains complete.** API/worker/test image installation commands explicitly select the server/test dependency sets they need; the docs do not accidentally turn the operator-minimal package into an under-provisioned server image.
4. **No fictional policy download.** Replace `policy.downloaded-from-server.json` with a named, real handoff procedure owned by a human/operator. Store the copied policy outside the repository and agent workspace. The procedure reveals no private key, `.env`, database credential/state, or trust-store secret.
5. **Policy epoch verification.** Provide a copy/paste way to compute the policy's canonical digest from the explicit copied file and compare it with the HTTPS `/health/ready` `policy_digest` before signing. Raw-file `sha256sum` is insufficient because `Policy` hashes normalized canonical JSON (`policy.py:220-246`). A mismatch must stop the flow.
6. **Exact review context.** The runbook tells the human to independently verify repository, PR number, base SHA, head SHA, required scope(s), current deployed policy digest, and the actual diff. It explicitly says that a new commit, base update, policy/holdout change, or expiry requires fresh approval.
7. **Private-key isolation.** Every signing/keygen example is labeled “run only by the human on the human-controlled workstation.” Private keys and signed envelope files use paths outside the repository/agent workspace and restrictive permissions. The docs never instruct an agent, API container, worker, or CI host to read, generate, copy, or submit the human private key.
8. **One envelope per scope.** Include a multi-scope example or loop-safe manual sequence showing separate create/submit operations for e.g. `database` and `governance`, distinct output files, and no post-signature editing/reuse. Each scope must be covered by the signing key's server-side trust-store authorization.
9. **Submission contract.** Use the externally reachable HTTPS Trust CI base URL (not a repository-local or unauthenticated substitute), explain that the CLI appends `/approvals`, and show the expected accepted response fields. Document 400 = malformed/unconfigured scope, 403 = signature/key/exact fields/policy/TTL failure, 404 = no job for exact SHA, 409 = replay, and 503 = kill switch/control-plane unavailable.
10. **End-state verification.** After all required scopes are accepted, verify on GitHub that the same App-owned policy-epoch Check Run for the exact head SHA resumes. A successful POST alone does not authorize merge; only the exact App-owned successful check can satisfy branch protection.
11. **Regression command.** Add a documented automated check that constructs a disposable environment with only the operator dependency set, runs help/create/submit-path tests without production credentials, and proves the full Trust CI test/install path still works. Test keys must be generated only in a disposable test directory and must never be described as human approvals.
12. **Rollback/troubleshooting.** If the operator CLI release is faulty, the runbook must say to stop signing, retain the failing envelope only according to audit policy, and use the previous reviewed operator CLI version. It must not suggest weakening approval scopes, editing deployed policy/trust store to force acceptance, forging a Check Run, or removing branch protection as a routine repair.

## Recommended operator-flow topology

```text
reviewed source/version
    -> isolated operator CLI (operator dependencies only)
    -> exact deployed policy copied by authenticated human-owned channel
    -> canonical digest equals HTTPS /health/ready.policy_digest
    -> human verifies exact PR/base/head/diff/missing scopes
    -> one freshly signed envelope per scope, outside checkout
    -> POST each envelope to HTTPS /approvals
    -> same exact-SHA App-owned Check Run resumes
    -> branch protection decides merge eligibility
```

## Scope boundary

This audit does not recommend a public policy-document endpoint; an authenticated out-of-band handoff is sufficient if it is concrete and digest-verifiable. It also does not authorize reading/generating a production human key, submitting an approval, modifying deployed policy/trust store, or bypassing the `database`/`governance` scopes. Those invariants must remain unchanged by the fix.
