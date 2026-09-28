# Issue #218 clean squash delivery

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown cannot override typed criteria or approval scopes.

Change ID: `20260925-fix-github-issue-218-locally-deliver-the-verifie-566746`

Route: `566746aef130`

Risk: red

Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`

Verified development source: `68dfc70c5f58adcc927f731c5d88de09a1b4b242`

Source tree: `0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66`

## Problem and outcome

The cumulative #227-through-#218 source needs a clean one-commit delivery because inherited commits predate the full-chain hygiene gate. Independent reviews exposed fail-closed gaps in coverage validation, Git isolation, safe file/object inspection, diagnostic confidentiality, whitespace ordering and pre-read resource bounds. The user's instruction to continue #227 through #0 authorizes the bounded local repairs recorded here without external actions or source-branch rewrites.

## Scope

In scope:

- non-destructive `git merge --squash 68dfc70c...` into this isolated route;
- exact tree/provenance comparison against the verified development source;
- the route-local delivery package and exact thirteen-path post-source contour enumerated in `architecture.md` (historical eleven repair paths plus two dated release-document corrections);
- the bounded independent-review security repairs, maximum-monotone budgeted whitespace classifier with fail-closed ambiguous multiplicities, and endpoint/worktree pre-read budgets with focused regressions;
- fast whitespace, secret, spec, and selected-chain checks before a later authorized commit;
- rollback and observable go/no-go criteria.

Out of scope:

- changing product behavior or tests beyond the exact compatibility and independent-review repairs recorded in this package;
- weakening secret, whitespace, range, receipt, or source-stability checks;
- issue #219 Trust CI runner/holdout/digest work or any `trust-ci/**` delta;
- network, remote, GitHub, deployment, Daybreak, merge, tag, release, or production action;
- committing before all four route analysis reports are present and reconciled.

## Constraints

- Preserve every source branch and commit.
- The staged tree before this package must equal source tree `0914b5d6...` exactly.
- Source-relative deltas are limited to three change-package templates,
  `.grok-stack/adaptive_grok/{util,verification}.py`,
  `tests/{test_change_receipts,test_hooks,test_util_fingerprint,test_verification_doctor}.py`,
  `decisions.md`, `mistakes.md`, `README.md`, `START_HERE.md`, and this package.
- Refresh the scope/design record against this corrected bounded scope using the user's existing explicit continuation instruction; it is local workflow evidence only, not self-review, an external grant, a signed human approval, or merge authority.
