# Trust CI Repository Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add fail-closed immutable repository-specific Trust CI policy profiles while preserving legacy schema-v1 digest and Check Run behavior.

**Architecture:** A server-mounted `PolicyCatalog` owns exact repository-to-effective-`Policy` mappings. The API persists the selected effective digest in the existing job `policy_digest`; the worker resolves the exact `(repository, digest)` before constructing a `JobRunner`, so retries and replays cannot switch profiles.

**Tech Stack:** Python 3.11+, stdlib dataclasses/JSON/SHA-256, FastAPI, PostgreSQL-backed Store interface, `unittest`, Docker-isolated Trust CI runner.

**Spec:** `docs/superpowers/specs/2026-08-29-trust-ci-repository-profiles-design.md`

## Global Constraints

- Keep policy schema version `1`; legacy policy canonical digest and Check Run name must remain bit-for-bit unchanged.
- Do not add or edit SQL migrations; `Job.repository` plus `Job.policy_digest` is the durable profile binding.
- Exact repository matching only: no wildcard, default, aliases, trimming of webhook identity, or case normalization.
- Catalog profile objects contain exactly `repository`, `commands`, and `holdout`; catalog `holdout.host_path` is mandatory, absolute, profile-scoped, and digest-bound. Legacy policies omit it and use `TRUST_CI_HOLDOUT_HOST_PATH`.
- Catalog local and daemon holdout paths must be strict descendants of independently configured trusted roots and share the same relative suffix; reject roots, traversal, outside-root paths, and mismatches before constructing dependencies.
- Catalog mode and legacy `allowed_repositories`/global `commands`/global `holdout` mode are mutually exclusive.
- `status_context`, `pipeline`, checkout/lease/retry/output limits, allowed environment, sandbox, and approval rules remain common in catalog mode.
- Repository commands and holdout definitions are profile-scoped.
- Never read or modify deployed policy, holdout, keys, secrets, GitHub App settings, branch protection, or PostgreSQL state.
- Keep GitHub Actions absent.

## File Structure

- Modify `trust-ci/src/adaptive_trust_ci/policy.py`: immutable `PolicyCatalog`, compatibility parsing, exact current/bound resolution, deterministic catalog diagnostics.
- Modify `trust-ci/src/adaptive_trust_ci/api.py`: catalog loading, repository-profile selection at webhook enqueue, job-bound approval validation, compatible health/metrics fields.
- Modify `trust-ci/src/adaptive_trust_ci/worker.py`: per-job bound resolution and selected-runner construction; terminal failure for unavailable binding.
- Keep `trust-ci/src/adaptive_trust_ci/runner.py` runner-facing `Policy` contract unchanged unless a focused diagnostic helper is required.
- Modify `trust-ci/tests/test_policy.py`, `test_api.py`; create `test_worker.py`; characterize `test_runner.py` only where bound-profile behavior needs direct proof.
- Modify `trust-ci/config/policy.example.json`, `trust-ci/README.md`, root `README.md`, and the active change-package files after behavior is verified.

---

### Task 1: Immutable Policy Catalog and Legacy Compatibility

**Files:**
- Modify: `trust-ci/src/adaptive_trust_ci/policy.py`
- Modify: `trust-ci/tests/test_policy.py`

**Interfaces:**
- Produces: `PolicyCatalog.load(path: Path) -> PolicyCatalog`
- Produces: `PolicyCatalog.from_dict(data: Mapping[str, Any]) -> PolicyCatalog`
- Produces: `PolicyCatalog.from_policy(policy: Policy) -> PolicyCatalog`
- Produces: `PolicyCatalog.resolve_repository(repository: str) -> Policy`
- Produces: `PolicyCatalog.resolve_bound(repository: str, policy_digest: str) -> Policy`
- Produces properties: `digest`, `status_context`, `lease_seconds`, `profile_count`, `mode`, and `profiles`

- [ ] **Step 1: Add failing legacy compatibility and catalog isolation tests**

Add tests that capture the existing digest before introducing the catalog, wrap the same `Policy` with `PolicyCatalog.from_policy`, and assert equal digest/check name. Add `catalog_data()` with two exact repository profiles, distinct command names and holdout digests. Assert exact lookup, case-variant rejection, A-only mutation leaving B's digest stable, common-field mutation rotating both, catalog-order independence, and mixed-form rejection.

```python
legacy = Policy.from_dict(policy_data())
catalog = PolicyCatalog.from_dict(policy_data())
self.assertEqual(catalog.mode, 'legacy')
self.assertEqual(catalog.digest, legacy.digest)
self.assertEqual(catalog.resolve_repository('Dimkox/adaptive-grok-build-pro').check_name, legacy.check_name)

catalog = PolicyCatalog.from_dict(catalog_data())
a = catalog.resolve_repository('Dimkox/adaptive-grok-build-pro')
b = catalog.resolve_repository('Dimkox/ii-tonya-platform')
self.assertNotEqual(a.digest, b.digest)
with self.assertRaisesRegex(PolicyError, 'not configured'):
    catalog.resolve_repository('dimkox/ii-tonya-platform')
```

- [ ] **Step 2: Run focused tests and confirm they fail**

Run: `/tmp/trust-ci-repo-profiles-venv/bin/python -m unittest discover -s trust-ci/tests -p 'test_policy.py' -v`

Expected: import/attribute failures for `PolicyCatalog` and catalog parsing assertions.

- [ ] **Step 3: Implement minimal catalog parsing and resolution**

Retain `Policy.from_dict` unchanged for legacy canonicalization. Parse catalog mode only when `repository_profiles` is present; reject any simultaneous `allowed_repositories`, root `commands`, or root `holdout`. For every profile, synthesize a complete legacy-shaped effective mapping with `allowed_repositories: [repository]`, common fields copied from the root, and profile `commands`/`holdout`, then call `Policy.from_dict`.

```python
@dataclass(frozen=True)
class PolicyCatalog:
    profiles: tuple[Policy, ...]
    digest: str
    status_context: str
    lease_seconds: int
    mode: str

    def resolve_repository(self, repository: str) -> Policy:
        matches = [p for p in self.profiles if p.allows_repository(repository)]
        if len(matches) != 1:
            raise PolicyError(f'repository {repository!r} is not configured')
        return matches[0]

    def resolve_bound(self, repository: str, policy_digest: str) -> Policy:
        profile = self.resolve_repository(repository)
        if profile.digest != require_digest(policy_digest, 'policy_digest'):
            raise PolicyError('job policy binding is not active')
        return profile
```

Legacy mode stores the single existing `Policy` object so its digest remains unchanged. Catalog digest is SHA-256 of canonical `{'schema_version': 1, 'profiles': [{'repository': ..., 'policy_digest': ...}, ...]}` sorted by repository; it is diagnostic only.

- [ ] **Step 4: Run policy tests and full Trust CI unit baseline**

Run:

```bash
/tmp/trust-ci-repo-profiles-venv/bin/python -m unittest discover -s trust-ci/tests -p 'test_policy.py' -v
/tmp/trust-ci-repo-profiles-venv/bin/python -m unittest discover -s trust-ci/tests -p 'test_*.py'
```

Expected: all tests pass; legacy assertions preserve the exact pre-change digest.

- [ ] **Step 5: Commit the catalog slice**

```bash
git add trust-ci/src/adaptive_trust_ci/policy.py trust-ci/tests/test_policy.py
git commit -m "feat: add immutable Trust CI policy catalog"
```

---

### Task 2: Webhook Enqueue and Approval Binding

**Files:**
- Modify: `trust-ci/src/adaptive_trust_ci/api.py`
- Modify: `trust-ci/tests/test_api.py`

**Interfaces:**
- Consumes: `PolicyCatalog.load`, `from_policy`, `resolve_repository`, `resolve_bound`
- Preserves: `create_app(..., policy: Policy | PolicyCatalog | None = None) -> FastAPI`
- Produces: enqueue with selected `Policy.digest` and `Policy.max_attempts`

- [ ] **Step 1: Add failing API profile-selection tests**

Create a two-profile catalog in `ApiTests`, inject it into `create_app`, post one signed webhook for each repository, and assert each persisted job carries its selected digest. Retain the current HTTP 403 test and add a case-variant assertion. Add an approval test where the job-bound profile supplies scopes/TTL. Assert legacy `/health/ready` still reports the original `policy_digest`; catalog mode reports `catalog_digest`, `policy_mode`, and `profile_count` without repository mappings.

```python
tonya_body = self.webhook_body(repository='Dimkox/ii-tonya-platform')
response = client.post('/webhooks/github', content=tonya_body, headers=self.headers(tonya_body))
job = store.get_job(response.json()['job_id'])
self.assertEqual(job.policy_digest, catalog.resolve_repository(job.repository).digest)
```

- [ ] **Step 2: Run focused API tests and confirm failures**

Run: `/tmp/trust-ci-repo-profiles-venv/bin/python -m unittest discover -s trust-ci/tests -p 'test_api.py' -v`

Expected: catalog injection/selection tests fail while existing legacy tests remain characterization coverage.

- [ ] **Step 3: Implement catalog-aware API behavior**

Normalize the injected argument:

```python
if policy is None:
    active_catalog = PolicyCatalog.load(settings.common.policy_path)
elif isinstance(policy, Policy):
    active_catalog = PolicyCatalog.from_policy(policy)
else:
    active_catalog = policy
```

Resolve the exact repository before both cancellation and enqueue. Enqueue with `selected.digest` and `selected.max_attempts`. For approvals, fetch the job, then call `active_catalog.resolve_bound(job.repository, job.policy_digest)` before checking `approval_scopes` and `max_approval_ttl_seconds`; return HTTP 409 when the stored binding is unavailable. Keep signature verification before event parsing/profile lookup.

Health compatibility: legacy mode retains `policy_digest` equal to the existing digest. Catalog mode exposes only low-cardinality `catalog_digest`, `policy_mode`, `profile_count`, common `status_context`, active approval keys, and publisher. Metrics use the catalog diagnostic digest/name and must not add repository labels.

- [ ] **Step 4: Run API and complete Trust CI tests**

Run:

```bash
/tmp/trust-ci-repo-profiles-venv/bin/python -m unittest discover -s trust-ci/tests -p 'test_api.py' -v
/tmp/trust-ci-repo-profiles-venv/bin/python -m unittest discover -s trust-ci/tests -p 'test_*.py'
```

Expected: all pass; duplicate webhook remains one job for the same selected digest.

- [ ] **Step 5: Commit the API slice**

```bash
git add trust-ci/src/adaptive_trust_ci/api.py trust-ci/tests/test_api.py
git commit -m "feat: bind webhooks to repository policy profiles"
```

---

### Task 3: Worker Dispatch by Durable Repository/Digest Binding

**Files:**
- Modify: `trust-ci/src/adaptive_trust_ci/worker.py`
- Create: `trust-ci/tests/test_worker.py`
- Modify if required: `trust-ci/src/adaptive_trust_ci/runner.py`
- Modify if required: `trust-ci/tests/test_runner.py`

**Interfaces:**
- Consumes: `PolicyCatalog.resolve_bound(job.repository, job.policy_digest) -> Policy`
- Produces: `Worker.catalog: PolicyCatalog`
- Produces: `Worker.runner_factory: Callable[[Policy], JobRunner]`
- Preserves: `Worker.run(once: bool = False) -> int`

- [ ] **Step 1: Add failing worker dispatch and stale-binding tests**

Build a fake store that returns one claimed job and records `finish`/`retry`, plus a runner factory that records the selected profile. Assert a job for each repository reaches only its own runner. Mutate/rebuild the catalog so the job digest is stale and assert no runner executes, the job finishes `failed` with `failure_code='policy-binding-unavailable'`, and no retry is scheduled.

```python
worker = Worker(settings, store, catalog, runner_factory, Event())
worker.run(once=True)
self.assertEqual(factory.policies, [catalog.resolve_bound(job.repository, job.policy_digest)])

worker = Worker(settings, store, changed_catalog, factory, Event())
worker.run(once=True)
self.assertEqual(factory.policies, [])
self.assertEqual(store.finished[-1].failure_code, 'policy-binding-unavailable')
```

- [ ] **Step 2: Run focused worker tests and confirm they fail**

Run: `/tmp/trust-ci-repo-profiles-venv/bin/python -m unittest discover -s trust-ci/tests -p 'test_worker.py' -v`

Expected: constructor/dispatch failures because `Worker` still owns one global runner.

- [ ] **Step 3: Implement selected-runner construction**

Load one `PolicyCatalog` in `Worker.build`. Validate every effective profile uses the exact configured immutable runner image; reject the process if any differs. Build shared store/signer/GitHub auth/client once and a closure `runner_factory(policy)` that supplies the selected policy to `JobRunner`.

In `run`, claim with common `catalog.lease_seconds`, resolve the bound profile, and construct the runner only after successful resolution. A `PolicyError` from bound resolution is terminal via `store.finish(..., 'failed', {'expected_policy_digest': ..., 'job_policy_digest': ...}, failure_code='policy-binding-unavailable')`. Other execution exceptions retain existing bounded retry/dead-job behavior using the selected runner.

If publishing a dead job still needs a runner, retain the selected runner in the exception path. Do not create a fallback runner for an unavailable profile and do not access GitHub/checkout commands before resolution.

- [ ] **Step 4: Run worker, runner, and complete Trust CI tests**

Run:

```bash
/tmp/trust-ci-repo-profiles-venv/bin/python -m unittest discover -s trust-ci/tests -p 'test_worker.py' -v
/tmp/trust-ci-repo-profiles-venv/bin/python -m unittest discover -s trust-ci/tests -p 'test_runner.py' -v
/tmp/trust-ci-repo-profiles-venv/bin/python -m unittest discover -s trust-ci/tests -p 'test_*.py'
```

Expected: all pass; selected holdout/command/check/attestation assertions remain green.

- [ ] **Step 5: Commit the worker slice**

```bash
git add trust-ci/src/adaptive_trust_ci/worker.py trust-ci/src/adaptive_trust_ci/runner.py trust-ci/tests/test_worker.py trust-ci/tests/test_runner.py
git commit -m "feat: dispatch Trust CI jobs by bound policy profile"
```

---

### Task 4: Configuration Contract, Documentation, and Final Evidence

**Files:**
- Modify: `trust-ci/config/policy.example.json`
- Modify: `trust-ci/README.md`
- Modify: `README.md`
- Modify: `decisions.md`
- Modify: `engineering/changes/20260829-add-repository-scoped-immutable-policy-profiles-f778c6/tasks.md`
- Modify: `engineering/changes/20260829-add-repository-scoped-immutable-policy-profiles-f778c6/release.md`

**Interfaces:**
- Consumes: final catalog JSON shape and operational behavior from Tasks 1-3.
- Produces: operator-readable legacy-first rollout and coherent rollback instructions.

- [ ] **Step 1: Add the exact catalog example and compatibility documentation**

Update `policy.example.json` to demonstrate two exact repository profiles while keeping immutable sandbox and holdout digests. In `trust-ci/README.md`, document both mutually exclusive schema-v1 modes, API-first/worker-atomic rollout, profile-specific Check Run names, no-fallback behavior, and legacy rollback. Do not include live secrets or claim deployment occurred.

- [ ] **Step 2: Refresh the root README current state and complete stack graph**

Update VERSION/current-state references only as required by the tree. Preserve the AGENTS requirement that every listed core graph node remains connected to every other listed node by a `---` edge. Explain that repository-profile support is code/config capability pending separately approved server policy installation.

- [ ] **Step 3: Record the proven decision and close implementation tasks**

Only after focused tests pass, add at most three sentences to `decisions.md`: exact repository plus effective content digest works because the existing job/store/approval/attestation fields already preserve immutable identity, avoiding a migration. Mark contract, tests, implementation, and documentation tasks complete; leave verification/reviews unchecked until receipts exist.

- [ ] **Step 4: Run plan self-checks and route verification**

Run:

```bash
python3 scripts/grok_spec.py validate --change-id 20260829-add-repository-scoped-immutable-policy-profiles-f778c6
git diff --check
/tmp/trust-ci-repo-profiles-venv/bin/python -m unittest discover -s trust-ci/tests -p 'test_*.py'
python3 scripts/grok_verify.py --mode pr
```

Expected: all commands pass and verification receipt binds the current tree fingerprint. Do not edit any file after recording final verification except through the required review-evidence cycle, which requires rerunning verification.

- [ ] **Step 5: Commit documentation before final receipts**

```bash
git add README.md trust-ci/README.md trust-ci/config/policy.example.json decisions.md engineering/changes/20260829-add-repository-scoped-immutable-policy-profiles-f778c6
git commit -m "docs: document repository-scoped Trust CI rollout"
```

- [ ] **Step 6: Dispatch and record independent route-selected reviews**

Dispatch `code_reviewer` and `test_reviewer` against the same final HEAD. Store reports under the active change evidence directory and record passes using:

```bash
python3 scripts/grok_review.py code_review --status pass --report engineering/changes/20260829-add-repository-scoped-immutable-policy-profiles-f778c6/evidence/code-review.md
python3 scripts/grok_review.py test_review --status pass --report engineering/changes/20260829-add-repository-scoped-immutable-policy-profiles-f778c6/evidence/test-review.md
```

If any reviewer requests a code change, return it to the same `integration_implementer`, then rerun verification and both reviews because all receipts become stale.

- [ ] **Step 7: Finalize branch delivery without deployment**

Run `python3 scripts/grok_status.py`; require zero evidence gaps. Transition the change to `ready`, commit final non-receipt metadata only if the workflow requires it and rerun stale evidence as necessary, push `feat/trust-ci-repository-profiles`, and open a PR to `main`. Wait for the App-owned policy-epoch Trust CI check on the exact PR head SHA. Do not merge, deploy, alter branch protection, or install the new server-side catalog in this task.
