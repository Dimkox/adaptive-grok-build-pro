# Bootstrap architecture analysis: parallel test runner tools

Route `56fd015ff1f0`; worktree `/home/pall/grok-projects/adaptive-grok-build-pro-test-tools`; branch `build/parallel-test-runner-tools`; inspected HEAD `64378d28c7b78cace463d96470c1898294b8f196`. Analysis only: no product diff existed at inspection, no tests/builds/deployed state were accessed. Root is the sole author under the recorded user override; final independent review follows implementation and verification.

The proposed two-file product scope is the smallest coherent prerequisite: add `pytest==9.1.1`, `pytest-xdist==3.8.0`, and `pytest-cov==7.1.0` to `trust-ci/runner.Dockerfile`, and extend the existing pin tuple in `trust-ci/tests/test_ops.py:132-138`. Keep existing `coverage==7.15.4`, Ruff/Bandit/tomli pins, build backend and every other image instruction unchanged. Installing tools makes a subsequently built runner capable of the later test-runner patch; it does not itself select pytest, enable sharding, or change existing verification commands.

## Separation and build context

`architecture/rules.yaml:21-39` defines `FIT-TRUST-CI-SEPARATION`: a change cannot combine `trust-ci` with implementation prefixes including `.grok-stack`, `.grok`, architecture, delivery, engineering/contracts, factory, governance, pilot, schemas or scripts. Both proposed product paths belong to trust-ci. Durable paperwork under engineering/changes is outside those implementation prefixes. This branch therefore preserves the rule without an exception or model/rule edit; merging the runner implementation's .grok-stack changes into this prerequisite would defeat the separation.

`trust-ci/compose.build.yaml:23-30` defines runner-image using `context: .` and `dockerfile: runner.Dockerfile`. With the existing first Compose file under trust-ci, this is the trust-ci directory, consistent with `runner.Dockerfile:16-19` copying its pyproject.toml, README.md and src. Keep exact pins directly in the Dockerfile's existing installation command. Do not COPY or reference the separate root `.grok-stack/config/python-test-requirements.txt`, which is outside this build context and absent from this main-based prerequisite.

The existing runner starts from the supplied `PYTHON_BASE_IMAGE`, installs tools before dropping to UID/GID10001, then sets `/workspace`; the proposed pins require no new COPY, user, capability, mount, entrypoint, network edge or service. `trust-ci/compose.build.yaml:29` retains the immutable-base requirement. `trust-ci/pyproject.toml` remains Python>=3.11, setuptools==84.0.0, the existing application dependencies and the httpx test extra. The three tools belong in the runner image, not the API runtime dependency list or Dockerfile.worker/API/test images.

`trust-ci/.dockerignore` already excludes runtime, env/*.env, approval/attestation artifacts and common test/build caches. No context widening is needed. The analysis read tracked source/documentation only, not actual environment files or Docker state.

## Pin and authority implications

The baseline runner already pins `coverage==7.15.4`; preserve that tested version while introducing the selected pytest/xdist/cov pins. The existing pin assertion is the correct bounded source check: retain every previous pin assertion and the setuptools constraint, extending only the tuple. Static source inspection establishes consistency and scope; it does not establish dependency resolver success or a newly built image digest. Report any later resolver/build/import evidence separately rather than claiming a Dockerfile text assertion proves an image was built.

`trust-ci/compose.yaml` continues to use prebuilt images; no build instruction belongs in its deployed service definitions. `trust-ci/README.md:89-100` distinguishes source build/pin work from immutable runner digest and policy epoch activation. This patch does not edit deployed image selection, policy, holdout, branch protection, keys or PostgreSQL. Source merge alone cannot supply the updated runner to external Trust CI; later operator-owned image rollout is a separate exact-artifact operation, whose resulting policy epoch invalidates prior check/approval bindings.

Tracked policy.example.json approval rules classify trust-ci/** under governance and **/*.Dockerfile under production. These are repository example facts, not a claim about current deployed approval scopes. Existing external exact-head Trust CI and any scopes required by its deployed policy remain authoritative; no local receipt or this report substitutes for them.

## Acceptance and rollback

1. Final product diff consists only of the three new Dockerfile pins and matching additions to the existing test tuple; preserve all old pins, image instructions and source boundaries.
2. Run the existing test_ops pin/build-context assertions and route-required local verification against the final tree, then independent code/test review; this analysis runs none of those checks.
3. Reuse the parent's actual same-interpreter package/import evidence where available. Any future image build must retain the trust-ci context and immutable base, and demonstrate the exact installed versions; absence of a new build is an explicit evidence limit, not a reason to mutate live state here.
4. Keep main's serial runner behavior in this prerequisite. The later parallel-runner change and deployment of an approved rebuilt image are separate dependencies, so do not claim this source patch alone delivers accelerated external execution.
5. Source rollback removes these three pins and their matching assertions, leaving all prior versions intact. If an image is later activated, its separate rollout must retain the previous immutable image/policy recovery path; no deployment or rollback is authorized by this analysis.

Handoff fact: the isolated prerequisite must keep its three exact tool pins inside the existing trust-ci build context; sharing root .grok-stack requirements would both cross the context boundary and collapse the required change separation.
