# Architecture analysis — single-operator Codex/GitHub pilot

## Evidence binding and ruling

This read-only analysis is bound to route `0ce2d62a018e`, base/HEAD
`6f3b6ed2853b7a6f78804888cffca578d4dc9448`, and tree
`913f646649f878e97959d7ba2489a57de2379a1d`. The worktree contained only the
untracked active change package when inspected. No test suite, model call,
network request, credential read, Git write, or external effect was performed.

The smallest coherent design is a **separate, disabled-by-default,
operator-owned pilot CLI and state machine**. It may reuse hardened patterns and
pure value semantics from the repository, but it must not change the existing
M5 Codex adapter to eligible, expose M5/M6 endpoints, consume M7/M8
recommendations as authority, or replace the fake M9 environment. The existing
source explicitly says that M4–M9 execution and delivery are disabled and have
no operational provider, network, deployment, or production authority
(`START_HERE.md:13`); `CodexAdapter` likewise declares
`missing_capabilities=("rootless_host_isolation",)` and
`execution_eligible=False` (`factory/src/adaptive_factory/adapters/codex.py:6-15`).

There are two independent readiness conclusions:

1. The repository can implement and verify the closed pilot component with
   deterministic fakes and an unavailable live composition.
2. This host is **not live-execution-ready**. The observed Codex 0.153.4 helper
   smoke failed with
   `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. This is only
   evidence that the assembled confinement path is unusable on this host; it
   does not establish the kernel/root cause. Until a later exact-launcher smoke
   positively proves the required boundary, the job must stop as
   `needs_human/process_confinement_unavailable` before Codex or target tests
   start and before any PR is possible.

## Route and post-diff risk ruling

The active route does **not** need to be regenerated merely because the final
architecture diff escalates from yellow to red:

- verification deliberately maps route `medium` to pre-risk `yellow`
  (`.grok-stack/adaptive_grok/verification.py:64-66`);
- fitness computes `risk_post = max(risk_pre, escalation)` and retains the
  triggers (`.grok-stack/adaptive_grok/architecture_fitness.py:2218-2235`);
- verification records `risk_pre`, `risk_escalation`, and `risk_post`
  (`.grok-stack/adaptive_grok/verification.py:96-104,138-140`);
- the architecture policy assigns red to the new datastore, edges, external
  integration, network client, secret, and trust crossing that this real pilot
  necessarily introduces (`architecture/rules.yaml:582-599`);
- the same fitness result derives `architecture`, `security`, `data`, and
  `contract` scopes when those exact triggers are present
  (`.grok-stack/adaptive_grok/architecture_fitness.py:2380-2401`).

No inspected verifier or spec path requires `route.risk == spec.risk`, mutates
the route, or requests a reroute after this monotonic escalation. Route
`0ce2d62a018e` already selected the architect/integration analyses, the sole
`integration_implementer`, and independent code/test/security reviews needed by
this bounded work. Retaining it is therefore the intended use of post-diff risk,
provided the writer does all of the following:

- set `change-spec.yaml` to `risk.tier=red`;
- list explicit forbidden outcomes;
- list at least `architecture`, `security`, `data`, and `contract` in
  `approvals.required_scopes`, then reconcile that list against the exact final
  fitness output rather than guessing it;
- require exact architecture fitness evidence showing
  `risk_pre=yellow`, `risk_escalation=red`, `risk_post=red`, with every
  applicable category passing;
- keep all route-selected reviews on that exact final fingerprint.

The typed-spec completeness gate requires forbidden outcomes and non-empty
scopes for red risk (`.grok-stack/adaptive_grok/spec.py:746-758`), but those
strings are a risk/approval requirement declaration, **not an approval or an
operational grant**. This local ruling cannot authorize Codex data transfer,
branch upload, PR creation, merge, Trust CI publication, or deployment. A reroute
is required only if implementation changes the task/agent set beyond the current
route, not simply to restate the red post-risk already designed into fitness.

## Options considered

| Option | Result |
| --- | --- |
| Turn on M5–M9 and add GitHub to `TD-FACTORY-CONTROL` | Rejected. It would contradict the shipped disabled state and violate `FIT-FACTORY-NO-TRUST-OR-EXTERNAL-EDGE` (`architecture/rules.yaml:170-190`). |
| Extend the landing runtime/provider/store in place | Rejected. Its contracts, state recovery, exact landing source, attempts, and artifact semantics are landing-specific; generalization would couple an arbitrary code writer to L5 and falsely imply that its provider/publisher is live. |
| Add one explicit operator-pilot component with narrow ports and private SQLite | **Recommended.** It is operationally honest, one-process and reversible, adds no daemon/queue/framework, and can remain unavailable when credentials or confinement are absent. |

## Trust domains and capabilities

The architecture must distinguish these principals even if a single operator
starts them from one CLI:

| Boundary | Holds | Must not hold/do |
| --- | --- | --- |
| Operator control/coordinator | Immutable profile identity, state transitions, evidence digests, local grant verifier | No provider/GitHub secret bytes; no shell built from issue/model content; no merge/check/deploy authority |
| GitHub broker | One repository-scoped credential handle; issue-read and later branch/PR methods | No Codex auth; never enters model/test namespace; no force/update/delete/merge/close operation |
| Codex supervisor | Exact Codex executable/profile and provider-auth handle; provider transport | No GitHub credential/remote; no authority to choose repo/base/path/test/branch/grant; raw stream is not durable authority |
| Confined writer workspace | One private worktree, issue snapshot as untrusted data, allowlisted application paths | No secrets, remotes, host sockets, other repositories, `.git` writes, Trust CI paths, or tool network |
| Confined validation workspace | Sealed candidate, fixed unittest argv, read-only source plus private temp | No provider/GitHub auth, network, application mutation, or use of writer identity |
| Trust CI and human acceptance | Existing App-owned exact-SHA check and human decision | The pilot cannot write, synthesize, or substitute either authority |

The issue body, target repository, generated diff, Codex events, and test code
are untrusted data. The operator-owned profile is the only authority for the
repository, exact base, allowed paths/modes, executable/model, prompt/tool
policy, one test argv, bounds, branch prefix, and GitHub endpoints. No issue or
model field may become an executable, argv option, environment name, path,
remote, ref, URL, credential locator, grant resource, or state transition.

## Minimal component and closed interfaces

Place the live integration in a new governed top-level `operator-pilot/`
package, not under `factory/src/adaptive_factory`, `delivery/`, or `trust-ci/`.
It is one CLI process with small modules, not a service or platform:

- `contracts.py`: closed version-1 records and canonical domain-separated
  digests;
- `coordinator.py`: the only state-transition owner;
- `store.py`: private single-writer SQLite and immutable event/effect ledger;
- `issue_source.py` and `github_publisher.py`: structured, transport-injected
  GitHub adapters;
- `git_workspace.py`: private clone, exact checkout, candidate sealing, and
  independent validation clone;
- `codex_executor.py`: exact-profile, one-start supervisor over an injected
  confinement launcher;
- `gate.py`: trusted unittest runner plus deterministic independent
  adjudication;
- `cli.py`: only `run`, `status`, and read-only `reconcile`; no daemon/API.

Use deterministic fakes for every network/process/effect port. Reuse the
repository's canonical JSON/digest conventions and the hardening patterns in
`ExactGitLandingWorkspace`, `FixedCommandLandingProvider`, and
`SQLiteLandingJobStore`; do not import the specialised landing classes. Never
import or modify `adaptive_trust_ci`. M6's fail-closed adjudication precedence is
a useful pattern, but the pilot must not fabricate an M5 `WorkspaceResultV1` or
M6 holdout/review facts merely to instantiate its contracts. A pilot-owned
`CandidateGateV1` is more truthful than claiming a live M6 verdict.

The minimum closed records are:

- `PilotProfileV1`: one repository, normalized GitHub owner/name and endpoints,
  allowed source locator digest, exact base SHA, allowed path roots/modes and
  diff ceilings, exact Codex path/version/SHA/model/prompt/schema/tool-policy
  digests, one tuple argv for `python -m unittest ...`, all resource ceilings,
  deterministic branch prefix, and profile epoch; no credentials;
- `IssueSnapshotV1`: repository, numeric issue, GitHub node ID, state,
  `updated_at`, bounded title/body bytes and digest, observed base SHA, profile
  digest, and snapshot digest;
- `IsolationCapabilityEvidenceV1`: exact launcher/helper/profile digests,
  positive denial/capability checks, host-profile digest, bounded observation
  time, status, and evidence digest; it is local capability evidence, not Trust
  CI attestation;
- `CodexRunV1`: snapshot/profile/workspace identities, exactly one invocation
  sequence, start/finish times, exit/disposition, bounded usage where available,
  stdout/stderr digests and sizes, and executor evidence digest; no raw streams;
- `CandidateV1`: exact base, single-parent candidate commit, tree, NUL-safe
  changed-path inventory, diff digest/line count, profile/snapshot/Codex evidence
  digests, and candidate digest;
- `CandidateGateV1`: candidate, test-profile/result, validation-workspace and
  independent-evaluator identities, requirement coverage, immutable-tree check,
  decision/reason and gate digest;
- `ExternalEffectV1`: effect kind, canonical target resource, exact candidate
  and grant digest, intent sequence, observation identity, state, and digest.

The repository profile may be configured outside source in an owned mode-0600
regular non-link file. Credential handles are separate inputs owned by their
adapter. Absence, drift, partial configuration, unexpected keys, links, broad
paths, dynamic argv, non-exact SHA, or ambiguous endpoint normalization blocks
composition; there is no fallback model, repo, command, or credential.

## End-to-end state machine

The finite happy path is:

```text
created
  -> issue_snapshotted
  -> workspace_ready
  -> invocation_intent
  -> candidate_sealed
  -> validation_intent
  -> gate_passed
  -> awaiting_grants
  -> branch_intent -> branch_observed
  -> pr_intent -> pr_observed
  -> awaiting_human
```

Terminal local states are `rejected`, `needs_human`, and `cancelled`. There is
one issue snapshot, one model invocation intent, one candidate, one unittest
command, one semantic adjudication, at most one new branch effect, and at most
one draft-PR effect. There is no retry/repair/resume/fallback loop. The finite
stop condition is a factually observed draft PR bound to the exact candidate,
after which the pilot returns `awaiting_human` and exits. It does not poll or
publish Trust CI, accept, merge, close, tag, release, deploy, or activate M8/M9.

### 1. Snapshot

The GitHub broker reads exactly one issue from the allowlisted repository and
records the bounded immutable snapshot before downstream work. Re-fetch is not
allowed after the snapshot is durable. A changed issue creates a new job; it
does not mutate the old snapshot. Provider data-transfer consent must be an
operator-owned profile/command fact bound to this snapshot because sending a
private issue/source to Codex is an external disclosure even though it is not a
GitHub write.

### 2. Private Git workspace

Create a root outside both the control repository and source repository under
umask `077`; require owned, mode-0700, non-link directories. Clone with sterile
Git configuration, `--no-local --no-hardlinks --no-tags`, no recursive
submodules, then detach at the configured exact base SHA and verify its tree.
For a local source, prove there is no alternates file, shared object inode, or
shared common Git directory. (`--no-local` adds no security property to an HTTPS
transport; the object independence still must be checked.) Remove the origin,
credential helpers, hooks, and acquisition environment before Codex starts.

Codex receives the worktree application view and approved writable paths, not
the Git control directory. After its one call, trusted code rejects an empty or
over-limit diff, disallowed path/mode, symlink, submodule/gitlink, special file,
`.git` change, binary where forbidden, source/base drift, or untracked member
outside policy. It creates one deterministic single-parent candidate commit
with trusted author/message/time inputs and records commit/tree/diff identities.
The model cannot commit or name the branch.

Create a second private `--no-local --no-hardlinks` clone detached at that
candidate for validation. This prevents target tests from mutating the sealed
writer repository and lets the gate verify both repositories after execution.

### 3. Process confinement and one Codex call

A private clone is an **integrity and aliasing boundary**, not a process
security boundary. Without OS confinement, Codex and repository tests still run
as the operator UID and can read any operator-readable repository, credential,
socket, or host path and use any reachable network. File mode 0700, a sterile
environment, `shell=False`, Codex `--sandbox workspace-write`, and absence of a
remote do not change that fact.

The existing `HostIsolationReport.probe()` only finds bwrap/podman,
newuidmap, an egress helper, and a supplied userns boolean
(`factory/src/adaptive_factory/workspace.py:404-430`). It is a discovery probe,
not activation proof. The pilot needs a concrete launcher smoke for the exact
assembled profile that proves all of these before `invocation_intent`:

- only the private workspace and dedicated temp are visible; an external
  sentinel and control/source repositories are unreadable;
- only configured application roots are writable and `.git` is not writable;
- model-generated tools cannot reach the network or host sockets;
- GitHub, Trust CI, and other host credentials are absent and unreadable;
- provider transport/auth is confined to the Codex supervisor and cannot be
  inherited or read by its tool children;
- process, CPU, memory, file, output, and wall limits work and descendant
  cleanup is positively observed.

The current bwrap failure makes this capability false. Do not weaken the profile
to `danger-full-access`, reinterpret the private clone as a sandbox, or add a
container/proxy platform in this slice. A later reviewed launcher/environment
repair may supply fresh positive evidence; until then live composition remains
unavailable.

When eligible, persist `invocation_intent` before exactly one `Popen`. Use a
fixed argv tuple, `shell=False`, prompt on stdin, no issue content in argv, exact
binary/version/digest/model, ephemeral/ignore-user-config/ignore-rules modes,
closed final-output schema, JSONL, bounded concurrent stdout/stderr reads,
`close_fds`, a new process group, monotonic timeout, and process-group kill.
Any transition into invocation consumes the one attempt. Timeout, overflow,
unknown/malformed stream, missing or duplicate terminal, unexpected tool
capability, nonzero exit, cancellation, or crash is terminal `needs_human` or
`rejected`; never call Codex again for that job.

### 4. Deterministic gate

“Deterministic” means the trusted decision function has closed inputs and fixed
precedence; it does not claim that untrusted tests or a model are reproducible.
The gate operates only on the sealed candidate and consists of:

1. recompute base/parent/tree/diff/path/mode/profile/snapshot/Codex bindings;
2. run exactly the operator-profile unittest argv, with an exact interpreter,
   no shell, no network or credentials, read-only candidate source, private
   temp, bounded output/time/processes, and `PYTHONDONTWRITEBYTECODE=1`;
3. recheck that candidate and validation trees did not change;
4. run a separate trusted pure evaluator identity over the closed pilot
   requirement set, changed-path policy, test evidence, and prohibited outcomes;
5. emit `pass` only when every requirement is proven and no finding exists.

The Codex writer cannot provide evaluator evidence or select its outcome.
`repair`, contradiction, unsupported coverage, test nonzero/timeout/overflow,
test mutation, identity drift, or evaluator/writer identity collision becomes
terminal `needs_human`/`rejected`. There is no second Codex call.

### 5. Grant-gated branch and draft PR

Publication is an adapter capability absent from Codex and the workspaces. The
coordinator revalidates the complete exact chain and a fresh grant immediately
before each mutation:

- branch creation requires existing `production/git-push-branch` plus an exact
  resource such as
  `github://OWNER/REPO/refs/heads/PREFIX/JOB@CANDIDATE_SHA?tree=TREE`;
- PR creation uses today's existing `external-write/external-write` vocabulary
  with an exact canonical pulls resource that also binds owner/repo, base ref
  and base SHA, head ref, candidate SHA/tree, title/body digest, and
  `draft=true`. Do not invent or claim a `pull-request-create` action that
  `state.py` does not currently support.

The current local grants are bound to control repository, route/change, exact
control HEAD/tree, TTL, action, and optional resource
(`.grok-stack/adaptive_grok/state.py:190-249,252-306`). That control binding
alone is insufficient for an external candidate; the pilot's `GrantVerifier`
must require the exact target resource above and bind its digest into the effect
intent. Recheck expiry immediately before transport invocation. Hooks are
defense in depth, not the nested publisher's authority.

The publisher credential is repository-scoped and enters only the GitHub broker
after gate pass. First observe that the deterministic ref is absent. Push only
`CANDIDATE_SHA:refs/heads/...` without force; if the ref already equals the
candidate, adopt it, while any other value is `needs_human/ref_conflict`.
Read back the exact ref. Require the remote base ref still equals the bound base
SHA; never rebase automatically.

Before PR POST, query by exact owner/repo/head/base and a deterministic hidden
job/candidate marker. Adopt only one exact match, reject conflicts, otherwise
create one draft PR and read it back. The pilot never relies on POST
idempotency, never blindly repeats an ambiguous write, and never expands a
branch grant into PR/merge/delete authority. Trust CI is then triggered and
evaluated through its existing external GitHub/App path; the pilot does not
hold that App key or manufacture its check.

## Durable recovery and evidence retention

Use a separate private SQLite file for this one-process operator pilot, modelled
as its own datastore rather than reusing landing tables. Follow the existing
hardening pattern: absolute root outside repositories, owned mode-0700 non-link
directory, owned mode-0600 regular single-link DB, distinct
`application_id`/`user_version`, exact schema inventory, foreign keys,
`journal_mode=WAL`, `synchronous=FULL`, busy timeout, `quick_check`,
`BEGIN IMMEDIATE`, bounded recovery, and optimistic revision checks. This is a
new datastore and is why the red spec must include `data` scope; it must not be
hidden to avoid the risk trigger.

Keep three minimal tables: current `jobs`, append-only `events`, and
intent/observation `effects`. Every row carries job/profile/snapshot/candidate
predecessor digests, a unique command key, revision, and bounded timestamps.
The private issue snapshot may be retained because it is needed as immutable
input, but it is never logged. Do not persist prompts, raw Codex JSONL,
reasoning, raw stdout/stderr, auth headers, token values, Git config, or raw
commands. Logs contain only job/state/reason, SHA/digests, counts, durations,
and effect status. Store safe GitHub observation fields only; hash bounded
diagnostics.

Recovery is state-specific and never speculative:

| Durable last state | Restart action |
| --- | --- |
| before `invocation_intent` | Revalidate immutable inputs; operator may start a new bound attempt only if the same job has never consumed one |
| `invocation_intent` without complete result | `needs_human/model_outcome_ambiguous`; inspect/clean workspace, never invoke again |
| sealed candidate before validation intent | Resume the not-yet-started local gate on the exact candidate |
| `validation_intent` without result | `needs_human/gate_outcome_ambiguous`; no automatic test replay |
| branch/PR intent without observation | Perform read-only remote reconciliation; adopt only an exact match, otherwise `needs_human`; no blind write retry |
| observed effect / `awaiting_human` | Return the durable fact idempotently; perform no effect |

A deliberate operator recovery may create a new job or, for a proven-absent
external effect, issue a fresh exact grant and explicit new effect command. It
must never rewrite the old event chain or turn ambiguity into automatic retry.

## Architecture-model impact

Model the capability before adding the network client. The minimum truthful
changes are:

- new `TD-OPERATOR-PILOT-CONTROL` and
  `TD-OPERATOR-PILOT-EXECUTION` domains using the existing
  `local_preflight` kind but distinct owners/capabilities;
- nodes for pilot control, pilot SQLite, GitHub broker, Codex supervisor,
  confined workspace/gate runner, and the external model provider; reuse the
  existing GitHub node;
- restricted data classes for issue/source/candidate/effect state, separate
  pilot GitHub and Codex secret classes, and a pilot failure signal;
- explicit local filesystem/SQLite edges, a provider HTTPS edge only from the
  Codex supervisor, and issue/publication HTTPS edges only from the GitHub
  broker; the execution runner has no network edge and no secrets;
- forbidden edges from pilot execution to every external/trust/production
  domain, and from pilot control to Trust CI and production trust;
- secret-flow rules allowing each pilot secret only in its broker/supervisor
  domain and extending runner no-secret policy to both pilot secrets;
- code-budget, module-boundary, network-client, tenant/restricted-data, and
  implementation-versus-Trust-CI separation coverage for `operator-pilot/`;
- closed pilot schema inventory and regenerated five Mermaid projections.

All new runtime entries remain `evidence=source_described`. Do not relabel them
`externally_proven` because source tests pass or because an operator later runs
one local job. Existing M4–M9 node runtimes, edges, contracts, and unavailable
flags remain unchanged.

## Finite acceptance criteria

1. With default/missing/drifted profile or failed isolation smoke, composition
   performs zero Codex/test/GitHub-write calls and returns a typed blocked or
   `needs_human` fact; the current host bwrap observation exercises this path.
2. An issue snapshot is accepted only for the one allowlisted repo/number and
   exact base/profile; hostile issue text cannot change any executable policy
   field.
3. The generation clone and validation clone are private, exact, non-shared,
   remote/credential-free, and fail closed on links, alternates, gitlinks,
   object aliasing, base drift, path/mode violations, or incomplete cleanup.
4. Each job can cross `invocation_intent` at most once across success, failure,
   timeout, cancellation, concurrent invocation, and process restart. Raw
   commands, content, model streams, and secrets never enter logs/evidence.
5. Exactly one fixed unittest argv and one independent pure semantic evaluation
   bind the same candidate. Only exit zero, immutable trees, complete proven
   coverage, and no finding yield `gate_passed`; no result causes repair/retry.
6. SQLite replay/conflict/restart tests prove ordered digest-linked state,
   single-writer concurrency, terminal ambiguous states, bounded recovery, and
   zero repeated Codex/push/PR effects.
7. Push and draft-PR fakes prove exact resource/grant/current-control-tree and
   candidate binding, expiry recheck, non-force new-ref behavior, stale-base and
   conflicting-ref rejection, exact read-back, and ambiguity reconciliation.
   There is no merge/close/delete/tag/release/deploy code path.
8. Architecture validation/fitness on the final exact tree passes and records
   yellow pre-risk, red escalation/post-risk, expected triggers and exact
   required scopes; typed spec and route-selected reports bind that tree.
9. Existing M5 adapter remains `execution_eligible=False`; default M5/L5
   provider/publisher composition and all M7–M9 operational flags remain
   unchanged; Trust CI files and deployed authority are untouched.

Focused tests should use local bare repositories, fake GitHub/model transports,
fake grant/time/crash seams, and an exact harmless confinement canary. A real
Codex/GitHub run is activation evidence after this source change, not a PR
verification dependency. No broad live suite or production credential is needed
to make the source a local PR candidate.

## Rollback and forward recovery

Rollback is bounded because the pilot is opt-in and separate:

1. disable/remove the pilot CLI/profile and revoke its Codex/GitHub credential
   handles and unexpired local grants;
2. leave the private SQLite/evidence file read-only for audit, or remove an exact
   job workspace only through an explicit operator cleanup command;
3. revert the operator-pilot source/model additions without changing M4–M9,
   Trust CI, published packages, or the external target repository.

Never make rollback itself an ungranted remote effect. A branch already pushed
or draft PR already created is left for the human operator; deleting the branch
or closing the PR requires a new exact external grant and is outside this
slice. For an ambiguous effect, forward recovery is read-only observation and
exact adoption or `needs_human`, never speculative replay. The safest terminal
artifact is always the immutable candidate/evidence chain; no local status can
make it merge authority.

## Explicit non-goals and residual limitations

- no multi-repository/multi-operator scheduler, daemon, webhook intake, queue,
  generic provider framework, automatic repair, second model, auto-rebase,
  auto-merge, deployment, cPanel, M8 cohort, or M9 environment;
- no GitHub App/Trust CI key reuse and no human approval-key access;
- no claim of weight-level model reproducibility when the provider exposes only
  an operator-configured model identifier;
- no claim that clone privacy confines a process;
- no live activation on the currently observed host until an exact, reviewed
  confinement repair passes the complete capability smoke.

## 2026-09-05T15:16Z amendment — confinement remediation

This supersedes only the stale host-readiness conclusion at lines 26–33 and the
last residual-limitation bullet above. Later operator-safe, no-model evidence
reports that, after a scoped Ubuntu AppArmor/bwrap remediation,
`codex sandbox -P :workspace -C /home/pall/grok-projects/adaptive-grok-build-pro-pilot -- /bin/true`
exited `0`; a boundary sample denied an outside write with `EROFS`, denied IPv4
socket creation with `EPERM`, and left the outside sentinel absent. The original
`RTM_NEWADDR` failure is therefore no longer an unconditional host blocker. This
is positive confinement-canary evidence, not evidence of a live model call or
pilot activation; live eligibility must still bind the exact final launcher,
profile, workspace and capability evidence and satisfy the remaining criteria.
