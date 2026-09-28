# Architecture — issue #218 clean squash delivery

## Source and candidate

Immutable development input is commit `68dfc70c5f58adcc927f731c5d88de09a1b4b242`, tree `0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66`. It contains cumulative #227/#226/#224/#222/#220/performance/#218 source. The recorded pre-package squash projection equalled that tree; this is historical construction evidence, not a claim that later repairs are byte-identical.

The delivery remains exactly one non-merge direct child of `cb9af4073ba6c3d515145164d771c75ebdfa3224`. Authorized review repairs are amended into that child only after the completion sequence below. Source branches remain intact.

## Exact post-source contour

The historical eleven non-package repair paths are:

- `.grok-stack/templates/change/brief.md`
- `.grok-stack/templates/change/requirements.md`
- `.grok-stack/templates/change/test-plan.md`
- `.grok-stack/adaptive_grok/util.py`
- `.grok-stack/adaptive_grok/verification.py`
- `tests/test_change_receipts.py`
- `tests/test_hooks.py`
- `tests/test_util_fingerprint.py`
- `tests/test_verification_doctor.py`
- `decisions.md`
- `mistakes.md`

The release-review correction adds only `README.md` and `START_HERE.md`, making thirteen non-package paths, plus this active change package. Those two documentation changes distinguish the September 24 observation from the locally present v2.0.19 tag; remote publication is unverified. `trust-ci/**`, #219, version/artifacts, architecture authority and external systems are excluded.

## Security boundary and algorithm

Root-bound, configuration-isolated Git execution disables replacement objects and ambient selectors. Closed-scope validation rederives the selected graph, bytes, object counts, worktree coverage and findings. Supported committed symlink blobs are inspected; gitlinks and unsafe/racing worktree objects fail closed. Diagnostics expose bounded path/commit/code metadata.

Whitespace comparison trims exact common prefixes/suffixes, occurrence-tags surviving equal-count clean lines, and reconstructs a maximum monotone anchor order using a budget-accounted longest increasing subsequence. Bad occurrences can be reused only in the same anchor interval. If surviving clean multiplicities differ in a changed interval containing bad lines, occurrence pairing is ambiguous: return typed incomplete coverage instead of discarding anchors and claiming clean. Established clean insertion and legacy-context cases remain compatible. Selection and interval work remain O(n log n) under one shared operation budget per chain/endpoint scan.

Endpoint blob loading validates the complete metadata batch, object identity/type and per-blob/aggregate sizes before requesting any content batch. Parsed content headers must match preflight metadata. Git object identities are immutable inside the trusted local Git administration boundary.

Worktree secret scanning shares one path/byte budget across dirty and untracked files. Paths are charged before inspection; descriptor-validated regular-file sizes are reserved before reading, and bytes are read only up to that reservation. Existing post-read descriptor/name/ancestor identity checks catch growth, replacement and other races. Exhaustion stops the loop and marks both worktree and total coverage incomplete. Scope recomputation repeats these checks. History and worktree phases each have their own explicit bounded resource inventory.

## Contracts, observability and recovery

No new API/event/schema/service/dependency is introduced. Report contract remains `adaptive-grok.verification-scan/v1` in receipt schema v2. Existing typed incomplete diagnostics now also describe ambiguity and pre-read budget exhaustion; old or incomplete receipts must be regenerated.

Observe source/base/head identity, inventory, scan completeness/findings, resource-limit codes, stage durations, and receipt freshness. Before delivery, preserve the branch or abandon it; after authorized delivery, use a separately reviewed revert of the single commit. No production/data migration occurs.

## Completion sequence

Focused adversarial tests → preliminary full `--no-record` verification → four independent reviews → persist reports and finish tracked accounting → `ready` → amend the single candidate → final recording verification on clean exact HEAD → verification PASS receipt → review receipts → read-only zero-gap status. Every product repair restarts the affected verification/review work. Local scope records and reviews are workflow evidence only; external App-owned exact-SHA Trust CI and required human approvals remain merge authority.
