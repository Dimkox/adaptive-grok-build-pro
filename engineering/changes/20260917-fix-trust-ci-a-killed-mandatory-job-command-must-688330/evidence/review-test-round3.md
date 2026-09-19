FAIL

# Test review — round 3 (delta) — route `68833064bec9`

Scope: the two post-round-2 closures (`stderr_tail` totality + documentation accuracy) on the final bytes.
All mutation runs used private `chmod 700` scratch under `$HOME/.cache` built with `git archive HEAD` plus the
dirty-file overlay; scratch md5s equal the reviewed tree before mutation. **reviewed tree modified: no** —
`git status --porcelain` is byte-identical before and after this review (9 lines, same set), all six md5s below
unchanged at the end, and no file in the reviewed tree was written except this report.

## 0. Bytes confirmed (all six match the brief)

`9c530687083fd92fe58927e72239fb5a` sandbox.py · `d1089aacd80908fe01bd094685d5cbe6` runner.py ·
`01219f9dca5649f04722f78d68f82f1b` api.py · `95af01302936127d092443c62eabf23a` test_ops.py ·
`84b1f30d83c67383bd26958a9b09e9d3` test_runner.py · `464fab127bf595260d00f0ff65ee5a0c` test_api.py.
Normalization is at `sandbox.py:88`; `stderr_tail: Any = ''` in the signature.

## 1. R2-2 symmetrical totality — PASS, claim verified exactly

Direct probe on the current bytes (`exit_code=124` / `exit_code=137`, tails `None`, `['x']`,
`b'command timed out after 120s'`, `5`, `object()`): 124 → `None` for all five, no raise; 137 →
`('signal', 'SIGKILL', 9)` for all five. A real `'…\ncommand timed out after 120s'` str still yields
`('timeout', None)`, so the normalization is not over-broad. Non-string removes corroboration, never hides a
proven kill — as the docstring claims.

Mutants (focused arm `test_non_string_stderr_tail_yields_no_claim_instead_of_raising`, run via
`PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests -p 'test_ops.py' -k "*test_non_string_stderr_tail*"`):

| Mutant | Result | Verdict vs author's claim |
| --- | --- | --- |
| **MT1** delete normalization (regex on raw `stderr_tail`) | `Ran 1 test` … `FAILED (errors=7)` | **matches** (`errors=7`). Also reproduces round 2 verbatim: `TypeError: expected string or bytes-like object, got 'float'` and `TypeError: cannot use a string pattern on a bytes-like object` at `sandbox.py:96` |
| **MT2** `tail = str(stderr_tail)` | `Ran 1 test` … `FAILED (failures=1)` | **matches**; the single failure is `test_ops.py:107` `assertIsNone(...stderr_tail=_MarkerSounding())` → `CommandAbort(kind='timeout'…) is not None` |
| **MT3** accept+decode `bytes` | `Ran 1 test` … `FAILED (failures=2)` | **matches** (fails at the `subTest` loop line 92 and the `marker_bytes` line 99) |
| **MT2 minus the `__str__` arm** | `Ran 1 test in 0.000s` → **`OK`** | **survives, as attributed** — the `__str__` arm exists specifically to refuse `str()` coercion |
| **MT3 minus the `__str__` arm** | `Ran 1 test` … `FAILED (failures=2)` | **still killed**, as attributed — a `bytes` arm cannot expose MT2 because of `repr` quoting |

The attribution statement in `review-response.md` is therefore measured, not assumed. No test-side gap found
in this delta; item 1 is clean.

## 2. R2-1 documentation accuracy — BLOCKING FINDING: a count is still asserted, and it is already false

`review-response.md` (05:42:46) R2-1 states the residual audit quotes **no** count: *"no count is quoted,
because the count moves when these very files are edited"*. `tasks.md` (mtime **05:44:42**, i.e. the *newest*
file, written after the response) line 65 still asserts one:

    is `grep -rn "AGENTS.md" <package> | grep -v /evidence/ | grep 018` → every remaining line (7 at the time of

Running that literal command against the current package:

    $ grep -rn "AGENTS.md" <pkg> | grep -v /evidence/ | grep 018 | wc -l
    6

No plausible variant yields 7: the same command without the `-v /evidence/` filter yields 11; with
`--include=*.md --include=*.yaml` yields 6; restricted to the four rewritten targets yields 6. So the number is
not a different-but-valid counting of the same thing — it moved exactly as the author predicted it would, and
the record now contains a count refutable by running the package's own command. That is the same defect class
as R2-1 itself and as #117/#84, and it contradicts `review-response.md`, so per the review contract it is
blocking. Fix is one edit to `tasks.md:65`: delete `(7 at the time of writing, self-referential ones included)`
and keep the properties clause, which is true (see below). Minimal, non-irreversible, no re-verification of
behaviour needed.

What *does* check out, so this is a wording defect and not a factual one:
- No line anywhere asserts the range comes from `AGENTS.md` positively. All 6 surviving lines are negations or
  records of the correction (`tasks.md:58`, `tasks.md:67`, `requirements.md:14` "**not** `AGENTS.md`",
  `release.md:26` "It is **not** in `AGENTS.md`", `test-plan.md:60`, `change-spec.yaml:99`).
- `grep -c "018" AGENTS.md` → `0`; `AGENTS.md:130` = `- All schema changes use versioned migrations.` (verbatim).
- Every replacement referent is true when run: `git ls-tree -r --name-only v2.0.13 | grep -c
  'factory/src/adaptive_factory/resources/.*\.sql'` → **18** (last `018_semantic_validation_bridge.sql`);
  `ls trust-ci/sql/ | wc -l` → **3** (`001_schema.sql`, `002_operational_indexes.sql`, `003_database_roles.sql`);
  today's factory set → **20** (last `020_execution_v2_priced_usage.sql`).
- The named bearers are real and at the named places: `PROJECT_STATE.json` lines **261, 352, 625, 889** all
  carry `"001-018"`, plus `README.md:32`, `START_HERE.md:57`, `CHANGELOG.md:75` (each line contains
  ``001`-`018``).
- The two other counts in the package were measured and are currently true — `test-plan.md:36` "now returns 4
  hits" for `grep -rn "assertIsNone(.*failure_code" trust-ci/tests/` → 4; `test-plan.md:6` "26 tests added …
  `test_ops` 14→29, `test_runner` 26→36, `test_api` 21→22" → 14/29, 26/36, 21/22 and 15+10+1 = 26. They count
  the frozen product tree rather than the package's own prose, so they are not the refuted-by-design class; only
  `tasks.md:65` needs the number removed.

## 3. Suite state on the final bytes — matches the report verbatim

    $ PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests
    Ran 269 tests in 6.975s
    OK (skipped=10)

Focused trio (per-module, since `tests` needs the discover top-level to resolve `_support`):
`test_ops.py` `Ran 29 … OK`, `test_runner.py` `Ran 36 … OK`, `test_api.py` `Ran 22 … OK` → **87**, matching the
reported `Ran 87 … OK`. `python3 -m ruff check` on the six files → `All checks passed!`. `pytest` is not
installed here, so the 10 skips stay unexecuted (disclosed, unchanged from rounds 1–2).
`scripts/grok_verify.py --mode pr` was **not** run, per instruction.

## 4. No residue

`find trust-ci engineering/changes/20260917-* -name '*.orig' -o -name '*.bak' -o -name '*~'` → empty; the
grouped variant adding `*.rej` → empty. `*.pyc` hits are all under `__pycache__/`, matched by
`.gitignore:34` and pre-existing (they cover modules this review never imported), so they are not mutation
residue. No `checkout`/`stash`/mutation was performed in the reviewed tree; every mutant edit lived only in
`$HOME/.cache/r3-*`.

## Verdict

**FAIL** on one blocking record finding (item 2, `tasks.md:65` count) that contradicts `review-response.md`.
Item 1 — the actual behaviour change and its test — passes on independently measured evidence, including the
specific MT2 attribution claim, which held exactly. Item 3 and item 4 pass. After the single-line wording fix,
item 2 can be re-confirmed without re-running anything in section 1, 3 or 4.
