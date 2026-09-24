# Architecture and impact analysis — issues #35, #36, #39, #48, #73, #121, #122, #167

## Scope and current boundary

This is a read-only architecture analysis for route `b26dfffbedae`. The issues span verifier shell safety, lint scope, evidence naming, runtime-observation semantics, policy-example documentation, and static side-project verification. They should not be implemented as one undifferentiated change: #35/#36/#48 touch executable gate behavior, #39 changes lint discovery policy, #73 changes evidence naming or triage documentation, #121 changes runtime evidence semantics, #122 is a governance-documentation contract, and #167 changes local verification selection. The external App-owned Trust CI check remains the merge authority; local profile selection cannot weaken it.

## Issue findings and bounded design

### #35 — multi-file `bash -n` is only a check of the first script

**Observed contract:** shell syntax validation must parse every intended file and fail if any file is invalid. A command with multiple script operands is unsafe because later operands become positional arguments.

**Affected boundary:** verifier/gate command construction and its tests. Search did not find a current literal in the repository source outside historical issue/evidence text, so the implementer must first locate the active command producer (or prove the remaining occurrence is in an external consumer). Do not patch historical evidence merely to make the search green.

**Safe design:** normalize a list of shell paths into one `bash -n -- <path>` invocation per file, accumulate the first non-zero result, and record the checked-file count. Empty input must fail closed. Preserve the existing result schema and diagnostics.

**Acceptance evidence:** one valid plus one invalid fixture returns non-zero and names the invalid file; all-valid fixtures return zero and report the count; empty input cannot report success. The test must exercise the actual command builder, not only restate a shell snippet.

### #36 — negated command captures the status of `!`

**Observed contract:** a recorder must preserve the wrapped command's exit code, including command-not-found/start failures. `if ! cmd; then code=$?` records the negation status and can turn failure into zero.

**Affected boundary:** shell step recorder and result serialization. The repair should use `cmd >log 2>&1 || code=$?` (or an equivalent status-preserving form), while retaining `set -e` compatibility and signal handling.

**Safe design:** make one recorder responsible for execution, wall time, output marker, and exit status. Do not infer execution from a zero code. A failed-to-start command remains a non-zero recorded check.

**Acceptance evidence:** true, false, and missing-command fixtures; assert recorded status, non-empty evidence marker/wall time, and final gate status. Avoid duration thresholds as the primary correctness proof because host load makes them brittle; an explicit execution marker is deterministic.

### #39 — broad JS lint scope walks worktrees and generated files

**Observed contract:** interactive lint should operate on repository-controlled files or changed files; deep verification may retain whole-repository lint with explicit exclusions and visible file count.

**Affected boundary:** JS lint configuration/runner. Existing generic Python ignore helpers do not prove the JS tool's scope. The architecture must define one source of truth for candidate paths and exclude `node_modules`, `dist`, `coverage`, `.worktrees`, scratch/release output, nested repositories, and other generated trees.

**Safe design:** for fast/interactive mode, derive tracked changed JS/TS files and pass them explicitly; for deep mode, use a bounded repository root plus explicit ignores and emit candidate/processed counts. Never silently turn an empty candidate set into green without an `skipped: no applicable files` result.

**Acceptance evidence:** fixtures under a sibling worktree, coverage, and generated directories are excluded; tracked source is included; output records counts and mode. Keep this independent from the product's static landing profile.

### #48 — several shell/environment checks can report success while checking nothing

**Observed contract:** environment verification must fail closed on empty discovery and preserve command status. The issue contains independent traps: assignments before control builtins, `pipefail` with `grep -q`, `grep -lf` typo, and PATH-only discovery.

**Affected boundary:** any environment guard/repair kit imported by this repository. Current source search did not identify the external gist's filenames as repository files, so first establish whether a local equivalent exists. If none exists, record #48 as external/unimplemented rather than introducing an unrelated shell kit.

**Safe design if a local equivalent exists:** isolate resolver, discovery, and assertion functions; separate “not found” from “found but invalid”; require non-empty lookup results before equality checks; capture pipeline output before matching; put assignments and control builtins on separate commands; run a non-interactive PATH fixture. Avoid writing to installed bundles or user shell startup files in local verification.

**Acceptance evidence:** regression tests cover all four traps, empty discovery, interactive/non-interactive resolution, and command startup failure. No production/live environment mutation is part of this issue batch.

### #73 — GitGuardian false positives on SHA-256 evidence fingerprints

**Observed contract:** evidence digests are non-secret integrity values, but names containing secret-like terms can trigger generic detectors. The merge authority is unaffected, yet noisy findings weaken triage.

**Affected boundary:** committed evidence schemas and documentation. The lowest-risk source change is terminology: use neutral names such as `grant_binding_digest`, `tree_fingerprint`, or `source_sha256` where semantically accurate; do not alter digest bytes or imply that a detector allow-list is security proof.

**Safe design:** establish one canonical naming convention and update producers/consumers/tests together. If historical records must remain byte-compatible, add an explicit compatibility reader and migrate only new records. Document that detector dispositions are external evidence and not a substitute for Trust CI.

**Acceptance evidence:** schema tests reject secret-like key names for integrity digests where the convention applies; digest values remain stable; package/manifest tests still pass. Do not add secrets or GitGuardian configuration to repository source.

### #121 — runtime-observation probe leaves are not re-derivable

**Observed contract:** a runtime dossier must distinguish durable, re-derivable rows from operator-attested provider probes. The current omni activation record mixes a durable pilot job with a provider probe that leaves no durable row.

**Affected boundary:** runtime observation evidence and its runbook/schema. This is not safely solved by fabricating a database row or making a provider call in local verification.

**Recommended bounded resolution:** choose and record the lower-risk option for this source-only route: downgrade the probe claim to explicitly `attested, not re-derivable`, cite the durable pilot row for re-derivable behavior, and prevent probe usage/IDs from being presented as durable job facts. Durable probe persistence would require a separate data/API change with migration, retention, idempotency, and operational authorization.

**Acceptance evidence:** schema/contract test rejects a probe marked re-derivable without a durable reference; dossier wording separates probe and pilot IDs and usage; runbook states the provider probe is outside automatic verification. Any live re-probe remains an explicit operational action.

### #122 — example policy advertises deployed governance scopes

**Observed contract:** `trust-ci/config/policy.example.json` is illustrative, while deployed policy epoch `06ecf1c875bc` is authoritative. The example currently looks like an executable description and can cause agents to request a human approval that the deployed gate does not require.

**Affected boundary:** policy example and Trust CI activation documentation. Do not modify deployed policy, trust stores, keys, or branch protection from this repository.

**Safe design:** mark the example as non-authoritative at the top level and in the governance runbook; point readers to the deployed epoch/check for actual requirements. If a scope is illustrative, label it explicitly. Keep parser tests for schema validity and add a documentation assertion that example policy cannot be treated as deployed policy.

**Acceptance evidence:** an agent-facing doc test finds the non-authoritative marker and exact source of deployed authority; existing policy parser tests remain unchanged; no claim is made that local JSON determines merge eligibility.

### #167 — static side-project HTML invokes the full 16-minute verifier

**Observed contract:** when product files are confined to `side-projects/seo-landings/**` and focused landing tests, local preflight should run the side-project contract tests. Full `grok_verify --mode pr` remains required when runtime, contracts, Trust CI, packages, architecture, or workflow files also change.

**Affected boundary:** `AGENTS.md`, adaptive-delivery route/profile selection, and landing test command documentation. The supplied contract already contains a focused-verification paragraph, so implementation should verify whether the route/runner actually honors it rather than duplicating the rule.

**Safe design:** add a deterministic changed-file classifier that selects the landing profile only for an allowlisted path set plus focused tests; classify any mixed diff as full PR verification. Emit the selected profile and file inventory. This is a local preflight optimization and must never bypass the exact App-owned merge check.

**Acceptance evidence:** landing-only fixture selects focused tests; mixed landing/runtime fixture selects full gate; unrelated no-op behavior remains unchanged; docs and route evidence agree. Do not add a GitHub Actions workflow.

## Cross-issue dependencies and sequencing

1. Establish the active verifier/runner entry points before changing #35/#36/#39/#167; these may share profile/command plumbing.
2. Implement shell status and scope safety (#35/#36), then add focused regressions for #48 only if a local equivalent exists.
3. Implement #39 and #167 in separate profile-selection layers so static landing scope cannot leak into runtime verification.
4. Handle #73 as a schema/doc compatibility change after locating all digest producers and readers.
5. Handle #121 as evidence wording/schema validation only unless a separate approved data/API route is opened.
6. Handle #122 as non-authoritative example documentation with parser/doc tests.
7. Re-run full local verification only after product files are changed, then route-selected reviews. Any evidence written by verification must be fingerprint-bound to the exact tree.

## Risks and explicit non-goals

- No changes to deployed Trust CI policy, PostgreSQL runtime state, GitHub App keys, human approvals, branch protection, or live provider services.
- A repository search did not establish a local implementation for the external #48 gist; implementation must not invent one without an identified source boundary.
- #121 cannot claim re-derivability until a durable row or an explicitly downgraded attestation is present.
- #73 cannot be “fixed” by suppressing detectors or weakening secret scanning.
- #167 cannot weaken merge authority; it only selects a local preflight profile for a narrowly bounded static tree.
