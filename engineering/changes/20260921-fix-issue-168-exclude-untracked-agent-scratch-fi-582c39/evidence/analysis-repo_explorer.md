# Repo explorer: fingerprint of agent scratch (#168)

Read-only source analysis for route `582c39d6afb6` at `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. The probe below used a disposable temporary Git repository; no product files, receipts, or external state were changed.

## Reproduction and root cause

With `PYTHONDONTWRITEBYTECODE=1`, I initialized a temporary repository, committed `base.txt`, recorded `tree_fingerprint`, created untracked `.qwen/tmp/probe.txt`, recorded it again, then removed the probe. `changed_files` returned `['.qwen/tmp/probe.txt']`; the fingerprint moved and returned to its baseline after deletion. This independently reproduces the issue's A/B observation.

`.grok-stack/adaptive_grok/util.py:129-143` filters only existing runtime/cache noise. `changed_files` (`:145-176`) unions staged, unstaged and untracked Git paths, then applies that filter without knowing whether a path is tracked. `tree_fingerprint` (`:183-201`) hashes every surviving path and its bytes. Receipt creation/validation calls this utility in `.grok-stack/adaptive_grok/receipts.py:452,517,554,664`, so a scratch write stales legitimate verification/review evidence. Broadly adding `.qwen/` to `_fingerprint_noise` would also hide tracked agent configuration or a tracked scratch-path file, weakening evidence binding.

## Bounded repair and tests

- Filter **only untracked** paths under the exact generated prefix `.qwen/tmp/` (after slash normalization), never all of `.qwen/` or other agent/config directories. Preserve all tracked paths from index, staged and unstaged diffs, and HEAD's existing binding. Any failure to establish tracked status must be conservative: include the candidate in the fingerprint or surface an error; never treat an uncertain path as scratch. The current Git-command loop silently ignores command failures, so its failure behavior deserves an explicit regression arm. Avoid an arbitrary consumer-configurable ignore list for this repair.
- Put the predicate near `changed_files` in `.grok-stack/adaptive_grok/util.py`; all receipt callers then share one interpretation. `tests/test_verification_doctor.py:705` covers stale-receipt behavior and offers an integration seam, though a focused disposable-Git utility test is sufficient for the core rule. Cases: create/edit/remove an **untracked** `.qwen/tmp` file keeps fingerprint stable; tracked `.qwen/tmp` edit changes it; untracked `.qwen/config` or `.agents`/`.codex` configuration changes it; ordinary untracked product file changes it; backslash normalization is exact; Git tracked-set inspection failure cannot hide the file. A no-HEAD/non-Git fallback lacks a trustworthy tracked set and should retain all files conservatively.
- Keep `changed_files(base=...)` semantics in mind: it also reports product change scope, and a tracked path changed since the base must remain visible even if it lies under `.qwen/tmp/`. This is why provenance belongs at collection time, not in a blanket post-filter.

The change is locally reversible by reverting the utility predicate. Existing receipt hashes are tied to old semantics and should be refreshed on the final changed tree; local receipts remain evidence, not merge authority.
