# Test review — local compose build-without-push smoke

Change: `engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Reviewer: `test_reviewer` (read-only except this report). Route: `d2ba49e0570d`. Write owner: `general_implementer`.  
HEAD: `5915b56db7d6aedcd52a6c023418db84d45dd98f` on `feat/trust-ci-control-plane`.  
Scope: daemon compile / image-smoke slice. Product tests and toolchain files were frozen from the previous docs resume. Did **not** require live PostgreSQL, `compose up`, registry push, or a new characterization test.

**PASS.**

| ID | Required case | Test / evidence | Result |
| --- | --- | --- | --- |
| P1 | Holdout example digest matches example bundle | `trust-ci/tests/test_ops.py::test_example_holdout_digest_matches_example_bundle` | Covered, independently **OK** |
| P1 | Two-file compose build-without-push; inspect `.Id` + JSON RepoDigests; no digest in tracked examples | `evidence/implementation-images.md` + `git diff --stat HEAD` on examples (empty) | Covered |
| P0 | Example `sandbox.image` still placeholder, not a local Id | `policy.example.json` + `test_trust_ci_policy_uses_immutable_sandbox_and_external_status` | Placeholder confirmed; test **OK** |
| P0 | Frozen K16 graph / version identity / optional toolchain catalog | `tests/test_structure.py`, `tests/test_toolchain.py` (docs-resume hunks only vs HEAD) | Independently **OK** |
| P0 | `grok_verify --mode pr` python-unittest + coverage | receipt `d2ba49e0570d/verification.json` | Recorded PASS (166 tests, coverage 75%); receipt already stale after `state.json` |

---

## Verdict

| Gate | Result |
| --- | --- |
| Product-test adequacy for this smoke | **PASS.** No product behavior changed. Existing holdout-digest lock, placeholder-or-digest sandbox check, and frozen docs/toolchain characterizations still hold. |
| Characterization coverage | **PASS.** Architect ruling confirmed: this slice did **not** need a new characterization test. The load-bearing automated lock is the example holdout digest. Build-without-push is ops evidence, not a unit-testable product contract. |
| Verification evidence | **PASS.** Independent focused unittests OK. Recorded `grok_verify --mode pr` PASS on fingerprint `a5465829a5fb4a7ef3b52df058a02f9f9f3b3671ec58cb8c23b4571c1726bdab` (166 OK, coverage 75%). Receipt already `stale` after the verifying→reviewing transition. This report will stale it again. |
| Residual test gaps | Documented below. None is a return-to-implementer item for this smoke. |

Do not return this image-smoke slice to an implementer for missing tests.

This report is local preflight. It is not the App-owned policy-epoch Check Run `adaptive-trust-ci/verified@<policy-sha12>`.

---

## 1. Slice under review

Product files were **frozen**. `git diff --stat HEAD` on the listed freeze set is still the previous independently reviewed docs/toolchain slice (8 files, 347/15):

```text
.grok-stack/config/toolchain.json
QUICKSTART.md
README.md
decisions.md
mistakes.md
tests/test_structure.py
tests/test_toolchain.py
trust-ci/README.md
```

Zero hunks vs HEAD for:

```text
trust-ci/compose.yaml
trust-ci/compose.build.yaml
Makefile
trust-ci/config/policy.example.json
trust-ci/.env.example
trust-ci/env/
trust-ci/config/trust-store.example.json
```

This smoke added tracked **evidence only** (`evidence/implementation-images.md` plus analysis/state paperwork). Leftover untracked `engineering/changes/20260817-вычисти*` remains unstaged.

---

## 2. Frozen test diffs vs HEAD `5915b56` — docs resume, not this smoke

`git diff HEAD -- tests/test_structure.py tests/test_toolchain.py` is exactly the prior K16 / optional-toolchain characterization already reviewed in `evidence/test-review-resume.md`:

- `test_readme_local_stack_graph_is_complete_k10` → `test_readme_stack_graph_is_complete`
- six Trust CI node IDs appended; mermaid edge count is `C(n,2)` not literal `45`
- `test_real_toolchain_json_required_and_optional_sets` requires `docker`/`syft`/`trivy`/`cosign` with `required is False`

No additional hunk from the smoke. `test_trust_ci_policy_uses_immutable_sandbox_and_external_status` was **not** tightened (architect: do not “fix” it this slice).

Independent re-run of the frozen tests: **OK**.

---

## 3. New characterization test — architect said no; confirmed

Architect (`analysis-architect-images.md`):

- fail-closed this turn is `git diff --exit-code` on examples, not a new unittest
- do **not** change `tests/test_*.py` this slice (protected; grant consumed)
- **next** product slice (separate grant) may tighten `test_trust_ci_policy_uses_immutable_sandbox` to **placeholder-only** and assert `.env.example` still has `REPLACE_WITH_` / no `[0-9a-f]{64}`

Task analyst (`analysis-task_analyst-images.md`): characterization tests for `--confirm-push` or placeholder lock = **No** (scope creep). Holdout digest already tested.

This reviewer agrees. Reasons:

1. **No product behavior changed.** AGENTS.md asks for a failing/characterization test *before behavior changes*. A daemon compile with frozen product files has nothing new to lock in unittest.
2. **Build-without-push is not a unit contract.** Test plan P1 already names `evidence/implementation-images.md` plus `git diff --exit-code` on examples. That is the right evidence kind.
3. **Holdout is already locked.** `test_example_holdout_digest_matches_example_bundle` binds `policy.example.json` `holdout.digest` to `bundle_digest(trust-ci/holdout.example)`.
4. **Placeholder-only tightening is a product change.** Doing it now would un-freeze `tests/test_structure.py`, invalidate docs-resume receipts, and need a new protected-path grant. Out of slice.

Missing a *new* test is therefore **not** a fail.

---

## 4. Example `sandbox.image` — still the placeholder

Tracked example (unchanged vs HEAD):

```text
sandbox.image = adaptive-trust-ci-runner@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST
```

`REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST` appears only in `tests/test_structure.py` (the allowed-placeholder branch) and `trust-ci/config/policy.example.json`. Local smoke Ids (`70a80960…`, `bffd013c…`, `900cfaaa…`) and the measured python Hub digest (`a116514e…`) appear **only** in change-package evidence markdown, labeled `local-image-id, not a registry pin` / `local-daemon-descriptor, not a registry pin`. They were **not** copied into `policy.example.json`, `.env.example`, `env/*.example`, `trust-store.example.json`, or tests.

Structure test still allows **either** placeholder **or** a real `@sha256:[0-9a-f]{64}`:

```python
image.endswith("@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST")
or re.search(r"(?:^sha256:|@sha256:)[0-9a-f]{64}$", image)
```

Architect correctly warned: pasting a local Id / leftover RepoDigest into `policy.example.json` would **pass** that test. Confirmed it did **not** happen. `Policy.from_dict` / `_IMAGE_DIGEST_RE` would still **reject** the current example image (placeholder is not 64 hex) — fail-closed for deploying the example unchanged.

`.env.example` image lines remain `REPLACE_WITH_{BASE,POSTGRES,DIND,API,WORKER,RUNNER}_DIGEST`. Independently grepped; no 64-hex substituted.

Focused unittest `test_trust_ci_policy_uses_immutable_sandbox_and_external_status`: **OK**.

---

## 5. Holdout digest test

`OperationsTests.test_example_holdout_digest_matches_example_bundle`:

- loads `trust-ci/config/policy.example.json`
- asserts `holdout.digest == bundle_digest(ROOT / 'trust-ci/holdout.example')`
- asserts `holdout.path == '/etc/adaptive-trust-ci/holdout'`

Current digest: `b78d17006e270cec373aa130d7b0d11de357ffa236297b41075234e6ad7d5db8`.  
That is the **example** bundle hash, not a production `/srv` or `/opt` pin. Those host paths remain absent; production holdout waits.

`bundle_digest` hashes paths + executable bits + content SHA-256. Mutating `holdout.example/validate.py` or changing the example digest would go red.

Independent re-run:

```text
PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest \
  test_ops.OperationsTests.test_example_holdout_digest_matches_example_bundle
Ran 1 test in 0.001s
OK
```

Architect’s dotted `PYTHONPATH=trust-ci/src` + `trust-ci.tests.test_ops` form needs `_support` on `sys.path`; adding `trust-ci/tests` is a command fix, not a product change. The test itself is adequate.

---

## 6. Test plan vs this slice

| Test-plan row | Adequacy for this smoke |
| --- | --- |
| P1 Holdout example digest | Unit test exists, independently green |
| P1 Local two-file build-without-push + inspect Ids + no digest in examples | Evidence file + empty example diff vs HEAD. Not a unittest. Correct. |
| P0 No `.github/workflows/` | `test_no_github_actions_workflow_exists` independently **OK** |
| P0 `grok_verify --mode pr` | Recorded PASS including python-unittest (166) and coverage 75% / `fail_under` 74 |
| P0 Live Postgres / restart drill | Out of this slice; prior `test-review.md` on `2865fdc` remains the live-harness review |
| P1 Source mutation after exit 0 | Prior runner characterization; not this smoke |
| P2 App-owned check / offline attestation | Out of slice |

---

## 7. Independent focused re-runs (all OK)

```text
tests.test_structure.StructureTests.test_readme_stack_graph_is_complete
tests.test_structure.StructureTests.test_version_identity_matches_readme
tests.test_structure.StructureTests.test_trust_ci_policy_uses_immutable_sandbox_and_external_status
tests.test_structure.StructureTests.test_no_github_actions_workflow_exists
tests.test_toolchain.ToolchainTests.test_real_toolchain_json_required_and_optional_sets
test_ops.OperationsTests.test_example_holdout_digest_matches_example_bundle
```

Did **not** re-record `grok_verify` (would rewrite the fingerprint-bound receipt). Did not re-run live Postgres or Docker build.

VERSION remains `2.0.11`. README H1 still matches. Trust CI identity `2.1.0` is a separate sentence (no test collapses them; pre-existing, not this slice).

---

## 8. `grok_verify --mode pr` recorded PASS

Receipt: `.grok-stack/runtime/receipts/d2ba49e0570d/verification.json`

| Field | Value |
| --- | --- |
| status | pass |
| mode | pr |
| profiles | base |
| created_at | 2026-08-23T20:43:39+00:00 |
| tree_fingerprint | `a5465829a5fb4a7ef3b52df058a02f9f9f3b3671ec58cb8c23b4571c1726bdab` |
| stale | **true** (`stale_at` 20:44:06, reason: tree changed after tool use — `state.json` reviewing transition) |

Checks: git-diff-check, secret-scan, contract-structure, sql-safety, ruff, bandit, **python-unittest** `Ran 166 tests in 43.201s OK`, **coverage** TOTAL 75%.

`grok_verify` still discovers only root `tests/`, not `trust-ci/tests`. Pre-existing. The holdout test must be run via the handoff `PYTHONPATH` command (done here).

---

## 9. Surrounding suite (not weakened)

| Test | Still adequate? |
| --- | --- |
| `test_example_holdout_digest_matches_example_bundle` | Yes. Digest unchanged; independently OK. |
| `test_trust_ci_policy_uses_immutable_sandbox_and_external_status` | Yes, still placeholder-or-digest. Placeholder remains. |
| `test_build_override_requires_digest_pinned_python_base` | Yes. Compose/Dockerfiles not edited this slice. |
| `test_readme_stack_graph_is_complete` / version identity / optional toolchain | Frozen docs-resume locks; independently OK. |
| `test_no_github_actions_workflow_exists` | Yes. Independently OK. |
| Runner mutation / live Postgres / restart drill | Not re-run; not required for this smoke. |

No test reintroduces `.github/workflows/` or writes a digest into examples.

---

## 10. Gaps (not fail)

- **Structure sandbox check is not placeholder-only.** A local Id pasted into `policy.example.json` would pass. Architect deferred the tighten to the next product slice. This smoke did not paste one; confirmed by reading the example and grepping smoke Ids.
- **No `.env.example` REPLACE_WITH_ / no-64-hex assert.** Same deferred lock. Manual grep this review: still placeholders.
- **`grok_verify --mode pr` does not discover `trust-ci/tests`.** Pre-existing. Operators keep the handoff unittest on `trust-ci/tests`.
- **Verification receipt is already stale** after `state.json` transition; this report stales it again. Expected.
- Evidence table quotes local `name@sha256:<id>` as inspect JSON (labeled not-a-pin). That is honesty of the smoke dump, not a tracked pin. Product files were not updated. Code-review concern if any; not a missing test.

None of these would let this smoke’s failure modes (digest written to examples, holdout example drift, VERSION bump, K16 graph regress, required scanners) return unnoticed.

---

## Verdict (repeat)

**PASS.** Coverage for the local compose build-without-push smoke is adequate. No new characterization test was required. Example `sandbox.image` is still `adaptive-trust-ci-runner@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST`. Example holdout digest remains test-locked. Frozen docs/toolchain tests are unchanged vs the previous resume and independently green.

Focused tests re-run here (all OK):

```text
tests.test_structure.StructureTests.test_readme_stack_graph_is_complete
tests.test_structure.StructureTests.test_version_identity_matches_readme
tests.test_structure.StructureTests.test_trust_ci_policy_uses_immutable_sandbox_and_external_status
tests.test_structure.StructureTests.test_no_github_actions_workflow_exists
tests.test_toolchain.ToolchainTests.test_real_toolchain_json_required_and_optional_sets
test_ops.OperationsTests.test_example_holdout_digest_matches_example_bundle
```
