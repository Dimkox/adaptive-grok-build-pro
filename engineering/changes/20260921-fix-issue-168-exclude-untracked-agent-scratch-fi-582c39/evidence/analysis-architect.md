# Fingerprint scratch exclusion design

Route `582c39d6afb6`; architect analysis only; 2026-09-21. Baseline frozen PR170 `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. Read bootstrap/state, AGENTS, assigned role/route, issue168, previous architect reproduction and current util.py. Single owner: integration_implementer. Applicable adaptive-delivery/bugfix/API/integration skills do not authorize external operations. This report claims source analysis, not a new executed verification.

## Minimal design

Add a fixed, narrow generated-scratch rule for `.qwen/tmp/` only. The concrete incident and prior temporary-Git A/B justify this path; names such as .codex, .agents, .qwen and .claude are not inherently disposable and must never be excluded wholesale. Do not add configurable fingerprint ignores. Prefix matching needs a directory boundary so .qwen/tmp-config.json and .qwen/tmpfile stay included. Normalize the lexical separator convention once; do not resolve symlinks to decide whether a path is disposable.

Apply this exclusion only to paths known to be untracked. Prefer obtaining a NUL-separated tracked index inventory with `git ls-files --cached -z` once per changed_files call, retaining success versus failure explicitly. Paths supplied by staged/unstaged/base diff are also evidence of tracked change, including staged deletion where an index listing alone no longer contains the file. Any tracked-change provenance or membership overrides noise filtering. A newly added tracked scratch file, content edit, rename or deletion must affect the fingerprint. Do not insert `.qwen/tmp/` into the unconditional `_fingerprint_noise` check without changing the caller semantics.

Current `_fingerprint_noise` suppresses several cache-like paths even when tracked. The requested invariant is stronger: tracked source always remains bound. Apply the override before existing noise checks too, and explicitly test a tracked file below a previously ignored prefix so a superficial agent-scratch-only fix does not retain that hole. Preserve existing noise treatment for genuinely untracked caches/runtime material. HEAD continues binding committed content; ordinary untracked product/config files continue binding their bytes.

## Conservative uncertainty

A failed, timed-out or malformed tracked-set lookup must not mean an empty trustworthy set. Disable the new scratch exclusion when Git cannot establish tracking status, retaining scratch bytes in the fingerprint. In a non-Git tree, retain scratch; in an unborn Git repository, tracked-index membership can still be queried even though git_head is absent. Do not infer untracked status from `NO_HEAD`. The existing filesystem fallback should hash more under uncertainty, never omit a newly matched scratch path. Do not claim this small change fixes every existing Git command-failure behavior in changed_files.

Use NUL-safe parsing for the new inventory, and ensure command mocks can distinguish that invocation. A path proven tracked by a diff must remain protected even if it is absent from the current index. Do not introduce metadata-only caching of tracking status across calls: staging scratch changes its ownership and must immediately change behavior.

## Acceptance criteria

1. Real temporary Git fixture with a committed product file: creating, editing and removing untracked `.qwen/tmp/probe.txt` leaves tree_fingerprint unchanged; changed_files omits it.
2. Force-add and commit a scratch-path file (including when .gitignore excludes its directory); editing, staged editing, staged/unstaged deletion and rename affect fingerprint. Staging a previously untracked scratch file also changes the binding.
3. Tracked `.qwen/settings.json`, `.codex/config.toml`, `.agents/...`, and at least one tracked existing-noise-prefix file remain bound. Ordinary untracked product files and untracked agent configuration remain bound; `.qwen/tmpfile` remains bound.
4. Tracked inventory failure/nonzero/timeout retains scratch changes; non-Git fallback retains them; unborn repo covers staged file protection. No failure is silently interpreted as permission to exclude.
5. Mixed product+scratch edits invalidate a representative fingerprint-bound receipt while scratch-only edits preserve it. Existing runtime receipt writes remain non-self-invalidating when genuinely untracked.
6. Keep `changed_files(base=...)` semantics for tracked base-only changes/deletions, since callers use the same utility for review scope. Document the exact excluded path and untracked-only condition, without implying whole-agent-directory immunity.

## Delivery and recovery

Focused tests can use temporary Git fixtures and synthetic receipts; no Docker, providers or external CI changes are needed. Coordinator then runs full PR verification and selected independent code/test/security reviews. Existing local receipts may invalidate once when fingerprint inclusion changes; rerun evidence rather than relabeling historical receipts. No persisted schema or deployed policy is changed. Rollback is code/test revert and regeneration of local receipts. Shared-memory fact for coordinator: a tracked-index set alone cannot protect staged deletions; tracked diff provenance must also override the noise rule.
