# Repository reuse analysis — single-operator Codex/GitHub pilot

## Evidence binding and method

This read-only inventory is bound to route `0ce2d62a018e` and repository HEAD
`6f3b6ed2853b7a6f78804888cffca578d4dc9448`, tree
`913f646649f878e97959d7ba2489a57de2379a1d` (parent `33206fa06ae4b5bfb390cb68bbf233800d2902ab`).
`git status --short --branch` showed only the untracked active change package.
The inventory used `rg`, `sed`, `find`, `git rev-parse`, and `git log`; it did
not run tests, invoke a model, fetch the network, or modify product/runtime state.

## Smallest safe reuse surface

| Stage | Reuse exactly | Ruling |
| --- | --- | --- |
| Issue intake and authority | `factory/src/adaptive_factory/contracts.py`: `TaskIntakeV1`, `TaskLimitsV1`; `factory/src/adaptive_factory/execution_contracts.py`: `AuthorityBindingV1`, `ProviderProfileV1`, `CapabilityPolicyV1`, `ExecutionSelectionV1`, `TaskPacketV1`, `RunManifestV1` | Reuse these closed identities and M4 lifecycle. `TaskIntakeV1` already admits `source_type="github_issue_projection"`. Add a pilot-specific closed `IssueSnapshotV1`; there is no current issue client or snapshot contract. Issue text is data only and must not select repository, base, model, commands, paths, branch, credentials, or grants. Override broad M4 limits with a trusted repository profile that permits exactly one Codex start and no automatic retry/repair. |
| Execution claim/result | `factory/src/adaptive_factory/service.py`: `FactoryService.claim_execution()` and execution finalization; `execution_contracts.py`: `WorkspaceResultV1` | Reuse claim/packet/result binding and durable idempotency. Do not let a provider self-assert eligibility. Extend through a narrow port/component rather than adding subprocess or GitHub behavior to the already-large service. |
| Pinned Codex call | `factory/src/adaptive_factory/landing_normalizer.py`: `CodexLandingProfile`, `CodexExecutionRequest`, `CodexExecutionResult`, `CodexLandingExecutor` protocol and `CodexLandingNormalizer` only as a design/test pattern; `factory/src/adaptive_factory/landing_provider.py`: `FixedCommandLandingProvider._verify_executable()` and `_run()` as an extraction pattern | The shipped normalizer is landing-draft/read-only and explicitly ships no live executor; it is not a code writer. Generalize the profile/executor record in the pilot component. Preserve exact executable SHA/version and prompt/tool/schema digests. Use argv with `shell=False`, empty/minimal environment, private stdin, bounded concurrent stdout/stderr, timeout, process-group termination, and one start. A timeout or ambiguous completion is terminal; never resume or call Codex again. |
| Private exact-base workspace and sealing | `factory/src/adaptive_factory/landing_renderer.py`: `ExactGitLandingWorkspace._private_directory()`, `_environment()`, `_clone()`, `_checkout_exact()`, `_seal_commit()`, `_tree_members()`, `_changed_paths()`, `_independent_objects()`; `factory/src/adaptive_factory/workspace.py`: `WorkspaceHandle`, `WorkspacePolicy`, `WorkspaceSnapshotV1` | Reuse the implementation pattern, not `ExactGitLandingWorkspace` itself: it is hard-coded to one landing SHA and two files and permits 1–3 attempts. Required properties are umask `077`, root `0700`, local clone with `--no-local --no-hardlinks`, sterile Git config, detached exact SHA/tree, removal of origin before Codex, no alternates/shared inodes, trusted NUL-safe path/tree inspection, allowlisted modes/paths, non-empty bounded diff, deterministic single-parent candidate commit, and cleanup evidence. (`--no-local` is meaningful for the configured local source/mirror; it adds nothing to an HTTPS clone.) |
| Workspace policy | `factory/src/adaptive_factory/workspace.py`: `FakeWorkspaceBroker`, `FakeGitBroker`, `HostIsolationReport` | Reuse the closed path/network/environment decisions and tests. These are fakes/probes, not a real isolation boundary. `HostIsolationReport.probe()` only discovers binaries/user namespaces; it does not prove bwrap/podman isolation or tool egress denial. The live actuator must fail closed unless an actual sandbox smoke/proof exists. Provider transport credentials and publisher credentials must never enter the model/tool workspace. |
| Targeted command | `FixedCommandLandingProvider._run()` bounded-process pattern; `trust-ci/src/adaptive_trust_ci/workspace.py` only as a design/test reference for sterile Git, incremental output caps, timeout and descendant cleanup | Run only the trusted repository-profile argv (`python -m unittest discover -s tests -v` for the currently analysed target, with the absolute interpreter pinned by trusted config). Capture command/profile digest, bounded result, and verify the sealed SHA/tree and worktree remain unchanged afterward. Do **not** import or modify `adaptive_trust_ci`; deployed Trust CI is a separate trust domain. |
| Semantic gate | `factory/src/adaptive_factory/semantic_bridge.py`: `SemanticExecutionBindingV1`, `SemanticValidationInputsV1`, `build_semantic_subject()`; `semantic_contracts.py`: `SemanticSubjectV1`, `SemanticFindingV1`, `SemanticCoverageV1`, `SemanticVerdictV1`; `semantic_adjudication.py`: `adjudicate()` | Reuse M6 exact result/acceptance binding and independent-validator checks. Only deterministic `pass` on the same frozen candidate permits publication. In this pilot, `repair` and `needs_human` are terminal because a repair loop would violate the one-invocation requirement. There is no live semantic evaluator runner yet; the pilot needs a narrow injected evaluator port/profile. |
| Durable evidence/replay | Existing M4 PostgreSQL lifecycle plus exact digest-linked M4/M5/M6 records; landing SQLite store only as a hardening/test pattern | Do not import `LandingSQLiteStore`: its schema and recovery states are landing-specific. Persist immutable issue, candidate, validation, publication-command, and observation records with predecessor digests and command-key replay/conflict semantics. Prefer extending the existing durable control lifecycle via a small store module/additive migration over creating a second workflow engine. A new datastore is architecture-red and requires rerouting/approval. Crash during Codex is terminal ambiguity; crash around an external effect permits read-only reconciliation only. |
| Publication | `.grok-stack/adaptive_grok/state.py`: `add_approval()`, `has_valid_approval()`; `scripts/grok_approve.py`; hook/grant tests | Reuse the exact route/change/control-HEAD/tree/TTL grant principle, not the runtime hook as product authority. Branch upload and PR creation are two separate effects. Current vocabulary has `production/git-push-branch` but no `pull-request-create`; PR creation can only use resource-bound `external-write` today. A pilot authorization adapter must additionally bind target repository, exact candidate SHA/tree/diff, exact `refs/heads/...`, and exact pulls endpoint. The current control-repository grant alone is insufficient to authorize a write from an external clone. Use a publisher-only least-privilege credential and non-force new-ref creation; after ambiguity, observe and adopt only one exact candidate match. |
| Human/Trust CI boundary | Existing App-owned Trust CI and M7 `OperatorHandoffProposalV1` / `ReadyForPrBundleV1` | Do not reuse these as publication authority. M7 explicitly records absent external capability/blocked handoff. Local success ends at an exact PR proposal. Trust CI exact-SHA success and partner merge/close are separately observed facts; the pilot must not merge, close, deploy, activate M8/M9, or synthesize approval. |

## Minimal vertical implementation shape

The smallest coherent control flow is a single restart-safe state machine with
five immutable, digest-linked outputs: `IssueSnapshotV1` -> `CandidateChangeV1`
-> `CandidateValidationV1` -> `PullRequestProposalV1` -> factual
`DesignPartnerOutcomeV1`. Each transition commits before the next side effect.
The first locally ready slice should stop after proposal creation; the last
outcome is an observer record and remains outside human authority.

Keep the external actuator outside `factory/src/adaptive_factory` and
`delivery/src`: existing fitness rules forbid the factory control domain from
GitHub/external-platform edges, and delivery is local preflight. The minimal
safe shape is a small explicit operator-integration component with:

- closed `pilot_contracts.py` values and canonical digests;
- a pure `pilot_coordinator.py` state machine over injected ports;
- narrow `issue_source.py`, `codex_executor.py`, `git_workspace.py`,
  `candidate_validator.py`, and `github_publisher.py` adapters;
- one durable `pilot_store.py` implementation and one disabled-by-default CLI;
- deterministic fakes for every external/process port.

The architecture owner must name that component/trust domain and declare its
filesystem, provider, and GitHub edges before source implementation. Do not hide
it under an ungoverned prefix. Factory interaction should remain through closed
contracts/a local service port; a direct Python dependency, if chosen, needs an
explicit architecture dependency edge.

The exact sequence is: observe one allowlisted issue/base once; commit snapshot;
acquire a private exact clone; remove acquisition capability; start one pinned
Codex process in proven isolation; freeze and attest one candidate; run one
fixed argv and independent semantic evaluation; commit validation; revalidate
the entire chain and two exact grants; create one non-force branch; reconcile
its exact SHA; create/adopt one exact PR; then observe, never produce, Trust CI
and the partner decision.

## Existing test patterns and minimal critical additions

- `factory/tests/test_execution_service.py`: trusted registry before claim,
  exact packet/result snapshot, replay/conflict, proposal attestation and
  substitution failures.
- `factory/tests/test_workspace.py`: traversal/absolute/`.git`/symlink denial,
  credential stripping, network/external Git denial, and exact snapshot binding.
- `factory/tests/test_landing_normalizer.py`: unavailable/profile-drift stops,
  exactly one injected call, malformed result and output fail-closed behavior.
- `factory/tests/test_landing_sqlite_store.py`: private durable store, exact
  schema identity, restart replay, conflicting idempotency, and bounded recovery.
- `factory/tests/test_semantic_bridge.py` and
  `factory/tests/test_semantic_adjudication.py`: cross-run/SHA/result
  substitution, acceptance coverage, validator separation, and deterministic
  pass/repair/human precedence.
- `trust-ci/tests/test_workspace.py`: copy only test ideas for NUL-safe bounded
  Git output and killing timeout/overflow descendants; never import the product
  implementation from Trust CI.
- `trust-ci/tests/test_webhooks_github.py`: fake structured transport and exact
  endpoint/body/replay pattern only; its client is check-run scoped, not an
  issue or PR publisher.
- `tests/test_policy.py` and `tests/test_hooks.py`: exact-action/resource grant
  invalidation, cross-repository/effective-root non-borrowing, wrappers and
  dynamic-shell fail-closed behavior.

Minimal new critical tests should prove: issue/base/profile substitution fails;
issue text cannot widen policy; one start across success/failure/timeout/crash;
no remote/credential/network/tool escape; no-local object independence; exact
path/mode/tree/diff sealing; test mutation/nonzero/overflow/timeout blocks;
semantic non-pass or writer/evaluator collision blocks; restart never repeats
Codex/push/PR; candidate/grant/ref/API substitution blocks; push is non-force;
ambiguous effects reconcile by exact identity without duplication; no code path
can merge/close/deploy. Add focused structure/architecture tests for the new
component and contract/schema round trips. No broad live GitHub/Codex test is
needed for local readiness.

## Do not reuse or extend

- Do not generalize `ExactGitLandingWorkspace`, `ExactGitLandingArtifactSource`,
  `CodexLandingNormalizer`, or `LandingSQLiteStore` in place; each embeds landing
  contracts/policies and would couple an arbitrary code writer to the static
  landing runtime.
- Do not use the fixture-only `factory/src/adaptive_factory/adapters/codex.py`
  as a live runner; its provider profile is intentionally execution-ineligible.
- Do not add network/subprocess/GitHub credentials to factory service/API/store
  monoliths, or import `adaptive_trust_ci` into factory/pilot.
- Do not expand the Trust CI GitHub App. Its source requests checks write plus
  contents/PR read; it is independent merge trust, not the pilot publisher.
- Do not treat `engineering/contracts/schemas/github-pull-request-projection.v1.json`
  as an issue or PR-create contract.
- Do not interpolate issue/PR Markdown into a shell command. Use structured JSON
  transport; prior repository evidence records command-substitution caused by
  backticks inside a double-quoted PR body.
- Do not use model-selected commands, `shell=True`, `eval`, remote-bearing model
  workspaces, force push, automatic rebase/retry/repair, M7 handoff status, M8/M9,
  or local receipts as merge authority.

## Architecture and source-size budget

The proposed behavior is not merely the active route's declared yellow
contract/job change. `architecture/rules.yaml` rule
`FIT-ARCHITECTURE-EXPANSION-RISK` classifies every new external integration,
network client, secret, edge, service, datastore, or trust crossing as **red**.
`FIT-FACTORY-NO-TRUST-OR-EXTERNAL-EDGE` forbids an edge from
`TD-FACTORY-CONTROL` to the external platform/production/trust domains, and
`FIT-TRUST-CI-SEPARATION` forbids mixing implementation and Trust CI changes.
Therefore the current medium/yellow route is insufficient if implementation
adds the real GitHub/Codex/credential edges without a formal architecture/risk
ruling. Resolve this before the writer edits source; do not weaken fitness rules.

Changed-code ceilings are: all governed change 1,300,000 bytes / 24,000 lines /
AST 5,000; factory 950,000 / 22,000 / AST 1,450; `factory/src` 235,000 / 5,500 /
AST 1,010; factory tests 510,000 / 7,500 / AST 425. Existing concentration makes
in-place growth especially costly: `factory/src/adaptive_factory/store.py`
is about 4,571 lines, `api.py` 1,331, `service.py` 984, while landing modules are
already specialised (`landing_renderer.py` 725, `landing_sqlite_store.py` 679,
`landing_normalizer.py` 522). Keep the vertical in small modules, avoid another
generic framework/provider registry, and add only one target profile, one test
command, one model, one repository and one serial run.

## Open implementation decisions that must fail closed

1. A real rootless sandbox and egress proof are absent. Binary discovery is not
   proof; if the Codex CLI's provider transport cannot be separated from tool
   process network/credentials, the live pilot is blocked.
2. The current grant schema has no explicit PR-create action and binds the
   control repository identity, not the external candidate identity. Until an
   exact candidate/ref/resource authorization design is approved, publication
   remains disabled.
3. There is no live GitHub issue client, writable generic Git broker, semantic
   evaluator runner, PR publisher, or durable pilot operation ledger. Missing
   ports/config/credentials must produce typed terminal states, never fallback.
4. Adding those external/secret/trust edges triggers red architecture risk.
   Local fake-transport implementation may proceed only after the architecture
   route and boundaries match the intended live capability.
