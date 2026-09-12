# Separate runner-tooling bootstrap: source boundary and evidence reuse

2026-09-11. Read-only assessment of the priority worktree at base `64378d28c7b78cace463d96470c1898294b8f196`. No tests, image builds, product edits or deployed-state reads; this report is outside the repository.

## Exact cause and correct split

`architecture/rules.yaml:21` declares `FIT-TRUST-CI-SEPARATION` with severity error. `_change_separation` in `.grok-stack/adaptive_grok/architecture_fitness.py:1347` fails whenever the **same architecture diff** includes both an implementation path and a Trust CI path. `_matches` (`:161`) matches an exact prefix or `prefix + '/'`; the rule has no exception for small changes, Dockerfile dependency pins or tests. `tests/test_architecture_fitness.py:3343` explicitly covers mixed implementation/Trust CI rejection.

Implementation prefixes: `.grok`, `.grok-stack`, `architecture`, `delivery`, `engineering/contracts`, `factory`, `governance`, `pilot`, `schemas`, `scripts`. Trust CI prefix: `trust-ci`.

Separate commits in one PR do not solve this; the evaluated diff still includes both sides. Do not edit the guard, severity or prefixes, supply a fabricated narrowed changed-path list, or suppress the failed result. `architecture_fitness.py:2340` also requires caller-supplied changed paths to equal the derived diff exactly.

Recommended bootstrap product diff:

```text
trust-ci/runner.Dockerfile
trust-ci/tests/test_ops.py
```

Keep exact pytest 9.1.1 / pytest-xdist 3.8.0 / pytest-cov 7.1.0 pins inline in that Dockerfile; coverage 7.15.4 and all previous image configuration remain. The current test_ops change uses literal pin assertions and needs no file from the acceleration implementation.

**Do not copy `.grok-stack/config/python-test-requirements.txt` into the bootstrap PR**: even that dependency-only file is inside an implementation prefix and would recreate the failure. The scoped requirements, runner module, verifier changes, root opt-in and parallel integration tests belong to the acceleration PR. That PR must have no `trust-ci/**` delta against its final reviewed base.

Normal bootstrap evidence under its new `engineering/changes/<id>/` is outside the rule's `engineering/contracts` prefix. README or a runbook may document source preparation if useful; no unrelated current-state rewrite is needed. Absence of a separation violation does not exempt those documents from other checks.

## New route and independent review

Create an isolated bootstrap branch/worktree from its intended trusted main base and a new route/change identity describing only the runner recipe dependency preparation and pin invariant. At analysis time no bootstrap route exists, so its actual quality profiles and required evidence remain to be read from the new route, not guessed or copied from `49ad08e34053`.

The explicit user exception recorded in the priority package authorizes root as sole writer and the available architect/docs_researcher agents as independent code/test reviewers; splitting this necessary delivery prerequisite does not require asking again for that capacity exception. Carry its exact scope/provenance into the bootstrap package. Do not represent unavailable agents as having run. If the new route names additional evidence kinds, account for those explicitly within the authorized independent-review arrangement; do not silently discard them.

The same two independent agents can review the bootstrap. They must inspect its actual extracted diff, surrounding Dockerfile/build-context/test behavior and new verification report. No product author may approve their own work. A previous analysis is reusable context, not a new independent approval.

`receipts.py:528` binds a receipt to route ID, tree fingerprint, spec and architecture/governance bindings; `missing_evidence` rejects stale tree/bindings. Therefore:

- Official dependency compatibility research and unchanged public source facts may be cited/reused with their provenance.
- Existing passing test-lane logs remain historical observations of the mixed tree; root reports 641 tests/coverage/Factory PostgreSQL passed, but the aggregate verifier failed architecture separation. Do not relabel that aggregate pass.
- New bootstrap and revised acceleration trees need fresh applicable verification and review receipts. Reusing agents is permitted; copying old receipt JSON is not.
- When bootstrap merges or either PR is rebased, refresh the acceleration route's actual base, exact diff and bindings. External Trust CI must verify each final exact head under the applicable current policy epoch.

## Is an image build necessary for the source-prepared claim?

No. The bounded claim can be: **the source recipe now requests the three exact test-tool versions, and the source invariant protects those pins; the image has not been built or deployed.** Source preparation is a reviewable repository outcome. It does not establish pip resolution in the target image, resulting image digest, installed package inventory, sandbox execution or current deployment.

The existing invariant `OperationsTests.test_runner_tools_and_build_backend_are_exactly_pinned` reads tracked text and uses unittest assertions. Adding three strings requires no pytest import, plugin installation or worker invocation. The existing runner recipe already requests the service `[test]` dependencies used by the surrounding test_ops module; this extracted test adds no new runtime dependency and avoids the feature suite's tooling cycle. The test is a source-presence invariant, not proof that Docker executed those lines or that duplicate/conflicting later installs are impossible; independent inspection must ensure the pins occur in the existing active pip command.

Minimal meaningful validation for this two-file source change:

1. Run the changed pin invariant and neighboring immutable-base invariant, using the existing Trust CI unit setup (`PYTHONPATH=trust-ci/src:trust-ci/tests`), then the relevant operations suite as required by the route. These two invariants only inspect source; this analysis did not run them.
2. Inspect the small Dockerfile diff: valid continued pip command, three exact package pins, existing coverage/lint/backend pins preserved, no runtime installer, no changed user/network/mount/policy semantics and no build-context escape.
3. Run the repository-required `python3 scripts/grok_verify.py --mode pr` on the final isolated bootstrap tree and require the exact separation check to pass. A source change is not a no-op; the previous failed full verification cannot replace this check.
4. Complete new-route independent review, record current receipts, and require the App-owned exact-head external check plus applicable signed scopes before merge.

An image build becomes necessary before claiming **a usable built runner image**. Testing that immutable image under actual runner constraints is necessary before claiming the parallel backend can run there. Deployment and policy-epoch/protection transition remain independently owned operations, not consequences of merging this recipe PR.

Memory fact: bootstrap can contain the Dockerfile and its stdlib pin invariant without the scoped requirements file; `.grok-stack/config` belongs to the prohibited opposite side of this exact separation rule. Source preparation needs source validation and honest claim limits, not a fabricated image build/deployment prerequisite or proof.
