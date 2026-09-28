# Independent test review — `e3924257` (PASS)

- Package-stated base: `5713b407818dbb6c2d1acfcb0b0d9661c32e1153`
- Candidate HEAD: `e3924257a1b4fdfe5fe806be9a8969af582affc9`
- Git tree before and after probes: `b666d556e27d792d7cc0145d4c79f74d5c55a7fa`
- Worktree before and after: only untracked `engineering/changes/20260924-reject-unsafe-change-package-paths-issue-53-cba934/evidence/next-gap.md`, sha256 `9f577352e25774070f5e1393aee3ece489c0282942ef475454e394079cb97c22`
- `tree_fingerprint()` was not executed: that shell objective was circuit-broken. The identity above is HEAD, `HEAD^{tree}`, and the one untracked file, and it matched after the probes.
- Scratch: `/home/pall/.review-scratch-e3924257` mode `0700` under `/home/pall` (mode `750`, not sticky). Snapshot is a git archive of HEAD plus `next-gap.md`. Its scratch commit tree is `4b55e7e4d5a45ea9ac2aeca2d9ac1d9cd8f3dd3c` because that file was committed there. Mutations stayed in the scratch.
- Reviewer: route-selected `test_reviewer`, read-only on the candidate.
- reviewed-tree-modified: no
- Verdict: **PASS**. No Critical or Important finding. One Minor limitation: a redundant route-snapshot backstop is not independently mutation-locked.

Startup capacity, recorded before the review and not remeasured after the quota probe was blocked: `2026-09-26T15:58:12+00:00`, `nproc --all` 28, `nproc` 22, affinity `0,1,8-27`, cgroup `0::/user.slice/user-1000.slice/session-10543.scope`, cpuset `/user.slice`. Physical cores, `cpu.max`, and the `taskset -c 0-27` widening probe were not established; the circuit breaker blocked that objective. Conservative capacity used here is 22. This review did not dispatch other agents.

## Question

Does `tests/test_change_path_safety.py` lock issue #53?

Yes, for the writer and structure class this package accepted. Issue #53 is a Windows path materialised as a directory (`trust-ci/C:\Users\…\new-chat/…`), a missing structure check that would have rejected `\`, `:`, or a drive prefix in a tracked or untracked name, and the host-identity leak that follows. The module pins those outcomes: hostile titles and route identities are refused before a package exists, caller-supplied ids and package-root symlinks cannot write outside `engineering/changes/`, route ids that are not one bounded snapshot component are refused, the change CLI turns `ValueError` into exit 2 without a traceback, and the structure scan fails on the issue-shaped untracked path and on a raw non-UTF-8 name. Ordinary prose, CRLF, and the historical Cyrillic package name stay accepted.

The issue's AGENTS.md blanket-commit guidance and the absent `test_promotions.py` on `main` are recorded residuals of this package. This module does not claim to lock them.

## Executed evidence

Control, from the candidate worktree, bytecode writes disabled:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_change_path_safety
Ran 36 tests in 12.193s
OK
```

`git status --porcelain=v1` immediately afterwards was still only `next-gap.md`.

Mutants were applied only under the scratch, then the same module or the named tests were run with `PYTHONDONTWRITEBYTECODE=1`.

| Mutant | Edit | Result |
| --- | --- | --- |
| Title backslash guard | `change.py` line 137, `if` forced false | **Killed.** 4 failures. `test_backslash_alone_leaks_no_host_identity` and the UNC differential row accepted `\\fileserv\…` with no `ValueError`. `test_backslash_title_creates_no_directory` still refused `trust-ci/C:\Users\…\new-chat`, but for `drive prefix`, so the required `backslash` reason failed. |
| Route-id pattern | `state.py` `route_id_block_reason`, pattern check forced false | **Killed.** `test_route_snapshot_writer_enforces_the_complete_id_alphabet_and_length` accepted both `abcdef\child` and 129 `a`s. `test_full_route_id_cannot_escape_runtime_snapshot_paths` created `20260926-safe-title-abcdef` for `abcdef/../../../../../victim` and raised `OSError: File name too long` for the 300-character id inside `update_route` after scaffolding. |
| Route snapshot parent check | `state.py` line 135, `resolved.parent != base` forced false | **Survived.** Full module, 36 tests, 11.719s, OK. See the limitation. |
| Package child containment | `change.py` line 284, `resolved.parent != base` forced false | **Killed.** `test_transition_cannot_write_outside_the_packages_directory` did not raise for the outside symlink, and `outside/state.json` bytes changed. |

With the route-id pattern already disabled and the parent check left intact, `test_route_snapshot_writers_reject_an_escaping_route_id` still passed. The parent comparison is what satisfied that test. It is not what the suite requires while the pattern remains, which is why removing only the parent comparison stayed green.

A separate scratch rename probe (`mv` onto `inside/id.json` symlinked to `../victim`) left `victim` containing `ORIGINAL` and replaced the leaf symlink with a regular file. That matches `atomic_write_text`, which writes a temp file in `path.parent` and `os.replace`s it onto `path`.

## Why the issue class is locked

- AC-001. Backslash, UNC, drive prefix, and POSIX/tilde/Unicode absolute titles each have a no-directory assertion. The executed backslash deletion shows the UNC case is not redundant with the drive-prefix rule, and the issue-shaped `C:\Users\…` title is still refused by the drive-prefix rule.
- AC-002 / AC-006. Control bytes, surrogate titles, nested route payload, non-finite numbers, wrong field shapes, and a hostile `route_id` / `created_at` are refused with an empty `engineering/changes/`. Disabling the route-id pattern was killed before a safe snapshot could stand in for an escaping id, including by a package directory actually appearing.
- AC-003. `printable_value` is asserted directly for controls, C1, bidi marks, Cyrillic, and the 160-character bound, and the refusal/CLI tests require the escaped form rather than the raw byte.
- AC-004. Package child, package-root, and package-root loop cases assert outside bytes or an empty external directory and a bounded `ValueError`. The child deletion was killed by an observed outside write. Route-directory symlink and loop tests assert the same for `set_active_route`.
- AC-005. Colon, slash, URL, `/goal`, CRLF/tab, and `HISTORICAL_CYRILLIC` (`20260814-рабочий-релиз-v2-0-0-пакеты-и-выкат-e86e93`) must still create, transition, read, and print. Differential harmless titles pin the over-tight direction.
- AC-007. The change CLI tests require exit 2, empty stdout, `error: refusing to`, no traceback, and no package for hostile titles, an escaping route id, and non-object persisted routes.
- AC-008, this module's half. `test_writer_and_schemas_reject_the_same_unsafe_id_shapes` ties `package_id_block_reason` to both persisted schema patterns and to every current package directory. `grok_spec generate` is not executed here; it calls `package_dir`, whose outside-write deletion this module killed.
- AC-009. `test_tracked_tree_has_no_backslash_colon_or_control_byte_path` scans `git ls-files --cached --others --exclude-standard -z`. The nested tests copy that test into a fixture repo and require a non-zero result for `trust-ci/C:\Users\someone\new-chat/probe.py` and for a raw `\x85` filename, without `UnicodeEncodeError`.

## Limitation

Minor. `route_snapshot_path`'s `resolved.parent != base` check is not independently locked. For a pattern-valid id the resolved parent leaves `routes/` only when the leaf `routes/<id>.json` is a symlink (the routes directory itself is a separate, tested check). `dump_json` does not follow that final symlink: `os.replace` replaces the directory entry, and the rename probe left the outside target untouched. The check is still the backstop that blocked `abcdef/../../../../../victim` after the pattern was removed, but no current test reaches it while the pattern is present. A regression that deletes only that comparison stays green. It does not reopen the issue's outside write unless the route-id pattern is also gone, and that second deletion is killed.

## Unexecuted

Further `sed` of scratch `state.py` and `change.py` was then denied as a protected-path shell mutation. These claims were not mutation-probed in this pass; the control suite already executed the tests:

- drive-prefix, absolute-path, non-printable, and control-byte title rules as separate deletions
- `printable_value` pass-through and truncation
- package-root symlink and symlink-loop handlers
- symlinked `routes/` directory and its loop handler
- `route_payload_block_reason` and `route_shape_block_reason` early `return None`
- `grok_change.py` catching `RuntimeError` instead of `ValueError`
- allowing `:` or dropping `nul` from package ids
- treating newline as a title control byte
- an ASCII-only absolute-path expression
- raising the route-id length bound above 128 without removing the alphabet

A live leaf-symlink call through `set_active_route` was not run; the probe script was circuit-broken, and the rename experiment plus `atomic_write_text` is the evidence used instead. Windows/NTFS, concurrent symlink swaps, external Trust CI, `grok_verify`, and attribution of the original malformed-path writer were not judged.

VERDICT: PASS
