# Test review — `tests/test_change_path_safety.py` (issue #53)

Reviewer: independent `test_reviewer` (route `cba934e15911`), read-only. Method: `python3 -B`
with mutants applied **in memory** (patched module source exec'd into a synthetic
`adaptive_grok.change`), scratch confined to `/tmp/qwen-testrev-53` (mode 0700); the reviewer
confirmed by `git status --porcelain` diff that it changed nothing in the worktree.

Baseline control measured by the reviewer: `Ran 12 tests … OK`, 12 methods, 181 `subTest`
blocks entered, 0 skipped, 0 failures, and re-loading the suite against an *unpatched* module
through the same harness was also green — so the harness introduces neither false greens
nor false reds.

## Mutation battery as first measured

| Mutation | First outcome | Now |
| --- | --- | --- |
| a — drop the backslash check in `title_block_reason` | KILLED only by an English substring; the username leak reproduced | KILLED behaviourally (`test_backslash_alone_leaks_no_host_identity`) |
| b — drop the title control-byte check | KILLED (4 failures) | KILLED |
| c — drop the drive-prefix check | KILLED (1 failure) | KILLED |
| d — `change_id_block_reason` always `None` | KILLED (3 failures + 2 errors) | KILLED |
| e — validate only the joined id, not each component | **SURVIVED** | KILLED (`_SubTest` in the route-component case) |
| f — remove `package_dir`'s containment check | **SURVIVED** (proven exploitable: `transition` rewrote `root/outside/state.json`) | KILLED (symlink-to-outside + symlink-loop subtests) |
| g — `printable_value` pass-through | **SURVIVED** (`repr()` escaped independently, so the function was inert) | KILLED (direct assertions + no `!r` at the message sites) |
| h — revert `transition` to an unvalidated path | KILLED (1 failure + 5 errors) | KILLED |
| i — remove the 255-byte component limit | **SURVIVED** | KILLED (`'x' * 300`) |
| j — also refuse `:` in titles (backward-compat direction) | green→red flip confirmed on 4 tests | KILLED (5 tests) |
| k — sanitise `..` by collapsing instead of refusing | KILLED by exception type | KILLED |

Re-measured after the repair wave with `/tmp/issuewave/mutants53.py` (in-memory, worktree
untouched): **9 of 9 killed, control green**. The four original survivors (e, f, g, i) are the
ones that needed new tests, and each now has one.

## Findings and their disposition

1. **Major — the only symlink defence had zero coverage.** `'evil'` passes component validation,
   so nothing could reach the containment branch; deleting it kept all 12 tests green while
   AC-004 claimed the boundary. **Repaired**: `test_transition_cannot_write_outside_the_packages_directory`
   now creates `engineering/changes/over-link -> ../../outside` and a `loop-a <-> loop-b` pair and
   asserts `ValueError` plus byte-equality of the outside `state.json`, and that the refusal
   carries neither the absolute packages path nor a newline.
2. **Major — the backslash rule was guarded only by a message substring**, and with a
   backslash-only input (no drive letter, no control byte) the host username still materialised.
   **Repaired** with a behavioural UNC-style case that asserts nothing was created.
3. **Major — `printable_value` was inert dead code**: every call site also applied `!r`, and
   `repr()` escapes control bytes on its own. **Repaired**: message sites now quote through
   `quoted_value()`/`printable_value()` alone, and the function is asserted directly (escaping,
   C1 bytes, non-ASCII visibility, and the 160-char echo bound).
4. **Major — per-component validation was unpinned** (only the joined id is distinguishable by
   the old assertions), with a measured escape producing the leading-dash name
   `-safe-title-4803cb`. **Repaired**: each route case now asserts which component was refused
   (`unsafe route id prefix` / `unsafe created_at date` / `is not text`), `created_at: ''` is a
   case, a leading dash is refused outright, and every case asserts an empty packages directory.
5. **Major — forward collision with issue #52**: the old test asserted that *newly created*
   package names keep non-ASCII characters, which is exactly what #52 proposes to remove.
   **Repaired** charset-independently: a throwaway copy now renames the fresh package to a
   literal historical Cyrillic name and asserts acceptance, `transition`, descriptor read,
   byte round-trip and printability — so the guard no longer depends on how many Cyrillic
   directories the checkout happens to keep.
6. **Minor — hard-coded bounds**: `assertGreater(len(names), 100)` (measured 148) and
   `assertGreater(len(tracked), 1000)` (measured 3949). These fail *closed* (a false alarm, never
   a silent green), but the package-count margin was thin, so the floors are now 20 and 500. The
   reviewer's simulated post-#52 tree showed the old `>100` floor firing while blaming the
   checkout; that misleading failure mode is what this loosening removes.
7. **Minor — two `skipTest` branches fail open** (git unavailable; no non-ASCII package left).
   Accepted deliberately: the checkout scan is supplementary evidence, and findings 1–5 moved the
   load-bearing guarantees onto fixtures that always run. The `checked > 0` floor still prevents
   the non-ASCII readability test from passing vacuously today.
8. **Minor — the byte-equality assertion in the traversal test is unreachable in the
   collapsing-sanitiser scenario** because the exception type fires first. Kept: it is the
   independent signal for the containment path (finding 1), which the reviewer proved red.

## Verified as genuinely non-vacuous (measured by the reviewer)

- The `git ls-files -z` structure test really inspects **3949** tracked paths (294 of them
  non-ASCII) and returns no findings; by design it does not flag non-ASCII, which is #52's rule.
- `unsafe_package_entries` really walks to depth 2: with validation and containment removed it
  reported `20260925-safe-title-ebe731/evidence` as a nested violation.
- `if not (ROOT / relative).is_file(): continue` skipped nothing: 19/19 non-ASCII packages carry
  `state.json`, `checked = 19`.
- `tests/test_structure.py:31` compares only top-level entries, so this module's scan is the
  repository's only structural guard for the #53 artifact shape — and it covers tracked paths,
  not untracked working-tree litter.

## Not verified by the reviewer (and still open)

- Windows/NTFS behaviour of the `:` and drive-prefix rules: reasoned, never executed on NTFS.
  The reserved-name rule added in the repair wave inherits that limitation.
- Whether a leading-dash package name breaks a concrete downstream consumer; the name was
  produced, not traced. (Moot for new ids now that a leading dash is refused.)
- Any interaction of this suite with sibling suites inside one verifier wave, and the
  fingerprint/verdict the in-flight gate bound to.

## Verdict
The reviewer's first pass was **FAIL** for merge-pending-push quality on coverage grounds
(findings 1–5). All five were repaired in this contour and re-measured: 15 tests green, mutation
battery 9/9 killed, control green, `ruff` clean.
