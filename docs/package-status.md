# Local package status and checkpoints

`python3 scripts/grok_status.py` observes the current worktree. It preserves `route`, `change`, `agents`, and `evidence_gaps`, and adds:

| Field | Meaning |
| --- | --- |
| `package_completeness` | Selected package identity, durable stage, observation time, typed findings, evidence accounting, and initial checkpoint HEAD. |
| `package_incomplete` | The same findings list, including expected draft work and explicit unavailable input. Consume each finding's stable `code`, `severity`, and `path`. |
| `worktree` | Current branch/HEAD, route base, named diagnostic base, commit count, dirty product paths, observation time, and unknown/partial-query findings. |

Package status is `draft`, `complete`, `incomplete`, or `unknown`. A valid new draft has expected unresolved objective fields and empty acceptance criteria. Those omissions are errors from `scoped` onward, including a blocked implementation. Malformed drafts still have errors. `complete` only describes the bounded fields inspected; it establishes neither a successful run nor a fresh receipt. Older packages without typed accounting receive `legacy_evidence_accounting` and are never rewritten by status. Historical v1 specifications remain readable but cannot establish current typed completeness.

The inspector reads `state.json`, `change-spec.yaml`, the eight standard package Markdown files, and explicitly declared current evidence references. It does not discover other packages/worktrees or crawl the evidence directory. It rejects traversal, symbolic links in any path component, nonregular files, concurrent replacements, invalid encoding, and unavailable safe-read support. Limits are 64 files, 256 KiB per ordinary file, the existing 1,000,000-byte spec limit, 1 MiB aggregate bytes, and 100 findings. Exceeding a limit is an incomplete inspection. Reports must be package-relative `.md` or `.json` files under `evidence/`, with at most three nested directories; hidden or credential/secret file names are excluded.

Only exact owned template tokens, the generated unchecked `Given ..., when ..., then ...` row, and a standalone `<!--RUNTABLE-->` in these current Markdown inputs are placeholders. Fenced/indented code, blockquotes, inline code, arbitrary TODO/TBD prose, and unreferenced historical reports are not current obligations.

Status does not create runtime directories or bytecode, refresh the index, fetch refs, write checkpoints, run tests, or alter receipt/grant state. Filesystem access times are outside this no-write guarantee. Existing receipt validation remains a separate, potentially more expensive operation. A known unsafe/unreadable package prevents legacy receipt readers from reopening that input and produces an explicit evidence gap; it never produces an empty success result.

## Diagnostic Git baseline

The immutable initial checkpoint HEAD is preferred for `diagnostic_base`, with `base_source=initial_checkpoint`. A legacy package without that checkpoint uses its available exact `route_base`, with `base_source=route_base`. Both values are exposed; route authority is never rewritten. A recorded but broken/unknown checkpoint does not fall back to current HEAD or the route base. Unavailable Git/HEAD/base, a nonancestor base, changed HEAD, or a failed/truncated query leaves the relevant values null/unknown.

`uncommitted_product_zero_ahead=true` means a complete snapshot saw dirty product paths and zero commits since that named base. It identifies work needing a checkpoint, not proof of a crash. NUL-delimited Git status includes staged, unstaged, deleted, renamed, and untracked paths, including whitespace and Unicode names. Package paperwork under `engineering/changes/`, runtime files, and conventional dependency/cache output are excluded; product Markdown, rules, and skills remain product paths. Snapshot limits are 256 dirty paths, 256 KiB output per Git query, and two seconds per query. The snapshot is observational, not an atomic content fingerprint.

`branch` and each `dirty_product_paths` identity is a UTF-8 string when possible. Otherwise it is a tagged object `{"encoding":"hex","value":"..."}` containing the original filesystem bytes; a literal filename resembling that object remains a string. Individual identities are limited to4096 bytes and the encoded path list to32768 bytes including its formatting reserve. Overflow produces the explicit `git_path_representation_limit` unknown observation instead of a truncated successful checkpoint.

## Durable lifecycle observations

New `grok_change.py start` calls write one initial checkpoint in `state.json` and append its human-readable presentation to `evidence/README.md`. It includes change/route identity, time, actual branch/HEAD (or explicit unknown), product dirty state, and `draft; implementation not started`. The first successful transition to `implementing` appends one implementation checkpoint. Repeated starts and later reentry to implementation preserve those observations. An old package can acquire its first implementation observation through an explicit transition; its original start HEAD is never fabricated.

The state file is canonical and is written before the README mirror. A mirror failure raises an error and leaves `checkpoint_mirror_pending=true` in durable state. Retrying `start`, or retrying the same transition to the already-recorded stage, repairs the mirror without adding another checkpoint/history event. This is explicit recovery, not two-file crash atomicity. Finish all package/checkpoint writes before final verification and review: they retain their existing effect on full-tree receipt freshness. Cross-host continuation still requires separately authorized commit/publication.

## Evidence accounting

New state contains `evidence_accounting` with `schema_version=1` and an `obligations` list. Route receipt kinds initialize as `not_run` with reason `implementation not started`. Authors explicitly maintain current rows in state; no receipt writer silently edits the package after computing its fingerprint. Additional domain runs must be declared, never inferred from prose headings.

Each row has a unique bounded `id` and `kind` (`receipt` or `run`). A receipt row also has `receipt_kind` from the existing closed receipt vocabulary. Every required route receipt kind needs a row. A row is either:

- `status=not_run` with a nonblank `reason` (at most 4096 characters); or
- `status=recorded` with `outcome=pass|fail`, a timezone-bearing ISO `recorded_at`, and a nonempty safe report `reference`, such as `evidence/verification.md`. A run additionally names its `command` as 1–32 string arguments, each at most 512 characters.

A recorded failure is accounted for. Neither a recorded result nor `not_run` proves execution success or satisfies `validate_evidence()`. This metadata is self-reported and does not replace structured review provenance, criterion coverage, signed approvals, or external Trust CI.

Stop prints bounded warnings and always remains nonblocking. A passing review with package errors is refused before creating/replacing its receipt; an incomplete account can still receive a failed review. Unsafe selected inputs prevent either receipt operation until binding can be read safely. Review preflight never requires its own or a subsequent review receipt. Existing receipt envelopes, freshness checks, delegated grants, PR-only delivery, and exact-SHA external merge authority remain unchanged.
