# Implementation report — current landing source binding

Route `eb3f80383d44` was implemented by the selected sole writer from control
HEAD `33206fa06ae4b5bfb390cb68bbf233800d2902ab`, tree
`6e24f82570bcb78ae90b92ee3e67d7fa7fbb4b28`. The bounded repair changes the
accepted landing epoch to commit
`699010380f4f90a0193a9c22090c35e6aded7d2c`, tree
`f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`, advances the renderer and OpenAPI
metadata identity to `1.0.1`, and adds protected source-owned `index.css` to
the 20-member deploy inventory. `LANDING_WRITE_PATHS` remains exactly
`content.css,index.html`.

## TDD evidence

Tests were authored before production changes. The initial resolved command
was:

```text
PYTHONPATH=factory/src:. python3 -m unittest -v \
  factory.tests.test_landing_renderer.LandingRendererTests.test_current_source_identity_and_external_stylesheet_contract_are_exact \
  factory.tests.test_landing_renderer.LandingRendererTests.test_exact_target_workspace_is_private_detached_independent_and_two_file_bounded \
  factory.tests.test_landing_artifact.LandingArtifactTests.test_same_candidate_seals_reproducibly_with_exact_deploy_inventory \
  factory.tests.test_landing_contracts.LandingContractTests.test_six_json_schemas_and_additive_openapi_are_closed_version_one \
  factory.tests.test_landing_api.LandingApiTests.test_routes_are_visible_and_default_provider_is_unavailable_without_blob_read \
  factory.tests.test_landing_api.LandingApiTests.test_prior_and_mixed_source_tuples_fail_before_provider_or_blob_work
```

RED was factual: stale `TARGET_BASE_SHA` failed, both renderer/artifact paths
raised `LandingRenderError: source_active_content`, and OpenAPI reported
`1.0.0` instead of `1.0.1`. The two API selectors used the host interpreter
without FastAPI and produced loader errors; they count as zero evidence and
were rerun with the factory environment. After the minimal implementation,
the same six selectors under `factory/.venv/bin/python` passed 6/6 in 0.917s.

A self-review regression then added an unquoted foreign stylesheet tag. Its
single selector failed because no `LandingRenderError` was raised; after the
fail-closed link classification repair, that exact selector passed 1/1 in
0.001s.

## Focused GREEN evidence

```text
PYTHONPATH=factory/src:. factory/.venv/bin/python -m unittest -v \
  factory.tests.test_landing_renderer \
  factory.tests.test_landing_artifact \
  factory.tests.test_landing_contracts \
  factory.tests.test_landing_api \
  factory.tests.test_landing_intake \
  factory.tests.test_landing_provider
```

Result: 47/47 passed in 7.412s. Root current-state tests passed 14/14 in
0.090s; the affected README version method and complete K22 graph check also
passed. Targeted Ruff passed, configured targeted Bandit passed, JSON parsing
passed for PROJECT_STATE/OpenAPI/spec/state, typed change-spec gate validation
returned `ok: true`, digest
`e392a3d246ae7ec40af84bfa57a116229e52772963d7a9f273fd7bea729795de`,
and `git diff --check` passed.

## Immutable and external-effect checks

- Landing worktree remained clean at exact HEAD/tree above; its `index.css`
  SHA-256 is
  `91ae1c46ae5cc825d72e9ebde91e93901d0d8413d55f27f322613a593b8b1589`.
- Published `packages/adaptive-grok-build-pro-v2.0.14.zip` remained SHA-256
  `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`;
  its sidecar file remained SHA-256
  `1a961c35b8f12fa02579ec7888c889f0ae7ca8656b158eb731681ef8357caf3c`.
- No package, migration, old L5 package/evidence, provider, publisher, target
  repository, live URL, network resource, or external system was changed.

The tracked state is `verifying`. One exact-head PR verifier and the selected
code, test, and security reviews remain deliberately pending and are not
claimed by this implementation report.
