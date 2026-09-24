# Documentation and contract analysis — issues #35, #36, #39, #48, #73, #121, #122, #167

## Scope and evidence

Read-only review of the current tree, route package, repository contracts, Trust CI example policy, runbooks, tests, and current GitHub issue bodies. No product files were changed. These issues span distinct boundaries; a single source patch would risk claiming closure without evidence.

## Findings by issue

### #35 — multi-file `bash -n`

The issue is a shell-gate correctness defect: Bash parses the first positional script and treats later paths as positional parameters. The repository has shell scripts under `trust-ci/scripts/`, `trust-ci/postgres/init/`, `factory/runtime/`, and `scripts/bootstrap.sh`, but no current repository-wide rule or test that rejects a multi-path `bash -n` invocation. A fix should add a small static guard/test over tracked shell commands, plus a loop or one-file-per-invocation helper where the faulty command exists. Closure requires a regression proving every listed file is parsed and an empty file set cannot report green.

### #36 — exit status after `!`

This is a shell recorder defect. The safe form is `command ... || code=$?`; reading `$?` inside `if ! command; then` returns the negation status. The issue body does not identify a current path in this checkout. Before implementation, search selected gate scripts and tests for `if !` around captured status. If no live occurrence exists, do not invent a product fix. A regression must verify non-zero command failure remains non-zero, including command-not-found.

### #39 — unbounded JS lint scope

No ESLint/JS lint configuration or JS package tree corresponding to the described consumer workspace is present here. The relevant checked-in JavaScript tooling is the static landing browser contract (`side-projects/seo-landing-showcase/browser-contract.mjs`), whose focused contract is documented. The described 77,672-file scan is consumer/workspace-specific. Keep this issue open or link the external consumer successor; do not add unrelated ESLint configuration here.

### #48 — environment verifier silent-green traps

The issue describes a user-level CLI guard kit, gist files, and a `~/.bashrc` wrapper. Those paths are outside this repository; no matching guard script, self-test, CLI bundle checker, or shell wrapper is tracked here. The repository can carry a general finding/runbook, but cannot honestly close the product issue with a fabricated adaptation. Treat it as external/consumer scope unless a current in-tree reproduction is identified.

### #73 — GitGuardian SHA-256 false positive

The tree already uses `grant_binding_digest` in evidence, and existing review evidence records the observed generic-detector false positive as non-credential. The deployed merge authority remains the App-owned exact-SHA Trust CI check; GitGuardian is not the configured merge authority. `trust-ci/config/policy.example.json` is illustrative and must not be edited to simulate the deployed service. A source-only closure can document the naming convention and triage boundary, but cannot change the external detector or prove a future GitHub check. Prefer a narrowly scoped docs/test assertion that evidence digest keys avoid secret-like names, then require fresh external observation for final closure.

### #121 — non-re-derivable runtime observation

The issue identifies a historical dossier. Current contracts and runbooks require durable, independently re-derivable evidence, while a provider activation probe may require an authenticated live call and leaves no durable landing row. Valid resolutions are: durable probe record (data/behavior change), downgrade wording to operator attestation (docs-only), or a bounded re-derivation tool outside automatic verification. The lowest-risk source-only path is to revise dossier wording and add a decision/runbook marking probe leaves `attested, not re-derivable`, while citing the durable pilot row for profile claims. Do not claim the provider probe is locally re-derived.

### #122 — policy example overstates deployed approval scopes

`trust-ci/config/policy.example.json` is explicitly an example in `trust-ci/README.md` and rollout docs, while the issue reports agents mistaking its `approval_rules` globs for deployed policy. Tighten the example/readme wording: illustrative only, deployed policy external and authoritative, and identify where the policy epoch/check name is observed. Do not narrow or rewrite approval globs based only on historical PR observations; deployed policy is outside the repository.

### #167 — side-project verification profile

The replacement `AGENTS.md` already contains the requested focused scope rule: for product files confined to `side-projects/seo-landings/**` and focused landing tests, run landing contract tests first; retain full `grok_verify --mode pr` when runtime, contracts, Trust CI, packages, architecture, or workflow files also change. Remaining work is evidence: confirm adaptive-delivery does not still force the full command, and run focused contract coverage for the actual landing path. A successor PR can close this after focused tests and review.

## Cross-cutting delivery recommendation

1. Implement #122 and #167 as documentation/contract changes.
2. Implement #121 only with an explicit attestation wording decision, or escalate durable probe design as a data change.
3. Implement a bounded #73 naming/triage assertion if the route selects it.
4. For #35/#36, first locate a live in-tree caller; otherwise leave them external/historical.
5. Keep #39 and #48 open for their consumer workspaces; do not create unrelated product code here.

Record exact paths and focused tests before closing any issue. External Trust CI remains required for a merged PR, and issue closure follows the exact merged head.
