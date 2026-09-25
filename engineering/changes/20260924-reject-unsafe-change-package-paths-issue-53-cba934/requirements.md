# Requirements — Reject unsafe change-package paths (issue 53)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001 — Given a title that carries a backslash or a drive prefix, when `start_change` is called, then it raises `ValueError` and no directory is created under `engineering/changes/`.
- [x] AC-002 — Given a title or a route field that carries a control byte, when the change id is derived, then the call is refused before any filesystem write and the packages directory stays empty.
- [x] AC-003 — Given a refusal, when the operator reads the message, then the offending input is present and the message contains no byte a terminal would act on.
- [x] AC-004 — Given a caller-supplied `change_id` that resolves outside `engineering/changes/`, when `transition` runs, then it raises `ValueError` and the file outside the packages directory is unchanged.
- [x] AC-005 — Given ordinary task prose containing `:` and `/`, and the historical package names (19 of them Cyrillic), when validation runs, then all of them stay acceptable and readable.
- [x] AC-006 — Given a hostile route record, when the id is derived, then the refusal names *which* component was refused (`unsafe route id prefix`, `unsafe created_at date`, or `is not text`).

## Repair wave added by the independent reviews

- `package_dir`'s `candidate.resolve()` is wrapped: a symlink loop answered with `ValueError`
  instead of a `RuntimeError` traceback that prints the absolute host path (Major-1 of the code
  review), and symlink-to-outside plus a two-node loop are now tested.
- A POSIX absolute path handed as a title is refused (`ABSOLUTE_PATH_TITLE`, anchored, two or
  more segments). It is deliberately not a mention-level scan: `/goal …`, `api/v1 vs api/v2`,
  `scripts/grok_verify.py`, an embedded URL and prose containing such a path later on stay
  accepted, because `start_change` uses the raw user prompt as its default title.
- `printable_value` now carries the printability guarantee on its own (the message sites stopped
  wrapping it in `!r`, which escaped control bytes independently and made the function inert) and
  bounds the echo to 160 characters so a long prompt is not copied whole to stderr.
- Route `created_at`/`route_id` are type-checked instead of coerced with `str(...)`, which had
  turned `None` into a literal `None-…` id and destroyed the uniqueness suffix.
- A leading dash, a trailing `.`/space and the NTFS reserved names (`CON`, `nul.txt`, …) are
  refused for any package name.
- Tab, newline and carriage return in a title are ordinary whitespace, not control bytes; the
  original byte class refused `\r`, which would have failed a pasted CRLF prompt.
- `test_historical_non_ascii_package_stays_writable_readable_and_printable` no longer asserts
  that *new* names keep non-ASCII characters (that is #52's target state); it renames the fresh
  package to a literal historical Cyrillic name inside a throwaway copy and asserts the property
  there, so the guard cannot silently evaporate when #52 lands.
- Not fixed here on purpose: `scripts/grok_change.py` still lets the `ValueError` surface as a
  traceback instead of `parser.error(...)`. That file is contended by another contour in this
  wave; the sibling pattern to adopt is `grok_gate.py:50` / `grok_governance.py:53`.

## Failure and edge cases

- A route record with an injected `route_id` or `created_at` is the hostile input, not only the title: both are spliced into the id verbatim, so each derived component is validated separately.
- Tab and newline are ordinary in multi-line task text and are not control-byte refusals; every other C0, DEL and C1 byte is.
- `https://example.com/x` must not be mistaken for a drive prefix — the lookbehind keeps a letter-attached colon out of the rule.
- A package name that is only dots (`.`/`..`), whitespace-padded, or longer than 255 UTF-8 bytes is unusable on the filesystem and is refused with a reason.
- `_mirror_checkpoints` derives the repository root from `path.parents[2]`, so an id that escapes the packages directory would also corrupt that derivation; refusing the id first covers both.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none declared by the route (`human_gates: []`).
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: the durable contract `schemas/change-spec.schema.json` still allows `:` inside `change_id`, which is looser than the writer rule added here. Left in place deliberately: renaming historical packages is issue #52's scope, and no id derived after this change can contain `:`.

## Non-functional requirements

- Security: a host username or an injected terminal escape sequence must not reach a public path or a diagnostic stream.
- Reliability: refusal happens before any filesystem write, so a rejected call leaves no partial package to clean up.
- Performance: validation is one pass over a short string per call; no measurable cost on package creation.
- Observability: SIG-001 — refusals name the refused input and the rule that fired.
