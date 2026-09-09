# Repository exploration — M0–M9 delivery state

Inspected 2026-08-28 UTC in `/home/pall/grok-projects/adaptive-grok-build-pro-m3` for route `35568941ae59`. This is repository evidence only: it cannot establish the live state of GitHub, Trust CI, hosts, secrets, or deployment.

## Branch and worktree facts

| Surface | Exact state |
| --- | --- |
| `origin/main` | `1c06299894279a88b881defa3f19b004fa742223`; it does not contain the milestone branch lines below (their common base is generally `069fe822…`, or `48cb973…` for M0). |
| M0 branch | `milestone/m0-live-trust-authority` at `29339bbba0bc76c7603b979c11430e2208f8e74d`, 6 commits ahead / 12 behind `origin/main`; its worktree is not the M3 worktree. |
| M1 evidence branch | `milestone/m1-typed-intent-evidence` at `25bfbe59ea188d9687b20a9caad19e7db3d031f8`, 21 ahead / 3 behind `origin/main`; local worktree is clean. |
| M2 branch | `milestone/m2-executable-architecture` at `635c9ddf2d63c1ea823074106976a8f3de6299a9`, 102 ahead / 3 behind `origin/main`; local worktree is clean and matches `origin/milestone/m2-executable-architecture`. |
| M3 branch/worktree | `milestone/m3-controlled-knowledge-debt` at `bc5ef65052f7f0b3727faaac6c4ada11871d8a23`, whose parent is the M2 tip. The worktree has the untracked M3 candidate listed below plus the current untracked change package. |
| Factory design branch | `feature/model-agnostic-factory` at `c1e4203331c6bdfdcb3db228145ff2472761a960`, 2 ahead / 3 behind `origin/main`, clean. It is *not* descended from M3 or M2 (merge base `069fe822…`) and has no `factory/` commit. |

The M3 branch contains one M3/M4 planning commit only: `bc5ef65` (`docs: plan stacked M3 and M4 delivery`). The similarly named `c1e4203` on the factory-design branch is a different commit on a divergent parent. Neither is an integration/merge of M0–M3 into `main`.

## Milestone status

| Milestone | Implemented / evidenced | Not complete or not available |
| --- | --- | --- |
| M0 | Separate branch contains source/operator-safe records through `29339bb` (`M0.3` binding documentation). `decisions.md` records historical live-check and branch-protection assertions. | Not part of current `main` lineage. Live App ownership, exact-SHA check, approvals, host/service state, and protection cannot be re-established from this checkout; roadmap retains unchecked operational items. |
| M1 | Implemented local source on its separate branch: typed spec schema/CLI, criterion-bound receipts, holdout source changes, and Trust CI source changes. Its durable package is `ready` and names exact local source SHA `98649e4…`. | State itself says PR, App-owned exact-SHA check, signed approvals, merge, and deployed holdout/worker/policy/attestation are incomplete. Branch is divergent from `origin/main`. |
| M2 | M2-A executable architecture source is implemented on the M2 branch. Its package is `ready`; recorded exact product SHA `72927ee…` passed local verification and five reviews; `635c9dd` records the review evidence. | M2-B independent enforcement is explicitly separate and absent; no PR/external exact-SHA/deployment completion is present. Branch is divergent from `origin/main`. |
| M3 | An implementation plan exists, stacked on M2, and current untracked candidates create four schemas, three empty JSON registries, and `tests/test_governance.py`. | No tracked M3 product implementation commit exists. The loader, lifecycle/conflict rules, seven canonical samples, CLI, handoff, architecture/fitness, receipts/verifier/installer/docs integration, final verification, and reviews required by the plan are missing. |
| M4 | A detailed plan exists in `docs/superpowers/plans/2026-08-28-m4-durable-factory-control-plane.md`. | No `factory/` directory exists in this worktree or any commit reachable from local refs; `git log --all -- factory` is empty. Thus no PostgreSQL task control plane, migrations, leases, state machine, budgets, API, reconciliation, or M4 handoff consumer exists. |
| M5 | Design describes the intended execution plane. | No implementation surfaces for isolated workspaces, provider adapters, task packets, secret broker, network controller, systemd service, manifests, or orphan recovery. |
| M6 | Design/roadmap only. | No durable findings schema/store, independent semantic validator/adjudicator, or bounded repair implementation. |
| M7 | Roadmap only. | No branch/commit/push/PR lifecycle or shadow-mode metrics implementation. No autonomous external write is authorized by this route. |
| M8 | Roadmap only. | No durable trust-profile/promotion/demotion implementation or qualifying shadow-mode cohort evidence. |
| M9 | Roadmap only. | No preview/staging/canary/recovery implementation, signed promotion flow, delivery metrics, or exercised rollback. |

## M3 dirty-worktree provenance and quality

`git status --short` in the M3 worktree reports all of the following as `??`, not as modifications to tracked files:

```text
governance/
schemas/canonical-example.schema.json
schemas/debt-entry.schema.json
schemas/governance-handoff-v1.schema.json
schemas/governance-rule.schema.json
tests/test_governance.py
engineering/changes/20260826-m3-m9-production-delivery-continuation-355689/
```

The candidate governance/schema files have filesystem times around `11:24:06Z`; `tests/test_governance.py` is `11:25:09Z`. They postdate M3 branch HEAD (`11:11:47Z`) and predate the current package/route creation (`12:58:26Z`). This gives a plausible earlier uncommitted M3 attempt, but Git has no blob, commit, author, receipt, or fingerprint binding for it, so provenance is not cryptographically established.

The candidates cover only part of M3 Task 1. They use the existing schema validator and canonical empty registries, but do not add `.grok-stack/adaptive_grok/governance.py` or `scripts/grok_governance.py`. The seven required canonical-example files and `tests/test_governance_fitness.py` are absent. M2 integration paths have no tracked delta from the M2 branch.

Focused check run without bytecode writes:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_governance -v
Ran 4 tests: FAILED (1 failure)
```

`GovernanceSchemaTests.test_debt_and_example_schemas_validate_records_and_reject_duplicates` expects duplicate debt/example records to raise `SpecError`, but no exception is raised. Even the partial M3 Task 1 candidate therefore lacks a passing focused test baseline.

## M9 dependency blockers

The roadmap chain is `M0 → {M1, M2, M3} → M4 → M5 → M6 → M7 → M8 → M9`. The immediate hard blockers are:

1. M3 cannot publish the versioned `GovernanceHandoffV1` that M4 is designed to consume; its current candidate is untracked, partial, and failing.
2. M4 has no implementation at all, including its durable PostgreSQL task/lease/audit/budget control plane. M5–M9 cannot be meaningfully started as downstream delivery capabilities before that boundary exists.
3. M5, M6, M7, and M8 each lack their prerequisite runtime/evidence capability; in particular M8 requires M7 shadow-mode evidence, and M9 requires earned low-risk autonomy plus protected merge before any delivery path.
4. M1 and M2 remain local source candidates on divergent branches, and M2-B/external exact-SHA enforcement is not complete. M0 live facts are historical in-repo assertions, not proof for a new exact SHA.
5. The active M3–M9 package remains `draft`; its `change-spec.yaml` has zero acceptance criteria, invariants, forbidden outcomes, contracts, observability items, and approval scopes. The route explicitly requires `scope_and_design_approval` before a high-risk writer may proceed.

## Safe next sequencing implied by evidence

First establish/record current M0–M2 integration and external gates through the approved PR process; then finish M3 on its M2 parent with a clean committed product fingerprint and its stable handoff. Only then create a separately scoped M4 implementation route. Treat M5 through M9 as later individually approved milestones; no source evidence supports combining them into a delivery/deployment action now.
