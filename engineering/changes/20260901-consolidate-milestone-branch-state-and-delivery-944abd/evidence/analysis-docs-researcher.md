# Documentation and live-state audit

## Scope and binding

- Route: `944abd96ddb3`
- Repository: `Dimkox/adaptive-grok-build-pro`
- Read-only audit worktree: the isolated `chore/reconcile-milestone-state` worktree
- Audited base/head: `1c06299894279a88b881defa3f19b004fa742223` (`origin/main` and this worktree HEAD at observation time)
- Observation date: 2026-09-01 UTC
- Files compared: `PROJECT_STATE.json`, `README.md`, `START_HERE.md`, `decisions.md`, `mistakes.md`, `DARK_FACTORY_ROADMAP.md`, milestone branch evidence, all local/remote refs, all GitHub pull requests, live Trust CI readiness, and live `main` protection.
- Side effects: GitHub and Trust CI calls were GET-only. No product or external state was modified. This report is the only file written.

## Executive verdict

The current-main handoff is materially stale. `main` has M0 delivered and an early M1 schema/CLI slice from PR #4, but the complete M1 source plus M2 source were implemented and reviewed on the stacked PR #10, then merged only into `milestone/m1-typed-intent-evidence`. M3 was implemented and reviewed on PR #11 and merged only into `milestone/m2-executable-architecture`. M4 is implemented and had passing local reviews at product head `f82134d...`; PR #17 is still open, its remote head `8e65041...` failed both the current Trust CI check and GitGuardian, and the local branch contains two additional unpushed verifier commits through `cf0219b...`. None of the M1-completion, M2, M3, or M4 stacked source is delivered to `main`.

The live merge authority has moved from epoch `6737355947c2` to `06ecf1c875bc`. The Trust CI readiness endpoint reports full policy digest `06ecf1c875bc12fa696956998983e04b102f28571a586bc3bb7a2fff5083fdb2`; protected `main` requires `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114`. PR #19 proves a successful exact-head Check Run owned by App `adaptive-trust-ci` (`app.id=4694114`).

The repair must not call M1-M4 “complete on main,” and must not call stacked PR #10/#11 merges product delivery. Keep four independent status dimensions: implementation, independent review, merge into a named branch, and delivery to `main`.

## Live external facts

### Repository and release

- Default branch: `main`.
- Live `main` SHA: `1c06299894279a88b881defa3f19b004fa742223`.
- Latest GitHub release: `v2.0.12`, target `main`, published 2026-08-23T22:06:04Z.
- Current release identity claims in README/VERSION remain correct.

### Trust CI and branch protection

Live `GET /health/ready` returned:

```json
{
  "status": "ready",
  "policy_digest": "06ecf1c875bc12fa696956998983e04b102f28571a586bc3bb7a2fff5083fdb2",
  "status_context": "adaptive-trust-ci/verified",
  "active_approval_keys": 1,
  "status_publisher": "worker-github-app"
}
```

Live GitHub protection for `main`:

- required check: `adaptive-trust-ci/verified@06ecf1c875bc`;
- required-check App ID: `4694114`;
- strict/up-to-date checks: true;
- pull request required; approving review count is zero; stale reviews dismissed;
- administrators enforced;
- linear history and conversation resolution required;
- force pushes and branch deletion disabled.

Exact Check Run ownership proof:

| PR/head | Check | Conclusion | App |
| --- | --- | --- | --- |
| #19 `ecc85d903d03...` | `adaptive-trust-ci/verified@06ecf1c875bc` | success | `adaptive-trust-ci`, ID `4694114` |
| #18 `514f6e35e7ae...` | `adaptive-trust-ci/verified@06ecf1c875bc` | success | `adaptive-trust-ci`, ID `4694114` |
| #17 `8e6504168462...` | `adaptive-trust-ci/verified@06ecf1c875bc` | failure | `adaptive-trust-ci`, ID `4694114` |

## Milestone truth table

“Merged” names the actual target branch. “Delivered” means present on protected `main`, not merely accepted into a stacked milestone branch.

| Milestone | Implemented source | Independent/local review | GitHub disposition | Delivered to `main` | Truthful current label |
| --- | --- | --- | --- | --- | --- |
| M0 | Yes | Yes | PR #5 merged to `main`; merge commit `069fe8226add...`; old-epoch exact-head Trust CI succeeded | Yes | complete/delivered |
| M1 | Early schema/CLI slice is on `main` via PR #4. Complete typed-spec/evidence work is in the PR #10 stack (`df30427...` through M1 closure commits before M2) | Yes on the stacked source/evidence | PR #8 merged design/plan to `main`; PR #10 merged the complete M1+M2 head `022411b...` into `milestone/m1-typed-intent-evidence`, merge `c23fd49...` | Partial only; milestone exit source is not on `main` | implemented/reviewed on stack; not delivered |
| M2 | Yes in PR #10 (`b3b8339...` onward, final head `022411b...`) | Yes; current-epoch Trust CI succeeded on PR #10 head | PR #10 merged into `milestone/m1-typed-intent-evidence`, not `main` | No | implemented/reviewed/stack-merged; not delivered |
| M3 | Yes, final head `1e73ff9b91d...` | Yes; current-epoch Trust CI succeeded on PR #11 head | PR #11 merged into `milestone/m2-executable-architecture`, merge `67714a1...`, not `main` | No | implemented/reviewed/stack-merged; not delivered |
| M4 | Yes on local branch through `cf0219b...`; core product reached `f82134d...` and remote PR head is `8e65041...` | Five local reviews passed for product head `f82134d...`; the two later local verifier commits do not have a complete new review set in tracked evidence | PR #17 open against `milestone/m2-executable-architecture`; remote exact-head Trust CI and GitGuardian failed; local branch is two commits ahead of remote | No | implemented locally; external acceptance/delivery blocked |
| M5 | No milestone branch or PR | No | None | No | not started |
| M6 | No milestone branch or PR | No | None | No | not started |
| M7 | No milestone branch or PR | No | None | No | not started |
| M8 | No milestone branch or PR | No | None | No | not started |
| M9 | No milestone branch or PR | No | None | No | not started |

Important nuance: GitHub reports PR #10 and #11 as `MERGED`, but their bases were milestone branches. Their merge commits `c23fd49...` and `67714a1...` are not ancestors of `origin/main`. This is the exact source of the misleading “merged/delivered” shorthand.

## Pull-request inventory

| PR | State | Base <- head | Current trust result | Delivery meaning |
| ---: | --- | --- | --- | --- |
| 1 | closed | `main` <- `hardening/trust-boundary-v2-1` | superseded Actions-era checks | not delivered |
| 2 | merged | `main` <- `feat/trust-ci-control-plane` | pre-App bootstrap merge | delivered to main |
| 3 | merged | `main` <- `docs/dark-factory-roadmap` | pre-current epoch | delivered to main |
| 4 | merged | `main` <- `milestone/m1-typed-intent` | no Trust CI rollup | early M1 slice delivered to main |
| 5 | merged | `main` <- `milestone/m0-live-trust-authority` | `6737355947c2` success | M0 delivered to main |
| 6 | merged | `main` <- `fix/path-aware-shell-policy-circuit-breaker` | `6737355947c2` success | repair delivered to main |
| 7 | merged | `main` <- `fix/trust-ci-workspace-integrity` | `6737355947c2` success | repair delivered to main |
| 8 | merged | `main` <- `milestone/m1-typed-intent-evidence` | `6737355947c2` success | M1 design/plan delivered, not full M1 milestone |
| 9 | merged | `main` <- `docs/fresh-agent-bootstrap` | `6737355947c2` success | stale handoff text delivered to main |
| 10 | merged | `milestone/m1-typed-intent-evidence` <- `milestone/m2-executable-architecture` | `06ecf1c875bc` success | M1/M2 stack acceptance, not main delivery |
| 11 | merged | `milestone/m2-executable-architecture` <- `milestone/m3-controlled-knowledge-debt` | `06ecf1c875bc` success | M3 stack acceptance, not main delivery |
| 12 | open | `main` <- `fix/human-approval-cli` | old epoch action-required | not merge-eligible under current required context without refreshed exact-head check |
| 13 | open | `main` <- `feat/trust-ci-repository-profiles` | old epoch action-required | not merge-eligible under current required context without refreshed exact-head check |
| 14 | closed | `main` <- `policy/production-only-human-approvals` | current epoch failure | not delivered |
| 15 | open | `main` <- `mvp/investor-ready` | current epoch failure | blocked/not delivered |
| 16 | merged | `milestone/m2-executable-architecture` <- `fix/m2-trust-ci-zombie-process-group` | current epoch success | repair included in stacked M2, not main |
| 17 | open | `milestone/m2-executable-architecture` <- `milestone/m4-durable-control-plane-accepted-m3` | current epoch failure | M4 not accepted/delivered |
| 18 | merged | `fix/path-aware-shell-policy-circuit-breaker` <- `feature/seo-landing-codex-side-project` | current epoch success | merged to non-main feature base; not main delivery |
| 19 | open/clean | `main` <- `feature/seo-landing-codex-main` | current epoch success | exact-head check is green; still requires human merge |

## Branch inventory and interpretation

Local branches observed (25):

```text
chore/reconcile-milestone-state
docs/dark-factory-roadmap
feat/m4-durable-factory-control-plane
feat/trust-ci-control-plane
feat/trust-ci-repository-profiles
feature/model-agnostic-factory
feature/seo-landing-codex-main
feature/seo-landing-codex-side-project
feature/workflow-artifact-adapters
fix/human-approval-cli
fix/m3-restack-accepted-m2
fix/path-aware-shell-policy-circuit-breaker
fix/trust-ci-zombie-process-group
main
milestone/m0-live-trust-authority
milestone/m1-typed-intent
milestone/m1-typed-intent-evidence
milestone/m2-executable-architecture
milestone/m3-controlled-knowledge-debt
milestone/m4-durable-control-plane-accepted-m3
milestone/m4-durable-control-plane-local
mvp/investor-ready
policy/production-only-human-approvals
policy/promotion-task1-isolated
publish-2012
```

Remote non-PR branches observed (26):

```text
docs/dark-factory-roadmap
docs/fresh-agent-bootstrap
feat/trust-ci-control-plane
feat/trust-ci-control-plane-pr-anchor
feat/trust-ci-repository-profiles
feat/trusted-self-hosted-ci
feature/seo-landing-codex-main
feature/seo-landing-codex-side-project
feature/trusted-self-hosted-ci
feature/trusted-self-hosted-ci-v2
fix/human-approval-cli
fix/m2-trust-ci-zombie-process-group
fix/path-aware-shell-policy-circuit-breaker
fix/pretooluse-shell-targets
fix/trust-ci-workspace-integrity
handoff/m0-2-live-authority
hardening/trust-boundary-v2-1
main
milestone/a-plus-autopilot
milestone/m0-live-trust-authority
milestone/m1-typed-intent
milestone/m1-typed-intent-evidence
milestone/m2-executable-architecture
milestone/m3-controlled-knowledge-debt
milestone/m4-durable-control-plane-accepted-m3
mvp/investor-ready
```

`origin/pr/1` through `origin/pr/19` all exist as fetched evidence refs. The apparent count above is 26 names because both `feat/trusted-self-hosted-ci` and `feature/trusted-self-hosted-ci` are distinct refs; do not normalize them into one branch.

Local branch hazards relevant to the repair:

- local `main` is at `c54fd015...`, 213 commits behind `origin/main`; never use local `main` as current truth;
- the reconciliation branch/worktree is correctly based at `origin/main` `1c062998...`;
- local M4 `cf0219b...` is two commits ahead of remote M4 `8e65041...`;
- several local milestone branches are behind or divergent from their remotes because remote bases moved after stacked merges;
- branch names and worktree existence are evidence, not completion authority.

## Stale-claim matrix and exact minimal replacements

### `PROJECT_STATE.json`

| Current claim | Problem | Minimal truthful replacement |
| --- | --- | --- |
| `completed_milestones: ["M0"]` | Correct only if “completed” means delivered to main, but the meaning is implicit. | Keep the value but rename or document it as `delivered_milestones_on_main`. Add a separate `milestones` object with `implemented`, `reviewed`, `merged_target`, and `delivered_to_main` for M0-M9. |
| `active_milestone: "M1"` | Stale: M1-M4 source work progressed; delivery is the unresolved axis. | `active_milestone: "M4"` plus `active_phase: "reconcile_and_deliver_m1_through_m4_to_main"`, or an equivalent explicit two-field representation. Do not advance to M5. |
| `last_completed_milestone_merge` = PR #5 / `069fe822...` | Still correct for a milestone delivered to main. | Preserve unchanged; explicitly label it `last_milestone_delivered_to_main` if schema can change. |
| `active_work` = draft PR #8, design only, implementation not started | Entire object is stale. | Replace with the milestone truth table above and a `delivery_blocker`: M1-M3 only stack-merged; M4 PR #17 open/failing; next action is one current-main integration/delivery path, not Task 1 of old M1 plan. |
| `trust_ci.required_check` = `...@6737355947c2` | Stale deployed epoch. | `adaptive-trust-ci/verified@06ecf1c875bc`; optionally add full `policy_digest` `06ecf1c875bc12fa696956998983e04b102f28571a586bc3bb7a2fff5083fdb2` and `observed_at`. |
| no current main SHA / state observation timestamp | Makes future drift hard to distinguish from historical truth. | Add `observed_main_sha: 1c062998...` and `observed_at: 2026-09-01T...Z` (use actual write-time UTC). |

Recommended milestone values:

```text
M0 implemented=true reviewed=true merged_target=main delivered_to_main=true
M1 implemented=true reviewed=true merged_target=milestone/m1-typed-intent-evidence delivered_to_main=false main_slice=PR#4
M2 implemented=true reviewed=true merged_target=milestone/m1-typed-intent-evidence delivered_to_main=false
M3 implemented=true reviewed=true merged_target=milestone/m2-executable-architecture delivered_to_main=false
M4 implemented=true reviewed=product_head_only merged_target=null delivered_to_main=false blocker=PR#17 exact-head checks failed/local head ahead
M5-M9 implemented=false reviewed=false merged_target=null delivered_to_main=false
```

### `README.md`

Current-state bullets 13-14 are stale.

Replace the old epoch sentence with:

> Trust CI service identity is **2.1.0** (`trust-ci/pyproject.toml`); it is not product `2.0.12`. As observed on 2026-09-01, protected `main` requires the App-owned check `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114`; the deployed full policy digest is `06ecf1c875bc12fa696956998983e04b102f28571a586bc3bb7a2fff5083fdb2`.

Replace the “active M1 / draft PR #8 / implementation has not started” bullet with a compact status table or this paragraph:

> M0 is delivered to `main`. M1 has an early schema/CLI slice on `main`; complete M1 and M2 source was implemented/reviewed in PR #10 and merged only into `milestone/m1-typed-intent-evidence`. M3 was implemented/reviewed in PR #11 and merged only into `milestone/m2-executable-architecture`. M4 is implemented locally, but PR #17 remains open with failed exact-head checks and a local head two commits ahead of the remote. M1-M4 are therefore not delivered to `main`; do not begin M5 until one current-main integration path is verified and merged.

Do not change the identity/release bullets. PR #19 may be mentioned as concurrent non-milestone work, but it must not be represented as milestone progress.

### `START_HERE.md`

Stale areas: current-state bullets 9-14, bootstrap step 3, and the entire “Current M1 handoff” section.

Minimal replacement:

- update the required epoch to `06ecf1c875bc`, App `4694114`;
- replace “M1 implementation has not started” with the M0-M4 delivery distinction above;
- replace “continue M1 from PR #8 / Task 1” with “inspect PR #10, #11, #17 and their exact bases/heads; integrate from current protected `main`; do not treat a stack merge as main delivery; do not start M5”;
- retain the no-chat, no-secret, no-GitHub-Actions, and exact-SHA instructions unchanged.

Suggested section heading: `## Current milestone delivery handoff`, not `## Current M1 handoff`.

### `decisions.md`

The dated entries describing epoch `6737355947c2`, PR #5 as unmerged, or earlier operational gaps are historical evidence. Do not silently rewrite them. Add one superseding entry of no more than three sentences:

> ## 2026-09-01 — Separate stack acceptance from main delivery
>
> A milestone is delivered only when its source reaches protected `main`; a PR merged into another milestone branch records stack acceptance, not product delivery. Current epoch `06ecf1c875bc` is bound to App `4694114`; keep M1-M4 implementation/review/merge-target/main-delivery as separate fields and consolidate their delivery before starting M5.

### `mistakes.md`

The required route-proliferation root cause is absent. Add:

> ## 2026-09-01 — Used task routes and stacked merges as the milestone ledger
>
> **Symptom:** M1-M4 accumulated across separate routes, worktrees and stacked PRs while `PROJECT_STATE.json`, `START_HERE.md`, and README still said M1 had not started; GitHub “merged” states were mistaken for delivery to `main`.
> **Root cause:** Task-local route/change state was allowed to substitute for one repository-level delivery ledger, and the ledger did not record PR base/merge target separately from protected-main delivery. Reconcile all existing milestone evidence in one route and do not create a new route merely to restate each milestone.

This identifies the root cause rather than blaming the number of branches itself.

### `DARK_FACTORY_ROADMAP.md`

The baseline is explicitly historical, but its current-state gap table and startup handoff now misdirect readers.

Minimal changes:

1. Keep the original baseline SHA as historical provenance, but add a dated “live state overlay” immediately after it with observed `main` `1c062998...`, required epoch `06ecf1c875bc`, App `4694114`, and the M0-M9 truth table.
2. Replace §3.3’s “must be verified” wording with the live proof already established: App-owned exact-head checks and app-bound branch protection are operational. Preserve separately any genuinely unproven operational items.
3. Update §4 rows:
   - exact-SHA external Trust CI -> operational on protected main;
   - GitHub App -> installed/proven, App `4694114`;
   - typed business specification -> partial on main, complete reviewed stack source not delivered;
   - executable architecture -> implemented/reviewed/stack-merged, not delivered;
   - controlled learning and debt ledger -> implemented/reviewed/stack-merged, not delivered;
   - durable factory task queue/control plane -> implemented locally, PR #17 external checks failed, not delivered;
   - M5-M9 capabilities remain missing/deferred unless separately evidenced.
4. Do not mechanically check all M1-M4 work-item boxes. Keep them as acceptance criteria and add a milestone status line that identifies the exact reviewed source and whether it is on `main`. This avoids claiming current-main behavior that is only present on a stack.
5. Replace §12.2’s “start M0 only” prompt with a current-state instruction to reconcile/deliver M1-M4 from current main and stop before M5.
6. Clarify §11: a merge into a milestone base is stack acceptance; final product delivery still requires a current-main PR with a fresh current-epoch exact-head check.

Adjacent stale current-state file: `engineering/runbooks/trust-ci-activation-report.md` still presents `6737355947c2` as the required check. Preserve the original activation evidence, but add a dated superseding epoch note or move “current required check” to `PROJECT_STATE.json`; do not rewrite old Check Run IDs as if they used the new epoch.

## README graph completeness validation

The graph is currently complete and must remain byte-for-byte equivalent in topology after the documentation repair:

- nodes: 16;
- unique undirected `---` edges: 120;
- expected complete-graph edges: `16 * 15 / 2 = 120`;
- missing edges: none;
- duplicate edges: none;
- self edges: none;
- graph node set equals the 16-row node-role table exactly.

Nodes:

```text
Route Skills Agents Hooks Policy Verify Packages Contract Decisions Mistakes
TrustAPI TrustWorker Postgres Runner Holdout GitHubApp
```

The state repair adds no runtime node, so the safest minimal change is to leave the Mermaid block and node-role table untouched. A status table outside the graph does not require a graph node.

Revalidation command:

```bash
python3 - <<'PY'
from pathlib import Path
import itertools, re
s = Path('README.md').read_text()
b = re.search(r'## Stack graph\n.*?```mermaid\n(.*?)```', s, re.S).group(1)
edges = [tuple(sorted(x)) for x in re.findall(r'^\s*(\w+)\s*---\s*(\w+)\s*$', b, re.M)]
nodes = {n for edge in edges for n in edge}
expected = {tuple(sorted(x)) for x in itertools.combinations(nodes, 2)}
assert len(nodes) == 16
assert len(edges) == len(set(edges)) == len(expected) == 120
assert set(edges) == expected
PY
```

## Regression and verification recommendations

Add/extend a deterministic state consistency test rather than relying on prose review alone:

1. `PROJECT_STATE.json` parses and uses the current required epoch/App pair.
2. README and START_HERE current-state sections contain the same epoch and milestone delivery labels.
3. `delivered_to_main=true` is allowed only for a milestone whose named main merge commit is an ancestor of the recorded observed main SHA (or whose GitHub PR base is `main` and merge commit is recorded).
4. A stacked PR cannot set `delivered_to_main=true` when `baseRefName != main`.
5. M5-M9 remain not started until M4 is delivered to main.
6. The K16/120-edge graph invariant remains green.
7. Historical decisions are not required to use the current epoch; only explicitly current-state sections are.

Then run the repository-required gate on the final product tree:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/grok_verify.py --mode pr
```

Any commit after verification or review invalidates fingerprint-bound local receipts. External merge eligibility requires a fresh `adaptive-trust-ci/verified@06ecf1c875bc` Check Run from App `4694114` on the exact final PR head.

## Commands used for this audit

Read-only command families:

```text
git for-each-ref / git worktree list / git log / git show / git ls-tree
git merge-base --is-ancestor / git rev-list --left-right --count
gh repo view / gh pr list / gh pr view / gh api .../branches/main/protection
gh api .../commits/<sha>/check-runs / gh api .../releases/latest
curl http://127.0.0.1:18080/health/live
curl http://127.0.0.1:18080/health/ready
```

No claim above relies on chat history or an unverified branch name alone.
