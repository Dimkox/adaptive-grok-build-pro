# Review response — blob stream cleanup (#109)

Both independent reviews **PASS**ed. This note records the head movement they were bound to, the
one finding closed in-wave, the two deliberately not closed, and one interim claim by the test
reviewer that its own final report corrected — resolved by execution rather than by trusting
either narrative.

## Head accounting

| SHA | What it is | Reviews bound to it |
| --- | --- | --- |
| `05b69c7` | base = `origin/main` | — |
| `22f4926` | implementation (3 hunks + 3 arms + package) | code review **PASS** (read this SHA) |
| `8b4d82a` | `22f4926` amended for the code review's only Minor: a stray `'m` in the commit-message body. `git diff 22f4926 8b4d82a` is **empty** (same tree `ee74854…`), so the code review's conclusions carry over verbatim; the amend changes the message, not the artifact | test review **PASS** (executed red/green matrix on this SHA) |
| final head | `8b4d82a` + the test-review Finding 1 fix + this evidence + the two shared-memory lessons (`decisions.md`, `mistakes.md`) | receipts recorded on this head; see `verification.json` route receipt |

## Finding 1 (Suggestion) — CLOSED in this round

`assertIn("setup", str(exc).lower())` was vacuous: the appended `from exc` cause text carries the
fake selector's own message ("simulated selector setup failure"), so renaming the wrap message
kept arm 1 green (the reviewer's mutant M4 survived). Replaced with the literal promise:

```python
self.assertIn("streamed blob setup failed", str(raised.exception))
```

Proof it now bites, run in `/tmp/109-fix` (production module restored afterwards, blob hash
re-verified against `HEAD` = `c068fbc…`):

- three new arms → `Ran 3 tests … OK`;
- M4 re-applied (`"streamed blob setup failed: ` → `"blob io failed: `) → `Ran 1 test … FAILED (failures=1)`,
  i.e. the rename is now caught instead of surviving.

The reviewer's own commit-message/PR claim that the CLI sees a *typed, identifiable* setup error is
therefore pinned by the test, not just by `code == "io"`.

## Findings 2 and 3 (Nice to have) — NOT closed, with reason

- **M2 (swap the two closes)** survived: the swapped variant still attempts both closes and still
  closes the directory when the descriptor close fails, which is the property #109 promised. What it
  changes is which of the two close errors becomes primary — a behavior nobody specified. Pinning it
  would assert an ordering no requirement names, so it is left out of this wave.
- **M5 (drop the `if process.poll() is None` condition, stop unconditionally)** survived because the
  guard and the unconditional call are behaviorally equivalent here (`_stop_process` reaps and is
  idempotent for an already-stopped child). Asserting the presence of the condition would pin
  implementation, not behavior; the child-stopped property itself is already pinned by arm 2, whose
  red cause on base is exactly `AssertionError: unexpectedly None : child survived an exception the
  handlers do not name`.
- The pre-existing gap the reviewer also named (no arm where the child ignores `SIGKILL`, so the
  `wait(timeout=1)` inside `_stop_process` expires) belongs to `_stop_process`, shared with
  `_run_capped`; it is out of #109's scope and is not claimed as covered here.

## Interim-claim discrepancy, resolved by execution

The test reviewer's **interim** message stated that the `_profile_worktree_blob` hunk was "untested"
and that arm 3's red cause was an exception-type mismatch rather than a leaked fd. That is not what
happens, and the reviewer's own committed report (`review-test.md`, matrix row 3) says so. Verified
independently by the author:

```
$ cd /tmp/109-base && python3 -m unittest \
    tests.test_architecture_fitness.ArchitectureFitnessTests.test_profile_worktree_blob_closes_directory_when_descriptor_close_fails
AssertionError: 4 not found in [3, 3] : directory fd leaked behind a failing descriptor close
FAILED (failures=1)                      # two fd-3 closes attempted, fd 4 never
$ cd /tmp/109-fix && …same command…
Ran 1 test in 0.032s  OK
```

So arm 3 is red on base precisely on the leaked directory fd — the invariant the nested `try/finally`
restores. Recorded here because the durable rule in `mistakes.md` ("the issue/report trail must match
the code") applies to review artifacts too: an unexecuted claim in a review is evidence about the
reviewer, not about the code.

## Invariants re-checked after this round

- Production diff unchanged from the code-reviewed tree: only `.grok-stack/adaptive_grok/architecture_diff.py`
  (3 hunks); this round touched only `tests/test_architecture_fitness.py` (one assertion), the package
  evidence, and the two append-only shared-memory files.
- No new dependency, no `os.name`/`sys.platform` branch introduced, `_run_capped` untouched.
- Module status: 109 arms green locally; full `grok_verify --mode pr` recorded on the final head.
- `tasks.md` closed; the public correction of the issue's false `os.name` sentence remains on #109
  (`2026-09-17T00:06:48Z`), so the trail matches the shipped code.
