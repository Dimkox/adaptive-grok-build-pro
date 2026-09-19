FAIL

## Re-review on b81849a

Every quantity I failed at `d3e0d49`/`cbc65ac` is now correct and reproduces. What is not correct is two
*citation* cells that `b81849a` introduced next to the corrected numbers — and citations are this package's
product. Both are one-line fixes; none is a re-derivation.

- **C1 identity analyzability — CLOSED.** My own re-run of extracted block A, four processes: base `2f66ba6`
  = **12/38** json_schema (26 blocked), **21/50** all kinds (29 blocked); head `d871ea6` = **36/38**, **46/50**;
  unlocked **24** / **25**. My independent set-diff (my code, not block A) proves gained = 25 all-kinds / 24
  json_schema with **zero** regressions, so "moved from un-analyzable to analyzable" is exact. The old
  `14 / 38` row survives only inside marked supersession sentences (`grep -rn "14 */ *38"` → 7 hits: controller
  supersession blockquote, requirements AC-002 *Superseded*, brief, rollback, change-spec AC-003, harness intro).
- **C2 ablation per unit — CLOSED** (all six cells re-derived, not two). Block B verbatim: all-kinds `$defs` 24 /
  `format` 10 / `anyOf` 4; json_schema-only 23 / 9 / 3; denominators and the intermediate `13/38`, `22/50`,
  `27/38`, `36/50`, `33/50`, `42/50` all print as transcribed, plus the contrast rows (`oneOf` 6/3, `allOf` 8/6).
- **I4 CAR-1 — CLOSED.** Block C verbatim on the three real contracts: novel non-subsuming scalar →
  `incompatible ('changed_constraint',)` on attempt-status (`integer` over `string(1..128)|null`) and
  provider-observation (`boolean` over `integer(0..1e7)|null`); non-verdicts land on the subsuming, object-valued
  and `$ref`-valued arms and on failover-result's `$ref`-bearing union. The edit-class table now names each
  inserted branch shape in the header and per row, and the failover "tighten" cell is labelled a no-op, which I
  confirmed (branch 0 is a bare `$ref`).
- **I6 CAR vs R namespace — CLOSED.** `grep -rniE "residual R[1-5]"` → 0 hits. `R-n` outside `ai_architect`:
  8 lines, every one discussing the collision or the mapping table; the mapping table exists and names both
  referents. `\bR[1-5]\b` counts match the file's claim (0 on the other four lanes, 17 on `ai_architect`).
- **I3 annotation, agent text intact — CLOSED.** `git diff -U1 d3e0d49 b81849a -- <agent files>` shows only added
  `>` blockquotes; the agent's words survive identically, with one paragraph break moved (`… R1-R5)."`* Nothing
  in the package overclaims…` split after the quote). Substance of the annotation checks out: the §1 case it
  cites is real (see my control-arm measurement below) and its census is block E's.
- **I1/I2 test-plan, report count, provenance — CLOSED except SIG-001 attribution.** The fail-closed demand for
  CAR-5 is gone and inverted ("Do **not** smooth CAR-5 into fail-closed wording"); five reports, both route ids
  named, and both are checkable: `route.json` `analysis_agents` = 4 lanes (no `ai_architect`) for `59527d5a28f8`,
  and `ai_architect` is in `4c524b83df59`'s five. Falsity: `release.md` and `change-spec.yaml` SIG-001 say
  "both numbers are printed by block F and block A" — no block prints the 5 (see What I measured).
- **I5 harness — CLOSED as a mechanism.** `evidence/measurement-harness.md` exists (900 lines), stdlib-only
  (`collections copy json posixpath re subprocess sys pathlib` + the module under test), `find <pkg> -name '*.py'`
  → **0**. I extracted **all seven** embedded blocks programmatically and ran them one process per tree: every
  printed line in the file matches what I got, byte-for-byte. This is not re-wording.
- **Minors — CLOSED.** `architecture.py` cites all check out at `d871ea6`: `1240-1247` `$id` table consulted
  before the path table, table built `1170-1174`; also `1429`, `1431-1437`, `1697-1700`, `2131-2135`, `3037`,
  `3105-3107`. Chronology is locally phrased and measured: block F prints `78 0`, 211→219 entries, 12
  out-of-order pairs at both trees, 8 added headings. Architect header annotation present.
- **NEW false cell (decides this verdict): the "carried by" column for `CONTRACT-FACTORY-LANDING-OPENAPI-V1`.**
  It reads `root `servers`` and cites `analysis-ai_architect.md` item 10. The document named has **no `servers`
  key**, and item 10 attributes `root servers` to `CONTRACT-ADAPTIVE-DEMO-OPENAPI` and `$ref` response objects to
  the landing record (56 `$ref`s in it). The controller overwrote the lane's correct attribution with an
  un-blocked, un-measured one — the CAR-1 mistake class, re-committed. Fix: `$ref` response objects, or a block
  that prints the construct.

## What I measured

Private `--local` clone + two detached worktrees (`2f66ba6`, `d871ea6`); both clean
(`git status --porcelain -- factory/contracts architecture .grok-stack` → 0 lines); no probe string in any contract.

- `python3 extract_blocks.py` (regex on `^```python` fences) → `python blocks found = 7`, `console blocks = 11`.
- Block A (extracted) → `A: baserepo all 21/50, 29 blocked` · `baserepo json_schema 12/38, 26 blocked` ·
  `newmain all 46/50, 4 blocked` · `newmain json_schema 36/38, 2 blocked`; head blocked names are exactly the
  table's four.
- My own `my_analyzable.py` per tree: `n=21` / `n=46`; `comm` gained = 25 all-kinds, 24 json_schema, lost = ∅;
  module paths printed per process, so no same-process contamination.
- Block B → `$defs 24→22/50 / 23→13/38`, `format 10→36/50 / 9→27/38`, `anyOf 4→42/50 / 3→33/38` (+ 8 rows).
- Blocks C, C-2 (9 cells, 9 non-verdicts), D, E → verbatim; E: `_SUPPORTED_SCHEMA_KEYS=24 → 27`, delta
  `{'$defs','anyOf','format'}`, glob 38 = 28 json_schema+7 openapi+1 event+2 undeclared, 10 declared
  json_schema outside the glob, `$id`=41 distinct, 0 equal a path, 86 ref bases (76 urn), 0 ambiguous.
- Block F → `mistakes.md numstat d871ea6...b81849a = 78  0`, `211 → 219`, `out-of-order=12` both, 8 headings.
- CAR-5 and both control arms, my own script, one process per tree: with claimant — base
  `incompatible ('narrowed_constraint',)` vs head `compatible ()`; `c/y.json` absent — base
  `unsupported ('unsupported_schema_keyword',)` vs head `compatible`; **`$id` claimant absent — both trees
  `incompatible ('narrowed_constraint',)`**, so the controller's control-flipped sentence is true (but is
  recorded nowhere as runnable; §1's committed snippet needs an uncommitted `real.py`).
- `grep -n "analysis-\*|wc -l|ls engineering" measurement-harness.md` → only line 63 (a `diff --name-only`);
  no block prints the 5-report count.
- `git diff --name-only d871ea6...HEAD` → this package + `mistakes.md` only (INV-002). `gh issue view 147` →
  OPEN, title matches CAR-5. `git cat-file -t 2cbfa12`/`d48aa5d3` → commit; `00709f4`/`0284d33` → **not valid
  objects** anywhere in this repo.
- anyOf presence among the 25 unlocked: `anyOf` 3, `$defs` 20, `format` 6; the 3 are the three landing unions,
  all blocked at base and analyzable at head.

## Residual risks

1. **"and not the three `anyOf` ones"** (controller, lines 40-41, surviving fragment of the superseded sentence) has
   a false literal reading — that #133 left the three `anyOf` contracts locked, when it unlocked exactly those
   three, which the same file then probes. The measured intent is fine — only 3 of 25 unlocked records contain
   `anyOf` — but a durable record cannot rest on a clause whose literal reading contradicts its own table. State
   the 3-of-25 split.
2. **`analysis-architect.md` §1 is the package's only soundness demonstration and cannot be run as committed**
   (first line imports `<private-scratch>/real.py`; the no-`.py` rule keeps it out). My 40-line reconstruction
   confirms every number in it. Promote it to block G using ground rule 1's documented `exec(compile(...))`
   exception, and cover arm C there.
3. **Dangling in-package citations** in the two carried lanes: `brief.md` "producing directionally sound results"
   (this `brief.md` never contained it — 4c524b's does), and `review-test.md` / `review-security.md` /
   `verification-attempt.md` quoted "from the package" (all three exist only in route 4c524b's package). The new
   annotation fixed the AC-number drift in that same sentence and stopped short of these. One controller note
   ("these file names belong to the 4c524b package") closes the class. Likewise label `00709f4`/`0284d33` as
   throwaway-clone ids unreachable here, whose Table C rows are the durable record.
4. **The 20/50 question you asked.** Leaving the agent's sentence verbatim is right and I would not change the
   policy; recording it only in the controller table is not enough. `analysis-integration_architect.md:106` is a
   file a reader can open alone, and its bolded "baseline 20/50" then reads as measured. The package already owns
   the correct instrument — the `[ANNOTATION added by the controller]` blockquote used on `ai_architect` — and
   applying it beside line 106 costs one blockquote and breaks no rule. As shipped, the treatment of two stale
   numbers in two agent files is asymmetric, and the asymmetry is invisible from inside either file.
5. **One unlabelled comparator over-strictness:** `allOf [S,S] → [S]` is instance-set-preserving yet reports
   `incompatible (changed_constraint)` — the single cell where a provably neutral edit yields a verdict instead of
   degrading to `unsupported`. Fail-closed, so not a soundness item, but its neighbours are annotated "correct"
   and it is not, so it deserves the same one-word label.
6. Not re-litigated by me: the `grok_architecture.py fitness` gate rows stay attributed to the executing lane,
   which the controller now says explicitly, and `CONTRACT-ADAPTIVE-DEMO-OPENAPI`'s "not a construct gap" is true
   under its declared policy but incomplete — under `bidirectional` it *also* hits `unsupported_openapi_construct`.

## Delta re-check on 0b6299b

RE-REVIEW VERDICT: FAIL

Scope: the five deltas and every line `0b6299b` touched; nothing re-litigated. Method: private `chmod 700` clones
at `2f66ba6`/`d871ea6`, one process per tree; Blocks A/B/F extracted verbatim from `measurement-harness.md`;
`_openapi_schemas`/`_security_schemes` instrumented guard-by-guard to locate the real failing check.

1. **Delta 1 — NOT CLOSED (blocking).** Every figure requested is true: `landing-dogfood.v1.json` root keys
   `components`/`info`/`openapi`/`paths`, no `servers`, 56 `"$ref"`; `adaptive-demo.v1.json` has root `servers`;
   record→path pairing in `architecture/system.yaml` is as cited, and instrumenting the comparator confirms
   `ADAPTIVE-DEMO` is the record that trips the root-key whitelist (`architecture.py:2543`). But the cell sits under
   a column headed **"carried by"**, and the `$ref` count is not the carrier. Measured: strip all 56 `$ref`
   keys → still `unsupported_openapi_construct`; `factory-semantic.v1.json` carries exactly 56 refs with the same
   root keys and **is** analyzable at head; the first guard that actually fails is `_security_schemes`'
   `components` whitelist (`architecture.py:2431`) because `components` also holds `parameters`/`headers`/
   `responses`, and with those removed a second construct still fails at `architecture.py:2665`
   (`_supported_parameters`). Round two failed this cell for naming a false carrier; `0b6299b` replaced it with
   true facts naming no carrier, and the block index still has no row for it (only `ADAPTIVE-DEMO`'s "policy mode,
   not a construct").
2. **Delta 2 — CLOSED.** Block F really prints `mistakes.md numstat d871ea6...HEAD (added deleted) = 78 0` (and
   `78 0` still holds at `0b6299b`); block A really prints the analyzability numbers; `ls evidence/analysis-*.md |
   wc -l` = 5; no harness block prints a report count. Nit: the paragraph holds no analyzability figure, so "the
   analyzability numbers come from block A" gives provenance for a number that is not in the paragraph.
3. **Delta 3 — CLOSED.** Independent set-diff of my two sweeps: unlocked 25 all-kinds / 24 json_schema, base
   blocked 26 / 29, head 2 / 4 — and exactly **3** unlocked records contain a literal `anyOf`
   (LANDING-ATTEMPT-STATUS-V1, LANDING-FAILOVER-RESULT-V1, LANDING-PROVIDER-OBSERVATION-V1), the same 3 that flip
   under the `anyOf` ablation. Nit: necessity is **4** of 25 (block B's own all-kinds number), since
   `LANDING-FAILOVER-OPENAPI-V1` needs `anyOf` through a `$ref` while containing none — "necessary for those three
   … the other 22" is short by one.
4. **Delta 4 — annotated in both places; the test is real.** `git cat-file -t 00709f4` and `0284d33` both fail
   here *and* in the primary repo (this tree is a linked worktree sharing its object DB). Two wording defects:
   "resolve as objects in no repository" is a universal negative nothing here measures (by the package's own
   account they existed in the throwaway clones), and the new Table C note says block C "re-derives the in-process
   cells behind them" though block C's recorded output covers only 2 of the 3 contracts Table C names — it has no
   `LANDING-FAILOVER-OPENAPI-V1` section; line 213's "all three contracts" is the same over-cite (pre-existing).
5. **Delta 5 — referents all check out; one false clause.** `4c524b83df59`'s package really holds `brief.md`
   (Outcome, its line 17, verbatim), `requirements.md` AC-005 = "`prefixItems` … remains `unsupported`" (a genuine
   fail-closed disclosure, so the annotated sentence is true under this referent), and `review-test.md` /
   `review-security.md` / `verification-attempt.md`, each really containing its quoted fragment and all three
   really quoted in the annotated section. Both lane files are pure insertions (`9 0`, `8 0`) → lane text
   byte-unchanged. Block A yields **21/50** at base on my own run, 46/50 at head with exactly the four names
   listed. **False:** "this audit package holds its own reviewer reports under the same names" — it holds only
   `evidence/review-code.md` (route `59527d5a28f8` requires `verification` + `code_review`); no `review-test.md`,
   `review-security.md` or `verification-attempt.md` exists in it, and round two's item 3 said the opposite.

Your question — remaining descriptive cells with no measurement or block behind them:

* Line 37: the delta-1 carrier above — true facts, no named carrier, no block, absent from the block index.
* Lines 35–36 (`prefixItems`; "urn-`$ref` cascade into `prefixItems`"): attributed to a lane report, not a block.
  They survive my check (1 literal `prefixItems` at `$/properties/instructions`; READY-BUNDLE has none of its own
  and does carry the two `urn:adaptive-factory:m7:` refs) but are weaker than written — whitelisting `prefixItems`
  alone leaves **both** records `unsupported_schema_keyword`, so it is a trigger, not the whole carrier.
* Lines 41–43: "necessary for those three … the other 22" (necessity is 4).
* `analysis-ai_architect.md` pre-existing note "the fail-closed disclosure the agent meant is now AC-002/AC-003":
  in this package AC-002 is "the record says plainly what #133 fixed" and AC-003 is "superseded tables are marked",
  neither a comparator fail-closed disclosure — and it now collides with the new annotation assigning AC-005 to
  `4c524b`'s `requirements.md`.
* Same annotation's "copied into": both lane files differ from `4c524b`'s by 205 and 209 lines — rewritten.
