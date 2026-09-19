# Integration analysis: `change_id` and change-package path compatibility

Scope: read-only inspection of downstream contracts and consumers for issue #52 in this worktree. No product files or live services were changed or exercised.

## Findings

1. The generator is the primary source of the defect. `.grok-stack/adaptive_grok/change.py::start_change` puts `slugify(title)` directly into `engineering/changes/<change_id>`. `slugify` currently lowercases and strips task metadata, but explicitly retains Cyrillic (`[a-zа-яё0-9]`) and allows a 48-character component. The route supplies `created_at` and `route_id`; the actual task text/title is not required as identity.
2. The consumers already converge on a 128-character ASCII identifier envelope, though some are looser than others:
   - `schemas/change-spec.schema.json` and `schemas/change-spec-v1.schema.json` each currently accept the dated ID form with Cyrillic and a suffix of up to 120 characters; v2 also has `maxLength:128`.
   - `.grok-stack/adaptive_grok/workflow_artifacts.py` validates active-change IDs as `[A-Za-z0-9._:-]{3,128}` and derives the canonical path exactly as `engineering/changes/<id>`. The same module's `workflow_paths` enforces that bound, and task graph/report validators plus their JSON Schemas enforce 3..128 characters.
   - `factory/src/adaptive_factory/contracts.py` and `execution_contracts.py` accept `[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}`; SQL migration `015_execution_canonical_persistence.sql` repeats this exact 1..128 ASCII envelope for authority `change_id`.
   - `scripts/grok_spec.py`, `grok_artifacts.py`, deploy state, route/runtime JSON, and verification derive or compare the path from the exact ID string; they do not need a renamed or normalized directory.
3. The identifier appears in durable artifacts and trust bindings (route, active-change record, state, spec digest, workflow graph/report, execution authority packet, persisted factory intent). Silently rewriting existing IDs or paths would break exact equality, fingerprints/digests, receipts, package links, and possibly replay/authority bindings.
4. Current compatibility is mixed in the legacy tree: 119 package directories inspected; maximum name length is 64, so none exceed 128. Nineteen contain Unicode and therefore fail the ASCII runtime/factory validators; those are historical package IDs, not evidence that consumers should broaden to Unicode. No automatic directory rename is safe.

## Bounded recommendation

Use a single canonical **3–128 character ASCII** contract for IDs across newly generated paths and all schemas/validators:

`^[A-Za-z0-9][A-Za-z0-9._:/-]{2,127}$`

For generated IDs, retain the established dated prefix and route-derived collision-resistant suffix, with a conservative filesystem component budget of **64 ASCII bytes total**. Reserve fixed prefix/suffix lengths first; slug only safe, non-user-prompt task metadata (prefer a classified/routed task label or stable intent category), transliterate/strip to ASCII, collapse separators, and truncate the middle slug to the remaining positive budget. If metadata yields no safe letters/digits, use a fixed ASCII fallback such as `change`; do not include raw prompt text in the directory name. The 64-byte generator limit is an operational choice, not a schema limit: it remains below common 255-byte filesystem component limits and matches the longest current package names, while the 128-character contract remains compatible with execution and workflow APIs.

The `change-spec` schemas should be aligned with the consumer envelope: keep the existing required date prefix if that is a deliberate spec invariant, but replace the Cyrillic ranges with ASCII and ensure the length quantifier cannot exceed 128 (`date + separator + first slug char + bounded slug remainder + separator + route suffix`). The task-graph/convergence schemas can stay at `minLength:3,maxLength:128`; optionally add the shared ASCII pattern so schema and runtime reject the same identifiers. Preserve the stricter start-of-ID requirement in factory SQL/API (`[A-Za-z0-9]`), rather than weakening those consumers.

## Legacy-path migration

Do not rename historical Unicode directories as part of #52. Existing path names are immutable references in tracked documents, specs, receipts, governance facts, and possibly external records. New ASCII generation prevents new unsafe paths; old package data should continue to be read through explicit legacy/history handling. If any historical Unicode package must become executable/active, use a separately reviewed migration that inventories every exact-path reference and digest, writes the new tree atomically, updates all bound records/links, retains a verifiable old-to-new mapping, and invalidates/regenerates affected receipts and digests. Until such a migration exists, reject activation/use by ASCII-only runtime validators with a clear diagnostic rather than silently normalizing or moving it.

No database schema migration is indicated for this bounded generator fix: factory SQL already accepts the recommended canonical character/length envelope. Schema and application validators should be changed together only if implementation chooses to make the published `change-spec` contract explicitly ASCII-only; preserve legacy schema-v1 interpretation for existing records and avoid retroactive package rewrites.
