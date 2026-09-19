# Architecture — Fix issue #124: require code/test reviewers to perform mutation testing in a private scratch copy outside the reviewed worktree, preserve the reviewed tree as read-only, and report which claims were executed with commands/output plus reviewed-tree-modified:no and scratch path. Update reviewer briefs/templates and tests.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The code/test reviewer briefs do not specify a private scratch mutation method or required report fields. Reviewer TOMLs already use read-only sandbox mode, but the contract does not prohibit in-tree edits or require proof that the candidate tree stayed unchanged. Receipts catch persistent tree changes but not mutate-and-restore behavior.

## Proposed behavior

Make the reviewed source tree read-only by contract. Reviewers that need to mutate source use a private scratch snapshot under a trusted non-sticky parent, populated from the exact candidate including relevant uncommitted changes. Record HEAD and tree fingerprint before/after review; report scratch path, actual commands/results, claims exercised, unexecuted claims, and `reviewed tree modified: no`. A changed source fingerprint invalidates the review claim. Keep scratch-only files and cleanup isolated; do not add a mutation service or new receipt protocol.

Repository inspection disproved the issue body's specific statement that `package_stack.py` blanket-refuses `/tmp`: the existing code rejects unsafe writable ancestry and currently accepts a private child below sticky `/tmp`. The change package will use the stricter `$HOME/.cache` trusted-parent rule so the reviewer scratch contract is explicit and reproducible.

## Components and boundaries

## Data flow

## API and event contracts

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Snapshot the candidate rather than `git archive HEAD` alone, because review often covers a dirty implementation tree.
- Do not introduce reviewer locking as the first-line fix; read-only worktree + snapshot identity checks address the reported integrity hazard while preserving parallel reviews.

## Risks and mitigations
