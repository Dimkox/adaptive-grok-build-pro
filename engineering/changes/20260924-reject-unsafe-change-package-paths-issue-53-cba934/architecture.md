# Architecture — Reject unsafe change-package paths (issue 53)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`start_change` built the package identity by splicing three unvalidated pieces together — the first ten characters of `route['created_at']` with dashes removed, `slugify(title)` and the first six characters of `route['route_id']` — joined them with `-`, and used the result directly as a directory name under `engineering/changes/`. Nothing asserted that the result was one path component: a backslash survives `slugify`, so the title `trust-ci/C:\Users\…\new-chat` (issue #53) and a hostile `route_id` such as `C:\Users\x` produced multi-level or Windows-shaped names, and a control byte in `created_at` produced `202609\x012-safe-title-056f08`. `transition` joined the caller-supplied `change_id` onto the packages root with no containment check, so `transition(root, '../../outside', 'scoped', …)` returned status `scoped` after rewriting `<root>/outside/state.json`. `_mirror_checkpoints` derives the repository root from `path.parents[2]`, which such an id corrupts as well. There was no refusal path, so raw hostile text never had to be rendered — and once introduced, echoing it verbatim would have put terminal control bytes into logs.

## Proposed behavior

The same writer, failing closed. A title is screened by `title_block_reason` for a backslash, a C0/DEL/C1 control byte (tab, newline and carriage-return excluded) and a standalone drive prefix matched by `DRIVE_PREFIX`, whose lookbehind keeps `https://` out of the rule. Each derived component and then the joined id are screened by `change_id_block_reason`, which accepts only a non-empty, non-traversal, whitespace-trimmed string of alphanumerics plus `-._` up to the 255-byte component limit. Any caller-supplied id is resolved through `package_dir`, which re-runs that check and additionally requires the resolved parent to be exactly `engineering/changes/`. Every rejection goes through `_refuse`, which raises `ValueError` with the input rendered by `printable_value`. Validation happens before the first write, so a refused call creates and modifies nothing; accepted calls behave exactly as before.

## Components and boundaries

- `.grok-stack/adaptive_grok/change.py` owns the entire seam. New constants `PACKAGES_RELATIVE`, `MAX_COMPONENT_BYTES`, `ALLOWED_COMPONENT_PUNCTUATION`, `TITLE_CONTROL_BYTES` and `DRIVE_PREFIX` keep the rule in one place.
- New helpers: `printable_value` (diagnostic rendering), `title_block_reason` (summary-vs-path), `change_id_block_reason` (one-safe-component), `_derive_change_id` (per-component validation of the derived id), `package_dir` (the single containment resolution used by every package read and write). `_refuse` is the only raise site and the only place a refusal message is formatted.
- `start_change` and `transition` gained validation, not new responsibility. No other module changed.
- `scripts/grok_change.py` is the only caller of both entry points; it is unchanged and propagates the `ValueError` through its existing error path.
- `.grok-stack/runtime/active-route.json` stays untrusted input that is read first and validated before it can name anything.

## Data flow

Active route record (`created_at`, `route_id`) plus the task title → `title_block_reason` → `_derive_change_id` builds the three components and validates each, then validates the joined id → `package_dir` resolves one directory under `engineering/changes/` → template copy, `change-spec.yaml`, `route.json`, `state.json` → `_checkpoint` and `_mirror_checkpoints`. For a transition: caller `change_id` → `package_dir` (same component rule plus the resolved-parent check) → `state.json` → status history → mirrored checkpoint. A refusal terminates at `_refuse` before the first filesystem write; `state.json` and `route.json` remain the only durable outputs and their schema is unchanged.

## API and event contracts

None changed. No HTTP route, webhook, event schema, queue message or file under `contracts/` was touched, and `change-spec.yaml` declares empty `contracts`. The only observable difference at the Python boundary is the set of inputs `start_change` and `transition` refuse (`ValueError` where they previously wrote to disk); accepted inputs, return documents and the package directory layout are unchanged.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none — the route declares `human_gates: []` and selects no governance rule for this seam.
- Applicable canonical example IDs/versions: none.
- Open or overdue debt IDs: none opened. One pre-existing looseness is accepted and recorded in `brief.md` (Out of scope) and `requirements.md` (Governance context): `schemas/change-spec.schema.json` still allows `:` inside `change_id`, which is looser than the writer rule added here.
- Expected governance handoff or receipt impact: none — `governance/` is untouched; only the route's local `verification`, `code_review` and `test_review` receipts bind to this tree.

## Bitrix-specific impact

- Modules/events/agents/components affected: not applicable — the route selects the `api` domain and the change touches Python in `.grok-stack/adaptive_grok/` only.
- Cache and managed cache impact: not applicable.
- Installation/update/uninstall impact: not applicable; there is no install, update or uninstall step for this code.
- Core modification: forbidden unless explicitly approved.

## Decisions

The writer refuses instead of sanitising silently. Stripping `\`, `:` or a control byte from a title would have produced a working package while hiding the caller bug that handed a filesystem path where a summary belongs, and would still have written the remainder of that path — including a host username — into a public repository; a raised `ValueError` names the refused input and the rule that fired (SIG-001) and leaves no partial package behind. Validation is applied per derived component as well as to the joined id, because `created_at` and `route_id` are spliced in verbatim and are reachable through the route record, not only through the title. Two relaxations are deliberate: `:` and `/` remain allowed inside a *title* because they are ordinary task prose, cannot survive `slugify`, and refusing them would break routing for most real task text; non-ASCII names remain allowed because all 148 historical package directories, 19 of them Cyrillic, must stay readable and transitionable until issue #52 handles their transliteration. `package_dir` keeps the resolved-parent check on top of the character rule so that even a syntactically clean but escaping id can never leave `engineering/changes/`.

## Risks and mitigations

- Over-tight validation orphans a shipped package. Mitigated by `test_every_historical_package_name_is_still_acceptable`, which loops over all 148 directory names under `engineering/changes/` asserting `change_id_block_reason` returns `None`, and by `test_historical_non_ascii_paths_are_readable_and_printable`, which reads their `state.json`.
- A legitimate title gets refused and routing regresses (a `fix:` prefix, a path or a URL in task text). Mitigated by keeping those cases accepted and asserting them in `test_ordinary_punctuation_in_a_title_is_still_accepted` and `test_a_url_in_a_title_is_not_mistaken_for_a_drive_prefix`.
- An operator hits a refusal mid-workflow and loses a package. Bounded: nothing is written before the check, so the call is re-runnable with a corrected summary, and the message renders the input printably instead of dumping raw bytes.
- Residual schema mismatch: `change-spec.schema.json` still permits `:` in `change_id`. Accepted — no id derived after this change can contain `:`, and tightening the schema would touch historical ids owned by issue #52.
