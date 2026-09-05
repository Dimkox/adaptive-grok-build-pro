# Task analysis — Stage 4 single-operator design-partner pilot

## Binding and product ruling

This analysis is bound to route `0ce2d62a018e`, control-repository predecessor
`6f3b6ed2853b7a6f78804888cffca578d4dc9448`, tree
`913f646649f878e97959d7ba2489a57de2379a1d`, and exactly one allowlisted target:

- repository: `github.com/Dimkox/ai-dark-factory-landing`;
- base ref: `refs/heads/main`;
- base commit: `699010380f4f90a0193a9c22090c35e6aded7d2c`;
- base tree: `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`.

The current product remains **Stage 3/5 — Offline Technical Preview** until one
real design-partner cycle completes all five outputs below. Source code and fake
transport tests can make the cycle ready to run; they do not themselves earn
Stage 4. Stage 4 means that one external issue reaches an exact-head PR and an
independent human decision without a human writing or repairing candidate code.

## MVP user-visible outcome

The operator selects one existing issue in the allowlisted landing repository
and starts one run. The system snapshots the issue and exact base, invokes one
pinned Codex process in a credential-free disposable clone, freezes the resulting
non-empty Git change, runs the target's configured unit suite and an independent
semantic gate, and—only under exact delegated grants—publishes one non-force
branch and creates one PR. It then observes the App-owned Trust CI result on that
exact head and records whether the design partner merged it or closed it without
merge.

The operator can inspect one immutable digest chain from issue snapshot through
human outcome. A stopped or failed run reports the exact terminal stage/reason;
it does not silently refresh the issue, rebase, invoke Codex again, force-push,
open another PR, or reinterpret missing evidence as success.

## Five sequential outputs and handoffs

Each output is canonical, immutable, durably stored, and includes the digest of
the preceding output. The names below are logical contract names; an equivalent
implementation name is acceptable only if every listed field and transition is
preserved.

### O1 — `IssueSnapshotV1`

**Producer:** read-only GitHub issue source adapter using trusted operator
configuration, never issue-provided routing.

**Required identity:** repository ID, issue number and immutable node ID, issue
`updated_at`, author identity/association observation, canonical title/body
digests, fetched-at time, source-adapter/profile digest, exact base ref/SHA/tree,
trusted repository-profile digest, acceptance IDs, and `issue_snapshot_digest`.
Issue text is untrusted data and cannot choose the model, prompt, tools, test
command, paths, branch, repository, base, credentials, or approval policy.

**Handoff gate O1 -> O2:** target and base equal the tuple above; issue and base
are observed once; input is within fixed byte limits; the snapshot commits before
model execution. Any issue/base drift after snapshot is `stale_input` and stops
the run rather than changing O1.

### O2 — `CandidateChangeV1`

**Producer:** one pinned Codex invocation supervised outside a private disposable
`--no-local` exact-base workspace.

**Required identity:** O1 digest, run/attempt identity (`attempt=1`), provider,
adapter, model, executable/version/SHA-256, prompt/tool/output-schema digests,
start/end/exit disposition, exact parent SHA/tree, candidate commit/tree, sorted
changed paths with modes/blob digests, canonical diff digest/size, workspace
snapshot digest, cleanup disposition, and `candidate_digest`.

**Handoff gate O2 -> O3:** exactly one Codex process was started; candidate is a
non-empty descendant of exact base; all changed paths and tools are allowed by
the trusted repository profile; `.git`, sibling repositories, remotes, sockets,
credentials, and tool-network access were unavailable to model tools; the
workspace is clean at the sealed candidate. Provider timeout, ambiguous provider
completion, policy escape, zero diff, oversize diff, or invalid Git identity is
terminal `needs_human`. There is no automatic second invocation.

### O3 — `CandidateValidationV1`

**Producer:** trusted test runner plus an evaluator identity distinct from the
Codex writer.

**Required identity:** O2 digest and exact candidate SHA/tree; fixed test-profile
digest; exact configured command identity (the target currently documents
`python -m unittest discover -s tests -v`, with the actual absolute interpreter
resolved by trusted configuration); exit code, bounded duration/output digest,
post-test tree identity, semantic subject/rubric/evaluator digests, per-acceptance
coverage, decision, reason codes, and `validation_digest`.

**Handoff gate O3 -> O4:** the one configured unittest command returns zero,
does not mutate the sealed candidate, and the independent semantic decision is
`pass` for that same SHA/tree. Any test failure, timeout, source mutation,
uncovered required acceptance item, writer/evaluator identity collision,
contradiction, `repair`, or `needs_human` stops without publication. Repair is a
new explicitly started run with a new O1, not an automatic child attempt.

### O4 — `PullRequestProposalV1`

**Producer:** the sole Git publisher/PR actuator, outside the model workspace and
unavailable without exact grants and a dedicated least-privilege credential.

**Required identity:** O3 digest; exact repository/base ref/base SHA; deterministic
proposal branch ref; candidate SHA/tree/diff; branch-push grant identity; PR-create
external-write grant identity; push observation; PR number/node ID/URL; exact PR
base/head repositories, refs and SHAs; created-at; stable candidate marker; and
`proposal_digest`.

**Handoff gate O4 -> O5:** immediately before effect, the actuator rechecks O1-O3,
remote base still equals `699010380f4f90a0193a9c22090c35e6aded7d2c`, candidate
bytes are unchanged, and both unexpired grants match the current control HEAD,
repository, exact branch/API resource, and actions. Push is non-force to one new
branch. PR creation is idempotent by repository plus candidate digest. After an
ambiguous response, read-only reconciliation may adopt only the exact matching
branch/PR; a differing branch, multiple PRs, base drift, or uncertain ownership
stops `external_outcome_ambiguous`. Never overwrite, force-push, update a PR head,
or create a duplicate.

### O5 — `DesignPartnerOutcomeV1`

**Producer:** read-only Trust CI/GitHub observer followed by a factual human
decision observation; the factory writes neither the check nor the decision.

**Required identity:** O4 digest; PR and exact frozen head; required check name,
deployed policy digest, GitHub App ID, check-run/attestation IDs, start/completion
times and `SUCCESS`; then human actor, decision time and one closed result:
`merged_accepted` with merge commit/tree, or `closed_rejected` with the unmerged
PR identity. The final payload has `outcome_digest` and the complete O1-O5 chain.

**Completion gate:** Trust CI belongs to the branch-protection-configured App and
is successful on exactly the unchanged PR head before the human decision. The
human—not the factory—merges or closes the PR. A wrong/missing App, policy, check
name, head, stale base, `ACTION_REQUIRED`, `FAILURE`, timeout, changed PR, or no
human decision leaves Stage 4 incomplete. Acceptance and rejection both complete
the design-partner feedback loop, but remain distinct product outcomes.

## Explicit MVP acceptance criteria

1. **One target and one source epoch.** Every output names the exact landing
   repository and `699010...` / `f7dbbd...` base. Any other repository, ref, SHA,
   tree, fork, or later `main` requires a new route/profile and new evidence.
2. **One issue, one run, one Codex invocation.** Exact replay returns the stored
   state. A conflicting replay fails. No automatic retry, repair child, provider
   fallback, or second model call occurs after success, failure, timeout, crash,
   or ambiguous provider completion.
3. **Real isolation.** Acquisition credentials exist only in the supervisor.
   Before Codex starts, the writable clone has no usable remote or credential.
   Model tools cannot reach the network, host/sibling paths, daemon sockets,
   Trust CI, GitHub, or provider credentials. The publisher never exposes its
   credential to the workspace.
4. **Exact candidate.** Trusted Git inspection—not model claims—derives parent,
   head, tree, diff, modes and paths. The candidate is non-empty, within fixed
   file/byte limits, and violates no repository-profile path/tool rule.
5. **One trusted test command and independent semantics.** Tests and semantic
   evaluation bind the same frozen candidate. Only test exit zero plus semantic
   `pass` permits O4. The model cannot edit the test profile, acceptance set,
   evaluator identity, or verdict.
6. **Restart-safe evidence.** A restart after any committed output resumes from
   that output without repeating earlier effects. A crash during Codex becomes
   terminal ambiguity; a crash around push/PR creation performs observation-only
   reconciliation. Stored records and their digest links are revalidated before
   use; corruption fails closed and is never rewritten as success.
7. **Two separately authorized GitHub effects.** Branch upload requires an exact
   `production/git-push-branch` grant for the deterministic target ref. PR creation
   requires an exact `external-write` grant for the target repository's pulls API
   resource because the current local grant vocabulary has no distinct
   `pull-request-create` production action. Neither grant authorizes merge,
   close, label, comment, release, deployment, or another repository.
8. **Independent exact-SHA gate.** Local tests/reviews and proposal receipts are
   preflight evidence only. O5 requires the deployed App-owned Trust CI check on
   the exact PR head. The Trust CI App installation, repository policy/profile,
   branch protection and any human-signed approval scopes must actually exist for
   the landing repository; configuration proven only for the control repository
   is insufficient.
9. **Human boundary.** The system cannot accept its own work. It observes one
   explicit partner merge or close-without-merge and records it without triggering
   merge/close. One cycle does not activate M8, M9, auto-merge, deployment, or
   earned autonomy.

## Non-goals

- Multiple repositories, issues, operators, tenants, concurrent workers, queues,
  scheduling, HA, throughput optimization, or a generic agent framework.
- Claude support, provider selection, automatic fallback, model competition,
  retries, self-repair, more than one test command, or unattended follow-up runs.
- Issue creation/editing, comments, labels, project-board changes, reviewer
  assignment, force-push, PR update, merge, close, branch deletion, release, tag,
  deployment, hosting, cPanel, DNS/TLS, or production-site mutation by the pilot.
- New GitHub Actions, modification of deployed Trust CI policy/holdout/App keys,
  creation of human approval material, or treating a local receipt as merge
  authority.
- Generalizing the landing renderer/workspace into an arbitrary repository
  executor, changing published `v2.0.14` bytes, or claiming Stage 5/Shapiro L5.

## Critical gate versus backlog

Only these classes block local readiness or reopen a frozen candidate:

- the O1 -> O5 core path cannot produce or verify an exact, internally consistent
  handoff for the configured target;
- caller/model data can widen repository, base, paths, tools, provider, tests,
  evaluator, branch, PR, credentials, grants, or Trust CI authority;
- tenant/operator isolation or credential/network/process/workspace separation
  can be bypassed;
- a crash/replay can duplicate Codex, overwrite/push the wrong branch, create a
  second PR, lose a committed output, accept corrupted evidence, or associate a
  check/human decision with the wrong head;
- tests or semantic/Trust CI non-pass can be bypassed, or the system can merge or
  close without the human.

Minor error-copy quality, additional GitHub error variants, richer diagnostics,
rate-limit tuning, uncommon filesystem cleanup cases that cannot affect retained
evidence, broader repository portability, performance/soak work, dashboarding,
and extra semantic heuristics are backlog. A minor finding becomes blocking only
if it demonstrates a core-path break, authority/isolation bypass, or data/evidence
loss or corruption.

## Finite execution and stop conditions

- Local implementation evidence uses deterministic issue/Codex/GitHub fakes and
  the smallest focused tests. After tracked state is frozen, run one exact-head
  PR verifier and one parallel route-selected code/test/security review wave.
  Rerun only a failed/affected check after a source repair; do not repeat passing
  suites for paperwork or accumulate open-ended edge requirements.
- The local route may finish `ready` with O1-O5 contract/replay behavior proven by
  fakes and every external actuator disabled by default. It must not claim Stage
  4 from that result.
- A live pilot is a separately authorized run. It stops after one O5 human result
  or immediately on missing target Trust CI policy/App/branch protection,
  missing/expired exact grant or credential, source/issue/head drift, Codex
  ambiguity/failure, validation non-pass, external-effect ambiguity, or elapsed
  operator window. There is no background wait/retry loop.
