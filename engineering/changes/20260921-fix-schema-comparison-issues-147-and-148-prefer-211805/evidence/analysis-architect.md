# Schema precedence and bounded diagnostics design

Route `21180522da37`; architect analysis only; 2026-09-21. Baseline frozen PR170 `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. Read bootstrap/state/contract, architect role, route, issue147/148 snapshots, prior integration-architect reproduction and current architecture.py/architecture_fitness.py. Adaptive-delivery and bugfix/API skills apply. Single writer is general_implementer; no source contracts, deployed policy or external effects are in scope. No new execution-success claim.

## Scope ruling

Issue148 says not to change comparator precedence because it was written as an isolated diagnostic repair. This combined route explicitly authorizes issue147's precedence correction as a separate change. Keep the two effects independently testable: #147 changes resolver identity; #148 changes only formatting/count of unattributed findings. Do not use diagnostic cleanup to modify producer compatibility semantics, reason tuples, scope, or head/base refusal policy.

## Path resolution

`architecture.py:1268` already centralizes both resolution modes in schema_reference_target_path. `_SchemaResolver.resolve:1404-1410` currently requests ID_FIRST; change that caller to PATH_FIRST and update obsolete documentation that describes shadowing as intentional. When the strict relative-path lookup names a declared contract, choose that path regardless of a different claimant's $id. Only when no concrete path resolves should declared-ID lookup choose the target. Fragment processing and reference budgets remain unchanged.

Preserve explicit pure-ID references such as URN and HTTPS. Their path result is NOT_A_PATH, a supported fallback result, so the shared helper already reaches the ID table under PATH_FIRST. Review unsafe relative grammar carefully: the helper fails before consulting IDs for non-unresolved path errors. Do not widen syntax to solve this issue; run the shipped inventory and report any legitimate pure-ID regression instead of changing schemas. Same-target path/ID agreement remains legal.

A new global validation rule rejecting path-like IDs is not required for the minimal route: the issue accepts concrete-path precedence, and rejecting declarations globally can break inherited inventories and bypass the diagnostics/recovery policy being preserved for #148. Do not silently add such a rule merely because the issue offered it as an alternative. Duplicate ID-only resolution must still fail closed, while a real path may resolve even if unrelated claimants duplicate that text; existing closure diagnostics retain their separate signal.

## Dependency closure

Only current production callers are comparator resolve and `_reference_identity_candidates` in architecture_fitness.py. The latter currently unions PATH_FIRST and ID_FIRST candidates, including legacy identity recovery for strict-grammar refusal. Preserve this conservative union in this bounded fix: it cannot lose the true path edge, and removing claimant edges would separately change certified scope and existing ambiguity signals. A claimant-only edit may still conservatively trigger extra comparison; it may no longer redirect the comparator. Update comments that claim the comparator still uses ID_FIRST, explicitly describing retained conservative closure behavior. Do not simplify unsafe-path recovery, self-edge handling, transitive expansion or base/head union.

## Diagnostic bounding

Implement #148 at the final unsupported emission in `_contract_compatibility:898-910`, after `_contract_dependency_closure` has completed both inventory passes. For each in-scope referrer, compute sorted unique detail strings, emit at most a named positive constant (e.g. `_UNATTRIBUTED_REFERENCE_LIMIT = 5`), then one deterministic summary carrying the exact count of omitted unique details: `(+N more unattributed references)`. Keep the referrer prefix in the summary and never emit a summary when nothing was omitted.

Do not stop reference traversal after the cap, cap the raw signal collector, or skip the second inventory: a fatal head-only ambiguous ID encountered later must still abort and name its ID/carriers. Do not cap unrelated incompatibility findings or other unsupported reasons. Both inventories contribute to the deduplicated set without declaring either authoritative; authority remains solely their existing different abort policies. The row remains unsupported if any unattributed signal exists, even when all its concrete details beyond the cap are summarized.

This bounds report output per referrer, not collection memory. Existing schema-byte and contract-count bounds remain the memory boundary; describe this limit accurately rather than claim bounded collection. `_AMBIGUITY_OWNER_LIMIT = 5` bounds carrier names within a detail and is a separate limit that must remain intact.

## Acceptance tests

1. Exact issue147 target minLength 1->9 reproducer returns incompatible with narrowed_constraint despite unchanged claimant `$id=dir/target.json`; no-claimant control matches. Check path/ID agreement, nested relative path plus fragment, and claimant-only changes cannot redirect comparison.
2. Pure URN/HTTPS ID lookup and external/local fragments retain behavior. Ambiguous ID-only lookup remains unsupported/fail-closed as before. Unsupported unsafe relative grammar and work budgets remain unchanged.
3. Dependency tests still include the real path target, transitive referrers and before/after edges. Preserve all existing closure safety tests rather than rewriting them to a reduced scope. Tests that explicitly assert old comparator shadowing must be updated to the new expected target, with scope versus comparison distinguished.
4. Repeated identical collision within each inventory and across base/head yields one finding per referrer/detail. More unique details than limit yields exactly limit+1 unattributed lines, no duplicates, deterministic ordering, and summary count equals omitted unique details rather than repeated occurrences. At limit and empty cases emit no summary.
5. Multiple referrers get independent caps; out-of-scope referrers remain silent. A fatal head-only ID collision after many preceding signals still aborts. Base-only ambiguity stays nonfatal and visible only for the certified scope. A distinct non-unattributed refusal remains visible even after the unattributed cap is exhausted.
6. Inspect shipped inventory with unchanged contract bytes; focused architecture model/fitness tests precede coordinator full PR verification and independent code/test reviews.

## Risk and recovery

No public schema, migration, architecture rule, producer policy or runtime changes. Main risk is a false compatible verdict from incomplete resolver/graph coverage; secondary risk is hiding refusal evidence through premature truncation. Rollback is a code/test revert, although reverting precedence would reintroduce the known false-certification case and is inferior to a forward repair. Open PR137 changes nearby metadata comparison; record integration conflict risk and reconcile its final diff later, without reimplementing its separate behavior here.

Shared-memory fact for coordinator: diagnostic limits belong after complete dependency traversal; output bounding and memory bounding are distinct claims, and a cap must never turn late head-side ambiguity into a pass.
