# Review response — installer keep list (#110)

Code review **FAIL** (1 Critical + 2 Suggestion + 3 minor) and test review **FAIL** (2 Critical, 12/21
mutants survived, missing state-matrix arms) on `9d83ba4`. All of it was real; closed in `7938847`:

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | Critical (both) — `_make_plan` shadowed the outer target `state` with the per-entry keep state: `plan["target_state"]` could read `absent`/`identical` for a present directory, corrupting the plan contract and bypassing the `:1242` materialize guard (late `_stat_absent` still prevented mutation) | **Fixed**: loop writes `keep_state`; `target_state` asserted `directory` in keep tests 1–3. Mutation re-check: reintroducing the shadowing now fails the suite (clone-verified). |
| 2 | Critical (test review) — reader opened before stat, so a **FIFO** at a kept path hung `plan_install` forever | **Fixed**: stat-before-open at every step (non-regular/oversized refused pre-open; intermediates must be directories), post-open fstat re-verifies dev/ino/mode/size, bounded `_read_limit_plus_one`, then a new `test_fifo_at_a_kept_path_fails_closed_instead_of_hanging` proves it. |
| 3 | Suggestion/code + test — `target-owned` and `unmanaged` KEEP states untested (deleting the branches kept 24 green); nested (`MANAGED_DIRS`) kept paths only tested in `absent`; S_ISREG/size-cap/directory-type mutants survived | **Fixed**: state-matrix arms added (target-owned, unmanaged; nested absent→identical→drift through the multi-component reader); no-S_ISREG and no-dirtypes mutants now killed; oversized record refused at the byte boundary. |
| 4 | Suggestion/code + test — parity test shallow (dropping a payload file survived); reviewer counted 346 entries | **Fixed + corrected**: parity frozen as sorted (path,mode,sha256) manifest digest over the full set; measured base==head==**352** (the 346 figure came from the reviewers' own count slip; the identical-set claim itself verified true). `ruff.toml`-drop mutant now dies. |
| 5 | Suggestion — AC-004/tasks/test-plan claimed README hosts the rule; it went to QUICKSTART | **Fixed honestly**: spec AC-004, tasks and test-plan now name QUICKSTART; AC-004 also records the kept-`AGENTS.md` nuance (keepable only while bytes equal the managed rendering) and the target_state requirement. |
| 6 | Minor/code — reader used `getattr(os,"O_NOFOLLOW",0)` instead of the module's refusal convention; single `os.read` | **Fixed**: `_require_descriptor_primitives()` refusal + `_read_limit_plus_one`, matching the source-side reader. |
| 7 | Info (both, agreeing) — fail-closed behavior (`.grok-stack`-as-file, symlinked record/path, mode-000 dir) verified correct; FORBID-001/INV-001 hold; no-record parity exact; base `target_state` regression confirmed as introduced by this wave, now repaired | Acknowledged; both mutation matrices re-run against the committed round. |

Verification after fixes: `tests.test_installer` **28 OK**; ruff clean; shadowing/S_ISREG/dirtypes mutants
KILLED in a private 0700 clone; final `grok_verify --mode pr` and all receipts re-bound to the round head;
merge authority remains the App-owned exact-head check.

Limits: FIFO arm skips where the platform lacks mkfifo; the parity digest is a frozen-at-wave value —
intentional payload changes must update it together with a recorded reason.
