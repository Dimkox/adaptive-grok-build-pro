# M4 bounded architecture-budget amendment implementation report

## Status and authority

**DONE locally for the approved source/documentation amendment; package rebuild, exact-head verification, independent reviews, PR delivery and external acceptance remain pending.**

- Active route: `b7f288f1e81e`; branch: `integration/m4-main-20260902`.
- Starting baseline: `b5af3fe69e9694fb70aced1e804a2541143a1078`.
- Exact comparison base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`.
- The exact proposal was `analysis-architecture-budget-amendment-proposal.md`; the user granted its named `scope_and_design_approval` on 2026-09-03. `architecture-budget-approval.md` records that workflow evidence and explicitly grants no migration, external, release, PR or merge authority.
- The active change moved from `reviewing` to `implementing` with reason `Human approved the exact six-rule bounded architecture budget amendment; implementation remains local with no migration or external action`.
- The source-freeze commit is the commit containing this report; a commit cannot embed its own SHA. Its SHA/tree are returned by the implementation owner after the clean commit.

## TDD evidence

Tests were saved before the policy edit. The initial focused command selected one exact-model regression and five evaluator regressions:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_architecture_model.ArchitectureModelTests.test_repository_code_budgets_restore_m2_and_bound_factory_independently \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_overlapping_code_budgets_report_each_applicable_failure \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_narrow_budget_can_fail_while_parent_budgets_pass \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_combined_children_and_scopes_can_fail_parent_and_union_budgets \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_code_budget_prefixes_match_only_complete_path_segments \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_unknown_line_metrics_fail_closed_for_every_overlapping_budget
```

- RED: 6/6 failed because only the widened legacy rule existed; the original M2 object was not exact and the five approved stable IDs were absent.
- First post-rule run: 5/6 passed. The remaining test assumed declaration order, while the established loader intentionally canonicalizes stable-ID arrays; no production behavior was wrong.
- GREEN: the test now compares the exact ID-keyed objects plus canonical order, and the identical six-test command passed 6/6 in 1.457 seconds.
- Timeline RED: `tests.test_project_state.ProjectStateTests.test_delivery_schedule_is_dependency_relative_and_does_not_revive_missed_dates` failed with `KeyError: 'schedule'` before the machine-readable dependency-relative schedule existed.
- Timeline GREEN: the identical one-test command passed 1/1 after the minimal schedule object and document parity update.

The regressions cover all six IDs/values/prefixes/severity, exact restoration of the original M2 object, independent overlap findings, parent-pass/child-fail, child-pass/parent-fail, each scope parent passing while their union fails, sibling/path-segment boundaries, and unsupported binary line statistics failing closed for every matching rule.

## Implemented policy

All rules have severity `error` and are evaluated independently. Passing a broader or sibling rule does not offset another failure.

| Rule | Prefix scope | Ceilings: bytes / lines / AST | Current metrics | Headroom |
| --- | --- | ---: | ---: | ---: |
| `FIT-BOUNDED-ARCHITECTURE-CHANGE` | exact original six non-factory prefixes | 1,000,000 / 10,820 / 5,000 | 362,991 / 1,725 / 2,000 | 637,009 / 9,095 / 3,000 |
| `FIT-BOUNDED-ALL-GOVERNED-CHANGE` | original six plus `factory` | 1,300,000 / 24,000 / 5,000 | 1,269,849 / 23,007 / 2,911 | 30,151 / 993 / 2,089 |
| `FIT-BOUNDED-FACTORY-CHANGE` | `factory` | 950,000 / 22,000 / 1,000 | 906,858 / 21,282 / 911 | 43,142 / 718 / 89 |
| `FIT-BOUNDED-FACTORY-SOURCE-CHANGE` | `factory/src` | 235,000 / 5,500 / 650 | 228,166 / 5,359 / 595 | 6,834 / 141 / 55 |
| `FIT-BOUNDED-FACTORY-CONTRACT-CHANGE` | `factory/contracts` | 285,000 / 8,500 / 1 | 276,496 / 8,236 / 0 | 8,504 / 264 / 1 |
| `FIT-BOUNDED-FACTORY-TEST-CHANGE` | `factory/tests` | 340,000 / 7,500 / 350 | 329,961 / 7,222 / 316 | 10,039 / 278 / 34 |

The worktree report contains no unknown line statistics and returns overall `pass` with zero budget findings. The original M2 prefixes are exactly `.grok-stack/adaptive_grok`, `architecture`, `engineering/contracts`, `governance`, `schemas`, and `scripts`.

## Representation and migration freeze

`git diff --exit-code 5c5f111 -- factory` is empty. Exact objects therefore remain:

| Frozen object | Identity |
| --- | --- |
| complete `factory` tree | `38446747c72cc2ed8defcf3aae9f78c4b2dd2203` |
| `factory/src` tree | `e993a6a1ba2e889a881410d43f867267bcfd9251` |
| `factory/contracts` tree | `588b202c593e13168ab7f6330700a171b2e39764` |
| `factory/tests` tree | `fafbc55e8c42189ea993f481beec5ca24bdd004d` |
| migration resources tree | `0a61b29fd87d9615270cf236b5d7908e210b52e7` |
| checked OpenAPI blob | `78365e2367c31b22fbdcab16133ff0973f4460b5` |
| ordered migration-manifest SHA-256 | `869086ef829f7a4eeddbdf75e4f3d6daca39d14be63e108bfc185c0844a5506a` |

The migration composite is SHA-256 over one newline-terminated `NNN name sha256` row for each discovered migration in contiguous order `001` through `013`. No migration was added, edited, applied or rolled back; no database was contacted.

## Dependency-relative timeline correction

The user additionally authorized correction of the missed calendar plan. The canonical schedule now defines **T0** as the recorded external acceptance time of an exact M4 SHA, which is unknown and null until a separately authorized successor PR receives the App-owned exact-SHA check, required signed scopes and protected merge/acceptance. The current 2026-09-03 work is only M4's local-ready target.

M5, M6 and M7 enter only after their predecessor is accepted. M8 has no determinate calendar until at least 30 human-accepted tasks exist for the exact class/profile tuple. M9 enters only after accepted M8 plus signed artifact, environment and recovery evidence; local commit `000301796ac19c518ede110b97b9de09dc077cbd` is verified to exist but remains only an inactive, unaccepted source-only Task-1 contract slice. The former 2026-09-08 target is explicitly superseded and unachievable historical planning, never a waiver.

## Verification

- Focused exact-budget TDD: 6/6 PASS in 1.457s after the recorded RED.
- Full architecture fitness module: 90/90 PASS in 124.175s.
- Final governance and governance-fitness rerun: 63/63 PASS in 20.227s.
- Final change-receipt and verifier-doctor rerun: 88/88 PASS in 167.147s.
- Final architecture-model, project-state, typed-spec, structure and installer rerun: 131/131 PASS in 8.924s, including the dependency-relative timeline parity test.
- Architecture `validate`, repository `drift`, and five diagram `--check` projections: PASS.
- Worktree architecture fitness: PASS, six applicable budget rules, zero findings; evidence digest `b2b71217df45435460cefe6dd0e36f0b409430747b299816fbbcda6da05bb617` at that pre-report checkpoint.
- Governance validation/projection checks: PASS; governance digest `dfb263...` at that checkpoint.
- Typed change spec: PASS, 5/5 criteria mapped; digest `1eb08251a013ea7cc5797cf5c7963f6aa07c6f953e8375c73fa8798c7012d10b`, fingerprint `8964e17efea521f918c69bc111d23761cf8cd3890bebfe1a4edb2abe6b43bfaa` before final report edits.
- Factory migration unit tests: 6/6 PASS; exact migration object/composite checks independently report `001..013` and the frozen digest.
- Changed-tree secret scan: PASS, zero potential secrets across 25 files.
- JSON parsing and `git diff --check`: PASS and rerun after this final evidence edit before commit.

## Changed surfaces

- Policy/tests: `architecture/rules.yaml`, `tests/test_architecture_model.py`, `tests/test_architecture_fitness.py`, `tests/test_project_state.py`.
- Typed/current change package: `change-spec.yaml`, `architecture.md`, `brief.md`, `requirements.md`, `tasks.md`, `test-plan.md`, `release.md`, `rollback.md`, `schedule.md`, `state.json`.
- Approval and implementation evidence: `architecture-budget-approval.md`, this report, `implementation-ledger.md`, `implementation-report.md`.
- Current-state/self-learning: `README.md`, `START_HERE.md`, `DARK_FACTORY_ROADMAP.md`, `PROJECT_STATE.json`, `packages/README.md`, `decisions.md`, `mistakes.md`.

No evaluator, architecture schema, factory code, factory test, API, OpenAPI, SQL, migration, Trust CI code/configuration, runtime dependency, or package artifact changed.

## Residual gates and risks

- The aggregate rule has 993 changed-line headroom; factory source has 141; contracts 264; tests 278; factory AST has 89. These finite margins are intentional review triggers, not growth targets or exceptions.
- The tracked `2.0.13` ZIP/sidecar now predate this source/docs amendment and remain stale. Rebuild is a separate artifact-only task from this clean source HEAD; no package parity claim is made here.
- Final exact-head `grok_verify`, five route-selected independent reviews/reports/receipts, separately authorized PR delivery, the App-owned external exact-SHA gate, signed scopes and protected merge remain pending.
- T0 is unknown. No M4 acceptance/delivery, M5-M9 acceptance, external operation, migration action, deployment or production authority is claimed.
