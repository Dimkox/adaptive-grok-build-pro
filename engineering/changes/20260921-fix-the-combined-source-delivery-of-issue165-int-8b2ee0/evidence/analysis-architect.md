# Architecture assessment — combined factory/tooling candidates

Role: route-selected `architect`, route `8b2ee0533ba5`.
Assessment: bounded design is viable, subject to the actual delivered-base and
current-package obligations below. This is static analysis, not a review receipt,
test result, scope approval, or merge authorization.

## Inputs and assessment boundary

Inspected `AGENTS.md`, bootstrap/handoff, the actual local route, package brief,
requirements, candidate manifest, prefix-integration proposal, architecture model
and rules, and the relevant source/test changes. Exact candidate identities are:

| Input | Commit |
| --- | --- |
| Generated route base | `839d3aa26bc90417424d814ee48d8b5cd3be367e` |
| PR173 source prerequisite | `23984e55560c6d559a46445061f10331ca05bcf9` |
| Issue165 candidate | `163847842ccddacd6f179c7a3ea082765530bb84` |
| Issue163 candidate | `d80c5c8d8e5afe938d195401715daf5e69192a81` |
| Issues62/118 candidate | `08dd467d0dc9c173af01f3b47876a9a3fa1ca639` |

At assignment, PR173 was still open and the package was a draft with no source
imports. Its future merged tree is a conditional prerequisite, not an observed
fact in this report. Source imports must wait for actual delivery and fetched
commit/tree identity. Static Git reads, text reads and blob-size arithmetic were
performed; no product imports, tests, compilation, lint, Docker, migration,
external operation, or receipt command was run. The external CI owns the CPU lane.

## Bounded architecture and ownership

The corrected manifest contains 19 distinct paths: nine for165, seven for163,
three for62/118. The original 18 paths are unchanged; the additional path is the
165 candidate's `.grok/hooks/stop_gate.py`, SHA-256
`7be3f2be3fb9ea1e581344388a40da84c3a092945e3fb1a51a024847ad0bf48b`.
The first assessment inherited the manifest's omission of this necessary adapter;
repository/integration analysis found it, and this revision explicitly includes
its source and acceptance boundary. Their product responsibilities remain separate, with one selected
`data_implementer` owning every import and any subsequent integration repair.
Root owns shared handoff and evidence packaging. There is no reason to add a
service, dependency, queue, configuration schema, production interface, or new
architecture node.

* `package_status.py`, lifecycle/state changes, the evidence template, and
  status/review CLI adapters remain local preflight observations. They do not
  grant approval or redefine receipts. `change.py` may write explicit lifecycle
  observations; `grok_status.py` stays observational, including unavailable input.
  The Stop hook is also owned by `NODE-LOCAL-ROUTE-POLICY` through its existing
  `.grok` path. It adds bounded package/worktree warnings, including for routes
  without receipt obligations, while retaining warning-only Stop semantics and
  the existing local completion path. It creates no external approval authority.
* `_cpu_capacity.py` is a private helper of `python_test_runner.py`, already
  covered by the `.grok-stack/adaptive_grok` ownership of
  `NODE-LOCAL-ROUTE-POLICY` in `TD-LOCAL-PREFLIGHT`. Its only added dependency is
  standard-library parsing and bounded reads of process-visible Linux metadata.
  Root test files and CLI scripts remain under `NODE-LOCAL-VERIFIER`. No network
  edge or secret capability is added. Keep the helper private; it is not a
  host-wide scheduler or authoritative capacity service.
* The semantic repair decoder and PostgreSQL store stay within the factory
  semantic-control boundary. Migration022 replaces the existing planning
  function, preserving its signature/security boundary and immutable001–021.
  The new internal refusal envelope does not change successful repair/escalation
  contracts or create a second state source.

`trust-ci/`, deployed policy/holdout/images, runtime databases, signing material,
published archives, provider behavior and general CI capacity qualification are
outside this integration. In particular, issue158 belongs to its separate source
delivery; copying it here would breach `FIT-TRUST-CI-SEPARATION`.

## Finding A1: the recorded old base has a concrete budget consequence

Architecture comparison uses the route's exact `base_commit` through
`select_architecture_comparison_base`; fetching a newer main or a same-tree merge
does not silently replace that comparison base. The PR hygiene inventory also
unions the route and locally selected PR-target ranges. Thus a successor target
alone does not remove already-delivered PR173 files from the old route's checks.

`_code_budget` charges the maximum of base/head **whole-file sizes** for every
changed governed path, and whole-file AST complexity for changed Python files.
A small hunk in a large file is not charged only its added bytes. Git
`cat-file --batch-check` on the exact objects above gives the following projected
size sums if all 19 manifest paths are imported byte-for-byte:

| Budget | Limit | Against route839 | Against a future base with exact PR173 tree |
| --- | ---: | ---: | ---: |
| All governed change | 1,300,000 | **1,463,628** | 1,037,462 |
| Architecture/tooling change | 1,000,000 | 497,263 | 71,097 |
| Factory total | 1,150,000 | 966,365 | 966,365 |
| Factory source | 375,000 | 252,088 | 252,088 |
| Factory tests | 775,000 | 714,277 | 714,277 |

The nineteenth path does not alter these sums: `.grok/hooks/stop_gate.py` matches
none of the `code_budgets[].path_prefixes` in the unchanged rules. Both broad
budgets select `.grok-stack/adaptive_grok`, not `.grok`; the other budgets select
factory or pilot paths. This is the rule's existing scope, not an exclusion added
for delivery. The hook remains part of the actual 19-path source diff, architecture
ownership, applicable separation policies, tests and independent review.

The old-base projection exceeds `FIT-BOUNDED-ALL-GOVERNED-CHANGE` by163,628 bytes.
It includes eight predecessor-only governed files; the factory prefix test is
counted once at the163 candidate size. The fresh-base projection omits those
already-delivered files while retaining every actual successor path. Neither
projection is an executed fitness result, and neither establishes AST-complexity,
line-count, contract, drift, governance, or other fitness success.

Coordinator-adopted mandatory continuation: after actual PR173 delivery, fetch and establish its
real merged main SHA and tree equality; use the normal routing mechanism for the
successor on that actual delivered base. Preserve this original route/package,
the reason for continuation, candidate hashes and analysis provenance. A newly
generated route must satisfy its own evidence obligations. Do not hand-edit
runtime route bases/fingerprints, select a fictitious merge-base, relax a rule or
threshold, or convert a diagnostic result into a passing receipt. If the actual
new-base integrated run still exceeds a limit, return the bounded failure to the
single writer and reduce or split real delivery scope without removing proof.

## Finding A2:165 must account for this integrated package truthfully

The current package's `state.json` was created before165 code is present and has
neither `checkpoints` nor `evidence_accounting`. In the candidate implementation,
calling `start_change` on an existing package does not retroactively initialize
either field. `inspect_package` exposes missing accounting as a legacy warning;
it does not migrate state or manufacture evidence. This applies equally if a
new-base package is created with the predecessor's old lifecycle implementation.

Root has adopted explicit version1 accounting for all six obligations of
the current route: `verification`, `code_review`, `test_review`,
`security_review`, `data_review`, `release_review`. Each begins as `not_run` with
an honest reason such as "combined tree not yet verified" or "awaiting integrated
verification". At this static re-read the original draft state still has its
legacy shape; the coordinator must initialize the real successor's six rows,
without inventing checkpoints or treating this plan as already-written receipts.
A required review with a `not_run` reason is accounted for, not
passed. The inspector's `complete` label describes inspected documentation only;
fresh runtime receipts and zero evidence gaps remain separate obligations.

Candidate full/focused runs and previous reviews may be recorded as explicitly
historical source-provenance/run rows or linked adoption reports, bound to their
actual commit, source hashes, command, time, outcome and limits. They cannot fill
the current combined verification/review obligation by relabelling their heads.
Keep original failures, revised results, conditional skips and missing outcomes.
Every recorded reference must be a nonempty allowed `.md`/`.json` report under
the current package's `evidence/`, within safe path/depth limits. Cross-package
paths or `..` references cannot serve as inspector-selected references.

Do not transplant the165 package's route/change IDs or checkpoints. A missing
initial checkpoint remains absent with the documented route-base fallback; an
initial HEAD must not be reconstructed as if it were observed at creation.
Existing exact provenance may be documented separately. A first implementation
checkpoint is legitimate only when the new implementation executes a real legal
lifecycle transition. Repeated `start` merely repairs a pending mirror; arbitrary
stage cycling solely to synthesize a desired checkpoint is unnecessary.

Keep explicitly selected current reports within the inspector's 64-file,
256KiB-per-ordinary-file and1MiB-aggregate bounds. Large immutable logs can remain
archival artifacts with a concise factual current report and hashes; do not point
accounting at an oversized full log, conceal an unsuccessful result, or change
inspector limits for this package. Finish accounting, reports, mirror recovery,
handoff and lifecycle edits before final receipt capture. Every later tracked
change invalidates the fingerprint again.

The original empty typed scaffold was expected draft work, not completion. Root
has now populated its objective and seven typed acceptance criteria, including
the Stop hook and the explicit remaining62 outcome; current validation still
belongs to the successor's real checks. By the coordinator's
verified integration constraint, typed acceptance receipt references must remain
within the currently trusted five-kind vocabulary
(`verification/code_review/test_review/security_review/release_review`). The
route's real `data_review` report and receipt remain mandatory independently.
The separate162 trusted-validator successor and its deployment are not delivered
by this workaround; no end-to-end seven-kind compatibility is claimed.

## Interaction risks and acceptance proof

| Boundary | Risk and required integrated proof |
| --- | --- |
| PR173 prefix upgrade +163 | Use the manifest's163 `test_execution_persistence_postgres.py` blob. It includes the166 ancestor and adds022. Preserve the explicit real001–020→021 proof, then real001–021→022 proof, immutable ledger identities/timestamps, populated rows, function OID/owner/ACL/security/search path, rollback/retry, and empty replay. The supplied prefix proposal explains the overlapping old merge hunk; do not choose the older block and lose022 coverage. |
|163 refusal vs successful result | A strict singleton `repair_plan_rejection` object selects allowlisted reasons; unknown reasons become the bounded generic refusal. Legacy SQL NULL remains `store_returned_null`; malformed JSON/shapes/bindings remain corruption. Tests must continue distinguishing all of these from successful replay and persisted escalation. |
|163 transaction ownership | The store classifies the function response after leaving its transaction context. Moving refusal raising into the transaction could roll back intended state. Preserve deadline/escalation persistence, exception-subtransaction behavior, successful replay after deadline, contention and refusal paths. Do not invent a mixed-version zero-downtime rollout claim. |
|165 +173 fingerprint/tooling | The new diagnostic byte-name representation must round-trip through canonical state/CLI reads, remain collision-free and bounded, and retain explicit unknown results. Existing receipt serializers/authority are unchanged. Integrated tests must retain unsafe-file avoidance, status nonmutation, review preflight refusal, checkpoint mirror recovery and freshness behavior with the actual173 utility implementation. |
|165 Stop hook | Include the exact candidate hook and retain regressions that warn for an incomplete package even with no receipt obligations or apparently current receipts. Unsafe selected inputs must not be reopened by legacy receipt validation. Diagnostics remain nonblocking and do not create completion, approval or verification evidence. |
|62/118 auto vs explicit control | Only Linux `auto` consults cgroups. Preserve default-off, explicit0–64/env precedence, child suppression, other POSIX handling and non-POSIX auto0 without unnecessary reads. Quota calculation is the minimum of visible finite capacities, affinity/count and28, with floor/minimum1 policy; unknown inputs conservatively select1. |
| Capacity parsing | Preserve exact v1 CPU-controller selection and hybrid behavior, v2 membership, escaped mount paths, component containment, all relevant exposed ancestors/mounts, absent-v2-control versus malformed/unreadable distinctions, and bounded metadata/read/depth limits. Hidden parents, PID headroom and idle capacity remain unproven. |
|118 prelaunch fallback | Unsupported cleanup capability selects actual serial execution before launching or pinning xdist. Retain supported parallel pins, measured serial coverage-only requirements, actual engine/worker reporting, exact-once collection, cleanup and failure propagation. A real failed parallel run must never be retried serially. |
| Empty serial suite | The candidate retains non-vacuous zero-test regressions; the earlier alleged empty-suite defect was not reproduced on the measured runtime. Keep the existing serial commands/accounting and reported interpreter bounds. Neither native Windows nor older-Python qualification follows from a mocked capability seam. |

After source import, compare all 19 hashes against the manifest and separately
establish the actual base tree. Any changed candidate bytes require a documented
reason and writer-owned measured regression, not a blanket declaration of parity.
Run the complete integrated `python3 scripts/grok_verify.py --mode pr` only when
the CPU lane is assigned, then every current route-selected independent reviewer
on the integrated diff. Review reports must bind actual source/evidence; final
receipts must bind the final frozen tree. Full aggregate coverage is not a
substitute for executing the meaningful domain/PostgreSQL and runner regressions.

## Delivery and recovery limits

Source delivery may resolve165/163/118 only after the corresponding acceptance
outcomes and exact-head external Trust CI succeed. Keep62 open: bounded App Check
Run command output is a separate Trust CI source successor, outside this bundle.
This source delivery also does not resolve159 or158.
Close retained PR135 as superseded only after the successor actually lands.
Branch publication/PR/merge require exact delegated operations and the real
App-owned check; local accounting, static projections and historic candidate
reviews authorize none of them.

Rollback before deployment is a normal reviewed source revert. A deployed022
installation is a separate database/application operation: preserve immutable
migration history, use the candidate's coordinated version/recovery plan, and
prefer an additive forward correction when necessary. This integration performs
no database operation, provider call, service restart or image rollout.

Suggested shared-memory fact for the coordinator: a generated route retains its
original architecture comparison base even after a same-tree predecessor merge;
whole-file budget accounting can therefore charge already-delivered source.
Generating the successor only against the actual delivered base preserves both
honest budget scope and the original provenance without weakening a rule.
