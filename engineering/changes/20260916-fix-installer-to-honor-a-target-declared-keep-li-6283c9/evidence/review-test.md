FAIL

# Test review — installer keep list (#110)

- Reviewer: route `test_reviewer` (read-only). Subject: `tests/test_installer.py` (7 keep arms) + `test-plan.md` vs `scripts/install_into.py`.
- Baseline: `/home/pall/grok-projects/adaptive-grok-build-keep` @ `9d83ba4a0fd4aa3f7f879acc7e2f4a2883e99017`, branch `fix/installer-keep-list`, `git status --porcelain` empty.
- All mutation/probe work ran in a private clone `/tmp/keepreview/clone` (`drwx------` 0700, independent repo, `git clone --no-hardlinks`); `install_into.py` was restored byte-identical after every mutation (`restored: True`, clone `status --porcelain` empty). The reviewed repo received no writes except this file.

## 1. Hermeticity + env — PASS

| Run | Result |
| --- | --- |
| `python3 -m unittest tests.test_installer` (clone, normal env) | `Ran 24 tests in 10.965s` → `OK` |
| `env -i PATH=/usr/bin:/bin HOME=/tmp/keepreview python3 -m unittest tests.test_installer` | `Ran 24 tests in 10.400s` → `OK` |
| `env -i PATH=/usr/bin:/bin` (no HOME) | 24 `... ok` lines, 0 failures |
| `python3 -m unittest discover -s tests -t .` (whole repo, HEAD) | `Ran 752 tests in 390.144s` → `OK (skipped=1)` |
| `ruff check tests/test_installer.py scripts/install_into.py` (repo config `select=["E4","E7","E9","F"]`) | `All checks passed!` |
| `ruff check --select F811 tests/test_installer.py scripts/install_into.py` | `All checks passed!` |

The 7 keep arms pass under `env -i`: they depend only on stdlib `json`, `tempfile`, the checked-out source tree as installer source, and `plan_install` (no subprocess). The only arms needing `python3` on `PATH` are the pre-existing CLI/subprocess arms. The added `import json` (tests line 5) is the single `json` import in the file, is not shadowed by any local name, and does not collide with the importlib-loaded module registered as `sys.modules["install_into"]`. F811 clean.

## 2. Mutation battery (21 mutants, keep-relevant code only unless noted)

| # | Mutation (anchor) | Result | Killed by |
| --- | --- | --- | --- |
| m1 | kept-filter deleted in `_make_plan`: `deliverable = tuple(selected_payload)` | KILLED | test 1, test 2 (not 3,4,5,6,7) |
| m2 | drift comparison always "identical": `elif existing is not None:` | KILLED | test 3 only |
| m3 | drop `S_ISREG` check in `_read_target_relative` | **SURVIVED** | — |
| m4 | drop kept-path/record size cap (`st_size > limit`) | **SURVIVED** | — |
| m5 | record parser accepts unknown keys (`if not isinstance(record, dict)`) | KILLED | test 5 subTest `unknown key` |
| m6 | symlinked record → silent empty (`try/except` → `frozenset()`) | KILLED | test 6 |
| m7 | **REPAIR** of the `target_state` clobber (`state` → `keep_state`) | **SURVIVED** (24 OK) | — ⇒ the shipped regression is undetectable |
| m8 | delete the `target-owned` branch | **SURVIVED** | — |
| m9 | `unmanaged` label → `absent` | **SURVIVED** | — |
| m10 | delete the `unmanaged` branch (path silently unreported) | **SURVIVED** | — |
| m11 | `reason: "declared by target"` → other text | KILLED | test 1 (exact-dict assert) |
| m12 | `action: "KEEP"` → other text | KILLED | test 1 |
| m13 | `for path in sorted(kept)` → `for path in kept` | **SURVIVED** | — |
| m14 | drop the `state == "directory"` short-circuit | KILLED | test 7 + 8 inherited (materialize/CLI/unsafe-ancestry) |
| m15 | `_target_state` returns `directory` for non-dirs (pre-existing fn) | **SURVIVED** | — (pre-existing, not this commit) |
| m16 | record read follows symlinks (`O_NOFOLLOW` dropped for the record) | KILLED | test 6 |
| m16b | kept **payload path** read follows symlinks (record stays safe) | **SURVIVED** | — ⇒ test 6's "…or path" half is decorative |
| m17 | intermediate directory `os.open` loses `O_NOFOLLOW` | **SURVIVED** | — |
| m18 | deliverable also drops `ruff.toml` (unlisted managed file) | **SURVIVED** | — ⇒ entry set not pinned (see §5) |
| m19 | nested kept path (`"/" in path`) still delivered | **SURVIVED** | — ⇒ AC-001 "never delivered" untested for `MANAGED_DIRS` shapes |
| m20 | `_path_parts(item)` per-entry validation removed | KILLED | test 5 |

Kill rate 9/21. Every survivor above is a gap, not a mutant-quality artifact: each was confirmed non-crashing and the suite green.

## 3. Acceptance criteria vs arms present

State matrix named by the objective (`absent|identical|target-owned|unmanaged`) is covered 2/4.

- **Critical — `target_state` regression shipped green (no arm).** `_make_plan` reuses the outer `state` variable (`= _target_state(target)`) as the per-path KEEP state (`scripts/install_into.py:785`, `:787`, report at `:792`, returned at `:797`). Measured on an existing directory target: declared `.coveragerc` absent → `target_state='absent'`; identical → `'identical'`; `target-owned`/`unmanaged` → `directory` (they `continue` before the assignment). Consequences proven: with a record declaring an absent kept path, `materialize_new` on an **existing** repository passes the plan-level guard at `:1242` and is only stopped later — traceback site `materialize_new:1308 → _materialize_new:1245 → _open_parent:912 → _stat_absent:889` — after the full 346-entry stage is built and then cleaned (target bytes intact, `.adaptive-install-*` residue none). So INV-001 ("materialize-new requires an absent target") is enforced by accident, and the plan JSON — a documented contract field (`docs/superpowers/plans/2026-08-27-m2a-queue-installer-pivot.md:65`, `absent|directory|unsafe`) — reports a state that never exists in that enum. Baseline: the value was correct at the merge base `379c641`, so this is a regression introduced by this commit. m7 proves no test can see it. Fix is one rename; the arm is `self.assertEqual(plan["target_state"], "directory")` in each of tests 1, 2, 4 plus one `materialize_new` refusal case on a directory target that carries a record.
- **Important — `target-owned` KEEP state untested (AC/objective).** m8 (delete the branch outright) and m9 (mislabel it) both survive. No test declares `architecture/system.yaml`, `architecture/rules.yaml`, `architecture/adoption.json` or a `governance/*/index.json` path in `kept_local`. This is the arm that answers "what happens when a consumer keeps a path the stack refuses to own" — user-visible plan output, zero coverage.
- **Important — `unmanaged` KEEP state untested.** m9 and m10 both survive; with the branch deleted, a declared path the stack does not manage disappears from `plan["kept"]` silently and all 24 tests still pass. Needs one arm (e.g. `kept_local: ["README.md"]` → `state: "unmanaged"`, still delivered as usual, `kept` names it).
- **Important — "never delivered" is untested for nested (`MANAGED_DIRS`) kept paths, the motivating case.** Test 4 declares `.grok-stack/config/routing.json` and asserts only its `state`; it never checks `plan["entries"]`. m19 (nested kept paths keep being delivered) survives all 24 tests. Test-plan row P0-1 claims "kept paths out of entries … keep tests 1, 2, **4**" — test 4 does not assert that, so the row overstates the evidence.
- **Important — AC-003 "bounded size" has no arm.** m4 survives. No test writes an oversized kept file or an oversized record. Measured behavior (`limit`s: `MAX_SOURCE_FILE_BYTES = 16777216` for kept paths, `MAX_SYNC_RECORD_BYTES = 65536` for the record): shipped code raises `kept path exceeds 16777216 bytes` (surfaced wrapped as `kept path is not safely readable: bandit.yaml`) and `kept path exceeds 65536 bytes: .grok-stack/AGBP_SYNC.json`; with the cap deleted both still fail closed but with misleading reasons (`kept path conflicts … would change it`, `stack sync record is not valid UTF-8 JSON`) because `os.read(fd, limit + 1)` truncates. Missing arms: one 17 MiB kept file, one >64 KiB record, asserting the cap message.
- **Critical (test gap + implementation hazard) — "kept path is a regular file" is neither tested nor enforced before the blocking open.** m3 survives. Behavior probes on a payload path that is not a regular file: directory → fails closed both ways (`is not a regular file` shipped; `EISDIR` → `cannot be read safely` without the check, so for directories the check is defense-in-depth); **FIFO → `plan_install` hangs forever in the shipped code**, `faulthandler` after 6 s: `install_into.py:681 _read_target_relative ← :781 _make_plan ← :809 plan_install`. Line 681 is `final = os.open(parts[-1], os.O_RDONLY|O_NOFOLLOW, dir_fd=parent_fd)`: the reader opens before it fstats, so the `S_ISREG` check at `:686` can never fire for a FIFO. The repo's own source-side reader does it in the safe order (`:473` `os.stat(..., follow_symlinks=False)` → `:474` `S_ISREG`/`S_ISLNK` → then `os.open`); `_read_target_relative` should copy that pattern (and the sibling test `test_materialize_new_rejects_existing_symlink_and_special_targets` already treats `fifo` as a real threat shape). Add the arm with `subprocess` + timeout so a regression fails instead of hanging CI.
- **Suggestion — symlinked *intermediate* directory of a kept path is unpinned.** m17 survives; the docstring claim "Every traversal step refuses symlinks" is pinned only for the record's final component (m16 killed by test 6). One arm with `t/.grok-stack` replaced by a symlink to an outside dir asserting `UnsafeInstallTarget` closes it.
- **Suggestion — test 6's name promises more than it delivers.** "record **or path**" — only the record is symlinked; m16b survives, so a symlinked kept payload file is unverified. Cheap: add a `bandit.yaml → /outside/bandit-copy` case and assert the raise (today's code raises correctly; nothing pins it).
- **Suggestion — determinism of the `kept` array order unpinned.** m13 survives. Entries are order-pinned (`test_existing_target_modes_are_read_only` asserts the byte-sorted path list) but `kept` is not, and the plan is advertised as deterministic JSON.
- **Nice to have — `_target_state` classification for a file/special target is unpinned** (m15). Pre-existing function, untouched by this commit; listed for completeness.

## 4. State matrix / materialize interaction

Shapes exercised today: `.coveragerc` (`MANAGED_FILES`) = absent (test 1), identical (tests 2, 4); `bandit.yaml` (`MANAGED_FILES`) = identical (test 4), drift (test 3); `.grok-stack/config/routing.json` (`MANAGED_DIRS`) = **absent only** (test 4). So for a nested managed path, both `identical` and `drift` are unexercised — the drift arm in particular is where the byte-compare and the `_read_target_relative` traversal of intermediate directories actually run (`bandit.yaml` and `.coveragerc` have no intermediate step, so the multi-component loop at `:672-677` is never entered by any passing assertion). Recommend routing one drift case through `.grok-stack/config/routing.json`.

`--materialize-new` into an absent parent is fine and is covered: `_kept_local` is short-circuited for non-`directory` states, and m14 (removing that short-circuit) is killed by test 7 plus eight inherited arms (`test_materialize_new_publishes_verified_payload_once`, `test_cli_modes_plan_by_default_and_materialize_only_when_explicit`, race/failure-injection arms). No new arm is needed for the absent case — a record cannot exist inside an absent target. The uncovered combination is the *reverse* (present target + record → `materialize_new` must still refuse), which is exactly the §3 Critical-1 case.

## 5. No-record parity arm (test 7) — shallow

It pins `plan["kept"] == []` plus membership of two names (`.coveragerc`, `bandit.yaml`) in the entry set. It does not pin entry count, modes, digests, or anything about the base commit; m18 (an unlisted managed file silently dropped from the payload) survives all 24 tests.

For the record, the parity claim itself is **true** — measured here: base `HEAD~1` plan vs `HEAD` plan for a no-record target = 346 entries both, identical path set, identical `size`/`sha256` per path, identical `dependency_advice`, `version`, `target_state`; the only delta is the added `"kept": []` key. (The `mode` field differed in my run only because the two trees were extracted under different umasks, not because of the change.) Suggested strengthening, using that same measurement: assert `len(plan["entries"]) == 346` and a `hashlib.sha256(json.dumps([e["path"], e["size"], e["sha256"] for ...]))` golden digest of the sorted manifest, or compare against a base-commit reference plan checked into `tests/data/`. Note the golden count must be maintained deliberately on each payload change — if that churn is unwanted, pin at least the entry count and the digest of the *sorted path list*.

## 6. test-plan.md / paperwork claims vs reality

| Claim | Verdict |
| --- | --- |
| "`python3 -m unittest tests.test_installer` (24 OK)" | **True** — 24 ran, OK, twice (also under `env -i`). |
| "17 inherited arms" | **True** — 24 total − 7 keep arms (`test_keep_list_*` ×4, `test_keep_record_validation_fails_closed`, `test_symlinked_keep_record_or_path_is_not_silently_ignored`, `test_target_without_record_behaves_exactly_as_before`). |
| Module name `tests.test_installer` | **True**; also selected by verification (`python-unittest` = `coverage run --rcfile=.coveragerc -m unittest discover -s tests`). |
| P0 row 1 "kept paths out of entries … keep tests 1, 2, 4" | **Overstated** — test 4 never inspects `entries` (m19 survives). |
| P0 row 3 "…no-record parity \| keep tests 5–7" | **Overstated** — parity is 2 names + `kept == []` (m18 survives). |
| `tasks.md` "README two-questions rule" `[x]`; `test-plan.md` "README two-questions rule"; change-spec AC-004 "the README states the two-questions rule" | **Stale wording** — the rule exists only at `QUICKSTART.md:29`; `README.md` contains no `kept_local`/`AGBP_SYNC` mention (grep). AC-004 as written is unsatisfied. `tests/test_structure.py::test_installer_safety_pivot_is_documented` already enforces README+QUICKSTART parity for other installer claims — mirror the sentence into `README.md` (or amend AC-004 to name QUICKSTART, and fix `state.json`, which already says "README-adjacent QUICKSTART rule"). |
| `tasks.md` "`grok_verify --mode pr` … [ ]" | **Understated/stale** — a passing local verification receipt bound to `9d83ba4` exists at `.grok-stack/runtime/receipts/6283c93ff5ba/verification.json` (`status: pass`, `mode: pr`, `created_at 2026-09-16T21:01:06+00:00`, `tree_fingerprint c79d7b5a…`). Check its freshness before re-running: this report file is itself a tree write and will date the receipt. |
| Spec coverage `criterion_mapped 4/4`, `evidence_counts.test 4` | Path-coupling only — the four ACs all cite `tests/test_installer.py`, so the metric cannot see the 2/4 state coverage in §3. Coverage-by-path is why this review had to mutate. |

## Required before this change is test-complete

1. Rename the loop-local keep state in `_make_plan` (one-line fix) and pin `plan["target_state"] == "directory"` in tests 1, 2, 4 + a `materialize_new`-refuses-present-directory-with-record arm.
2. Add KEEP-state arms for `target-owned` and `unmanaged`.
3. Assert `entries` exclusion in test 4 (nested `MANAGED_DIRS` path) and add a nested drift arm through `.grok-stack/config/routing.json`.
4. Add the size-cap arms (>16 MiB kept file, >64 KiB record).
5. Move the regular-file check in `_read_target_relative` before `os.open` (stat-then-open, like `:473-474`), and add a non-regular-kept-path arm run under a subprocess timeout so the FIFO hazard fails loudly instead of hanging.
6. Add a symlinked-intermediate-directory arm and a symlinked kept-payload-file arm (test 6's "…or path").
7. Strengthen test 7 with an entry count + sorted-manifest digest, and correct the README/QUICKSTART claim in AC-004, `tasks.md`, `test-plan.md`, `state.json`.
