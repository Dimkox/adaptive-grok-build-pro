# Trust Boundary and Trusted CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent agent-issued privilege escalation and make exact-SHA GitHub CI the authoritative verification path.

**Architecture:** Policy denies control-plane writes and all production/external side effects from Grok. Local approvals become non-authorizing requests, while strict verification runs on GitHub-hosted pull-request jobs and releases require a protected `production` Environment.

**Tech Stack:** Python 3.10+, `unittest`, GitHub Actions, GitHub CLI, existing Adaptive Grok hooks and runtime JSON.

**Spec:** `docs/superpowers/specs/2026-08-23-trust-boundary-design.md`

## Global Constraints

- Package identity remains `2.0.11` in this branch.
- Do not add `pyproject.toml`, `requirements.txt`, or `setup.py`.
- Preserve Python 3.10 compatibility.
- No new runtime Python dependency.
- Production and external writes must have no agent-callable bypass.
- Local verification stays backward compatible unless `--strict` is passed.
- Delivery uses a feature branch and pull request, never a direct push to `main`.

---

### Task 1: Lock the expected trust-boundary behavior with failing tests

**Files:**
- Modify: `tests/test_policy.py`
- Create: `tests/test_approval_requests.py`
- Modify: `tests/test_verification_doctor.py`
- Modify: `tests/test_structure.py`
- Modify: `tests/test_manifest_package.py`
- Create: `.github/workflows/trusted-ci.yml`

**Interfaces:**
- Consumes: existing `evaluate_pre_tool()`, `build_route()`, `set_active_route()`, and `verify()`.
- Produces: executable expectations for `request_approval(root, scope, reason)` and `verify(..., strict=True)`.

- [ ] **Step 1: Replace approval-bypass policy tests**

Assert that `git push`, `gh pr merge`, `docker push`, `npm publish`, and `gh release create` remain denied after `request_approval()`.

- [ ] **Step 2: Add approval-request persistence tests**

The test creates an active route, calls:

```python
request = request_approval(root, 'production', 'release candidate')
```

and asserts:

```python
self.assertEqual(request['status'], 'requested')
self.assertEqual(request['scope'], 'production')
self.assertEqual(request['route_id'], route['route_id'])
self.assertEqual(request['git_head'], git_head(root))
self.assertEqual(request['tree_fingerprint'], tree_fingerprint(root))
```

It also asserts that `.grok-stack/runtime/approvals.json` is not created.

- [ ] **Step 3: Add immutable control-plane tests**

Table-test writes to:

```python
(
    '.grok/hooks/pre_tool_use.py',
    '.grok-stack/adaptive_grok/policy.py',
    '.github/workflows/trusted-ci.yml',
    'AGENTS.md',
    'decisions.md',
    'mistakes.md',
    'scripts/grok_verify.py',
)
```

Every path must be denied. `local/modules/acme.demo/lib/Test.php` must remain allowed.

- [ ] **Step 4: Add strict-verification tests**

Patch `command_exists()` so Ruff, Bandit, or Coverage.py are unavailable and assert:

```python
report = verify(root, 'pr', ['base'], record=False, strict=True)
self.assertEqual(report['status'], 'fail')
self.assertTrue(report['strict'])
```

Run the corresponding non-strict call and assert the missing tool remains `skip`.

- [ ] **Step 5: Replace the no-GitHub-Actions structure contract**

Assert the repository and packaged file list include:

```text
.github/workflows/trusted-ci.yml
.github/workflows/release.yml
.github/CODEOWNERS
docs/TRUST-BOUNDARY.md
```

Remove assertions that workflows are forbidden.

- [ ] **Step 6: Commit tests and open a draft pull request**

Commit message:

```text
test: define trusted CI and immutable control plane
```

Open a draft pull request so the new workflow runs. Record the failing run caused by the missing implementation before starting Task 2.

### Task 2: Convert approvals into non-authorizing requests

**Files:**
- Modify: `.grok-stack/adaptive_grok/state.py`
- Modify: `scripts/grok_approve.py`
- Modify: `.grok-stack/adaptive_grok/deploy.py`
- Modify: `tests/test_deploy.py`

**Interfaces:**
- Produces:

```python
def approval_requests_path(root: Path) -> Path: ...
def request_approval(root: Path, scope: str, reason: str) -> dict[str, Any]: ...
```

- `request_approval()` appends a request under the runtime lock named `approval-requests`.
- `prepare_deploy(root, record=True)` records preparation after evidence/state checks; it does not grant or execute production access.

- [ ] **Step 1: Verify the approval-request tests fail for the expected missing symbol**

Run the targeted tests in trusted CI and confirm failure references `request_approval`.

- [ ] **Step 2: Implement request persistence**

Write an append-only bounded list of the latest 200 records containing id, status, scope, reason, route id, git HEAD, tree fingerprint, and timestamp.

- [ ] **Step 3: Change `grok_approve.py` semantics**

Keep the existing CLI shape. Print JSON containing the request plus:

```json
{
  "authorization": "not-granted",
  "next_step": "Use the protected pull-request or production Environment path."
}
```

- [ ] **Step 4: Remove deploy dependence on local approvals**

Keep deploy preparation and evidence checks. `--record` writes only a `deploy/prepared` receipt.

- [ ] **Step 5: Run targeted approval and deploy tests**

Expected: all approval-request and deploy tests pass.

- [ ] **Step 6: Commit**

Commit message:

```text
security: replace local grants with approval requests
```

### Task 3: Make policy enforcement non-bypassable from agent tools

**Files:**
- Modify: `.grok-stack/adaptive_grok/policy.py`
- Modify: `.grok-stack/config/policy.json`
- Modify: `.grok/hooks/README.md`
- Modify: `tests/test_policy.py`

**Interfaces:**
- Produces:

```python
DEFAULT_PROTECTED = [
    '.git/**',
    '.grok/**',
    '.grok-stack/**',
    '.github/**',
    'AGENTS.md',
    'decisions.md',
    'mistakes.md',
    'scripts/grok_*.py',
    ...
]
```

- `evaluate_pre_tool()` never consults a local approval for protected writes, production invocations, or MCP side effects.

- [ ] **Step 1: Verify immutable-path and post-request denial tests fail**

Confirm the failure is caused by current approval bypasses or missing protected patterns.

- [ ] **Step 2: Hard-deny production invocations**

Return:

```text
Production/publish side effects are not executable from Grok. Use a protected PR or GitHub Environment workflow.
```

- [ ] **Step 3: Hard-deny control-plane writes**

Do not offer `protected-path` approval as a bypass. Preserve the Bitrix `local/` allowance.

- [ ] **Step 4: Hard-deny MCP writes**

Return a message directing the operator to a human-owned integration path.

- [ ] **Step 5: Update policy configuration and hook documentation**

State explicitly that hooks are convenience guardrails and that GitHub branch rules are the authority.

- [ ] **Step 6: Run policy tests**

Expected: all policy tests pass, including wrapped-shell and false-positive cases.

- [ ] **Step 7: Commit**

Commit message:

```text
security: make control-plane and side-effect policy immutable
```

### Task 4: Add strict verification

**Files:**
- Modify: `.grok-stack/adaptive_grok/verification.py`
- Modify: `scripts/grok_verify.py`
- Modify: `tests/test_verification_doctor.py`
- Modify: `README.md`

**Interfaces:**
- Produces:

```python
def verify(
    root: Path,
    mode: str = 'pr',
    profiles: list[str] | None = None,
    record: bool = True,
    strict: bool = False,
) -> dict[str, object]: ...
```

- The report contains `"strict": strict`.
- Missing required tools become `fail` only in strict mode.

- [ ] **Step 1: Verify strict-mode tests fail**

Confirm current `verify()` rejects the `strict` argument.

- [ ] **Step 2: Thread `strict` through Ruff, Bandit, and Python coverage checks**

Use `fail` for a missing required executable in strict mode and preserve `skip` otherwise.

- [ ] **Step 3: Add CLI flag**

Add:

```python
parser.add_argument('--strict', action='store_true')
```

and pass it to `verify()`.

- [ ] **Step 4: Run verification tests**

Expected: strict and non-strict behavior tests pass.

- [ ] **Step 5: Commit**

Commit message:

```text
ci: add fail-closed strict verification mode
```

### Task 5: Add authoritative pull-request CI and protected release workflow

**Files:**
- Create: `.github/workflows/trusted-ci.yml`
- Create: `.github/workflows/release.yml`
- Create: `.github/CODEOWNERS`
- Create: `docs/TRUST-BOUNDARY.md`
- Modify: `AGENTS.md`
- Modify: `decisions.md`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `tests/test_structure.py`
- Modify: `tests/test_manifest_package.py`

**Interfaces:**
- Trusted CI required command:

```bash
python3 scripts/grok_verify.py --mode pr --strict --json
```

- Release required command:

```bash
python3 scripts/grok_verify.py --mode release --strict --json
```

- [ ] **Step 1: Implement trusted CI**

Use read-only permissions, exact event SHA checkout, Python 3.10 and 3.12, and install Ruff, Bandit, and Coverage.py before verification.

- [ ] **Step 2: Implement release workflow**

Use `workflow_dispatch`, `ref == main`, `environment: production`, `contents: write`, version/tag guards, strict verification, packaging, annotated tag, and `gh release create`.

- [ ] **Step 3: Add CODEOWNERS**

Assign `.github/`, `.grok/`, `.grok-stack/`, governance documents, `scripts/grok_*.py`, and trust-related tests to `@Dimkox`.

- [ ] **Step 4: Add operator documentation**

Document exact branch-rule and Environment settings and state that the workflow is not authoritative until those settings are enabled.

- [ ] **Step 5: Remove direct-push release instructions**

Rewrite the standing contract to branch → PR → required checks → human merge → Environment-approved release.

- [ ] **Step 6: Update changelog and product map without bumping VERSION**

Describe the unreleased trust-boundary hardening and keep published identity at `2.0.11`.

- [ ] **Step 7: Run structure and package tests**

Expected: workflows and governance files are present in source and release package; legacy “Actions absent” assertions are gone.

- [ ] **Step 8: Commit**

Commit message:

```text
ci: add protected PR and release workflows
```

### Task 6: Full verification and pull-request completion

**Files:**
- Review all files changed by Tasks 1–5.

**Interfaces:**
- Consumes the exact PR head SHA.
- Produces an auditable pull request with green strict CI or an explicit list of remaining failures.

- [ ] **Step 1: Run the full trusted CI matrix**

Both Python 3.10 and 3.12 jobs must complete with zero failures.

- [ ] **Step 2: Run package construction**

`python3 scripts/package_stack.py` must exit 0 and produce the versioned ZIP and checksum.

- [ ] **Step 3: Inspect the complete PR patch**

Check for accidental version bumps, local secret material, direct-push instructions, approval bypasses, and unrelated files.

- [ ] **Step 4: Re-read the design and verify every invariant**

Map every invariant to code, test, workflow, or documented external setting.

- [ ] **Step 5: Mark the pull request ready for review**

Do not merge it automatically. The repository owner configures branch protection and the `production` Environment before merge.
