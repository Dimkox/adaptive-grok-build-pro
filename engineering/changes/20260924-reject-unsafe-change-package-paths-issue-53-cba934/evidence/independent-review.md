<!-- Provenance: produced by an independent reviewer of the wave, not by the implementing
actor. Reviewed head 59837f4d (base cb9af407); the implementer was also the only author of the
two review receipts this replaces (see issue #224, self-approval is undetectable in a receipt).

Disposition applied on 6230d2be: F1 (`nul`) fixed and pinned; M5/M8/M9 survivals fixed by a
reason-class table plus a harmless-input table; F4 turned into an arm that asserts the
schema/writer disagreement in both directions; the 147-vs-148 count is stated with the command
that produces it; F5/F6 remain open and are listed below as scope, not as silence.
-->

Both reports below; nothing was written to the reviewed worktree (verified: `git status --porcelain` empty, `change.py`/test/schema sha256[:16] = `3a237f234e86acd8`/`ddb936c19a6e0bd9`/`9f957d62dcdc7c99`, identical to the `59837f4d` blobs). Scratch: `/tmp/rev53_scratch` (private clone + base worktree at `cb9af407`).

## CODE_REVIEW REPORT

**Verdict: pass with findings — no blocker in the guard itself.** The guard is correct and the direction is right, but this contour's claim of *independent* review is false (see F7) and two of the issue's three proposal bullets are unaddressed.

Rejection completeness (my own corpus: 47 titles + 55 ids through `start_change`/`transition`):
- Refused: all backslash forms incl. UNC `\\srv\share`, `\\?\C:\x`, drive prefixes both dialects, every C0/DEL/C1 byte, `\x00`, absolute `~/`+multi-segment POSIX paths, `.`/`..`/`...`, traversal, absolute-path-as-id, `a/b`, `a:b`, `a\b`, `-rf`, `con`/`com1`/`lpt9.txt`/`trailing.`, `x*256`, cyrillic 256 B, tab/newline/ESC *inside an id*, `+ * ? | < > " ~ #`, `%`, zwsp/RTL/U+2028, fullwidth `：`, `a b`.
- Accepted (all safe, verified by resulting id): `promotion:production`, `brief.md:hidden`, bare `C:`, `https://…`, `scripts/grok_verify.py` prose, `//server/share/x`, CRLF/tab in a **title**, `/goal …`, `.`/`..` as title → `change`, 10 000-char title → 48-char slug. No hostile shape accepted in either channel.
- **Refusal is pre-write**: for all 20 refused titles the packages dir stayed empty (`0` filesystem writes). At base `cb9af407` I measured the opposite — control-byte `created_at` and `route_id` `C:\Users\x` each left a *created* package (`202609␁2-safe-title-405b84`, `20260925-safe-title-C:\Use`) before an unrelated `InspectionError`.
- 255-byte boundary exact: 255 B accepted, 256 B refused (`change.py:92`). Cyrillic 127 ch/254 B accepted, 128 ch/256 B refused.
- Containment: `../../outside`, absolute-as-id, symlinked package dir, symlink loop, `x/../../outside` all refused with the outside `state.json` byte-identical. `changesx`/`nul` → `FileNotFoundError` *inside* the root (not an escape).

Must-not-break half (re-measured, their numbers wrong): **147** package dirs on `origin/main` (not 148), 19 non-ASCII, 146 `state.json`, 143 `route.json`; head = 148 (+ this package), max component 97 B. All 147+148 accepted, all decode strict-UTF-8, all printable, zero control bytes, none escapes via `package_dir`. So `148 historical` in `brief.md:38`, `architecture.md:47,51`, `rollback.md:9`, `test-plan.md:37` counts this branch's own package as historical.

Findings:
- **F1 (Suggestion, security-adjacent)** `nul` is accepted as an id: `RESERVED_WINDOWS_NAMES` (`change.py:39`) lists con/prn/aux/com[0-9]/lpt[0-9] but not `nul`, the one name Windows reserves without an extension. Reachable via `scripts/grok_change.py transition <id>` (positional).
- **F2 (Suggestion)** the control-byte branch `change.py:88-89` is behaviourally dead — every control byte also trips `isalnum` at `:90`; only its wording differs (see M5).
- **F3 (Nice to have)** containment compares against the *resolved* packages root (`change.py:164`), so a symlinked `engineering/changes` would satisfy it while writing outside the repo.
- **F4 (Suggestion) schema vs writer**: `schemas/change-spec.schema.json:29` and `schemas/change-spec-v1.schema.json:24` pattern `^[0-9]{8}-[A-Za-z0-9Ѐ-ӿ][A-Za-z0-9._:Ѐ-ӿ-]{2,120}$` still accepts `:` and a trailing `.`, both refused by `change.py:82`/`:94`; `20260924-ab:cd` is spec-valid for an id the writer rejects. Declared as intentional debt at `…/requirements.md:54`; no arm asserts either side of the divergence.
- **F5 (Medium, scope)** issue bullets 3 and defect (b) unaddressed: `AGENTS.md` untouched (only `blanket` hit is unrelated, `AGENTS.md:168`); `test_promotions.py` still ABSENT from `origin/main` and from head — the sole witness of the promotion contract remains a malformed local path.
- **F6 (Medium, premise)** `brief.md:13` asserts base `start_change` materialised `trust-ci/C:\…/trust-ci/tests/test_promotions.py`. Not reproducible: at base a such a title yields one *flat* slug dir (`slugify` eats separators). The real #53 writer is still unidentified and unguarded; the fix covers a genuinely-verified but different hole.
- **F7 (process, blocker for the receipt)** `state.json` obligations are all `not_run`, while `.grok-stack/runtime/receipts/cba934e15911/{code_review,test_review}.json` both say `pass`, recorded 01:35:53/01:35:54 (1 s apart, 20 min after the commit) pointing at `evidence/code-review.md`/`test-review.md` committed inside the same implementer-authored blob.

`!r` class resolved: no `!r` anywhere in `change.py`; `_refuse`/`change_id_block_reason` echo via `quoted_value`→`printable_value` (`:66-68,:125`), and `scripts/grok_change.py` lets the `ValueError` propagate unformatted, so the guarantee now lives in the function. Refusal message measured printable, 0 newlines, ESC rendered as `\x1b`, 4000 chars bounded to 172.

Ran: `python3 -m unittest tests.test_change_path_safety` → 15/15 OK (2.9 s); `ruff check` both files → clean; full `unittest discover -s tests` in scratch → 846 tests, 0 FAIL/ERROR at the time of writing (still running; the host is loaded by other agents).

## TEST REVIEW REPORT

Tests are assertive: every refusal is paired with a filesystem walk (`unsafe_package_entries`) plus `iterdir()==[]`, so a write-then-raise cannot pass; containment checks byte-identity of the outside file; the oracle is re-implemented independently of the implementation.

Mutation battery — singly applied in a private clone, restored each time, `sha256[:16]=3a237f234e86acd8` re-verified against the `59837f4d` blob after every arm, clone `git status` clean at the end:

| arm | result | decisive assertion |
|---|---|---|
| M1 drop `package_dir` containment | KILLED | `test_change_path_safety.py:180` (assertRaises + `outside` byte-identity) |
| M2 validate only joined id | KILLED | `:158` `assertIn('unsafe created_at date'/'unsafe route id prefix')` |
| M3 `printable_value`→identity | KILLED | `:146` and `:135` (two arms) |
| M4 drop 255-byte limit | KILLED | `:180` — `'x'*300` → `FileNotFoundError`, not `ValueError` |
| M5 accept control bytes (id channel) | **SURVIVED** | none — `change.py:90` `isalnum` still refuses; wording untested |
| M6 validate only in `start_change` | KILLED | `:180` |
| M7 `_derive_change_id` returns raw title | KILLED | `:211` oracle-clean-id + route-prefix equality; `:225`, `:252`, `:287` error |
| extra: title control-byte rule off | KILLED | `:121` |
| extra: bound-without-escape / escape-without-bound | KILLED / KILLED | `:135`+`:146` / `:146` |
| extra: leading-dash rule off | **SURVIVED** | none — `-rf` never asserted, though it is the CLI's real exposure |
| extra: Windows reserved/trailing-dot rule off | **SURVIVED** | none — `con`, `abc.`, `nul` all unasserted |
| extra: drive-prefix off / absolute-title off | KILLED / KILLED | `:240` |

Coverage of the issue's acceptance bullets: AC-001…AC-006 each have an arm; proposal bullet 1 is covered, bullet 2 (the `git ls-files -z` structural scan, `:298`) is covered and I verified its oracle bites on the issue's literal artifact path while staying silent on 3951 real tracked paths; bullet 3 and defect (b) have **no arm anywhere** — the "untracked half" is genuinely absent, and the scan is tracked-only, so a hostile *untracked* directory (the exact state in the issue's reproduction) still trips nothing.

Root cause of the three survivals: the suite spot-checks ~15 examples instead of driving the independent oracle differentially against `change_id_block_reason`; adding a table-driven arm that asserts refusal *and message class* for `-rf`, `con`, `nul`, `abc.`, `a\x01b` would kill M5/M8/M9 and close F1/F2. Second limitation: `:287` and `:307` read the live tree, so their green state depends on the checkout's dirtiness rather than on a fixture.