# Reject unsafe change-package paths (issue 53)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260924-reject-unsafe-change-package-paths-issue-53-cba934`
Created: 2026-09-24T23:44:29+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

GitHub issue #53: a tool handed a Windows path to the change-package writer and nothing rejected it. `start_change` accepted the literal title `trust-ci/C:\Users\…\new-chat`, spliced it into the derived id without checking that the id is one directory name, and the tree grew `trust-ci/C:\Users\…\new-chat/trust-ci/tests/test_promotions.py` — a multi-level path materialised from a field that is contractually a single component, publishing a host username in a public repository. Measured before the fix, the same writer also accepted a control byte (`engineering/changes/202609\x012-safe-title-056f08/`) and an injected `route_id` (`engineering/changes/20260924-safe-title-C:\Use/`), and `transition(root, '../../outside', …)` returned status `scoped` after rewriting a `state.json` outside `engineering/changes/`.

## Outcome

An unsafe change-package path is refused before anything is written. Creating or opening a package now either yields exactly one safe directory under `engineering/changes/` or raises `ValueError` and leaves the tree byte-identical, so a hostile route record or a mistyped title cannot put a path, a host username or a control byte into the repository. Refusal messages echo the offending input in printable form, so a diagnostic cannot inject terminal escape sequences into an operator's log. Ordinary task prose and every existing non-ASCII package keep working unchanged.

## Scope

### In scope

- Validate the title in `start_change`: refuse a backslash, a C0/DEL/C1 control byte (tab, newline and carriage-return excluded) and a standalone drive prefix such as `D:/`, all before the first write.
- Validate each derived id component separately — the `created_at` date part, the title slug and the `route_id` prefix — so a hostile `.grok-stack/runtime/active-route.json` cannot reach the filesystem either.
- Contain caller-supplied ids: `transition` resolves `change_id` through `package_dir`, which accepts only one safe directory component directly under `engineering/changes/`.
- Render refused input through `printable_value` in every refusal message.
- Regression coverage in `tests/test_change_path_safety.py`, including the backward-compatibility cases below.

### Out of scope

- Transliteration or renaming of the existing `engineering/changes/**` directories, 19 of them non-ASCII. Issue #52 owns that rename; this change must keep those names creatable, readable and transitionable.
- Anything under `trust-ci/**`. The issue's artifact happened to carry that prefix; this change guards the change-package writer, not the trust-CI tree, and performs no cleanup of already-committed paths.
- Tightening `schemas/change-spec.schema.json`, which still allows `:` inside `change_id` and is therefore looser than the new writer rule.
- `engineering/changes/20260924-reject-unsafe-change-package-paths-issue-53-cba934/requirements.md` and the typed spec in this package: written before implementation and not edited by it.

## Constraints

- Backward compatibility: `:` and `/` inside a *title* stay accepted — they are ordinary prose and cannot survive `slugify`; non-ASCII package names stay allowed. All 148 historical directory names under `engineering/changes/` must still pass `change_id_block_reason`.
- Data/privacy: a host username or an injected terminal escape sequence must not reach a public path or a diagnostic stream. No existing package content is rewritten, so no migration exists to guard.
- Performance: one pass over a short string per call plus two path resolutions; no measurable cost on package creation.
- Operational: the gate is unconditional — no flag can disable it — and a refusal raises `ValueError` naming the input and the rule (SIG-001) instead of silently sanitising, consistent with the declared one-step `forward_fix` rollback strategy.
