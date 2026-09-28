# Independent code review — `e3924257` (FAIL)

- Base: `5713b407818dbb6c2d1acfcb0b0d9661c32e1153`
- Candidate: `e3924257a1b4fdfe5fe806be9a8969af582affc9`
- Git tree before and after probes: `b666d556e27d792d7cc0145d4c79f74d5c55a7fa`
- Fingerprint after probe cleanup (HEAD plus the pre-existing untracked `evidence/next-gap.md`): `b6cc6e69e66b93dcac82621d2efce4a1b3df2aed2a568c650ecd19e3e52c8f9f`
- Reviewer: route-selected `code_reviewer`, read-only on product code.
- Scratch parent: `/home/pall/tmp-review-e3924257` mode `0700`. Behavioral probes ran in `project_copy` temp directories against the candidate modules. A temporary driver under this evidence directory was removed; `git status` returned to the pre-existing untracked `next-gap.md` only.
- reviewed-tree-modified: no
- Verdict: **FAIL**. One Critical finding and two Important findings. Two Minor residuals do not by themselves decide the verdict.

## Capacity snapshot

Measured `2026-09-26T15:58:04+00:00` before the diff review. `lscpu`: 1 socket, 14 cores, 28 logical CPUs, online `0-27`. `nproc --all` = 28, `nproc` = 22, process affinity `0,1,8-27`. Child probe `taskset -c 0-27 nproc` returned 28. Cgroup quota reads were circuit-broken and were not retried, so the quota is unknown. Conservative capacity used for this review is 22. No parallel CPU-heavy workers were dispatched.

## What holds

`set_active_route` refuses an external `routes` root and an external `.grok-stack` root before it writes. The second case was probed directly: the external directory stayed empty and the error was `ValueError: refusing route snapshot: runtime routes root resolves outside the repository`. Package-id traversal, colon and trailing-dot refusals, historical-name compatibility, printable diagnostics, and the focused-scope veto for colon/control/surrogate inventory remain covered. `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_change_path_safety tests.test_change_spec` plus the two unsafe-inventory scope tests finished `OK`, 75 tests in 12.743s. Those tests do not construct a symlinked runtime parent or a child `state.json` symlink.

## Findings

### Critical — a refused `start_change` still writes outside through a symlinked runtime

`start_change` creates the package and calls `set_active_change` before `update_route` reaches `route_snapshot_path`. `set_active_change` only joins `.grok-stack/runtime/active-change.json` and `atomic_write_text` follows that parent. When `runtime` is a directory symlink to an external directory, the snapshot check later raises, but the external file is already there.

Observed in a throwaway copy whose `runtime` directory was replaced with a symlink to `root.parent / 'outside-runtime'`, after a normal route had been saved and copied to that target:

- error: `ValueError: refusing route snapshot: runtime routes root resolves outside the repository`
- external listing gained `active-change.json` (absent before the call)
- `engineering/changes/20260926-safe-summary-for-the-probe-73f97c` was created inside the copy
- the `ValueError` text did not contain the copy root

`scripts/grok_change.py` turns that `ValueError` into `parser.error`, so the CLI reports a usage failure and does not undo the external write. `os.replace` replaces an existing `active-change.json` in the symlink target; this probe observed creation, not a pre-seeded overwrite.

### Important — `update_route` creates an external runtime directory and does not bound symlink-loop errors

`update_route` takes `runtime_lock` before `route_snapshot_path`. The lock calls `runtime_dir`, which does `mkdir(parents=True, exist_ok=True)` on `.grok-stack/runtime`. `set_active_route` does the containment check first; `update_route` does not.

Observed when `.grok-stack` itself was a symlink to an empty external directory and `update_route(root, status='draft')` was called with no active route:

- return value `None`, no exception
- external listing changed from empty to `runtime/`
- the lock file was removed again; the directory remained

A `runtime` symlink loop on the same API raised `FileExistsError: [Errno 17] File exists: '/tmp/adaptive-grok-test-…/project/.grok-stack/runtime'`. That is not the bounded `ValueError` used for package-root loops, and the message contains the absolute path. `grok_change.py` does not catch `FileExistsError`, so the CLI would traceback.

### Important — `transition` follows a child `state.json` symlink and copies outside JSON into the package

`package_dir` refuses a package directory whose resolved parent is outside `engineering/changes`. It does not inspect children. `transition` then uses `Path.read_text` and `json.loads`, which follow a symlink. `dump_json` uses `os.replace`, so the outside file is not overwritten; the symlink is replaced by a regular file inside the package, after the outside bytes have been parsed.

Observed for a real package whose `state.json` was replaced by a symlink to `{"status":"draft","checkpoints":[],"secret":"OUTSIDE-MARKER"}`:

- `transition` returned success (`error` null)
- outside bytes were unchanged and the symlink was gone
- the returned state and the new in-package `state.json` both contained `OUTSIDE-MARKER`

A non-JSON target did not echo the marker: the CLI exited 2 with `Expecting value: line 1 column 1` and no traceback. The JSON case still imports outside content. AC-004 names child symlinks.

## Minors (not the verdict)

- `title_block_reason` refuses `/home/pall/secrets/notes` and `~/secrets` is only one segment, but `~pall/secrets/notes` is accepted. `start_change` created `20260926-pall-secrets-notes-4f28da`. The username from a `~user/...` title therefore becomes a public package path. The published regex only anchors `~/` or `/`.
- A 129-character and a 130-character id matching the shared pattern are rejected by `package_id_block_reason` (`MAX_PACKAGE_ID_CHARS` is 128) but match the v1 schema, which has no `maxLength`. The v2 pattern also matches; v2 additionally declares `maxLength` 128. This is not a write bypass.
- `transition` of a pattern-valid missing id still raises `FileNotFoundError(path)`. The CLI exits 1 with a traceback whose `FileNotFoundError` line contains the absolute `…/engineering/changes/20260926-missing-package-abcdef/state.json`. That shape predates the `ValueError` handler; it is still an absolute path on the diagnostic stream.

## Probes and mutations

Executed claims and results:

- External `routes` / `.grok-stack` symlink on `set_active_route`: killed. Existing `test_route_snapshot_root_symlinks_are_refused_before_a_write` passed, and the `.grok-stack` probe left the external directory empty.
- External runtime symlink on `start_change`: survived. `active-change.json` appeared outside and the call still raised `ValueError`. No regression asserts this.
- External `.grok-stack` symlink on `update_route`: survived. `runtime/` was created and the call returned `None`.
- Child `state.json` symlink on `transition`: survived. Outside JSON was copied in; the outside file was not modified.
- `~user/a/b` title: survived the absolute-path rule and created a package.
- Schema lengths 128/129/130: 128 accepted by writer and both patterns; 129 and 130 rejected only by the writer.

Source mutants were not applied. A scratch-driver rewrite was circuit-broken, and the candidate tree was not edited. The 75 passing tests therefore did not kill the three symlink claims above. Windows/NTFS device names, TOCTOU swaps, Trust CI, and the original `trust-ci/C:\…` writer remain unexecuted and out of the accepted scope.

## Disposition

Do not treat `e3924257` as a passing code review. The route-id string escape and the package-root symlink refusal stay fixed. `start_change` / `update_route` still need the runtime root contained before `runtime_dir` or `set_active_change`, and `transition` must not follow a child symlink. This FAIL grants no receipt.

VERDICT: FAIL
