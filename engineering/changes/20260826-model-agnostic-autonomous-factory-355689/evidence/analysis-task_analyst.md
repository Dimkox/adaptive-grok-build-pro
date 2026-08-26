# Task analysis — bounded M1 and design gate

Route: `35568941ae59`
Change: `20260826-model-agnostic-autonomous-factory-355689`
Scope: read-only analysis for the written architecture specification; this is not an implementation plan.

## Ruling

Treat the current branch as a design-only gate for the approved model-agnostic factory direction. The next implementation milestone is not a new factory runtime: it is completion of M1 Typed Intent and Evidence Traceability on top of the already-present `change-spec` schema/template/parser/CLI/tests. M2 and M3 may start only after M1 meets its exit criteria; M4 must consume the stable M1–M3 contracts; M5 follows M4; M6 follows M5; M7–M9 remain deferred until the required empirical evidence exists.

The root README records live App-bound Trust CI as the current baseline, so this design may treat M0 as established without performing M0 operations. That statement is not permission for this branch to mutate deployed policy, holdout, credentials, branch protection, or external state.

## Baseline facts and the actual M1 gap

Already present:

- strict-shaped `schemas/change-spec.schema.json` with stable IDs and risk tiers;
- package `change-spec.yaml` template;
- `grok_spec.py validate|generate|summarize|map` and a constrained YAML parser;
- generation that preserves unknown facts as `UNKNOWN` rather than inventing them;
- tests for schema shape, unsafe YAML constructs, mapped acceptance evidence, red-risk completeness, and Markdown non-authority.

Still missing for the roadmap M1 exit:

- criterion IDs and the canonical spec digest in fingerprint-bound verification/review evidence;
- typed spec digest and criterion coverage in the signed Trust CI attestation;
- independent external holdout rejection of missing, malformed, incomplete, or stale required specs;
- explicit, machine-enforced documentation-only micro-change exemptions;
- complete staleness rules for base/head SHA, referenced contracts, and policy changes;
- canonical Markdown-to-spec linking instead of duplicated authority across package files;
- a filled active `change-spec.yaml`; it currently contains placeholders, `UNKNOWN`, empty criteria, and no red-risk approval scopes.

## Bounded M1 acceptance criteria

These criteria describe the future M1 completion slice. They do not authorize implementation during this design gate.

### M1-AC-01 — authoritative complete spec

Every standard/high-risk durable change has exactly one canonical `engineering/changes/<change-id>/change-spec.yaml` that validates against a versioned schema. The active package is red risk with domains `ai` and `security`, contains stable objective/criterion/invariant/forbidden-outcome IDs, has no template tokens or `UNKNOWN`, and names the required architecture/security approval scopes. Markdown may explain or link to this file but cannot override any typed field.

### M1-AC-02 — safe, bounded, deterministic parsing

Validation fails closed on extra fields, duplicate IDs, ambiguous/unsupported YAML, unsafe tags/anchors/aliases/merge keys, invalid risk or approval values, empty required evidence, and unresolved placeholders. Input bytes, nesting, collection counts, and scalar lengths have explicit ceilings. Evidence and contract references are canonical repository-relative identifiers: absolute paths, `..` traversal, control characters, and resolution outside the repository are rejected.

### M1-AC-03 — no invented intent

Generation copies only route-known facts and emits explicit incomplete markers for facts not supplied by an approved source. Generated specs cannot pass the complete gate until a human or separately authorized scope decision supplies measurable objective, target, criteria, forbidden outcomes, evidence mapping, rollback, and approvals.

### M1-AC-04 — requirement-level evidence coverage

Every acceptance criterion maps to at least one resolvable independent evidence source; security-critical invariants and forbidden outcomes also have explicit independent evidence. Coverage reports distinguish `proven`, `unproven`, `contradicted`, and `out_of_scope`; a filename or command string alone is not treated as proof of execution or success.

### M1-AC-05 — local evidence binds the spec

Verification and review receipts record the canonical spec digest, covered criterion IDs, exact repository fingerprint, and applicable exact SHA(s). A changed spec, referenced contract, policy digest, tree fingerprint, base SHA, or head SHA invalidates affected receipts; stale evidence cannot satisfy local completion.

### M1-AC-06 — Trust CI independently binds the spec

The Trust CI worker independently computes or verifies the canonical spec digest from the exact checkout and includes that digest plus criterion-coverage summary in its signed attestation. The attestation remains bound to exact head SHA, policy epoch/digest, holdout digest, and signer identity. Factory or implementer output cannot supply the authoritative coverage verdict, sign it, publish it, or edit the deployed validator.

### M1-AC-07 — external holdout fails closed

The externally deployed, digest-pinned holdout rejects required specs that are missing, malformed, incomplete, stale, path-unsafe, or lack required criterion evidence. A repository-side holdout example is test material only and is never accepted as deployed authority. Updating deployed policy/holdout is a separately approved operator action, not part of an autonomous task.

### M1-AC-08 — narrow exemption policy

Only explicitly classified documentation-only micro changes may be exempt, through a machine-readable policy decision with actor, reason, exact paths, base/head SHA, policy digest, and expiry. Red-risk work; AI/security changes; factory/trust/governance/control-plane paths; executable documentation; generated code; contracts; and mixed docs/code diffs are never implicitly exempt. Absence or ambiguity fails closed.

### M1-AC-09 — compatibility and adoption are controlled

Schema evolution uses an explicit version and deterministic compatibility rules. Existing historical packages are not silently reinterpreted, bulk-mutated, or allowed to make current standard/high-risk work fail unpredictably: enforcement activates only with a reviewed adoption/backfill rule and tests for legacy, current, and future-version inputs. Rollback/forward-fix does not erase evidence or weaken the merge trust boundary.

### M1-AC-10 — approved factory constraints are typed invariants, not runtime claims

The active spec records, as requirements/invariants/forbidden outcomes for later milestones: provider-neutral core; versioned JSON/JSONL adapter protocol; Codex first through `codex exec --json`; explicit Grok compatibility adapter; no silent provider fallback; prompt/repository/notes as untrusted data; no chain-of-thought storage; no credentials available to repository subprocesses; no autonomous external writes; one application writer; readers at most 20 and at most 10 per repository; infrastructure retries at most 2; repair cycles at most 3; task wall time at most 4 hours; task cost at most USD 25. M1 proves that these constraints are represented and traceable, not that M4–M6 enforce them yet.

### M1-AC-11 — observable, machine-readable outcomes

CLI and verification surfaces return stable machine-readable success/failure codes and a summary containing spec digest, risk, criterion counts, unmapped/contradicted IDs, and staleness reason without exposing prompts, secrets, or hidden reasoning. Logs treat prompt, repository, and note contents as data and record no chain of thought.

### M1-AC-12 — evidence for M1 completion

Focused schema/parser/CLI tests, verifier/receipt tests, Trust CI attestation tests, external holdout tests, staleness tests, adversarial path/parser tests, and legacy/adoption tests pass on the same final fingerprint. Route-required code, test, security, and release reviews then inspect that final tree; a later PR still requires the App-owned policy-epoch check on its exact head SHA. Local receipts and this report are not merge authority.

## Explicit non-goals for M1

- No M2 executable architecture graph, fitness engine, or architecture-diff implementation.
- No M3 governance rule lifecycle, canonical-pattern registry, or debt ledger.
- No `factory/` PostgreSQL task queue, leases, scheduler, audit log, budgets, WIP controls, or reconciliation (M4).
- No provider launcher, Codex/Grok runtime adapter, systemd unit, worker pool, worktree manager, note broker, secret broker, network controller, or run-manifest runtime (M5).
- No semantic validator, meta-reviewer, finding store, or repair loop (M6).
- No branch push, PR creation, merge, release, deployment, systemd installation, autonomous external write, auto-merge, preview, canary, or production mutation (M7–M9).
- No provider-specific fields in the M1 intent schema merely to configure Codex; provider selection and effective model belong to later task/run contracts and manifests.
- No reuse of `trust_ci_jobs` as the factory queue, no collapse of factory and Trust CI trust domains, no GitHub Actions, and no root packaging marker.
- No implementation code or implementation plan in the current design/docs branch.

## Unresolved design choices to expose in the design spec

These are choices, not permission to defer security properties:

1. **Schema compatibility:** extend schema v1 only where absence has an unambiguous safe meaning, or introduce v2 for criterion verdicts/bindings. The design must name readers, writers, compatibility window, and rejection behavior for unknown future versions.
2. **Evidence envelope:** decide the canonical representation for criterion status and provenance in local receipts versus Trust CI attestations. Trust CI must derive its verdict independently rather than trusting a local coverage blob.
3. **Staleness binding:** decide whether base/head SHA, policy digest, and referenced-contract digests live inside the spec or in a signed validation envelope around the spec. Either design must make replay and partial rebinding impossible.
4. **Reference resolution:** define allowed evidence/contract URI forms, repository-root resolution, existence checks, symlink handling, test-selector syntax, and how external evidence is named without permitting arbitrary filesystem/network access.
5. **Exemption authority:** define who may classify a documentation-only micro change, the exact allowlisted paths/diff properties, expiry, audit record, and how post-diff escalation cancels an exemption.
6. **Historical adoption:** choose a bounded backfill/legacy policy for existing packages. Do not bulk-edit history merely to obtain green validation, and do not leave standard/high-risk enforcement optional indefinitely.
7. **Approval semantics:** map route `scope_and_design_approval` to architecture/security review records without confusing it with an Ed25519 Trust CI human security approval or a local delegated operational grant.
8. **Failure UX:** define deterministic `invalid`, `incomplete`, `stale`, and `exempt` states and operator remediation without leaking untrusted content into policy instructions or logs.

The user has already resolved the macro-architecture, milestone order, initial limits, trust boundaries, and prohibition on external writes/fallback/chain-of-thought storage. Those items must not be reopened as optional design questions.

## Roadmap ordering constraints

1. Finish M1 and demonstrate all M1 exit evidence before M2 or M3 implementation begins.
2. Complete M2 executable architecture and M3 controlled knowledge/debt on top of the stable M1 contract; they may be separate follow-on branches, but neither may redefine M1 silently.
3. Begin M4 only after M1–M3 interfaces are stable. M4 owns PostgreSQL durable factory tasks, leases, budgets, WIP, retries, audit, and scheduler state, separate from `trust_ci.*`.
4. Begin M5 only after M4. M5 owns fixed systemd supervisor/workers, isolated worktrees/runtimes, append-only note broker, one technical writer lease, read/note concurrency, Codex/Grok/provider adapters, secrets/network isolation, and immutable run manifests.
5. Begin M6 only after M5. M6 owns independent semantic adjudication and at most three repair cycles returned to the same writer.
6. M7–M9 require their stated evidence cohorts and gates. In particular, no automated PR lifecycle or shadow-mode claim before M6 evidence, no earned autonomy before shadow-mode data, and no delivery autonomy before proven preview/canary/recovery controls.
7. Each milestone receives its own later implementation scope/branch/package as required by the roadmap; this analysis does not create any of them.

## Current user-review gate

The branch may be presented for `scope_and_design_approval` only when all of the following are true:

- `docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md` and the existing durable package consistently describe the approved macro-architecture, trust boundaries, exact limits, milestone order, recovery/observability, and explicit non-goals;
- the active `change-spec.yaml` is red-risk, complete, schema-valid, evidence-mapped, and contains no placeholders or invented facts;
- all route-selected read-only analysis reports have been synthesized, and unresolved choices above are either decided with rationale or clearly presented as user-review decisions;
- self-review finds no placeholders, internal contradictions, scope leakage into implementation, weakening of secret/network isolation, silent fallback, external-write authority, self-approval, or chain-of-thought retention;
- `decisions.md` records the approved design pattern and reason in at most three sentences;
- the exact docs/package tree is committed locally on `feature/model-agnostic-factory` as one coherent design/docs commit;
- no implementation code, implementation plan, second package, push, PR, merge, release, deploy, or systemd installation has occurred.

After that commit, stop. The local commit is the artifact for user review; it is not M1 completion, does not transition the design to implementation approval by implication, and grants no external action.
