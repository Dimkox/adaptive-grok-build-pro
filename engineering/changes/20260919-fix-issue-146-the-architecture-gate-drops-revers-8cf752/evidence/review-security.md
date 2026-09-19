PASS

Independent security review — `fix/contract-closure-id-refs` @ `7d21d95` (base `d871ea6`), issue #146 wave.
Reviewer: route-selected security agent, 2026-09-19. Every numbered claim below is marked **[measured]** (a command
in "What I measured" produced it in a throwaway clone) or **[inferred]** (code read only, not executed). Nothing
was executed in the delivery worktree; `scripts/grok_verify.py` was not run (gate run scheduled; contract with
this review).

## Critical (must fix)

None. No way for an authored contract to escape re-verification *beyond what already exists at base*, no fail-open
drop path, no off-inventory or off-disk resolution, no protected-path or secret content in the diff.

## Important (should fix)

1. **Closure precedence drops the $id edge — the claimant that the comparator WILL follow is never re-verified.**
   `.grok-stack/adaptive_grok/architecture_fitness.py:971-979` resolves each `$ref` with
   `precedence=SCHEMA_REFERENCE_PATH_FIRST`; when the raw base also equals a declared path, the `$id` target is
   never consulted (`architecture.py:1244-1256` returns at `first[0] is not None`). The comparator resolves the
   same base `$id`-first (`architecture.py:1341-1348`), so the dependent's *meaning* depends on the claimant, but
   the claimant never gets an edge to that dependent — edits to the claimant never re-verify it.
   Abuse scenario, **[measured]** (probe D2, real delivered tree + one synthetic claimant line): with
   `CONTRACT-FACTORY-LANDING-ATTEMPT-STATUS-V1` → `landing-input.v1.schema.json` (a real plain-relative edge) and an
   unrelated contract declaring `"$id": "landing-input.v1.schema.json"` (legal; no rule forbids it),
   `schema_reference_target_path` returns **claimant** under `ID_FIRST` and **path target** under `PATH_FIRST`
   (D1 output); editing only the claimant leaves the referrer **out of `scanned_scope`** (D2). The referrer's
   comparison resolves through the claimant's document on both sides, so a claimant edit that breaks referrers
   (e.g. removing/repointing what the referrer's fragment targets) certifies without re-verification.
   This is *not a regression* (the pre-#146 closure had the same omission, and probe A shows zero such shadows exist
   in the shipped inventory today: `duplicate_id_collisions={}`, `id_shadows_other_path={}`), and it is pinned
   *deliberately* by `tests/test_architecture_fitness.py:4314` (`expected_dependent=False` for CLAIMANT) via
   FORBID-003. But "never attach a dependent to a claimant" inverts the safety direction for a **scheduler**:
   attaching only costs re-verification; omitting an edge is a certification escape. Concrete fix: emit the union
   of both precedence results as reverse edges (path holder **and**, when unambiguous, `$id` holder); keep the
   AMBIGUOUS fail-closed. Union edges alone would make a claimant edit surface inside the referrer's comparison
   (the comparator's own ID_FIRST then does the right thing on both sides), which is exactly the scheduling half of
   #147's mitigation. Do this before or together with the #147 fix — see "Trust-boundary honesty".

2. **A duplicate declared `$id` aborts the whole `contract_compatibility` check from *either* inventory —
   poison in the base wedges every contributor's contract PR, including the PR that fixes it.**
   `architecture_fitness.py:916` loops `for inventory in (before, after)` and
   `architecture_fitness.py:977-979` raises the bare `SCHEMA_REFERENCE_AMBIGUOUS`
   (`architecture.py:1190-1192`, surfaced through `architecture.py:1204-1207`) with no offending id or record named.
   **[measured]** (probe C, real delivered tree + planted collision):
   - A1 clean base → colliding head: `RAISED 'ambiguous declared schema id'` — the introducing PR is correctly blocked.
   - C1 *unrelated* contract edit vs poisoned base+head: `RAISED` — one contributor's stale authored state aborts
     every other contributor's gate run, regardless of which contract they touched (the closure walks all records).
   - C2/C2b the cleanup PR with a **clean head, poisoned base**: `RAISED` too — because `before` is scanned first,
     **no contract-changing PR can ever repair main**; recovery requires `git revert` of #146 itself (which
     `rollback.md` lists as trigger #2, so the package knows the hazard but ships no bound/recovery path).
   Mitigating facts **[measured/read]**: today's main is collision-free (probe A, 41 declared `$id`s, 0 dupes), so
   this is latent, not live. The abort is fail-closed, bounded and auditable: `ArchitectureError` is caught by
   `verification.py:186-196` into `CheckResult("architecture","fail", …)` with code/message details, and the CLI
   path emits `{"code":…,"error":…,"ok":false}` (`scripts/grok_architecture.py:166-169`) — not a traceback crash.
   (`grok_verify` end-to-end not executed here: prohibited this session — **not run**, only the code path was read.)
   Concrete fix: raise AMBIGUOUS only for the `after` (head) inventory — head is the state being certified; for the
   `before` inventory attach the dependent to *all* candidate paths (union scheduling) so the per-pair comparator
   degrades it to an attributed `unsupported` row instead of aborting (probe C4 **[measured]**: `compare_contracts`
   already converts the same ambiguity into a per-pair `unsupported`, never an abort). And name the colliding id and
   the two record paths in the message.

3. **Three headline evidence numbers in the package do not reproduce on the tree they claim to measure.**
   `brief.md:23-24` and `architecture.md:13` assert "38 declared factory contracts, 89 non-local `$ref`s … 19
   cross-contract edges, 9 invisible" measured "at `d871ea6`"; `closure-fix-blast-radius.md:12` and `release.md`
   SIG-001 assert "closure goes from **10 to 27 target→dependent pairs**". **[measured]** on both pristine trees
   (probe A + occurrence recount, contracts bytes are identical base↔head): 36 factory-path contracts (50 declared
   total), 86 non-local `$ref` occurrences, 14 cross-contract pairs / 16 occurrences resolved by the new grammar,
   of which **4 pairs / 6 occurrences were invisible before** — the old grammar's 10 visible pairs/occurrences
   reproduce exactly. And the transitive target→dependent *pair* count is **22 → 27** (base→head), so "10 → 27"
   mixes base direct-edges with head transitive pairs: it inflates the fix's measured reach ~2× and the sentence
   mislabels its own units. Directionally every load-bearing claim checks out (all old edges preserved, the 5
   newly-acquired pairs are exactly the §2 table, comparator untouched — see below), but in a repository whose
   product is reproducible evidence (and with a recorded fabricated-evidence incident), numbers that a reader
   cannot re-derive are a trust defect. Fix: restate as "direct edges 10→14 (22→27 transitive pairs); 4 previously
   invisible dependency pairs", or state the exact counting definition and the input tree hash the 19/9/38/89 were
   measured on. Related smaller overclaim **[measured]**: `closure-fix-blast-radius.md:34-36` lists editing
   `M7-OPERATOR-HANDOFF-V1` as a **new** hard gate failure — `M7-OPERATOR-HANDOFF-V1`'s own identity verdict is
   `unsupported/unsupported_schema_keyword` at **base too** (probe B, identical verdicts both trees; probe E base
   run shows no non-self M7 failures because the self-failure is self-attributed), so that gate was already red for
   HANDOFF edits before #146; only the BRIDGES and TASK-EVIDENCE rows are genuinely new failures.

## Minor (nice to have)

4. **Stringly-typed deny-list coupling.** `_schema_reference_by_declared_path` (`architecture.py:1199-1203`) uses
   `return None, str(exc)`; the drop/raise decision matches message strings against `SCHEMA_REFERENCE_UNRESOLVED`
   (`architecture.py:1129-1131`). Verified `ArchitectureError.__str__` is exactly the message today
   (`architecture.py:72-75`, **[measured]** via probe C repr output). If anyone later decorates those messages
   (prefixes, labels like the other raises in this file use), UNSAFE/ESCAPE silently leave the UNRESOLVED set and
   the closure starts *raising on ordinary malformed refs* — fail-closed but a false wedge. Give `ArchitectureError`
   a `reason` attribute (or compare on the constants at raise time) so the deny-list cannot drift.
5. **Closure skips the comparator's kind filter.** `_external_contract_reference_paths` attaches edges to any
   declared path, while `resolve` accepts only `event|json_schema|signed_payload`
   (`architecture.py:1350-1354`). A `$ref` to an `openapi` contract path yields a closure edge whose comparison
   then degrades to `unsupported`. Direction is safe (over-scheduling), **[inferred]** — no such edge exists in the
   current inventory to measure. Either mirror the filter or note it in the docstring.
6. **Duplicate contract *paths* are the one inventory shape the two implementations read differently**: the
   comparator raises (`architecture.py:1280-1281`) while the closure's `{record.path: record.id}` silently keeps
   the last record (`architecture_fitness.py:918`), which could attribute an edge to one of the two twins.
   Everything still fails closed because *any* comparison with that inventory raises→`unsupported`. **[inferred]**
   (model schema enforces `uniqueItems` on other collections but I found no contracts-path uniqueness rule;
   `architecture.py:343-352` checks id uniqueness only). Cheap: reuse the comparator's duplicate-path raise.

## Availability / blast radius — direct answers

- **Who can trigger the abort:** any contributor whose authored pair of contracts shares a `$id` string **and**
  any contract anywhere references that exact string as a non-path `$ref` base. **[measured]** one probe-C config.
- **Cross-PR effect:** every gate run whose *base or head* contains that state and which touches any contract file
  fails the whole `contract_compatibility` check (local via `verification.py:186`, exact-SHA external check runs
  the same library — **[inferred]**, trust-ci internals are a read boundary I honored: names not contents).
- **Worst demonstrated case:** the C2 arm — the repository cannot remove the poison through the gate at all
  (cleanup PR also aborts); only reverting #146 restores mobility. Precondition does not exist on current main
  (**[measured]**, probe A).
- **Bounded/auditable:** yes at the fail point (structured CheckResult/JSON error, stable message, deterministic),
  but the message names no offender (finding 2).

## Path and resource safety — direct answers

- `schema_reference_relative_path` (`architecture.py:1152-1183`, lifted byte-for-byte from the deleted
  `_SchemaResolver._relative_path` — diff-verified) rejects backslash/`?`/`%`/`#`/absolute `/`/any
  `[A-Za-z][A-Za-z0-9+.-]*:` scheme (so `file:`, `http:`, UNC-drive forms), non-NFC text, control/format
  characters (`_unsafe_text`, `architecture.py:114-119`), `.`/empty segments, and each segment must fullmatch
  `^[A-Za-z][A-Za-z0-9._~-]*$` (`architecture.py:1110`); `..` above the root is ESCAPE. Both regexes are linear,
  no backtracking bomb. **[measured]** indirectly via the 600-line differential and 115-test suite; not
  re-fuzzed.
- Traversal outside the inventory is impossible by construction: the result must be `in declared_paths` — a set
  of model-declared paths — before any edge exists (`architecture.py:1204-1207`); a syntactically valid
  `../../etc/passwd` yields ESCAPE/UNDECLARED, never a read. Nothing new touches the filesystem or network:
  the only added object interaction in the `.grok-stack` diff is `PurePosixPath` (grep of `+` lines, **[measured]**
  — output above); contract *contents* are only ever read through the pre-existing `O_NOFOLLOW`-per-component,
  size-capped `_read_regular_bytes` (`architecture.py:177-215`). URL/IRI bases can attach an edge **only** if a
  declared inventory record carries that exact `$id` — resolution stays inventory-bound, never fetched.
- Budgets, all pre-existing and unchanged: `MAX_DOCUMENT_BYTES=1_000_000`, `MAX_DEPTH=64`,
  `MAX_PARSED_NODES=100_000`, `MAX_CONTRACTS=256` (`architecture.py:21-27`), enforced at file read
  (`architecture.py:202-211`), JSON parse (`architecture.py:263-265`), inventory size
  (`architecture.py:659`), resolver record count (`architecture.py:1269`) and per-resolve/pointer consumption
  (`architecture.py:1315-1317`, `1383-1399`). The closure walks **no more documents** than before — one pass per
  inventory over exactly the records it already walked (`architecture_fitness.py:915-930`); the new work is two
  hash maps per inventory plus one bounded string walk per `$ref` occurrence (≤86 today). The closure's own walk
  has no counter, but each document is already node/depth-bounded at parse time — worst case O(256×100k) dict
  visits per gate run, linear in the pre-existing parse caps. **[measured]** runtime: full 50-target closure
  sweep × both trees completed in the probe runtimes below.
- Base↔head ordering: edges from both inventories accumulate into one `reverse_dependencies` map (a union), so a
  dependency introduced *or* removed within one commit still schedules both contracts; per-inventory `$id` maps
  are built per pass, no cross-state bleed. **[measured]** (probe A/C: a base-only removed edge keeps the
  dependent; introduced edges appear via the after pass) — and that same union is why a base-only poison aborts
  (finding 2).

## Scope containment — all verified

- **[measured]** `git show 7d21d95 --name-only`: 18 files — 2 source (`.grok-stack/adaptive_grok/{architecture,architecture_fitness}.py`),
  1 test (422 insertions / **0 deletions**, so no assertion was weakened — FORBID-001 structurally holds), and 15
  files confined to `engineering/changes/20260919-fix-issue-146-.../`. Grep of the name list against
  `^(architecture/|factory/contracts/|governance/|schemas/|trust-ci/|.github/)` → **no matches** (exit 1).
- **[measured]** secret/host scan of all `+` lines: no key material, no `auth/token/secret/password/bearer` key
  names, no `user@host` URLs, no `/home/…` or operator paths, no long-base64; the two long hex strings are the
  base commit SHA (40-hex, correct) and `route.json:"base_fingerprint"` (64-hex fingerprint under an inert,
  repo-standard key used by every prior `route.json` — the #73 "authorization-ish key" pattern does not recur).

## Trust-boundary honesty and ordering

Preserving #147's comparator precedence byte-for-byte is the right call for this wave: the alternative — silently
re-defining reference identity inside a "closure fix" — would have made #146 itself a policy change (FORBID-003
names #147 as the owner), and my 600-line differential plus the 115-test suite show nothing else moved
(**[measured]**). Landing #146 first does **not** widen #147's *comparison-side* attack surface: capture already
worked pre-#146, and every newly restored `$id`/fragment edge resolves identically in closure and comparator
because the shipped inventory has no id/path shadows (**[measured]**, probe A). What #146 leaves open is the
*scheduling-side* twin (finding 1) — a claimant edit never even reaches the captured comparison.

Recommended order: **(a) now/with merge:** nothing (this wave is a net integrity gain); **(b) before #147:**
land the union-edge change (finding 1) — it is confined to the closure, cannot false-certify, and converts future
#147 exploit attempts into loudly re-verified dependents; **(c) then:** #147 precedence fix (comparator
declared-path-first or reject path-form `$id`s outright), optionally retired together with (b)'s extra edges if
precedences are unified; **(d) any time, cheap:** finding 2's head-only scope + attributed message, which is
pure availability hardening.

Package overclaim check on the specific asked sentence — "every new failure collapses onto one root dependent":
**[measured] CONFIRMED.** Per-target end-to-end arms on the real tree (probe E, both code bases): exactly three
targets gain a non-self merge-blocking dependent (`M7-OPERATOR-HANDOFF-V1`, `M7-PREDECESSOR-BRIDGES-V1`,
`M7-TASK-EVIDENCE-V1` → all list precisely `CONTRACT-FACTORY-M7-READY-BUNDLE-V1: unsupported compatibility
semantics`), the base run shows zero non-self M7 failures, and the "only two `unsupported_schema_keyword`
contracts left" claim holds (probe B: HANDOFF and READY-BUNDLE; the two other non-compatible identities are
`unsupported_openapi_construct`, a different class). The claim fails only on the HANDOFF row's word *new*
(finding 3) and on the 10→27 / 19/9 arithmetic — not on the root-cause collapse itself.

## What I measured

All probes in `/tmp/rev146sec` (dir mode 700), clones via `git clone --local` of the review worktree; worktrees
`repo` = `7d21d95`, `wt_base` = `d871ea6`. Delivery worktree used only for read-only git/grep/file reads.

| # | command | key output |
|---|---|---|
| A | `python3 probe_a.py repo` / `wt_base` | 50 contracts, 50 unique ids/paths, 41 declared `$id`s, `duplicate_id_collisions={}`, `id_shadows_other_path={}`, direct edges head 14 / base 10 / **lost 0**, transitive pairs head 27 / base 22, gained pairs = exactly the §2 table (5) |
| A2 | occurrence recount (heredoc) | 86 non-local `$ref`s, 16 cross occurrences new / 10 old → 6 invisible (**not 19/9/89/38**) |
| B | `probe_b.py` × both trees | 46/50 identity-compatible; non-compatible: HANDOFF & READY-BUNDLE (`unsupported_schema_keyword`), 2 openapi (`unsupported_openapi_construct`); `diff ident_base ident_head` → **IDENTICAL** |
| C | `probe_c.py` (planted collision + referrer `$ref`) on real tree | A1 `clean→poisoned head: RAISED 'ambiguous declared schema id' code=contract`; C1 `unrelated PR vs poisoned base: RAISED`; C2/C2b `cleanup PR (clean head, poisoned base): RAISED`; C4 `compare_contracts → unsupported(...)` (no raise) |
| D2 | precedence probe (real edge + synthetic claimant) | D1 `comparator→CLAIMANT | closure→PATH-TARGET`; D2 edit claimant → **referrer not in scope** (status row unsupported caused by my claimant choice, scope answer unambiguous); D3 edit path-target → referrer **in scope** (#146 works) |
| E | `probe_e.py` / `probe_e_base.py` (all 50 targets × description-only edit × real `_contract_compatibility`) | head: 9 non-self unsupported rows; base: 6 rows (same LANDING set, minus exactly the 3 M7 rows) → three new failure targets, all READY-BUNDLE |
| F | `probe_f.py` × both trees, 50×4 variants×3 policies | 600 verdict lines each, `diff` → **differing lines: 0** |
| T | `python3 -m unittest -q tests.test_architecture_fitness` (clean head clone) | `Ran 115 tests in 70.587s — OK` |
| S | `git show --name-only` / protected-path grep / secret & host grep / `git diff --numstat tests` | no protected paths; no secret-like `+` lines; tests 422/0 insertions/deletions |

## Verdict rationale

The change does what it says for the stated scope: the reference grammar is genuinely one implementation (spy test
+ shared function identity), the closure's edge set is a strict superset with zero losses (measured), comparator
semantics are byte-identical (600 independent differential lines, 0 diffs; 115 tests green), edge-dropping is
deny-listed so a future reason cannot silently discard an edge (fail-closed by construction, with the fragility
noted in Minor 4), nothing escapes the declared inventory or reaches the network, and the delivered diff touches
only gate code, appended tests, and its own change package. The real residual risks — claimant-edge scheduling
omission (Important 1), base-inventory abort wedge (Important 2) and the non-reproducible headline numbers
(Important 3) — are hardening and evidence-hygiene items, none a false-certification *regression* introduced here.
PASS to merge, with Importants 1–2 landing in the #147 wave and Important 3's numbers corrected in the package
before the PR description is published.

## Scope I could not verify

- External exact-SHA `adaptive-trust-ci/verified@…` behavior on an ambiguity abort — `trust-ci/` contents are a
  declared read boundary; I read neither the runner nor any key/runtime file (names not even listed). **[boundary]**
- End-to-end `python3 scripts/grok_verify.py --mode pr` — explicitly prohibited this session; the catch-and-report
  path (`verification.py:186-196`) and CLI JSON error path were **read, not executed**. **[not run]**
- The controller's full 555-line 7-edit differential and the implementer's M0–M8 mutation matrix — not re-run;
  independently superseded where it matters by probe F (600 lines, 0 diffs) and the named anti-inheritance tests. **[not run]**
- `gh pr` overlap claims in `sequencing-and-overlap.md` (PRs #137/#138 file sets) — remote GitHub state not
  re-queried. **[not run]**
- Whether #147's *comparison-side* capture can produce a full false `compatible` on the real tree with real
  policies (the reproduction lives in #147's own record; probe D3 stayed fail-closed via B's own findings and the
  landing-family opacity). Declared out of scope by the brief; I did not pursue it.
