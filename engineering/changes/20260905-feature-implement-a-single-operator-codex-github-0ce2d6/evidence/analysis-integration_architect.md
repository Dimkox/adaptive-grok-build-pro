# Integration contract — single-operator GitHub proposal pilot

## Scope and evidence binding

This read-only analysis is bound to route `0ce2d62a018e` and control-repository
base `6f3b6ed2853b7a6f78804888cffca578d4dc9448`. No credential was read, no test or
model was run, and no network or external write was attempted.

The target identity was verified from the locally available Git object at
`/home/pall/grok-projects/ai-dark-factory-landing`, without fetching:

| Property | Closed value |
| --- | --- |
| GitHub repository | `Dimkox/ai-dark-factory-landing` |
| Internal repository ID | `github.com/Dimkox/ai-dark-factory-landing` |
| Canonical Git URL | `https://github.com/Dimkox/ai-dark-factory-landing.git` |
| Base ref | `refs/heads/main` |
| Exact base commit | `699010380f4f90a0193a9c22090c35e6aded7d2c` |
| Exact base tree | `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4` |
| Allowed changed paths | non-empty subset of `content.css`, `index.html` |
| Allowed changed modes | regular non-executable `100644` only |
| Explicitly protected member | `index.css`, Git blob `4117a5f263d3500af4d397d3eac07f0d7b89b167`, SHA-256 `91ae1c46ae5cc825d72e9ebde91e93901d0d8413d55f27f322613a593b8b1589` |
| Other source members | immutable for this pilot |
| Configured test argv | `(<trusted-absolute-python>, -m, unittest, discover, -s, tests, -v)` |
| Proposal kind | draft pull request only |
| Force, deletion, merge, close, label, comment | forbidden |

These values agree with `PROJECT_STATE.json` and the constants in
`factory/src/adaptive_factory/landing_renderer.py`. The target README at the
exact commit documents `python -m unittest discover -s tests -v`. The absolute
Python path and executable digest must come from trusted operator configuration,
not from the issue or target worktree.

## Integration ruling

The safe vertical is an immutable digest chain:

`TargetProfileV1 -> IssueSnapshotV1 -> CandidateChangeV1 -> CandidateValidationV1 -> BranchPushReceiptV1 -> ProposalReceiptV1`.

Each record is committed before the next effect. Caller data, issue data, Codex
output, and GitHub response data may never alter the target profile, base, path
allowlist, test command, branch derivation, grant scope, or credential source.
`TaskIntakeV1.source_type="github_issue_projection"` may carry the snapshot
digest into the existing task lifecycle, but the Trust CI pull-request projection
schema is not an issue-intake or proposal-create schema.

Local readiness should use deterministic transports. A real GitHub transport is
an external-platform/secret edge and must remain disabled unless the architecture
model and route authorize that edge. The existing factory domain must not import
or reuse the Trust CI GitHub App client.

## Closed target profile

`GitHubPilotTargetV1` must be a closed, canonical contract. Its digest covers at
least:

```text
schema_version = 1
profile_id = "landing-design-partner-699010"
repository_id = "github.com/Dimkox/ai-dark-factory-landing"
github_full_name = "Dimkox/ai-dark-factory-landing"
canonical_git_url = "https://github.com/Dimkox/ai-dark-factory-landing.git"
base_ref = "refs/heads/main"
base_sha = "699010380f4f90a0193a9c22090c35e6aded7d2c"
base_tree = "f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4"
allowed_write_paths = ["content.css", "index.html"]
protected_index_css_blob = "4117a5f263d3500af4d397d3eac07f0d7b89b167"
protected_index_css_sha256 = "91ae1c46ae5cc825d72e9ebde91e93901d0d8413d55f27f322613a593b8b1589"
allowed_modes = ["100644"]
test_argv = [<trusted-absolute-python>, "-m", "unittest", "discover", "-s", "tests", "-v"]
branch_prefix = "adaptive-pilot/issue-"
max_codex_starts = 1
allow_force = false
allow_merge = false
allow_close = false
trust_ci_profile = null
branch_protection_observation = "unavailable_private_plan_403"
```

The candidate branch is derived, never supplied:
`adaptive-pilot/issue-<issue-number>-<candidate-sha12>`. It must match a strict
ASCII ref-name grammar, be under `refs/heads/`, differ from `refs/heads/main`, and
contain no ref ambiguity. The profile accepts one serial run only.

The configured path policy is a non-empty subset, not an instruction to rewrite
both files. All other tracked paths and modes must remain byte-identical to the
base. Symlinks, gitlinks, alternate object stores, special files, executable-bit
changes, `.git/**`, `.github/**`, and new paths fail closed. Trusted Git inspection
must also prove a clean sealed worktree, exactly one candidate commit whose first
parent is the configured base, and the configured base/tree pair.

## Exact issue-intake interface

The issue reader is read-only and returns a bounded projection, never a raw API
object:

```python
class GitHubIssueIntake(Protocol):
    def snapshot(
        self, request: IssueSnapshotRequestV1
    ) -> IssueSnapshotV1: ...

IssueSnapshotRequestV1 = {
    "schema_version": 1,
    "target_profile_digest": HEX64,
    "repository": "Dimkox/ai-dark-factory-landing",
    "issue_number": POSITIVE_INT,
    "expected_base_ref": "refs/heads/main",
    "expected_base_sha": "699010380f4f90a0193a9c22090c35e6aded7d2c",
    "expected_base_tree": "f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4",
    "request_id": BOUNDED_ID,
}

IssueSnapshotV1 = {
    "schema_version": 1,
    "request_digest": HEX64,
    "target_profile_digest": HEX64,
    "repository": "Dimkox/ai-dark-factory-landing",
    "repository_node_id": BOUNDED_ID,
    "issue_number": POSITIVE_INT,
    "issue_node_id": BOUNDED_ID,
    "state": "open",
    "state_reason": NULL_OR_BOUNDED_STRING,
    "title": BOUNDED_UTF8,
    "body": BOUNDED_UTF8,
    "title_sha256": HEX64,
    "body_sha256": HEX64,
    "author_id": POSITIVE_INT,
    "author_login": BOUNDED_LOGIN,
    "author_association": BOUNDED_ENUM,
    "labels": SORTED_TUPLE_OF_ID_NODE_ID_NAME,
    "created_at": RFC3339_UTC,
    "updated_at": RFC3339_UTC,
    "html_url": EXACT_TARGET_ISSUE_URL,
    "observed_base_ref": "refs/heads/main",
    "observed_base_sha": "699010380f4f90a0193a9c22090c35e6aded7d2c",
    "profile_base_tree": "f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4",
    "api_profile_digest": HEX64,
    "auth_principal_digest": HEX64,
    "fetched_at": RFC3339_UTC,
    "issue_snapshot_digest": HEX64,
}
```

The adapter may perform only exact read operations for the configured repository,
issue number, repository identity, and base ref. It must reject an Issues API
object containing the pull-request discriminator, a non-open/deleted/transferred
issue, repository/ref mismatch, duplicate/unknown fields, oversize UTF-8, invalid
timestamps, or base drift. Comments, reactions, attachments, issue-edit history,
and linked URLs are outside this snapshot.

The body and title are untrusted data. They enter Codex through a canonical data
field beneath a fixed instruction and cannot select shell text, repository,
branch, prompt template, model, tools, evaluator, command, or grant. Immediately
before either publication effect, a read-only refresh must prove the same issue
node ID and `updated_at`; drift produces terminal `stale_issue`, not a refreshed
snapshot or a second Codex call.

## Exact non-force branch-push interface

```python
class GitBranchPublisher(Protocol):
    def observe_ref(self, request: RefObservationRequestV1) -> RefObservationV1: ...
    def publish_non_force(
        self, request: BranchPushRequestV1, authority: GrantUseV1
    ) -> BranchPushReceiptV1: ...

BranchPushRequestV1 = {
    "schema_version": 1,
    "target_profile_digest": HEX64,
    "issue_snapshot_digest": HEX64,
    "validation_digest": HEX64,
    "repository": "Dimkox/ai-dark-factory-landing",
    "canonical_git_url": "https://github.com/Dimkox/ai-dark-factory-landing.git",
    "base_ref": "refs/heads/main",
    "base_sha": EXACT_BASE_SHA,
    "base_tree": EXACT_BASE_TREE,
    "candidate_parent_sha": EXACT_BASE_SHA,
    "candidate_sha": HEX40,
    "candidate_tree": HEX40,
    "candidate_diff_digest": HEX64,
    "branch_ref": DERIVED_FULL_REF,
    "expected_remote_sha": None,
    "force": False,
    "delete": False,
    "tags": False,
    "operation_key": HEX64,
    "request_digest": HEX64,
}
```

`operation_key` is the domain-separated canonical digest of all fields except
itself. The prepared request and grant check commit durably before the transport
starts. The transport pushes the sealed object by an exact refspec equivalent to
`<candidate_sha>:<derived-full-ref>`. It must not set upstream, push tags, use a
wildcard, delete a ref, use `--force`, `--force-with-lease`, or target the base
ref. A publisher implementation must pass `--porcelain` and explicit no-force
policy; it must never construct a shell command from issue data.

`BranchPushReceiptV1` is closed and binds the request/resource/grant digests,
transport profile, authenticated principal digest, observed base SHA, remote ref,
observed remote SHA, timestamps, bounded output digests, and one outcome:

- `created_exact`: the ref was absent and is now the candidate;
- `already_exact`: reconciliation found the candidate before a write;
- `reconciled_exact`: an ambiguous transport result was followed by an exact
  read observation of the candidate;
- `no_effect`: bounded read reconciliation proves the ref remains absent;
- `conflict`: the ref exists at any other SHA or the base/issue changed;
- `external_outcome_ambiguous`: exact observation is unavailable or contradictory.

Only the first three outcomes permit proposal creation. `no_effect`, `conflict`,
and ambiguity do not trigger another push. A later operator-requested retry is a
new explicitly authorized command after reconciliation; it is not an automatic
workflow transition.

## Exact proposal-create interface

```python
class GitHubProposalPublisher(Protocol):
    def find_by_head(
        self, request: ProposalObservationRequestV1
    ) -> tuple[ProposalObservationV1, ...]: ...
    def create_draft(
        self, request: ProposalCreateRequestV1, authority: GrantUseV1
    ) -> ProposalReceiptV1: ...

ProposalCreateRequestV1 = {
    "schema_version": 1,
    "target_profile_digest": HEX64,
    "issue_snapshot_digest": HEX64,
    "validation_digest": HEX64,
    "push_receipt_digest": HEX64,
    "repository": "Dimkox/ai-dark-factory-landing",
    "base_ref": "main",
    "base_sha": EXACT_BASE_SHA,
    "head_owner": "Dimkox",
    "head_ref": DERIVED_SHORT_BRANCH,
    "head_sha": EXACT_CANDIDATE_SHA,
    "head_tree": EXACT_CANDIDATE_TREE,
    "title": BOUNDED_TRUSTED_RENDERING,
    "body": BOUNDED_TRUSTED_RENDERING_WITH_STABLE_CANDIDATE_MARKER,
    "title_sha256": HEX64,
    "body_sha256": HEX64,
    "draft": True,
    "maintainer_can_modify": False,
    "operation_key": HEX64,
    "request_digest": HEX64,
}
```

The only write is the equivalent of `POST
/repos/Dimkox/ai-dark-factory-landing/pulls` with the closed fields above. The
body may reference the issue using `Refs #<number>`; it must not contain a
`Fixes`/`Closes` keyword, executable content, credentials, or a user-supplied
shell fragment. It includes a stable, non-secret candidate/request digest marker
for reconciliation. No review request, label, comment, auto-merge, merge, close,
branch deletion, or deployment follows.

Before POST, the adapter must prove all of the following on fresh read
observations: `main` still equals the exact base; the issue snapshot is current;
the derived remote head equals the candidate; validation is still pass on that
candidate; and no pull request in `state=all` already owns the same head/base.
GitHub pull requests name a base branch, not an immutable base SHA, so a moved
`main` is terminal `stale_base` even when the candidate still descends from the
old commit.

`ProposalReceiptV1` binds the request/resource/grant/push digests and records the
PR number, node ID, URL, draft flag, observed head/base repository/ref/SHA,
timestamps, auth-principal digest, and one outcome:

- `created_exact`: POST succeeded and an exact follow-up read agrees;
- `already_exact`: preflight found one PR with the same marker, request, head SHA,
  base ref/SHA, and draft status;
- `reconciled_exact`: timeout, connection loss, or duplicate-style response was
  followed by exactly one matching PR observation;
- `no_effect`: bounded reconciliation finds no PR after an ambiguous result;
- `conflict`: a closed/mismatched PR owns the branch, more than one candidate
  exists, or any identity differs;
- `external_outcome_ambiguous`: observation cannot establish one exact result.

Only the first three are a proposal-created result. A `422` is not automatically
a duplicate success; it enters read-only reconciliation. `401`, permission
`403`, and target `404` are terminal auth/target failures. Timeout, `5xx`, and
connection loss never cause a second POST. On restart, an operation left
`prepared` or `in_flight` executes observation only; it does not repeat the
effect.

## Grant and resource binding

The existing local grant binds the control repository, route, change, control
HEAD, control tree fingerprint, actions, resources, source, and TTL. That binding
must remain, but it is insufficient by itself for an external target. The pilot
adds one exact operation resource per effect:

```text
github-operation/v1/git-push-branch/<sha256(canonical BranchPushRequestV1)>
github-operation/v1/pull-request-create/<sha256(canonical ProposalCreateRequestV1)>
```

The canonical request stored beside the grant-use record makes every target
field auditable; the compact resource remains safe under the current
`fnmatch`-based grant store. The pilot authority adapter must accept only literal
resources of that exact form and exact equality. It must reject `*`, `?`, `[`,
`]`, prefixes, repository-only URLs, `github-api`, and any other wildcard or
coarse resource, even if the generic grant helper would match it.

Use two separate grants:

1. scope `production`, action `git-push-branch`, exact push resource;
2. scope `external-write`, action `external-write`, exact proposal resource.

The second choice preserves the current grant vocabulary, which has no
`pull-request-create` action. It must not be represented as
`pull-request-merge`. A future schema version may add a named create action, but
the MVP must not silently reinterpret historical grants. The production grant
store currently permits a grant with no resource; the pilot must reject such a
grant. The external-write grant for coarse `github-api` is likewise insufficient.

`GrantUseV1` must return and persist the matched grant ID, scope, action, exact
resource, control bindings, creation/expiry, and grant-use digest. Check it
immediately before the corresponding effect. A unique durable key on
`(grant_id, action, resource_digest, operation_key)` prevents reuse for a
different operation. Candidate, branch, issue, base, request body, control HEAD,
tree, route, change, or TTL drift invalidates authority.

Do not run `git push` from the external clone and attempt to borrow a grant
resolved for another repository location. The host-side operator actuator must
resolve and validate the control-repository grant first, then call the injected
publisher capability with the sealed request. Shell-hook recognition is defense
in depth, not product authority and not cross-repository delegation.

## Authentication ownership

Credentials are owned by the single operator's host actuator, outside the Codex
workspace, durable evidence, issue payload, application API, and Git records.
Product code receives an injected `GitHubReadTransport`, `GitPushTransport`, and
`GitHubProposalTransport`; it does not receive a token string.

The live adapter may use an operator-preconfigured GitHub CLI/credential broker,
but must never invoke or parse `gh auth token`, inspect `~/.config/gh`, read a
credential helper, enumerate keychains, copy environment secrets, or log request
authorization headers. It sets non-interactive operation, scrubs bounded
stdout/stderr, and returns only:

```text
auth_profile_digest, principal_login, principal_node_id,
target_repository_permission_observation, capability_expiry, response facts
```

The corresponding canonical `auth_principal_digest` is evidence, not authority.
Read, push, and proposal capabilities are separate and least privilege. Trust CI
App credentials, CI signing keys, human approval keys, and deployment credentials
are never valid publisher credentials. Credentials used to acquire the source
must be removed before Codex starts; publisher credentials become available only
after the workspace is sealed and the model process is gone.

Missing credential/capability returns `auth_unavailable`; identity or permission
mismatch returns `auth_mismatch`; neither falls back to another account or
prompts interactively.

## Ambiguity and restart matrix

| Durable stage / observation | Permitted transition | Forbidden behavior |
| --- | --- | --- |
| Snapshot absent | one read snapshot | model or write before snapshot commit |
| Candidate execution `in_flight` after crash | terminal `provider_outcome_ambiguous` | second Codex start |
| Push prepared; remote ref absent | one authorized non-force create attempt | force, base push, implicit retry |
| Push prepared/in-flight; remote ref equals candidate | write `already_exact`/`reconciled_exact` receipt | another push |
| Push ambiguous; remote ref at another SHA | terminal `conflict` | overwrite or force-with-lease |
| Push ambiguous; ref cannot be read exactly | terminal `external_outcome_ambiguous` | assume success/no-effect |
| Proposal prepared; exact PR already exists | adopt one exact PR | second POST |
| Proposal in-flight; exactly one matching PR appears | write `reconciled_exact` receipt | update or recreate PR |
| Proposal ambiguous; no exact PR can be established | `no_effect` or ambiguity, then stop | blind POST retry |
| Any issue/base/head/profile/grant drift | terminal typed stale/conflict state | refresh, rebase, reprompt, or reuse grant |

Read-only reconciliation may use a small fixed number of observations under the
configured timeout to tolerate visibility delay. It may not issue a mutating
retry. Every observation records response identity, time, and digest. Corruption
or predecessor-digest mismatch is terminal and is never rewritten as success.

## Private-plan branch protection and Trust CI

The supplied branch-protection observation is an HTTP `403` caused by the target
repository's private-plan limitation. The only valid interpretation is
`branch_protection_unobservable_plan_limit`; protection state is `unknown`, not
`disabled`. Do not retry that endpoint, infer that `main` is writable, or use the
result as an authorization signal. The pilot may write only its derived non-main
head branch and may create only a draft proposal under the exact grants above.

The checked-in Trust CI example policy allowlists only
`Dimkox/adaptive-grok-build-pro`; its exact-allowlist test rejects other names.
There is no landing-repository Trust CI policy/App/required-check profile in the
available source. Therefore the truthful post-create status is:

```text
proposal_created_merge_gate_unavailable
reason = landing_trust_ci_profile_absent
merge_eligible = false
required_check = null
```

Local verification, semantic evidence, proposal receipts, and a human review do
not repair that absence. The pilot must not merge, enable auto-merge, represent
an App-owned success, or claim the design-partner acceptance loop complete. A
later human/operator-controlled onboarding of the landing repository to deployed
Trust CI, its GitHub App installation, and an observable branch-protection gate
is a separate change and external authority. Until then, human acceptance is an
external observation only; the safe reversible outcome is draft review followed
by a human-owned disposition outside this actuator.

## Minimal implementation seams and focused tests

Recommended additive seams, subject to the required architecture/risk ruling for
the new external-platform edge:

- `github_pilot_contracts.py`: closed target, snapshot, push, proposal, grant-use,
  receipt, and canonical digest contracts;
- `github_pilot_coordinator.py`: pure serial state machine and restart decisions;
- `github_pilot_store.py`: immutable output/operation ledger with predecessor
  digests and command-key replay/conflict semantics;
- `github_issue_source.py`: issue/ref read projection over injected transport;
- `github_branch_publisher.py`: non-force push and exact ref reconciliation;
- `github_proposal_publisher.py`: draft-create and exact head/base reconciliation;
- host composition/CLI: grant adapter and opaque-auth transports, disabled unless
  explicitly configured and granted.

Do not put network, credentials, subprocesses, or GitHub writes into
`factory/src/adaptive_factory/service.py`, `store.py`, Trust CI, or the Codex
workspace. If the architecture owner keeps contracts in factory, the live host
actuator still requires its own named node/trust edge outside the factory control
domain.

Critical focused tests only:

1. Target/repository/base/tree/issue substitution and a PR masquerading as an
   issue fail before Codex or any write.
2. Issue title/body cannot widen repository, paths, argv, branch, credentials,
   model, evaluator, or grants.
3. Candidate must be a non-empty single-parent descendant; only regular `100644`
   `index.html`/`content.css` may change; `index.css` and every other member remain
   exact.
4. Configured unittest non-zero, timeout, output overflow, or post-test tree
   mutation blocks publication; semantic non-pass blocks it as well.
5. Missing, expired, wildcard/coarse, wrong-control-root, wrong-route/change,
   wrong-candidate/ref/body, or cross-repository grant blocks the exact effect.
6. Push fake proves exact new refspec and rejects force, force-with-lease, tags,
   delete, upstream, default branch, and an existing different SHA.
7. Push timeout/crash reconciles exact candidate without a second push; absent,
   conflicting, and unobservable outcomes stop distinctly.
8. Proposal fake proves one draft POST with exact base/head/body marker; existing
   exact proposal is adopted; `422`, timeout, and `5xx` reconcile without a
   second POST; mismatched/multiple/closed results stop.
9. Restart at every prepared/in-flight/receipt boundary never repeats Codex,
   push, or proposal creation and never associates evidence with another SHA.
10. Branch-protection `403` maps only to unknown/plan-limited, and absent landing
    Trust CI maps to `merge_eligible=false`; no callable path merges, closes,
    labels, comments, deploys, or activates M8/M9.

The external GitHub/Codex smoke is not a local-readiness test. It requires a
separately authorized live run, exact grants, opaque host credentials, and the
missing target trust profile decision; none is present or exercised here.

## Amendment — exact surface for the real `v2.0.14` issue

This amendment supersedes the earlier two-path `allowed_write_paths` value for
this issue only, including critical-test item 3's earlier two-path assumption.
The exact base contains three root-page claims of `2.0.12` in
`index.html` (eyebrow, product signal, and JSON-LD), one visible `v2.0.12` claim
on each of the five localized landing pages, and a test assertion fixing the
JSON-LD value at `2.0.12`. Changing the inline JSON-LD also necessarily changes
the CSP hash in `.htaccess`.

The smallest semantically honest exact changed-path set is therefore:

```text
.htaccess
index.html
km/index.html
ko/index.html
lv/index.html
nl/index.html
tests/test_landing.py
zh-cn/index.html
```

The three-path subset `.htaccess`, `index.html`, and `tests/test_landing.py` is
only the mechanical minimum for the existing configured unittest to pass. It is
not the recommended issue boundary: it would leave all five crawlable localized
pages visibly advertising `v2.0.12` while the root page advertises `v2.0.14`.
`tests/test_international.py` currently checks structural/trust invariants but
does not assert version parity, so green tests alone would not expose that
contradiction.

The intended exact facts are:

- every visible landing version above becomes `v2.0.14`;
- root JSON-LD `SoftwareSourceCode.version` becomes `2.0.14`;
- the root product-signal label becomes exactly `Latest published release`, not
  the ambiguous `Public package version`;
- `tests/test_landing.py` expects JSON-LD version `2.0.14` and should assert the
  exact visible `v2.0.14` / `Latest published release` pair without weakening or
  deleting any existing assertion;
- `.htaccess` changes only the one `script-src` SHA-256 token needed for the
  final inline JSON-LD and preserves every directive, including
  `style-src 'self'`; it adds neither `unsafe-inline` nor `unsafe-eval`.

If the only inline JSON-LD byte change is `2.0.12` to `2.0.14`, the resulting
script body has SHA-256
`0289f29e141fc20a27c26577c848d57c8029975368110b2f687ce20cc8be098d` and CSP
source value:

```text
'sha256-AonynhQfwgonwmV3yEjVfIApl1NoEQsvaHziDMi+CY0='
```

The evaluator must nevertheless derive this value from the sealed candidate's
exact inline script bytes and compare it with `.htaccess`; it must not trust the
predicted constant if Codex reformats or otherwise changes the JSON-LD.

`content.css`, `index.css`, `dist/**`, historical design/spec documents, and all
other paths remain immutable. The statement in the historical landing design
that version `2.0.12` was public remains historically true and must not be
rewritten. The tracked deployment ZIP is not rebuilt by this issue; any later
deployment artifact must be sealed separately from the accepted candidate and
requires its own authority.

Because `.htaccess` and a test file are newly admitted, path admission alone is
insufficient. The independent semantic gate must enforce token-level intent:
only the CSP hash token may change in `.htaccess`; the test may only repin the
expected version and add the positive honest-label assertion; locale changes may
only replace the visible version token. Any relaxed assertion, directive drift,
new script/style capability, unrelated copy change, or additional path is a
terminal policy violation.
