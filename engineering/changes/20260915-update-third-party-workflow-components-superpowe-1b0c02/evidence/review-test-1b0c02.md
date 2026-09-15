# Test re-review (post-remediation) — `20260915-update-third-party-workflow-components-superpowe-1b0c02`

PASS (with low findings)

- Head reviewed: `3d19067` (single squashed commit on `b6fe340`), worktree
  `/home/pall/grok-projects/adaptive-grok-build-pro-third-party-sync`, clean tree.
- Reviewer: same independent test-analysis subagent as the first round (read-only), 2026-09-15.
- Supersedes the previous report on `c4b5e3f`. Scope unchanged: `tests/test_workflow_artifacts.py`
  (esp. `CurrentUpstreamFormatTests`), `tests/test_workflow_artifacts_adversarial.py`,
  `tests/test_workflow_artifacts_cli.py`, `tests/test_workflow_sources.py`, plus the package
  claim wording (`requirements.md`, `change-spec.yaml`, `tasks.md`), ADR-0001 and the amendment spec.
- Method: current-file reading, live `gh api` re-confirmation at the pinned tags, in-process
  mutation probes against copies of the shipped module in `/tmp` (repository tree untouched),
  and focused test runs.

## 1. Prior finding → status → evidence

| ID | Prior finding | Status now | Evidence on `3d19067` |
| --- | --- | --- | --- |
| F1 | Two new tests asserted only through `_advanced_status_hints`, which has no production call site | **Resolved by ruling + docs** (residual in-file marker, see R3) | `docs/superpowers/specs/2026-09-15-workflow-artifact-adapters-upstream-amendment.md:59-63` ("`_advanced_status_hints` currently has no call site in `converge()`; the corrections above are exercised by direct characterization tests, and wiring hints into convergence remains a separate bounded change"), `evidence/upstream-format-spot-check-2026-09-15.md:36-39`; the amendment is linked from `README.md:218` and `QUICKSTART.md:90`, so the deferral is on the same evidence chain AC-002 cites |
| F2 | Heading-level widening and sprint-status branch pinned by assertions that could not fail | **Resolved** | `tests/test_workflow_artifacts.py:657-676` asserts non-empty `['story-1-1-001', 'story-1-2-001']` from `## Epic N:` / `### Story N.M:`; `:691-715` proves an advancement delta (`set()` → `{'story-9-9-001'}`) by rewriting only `development_status:\n  story-9-9: …` in the nested upstream shape; `:678-689` adds the dotted-id collision case. Mutation probes A/B/C below show each new assertion fails under the pre-change parser |
| F3 | Class docstring presented every fixture as byte-verified against the tags | **Resolved** | `tests/test_workflow_artifacts.py:573-586` now separates three tiers: byte-verbatim (the two spec-kit emphasis lines, `NEEDS CLARIFICATION`), grammar-level mirrors with synthesized content (task rows, `## Epic N:`/`### Story N.M:`, dashed `development_status:` keys, bare `Status:`), parser-side extensions (`1.2a`, `ready-for-review`/`in-review`) kept "so newer documents do not silently drop". Both spec-kit quotes re-confirmed verbatim at `v1.0.7` (§3) |
| F4 | Positional README column coupling with a misleading failure message | **Resolved / accepted** | `tests/test_workflow_sources.py:41-58`: the section regex pins the exact header row `| Component | Pinned | Upstream | Observed latest | Observed |` and the `| --- |` separator, and `assert section, 'README.md is missing the Workflow sources table'` fires before any pin comparison, so a column edit now fails as a layout error, not as a date/semver mismatch against config. `assert len(cells) == 5, line` additionally names the offending row. Intentional operator-table coupling per ADR-0001 C3 |
| F5 | `tasks.md` T6 / AC-003 claimed 7 decisions + 14 mistakes; diff adds 9 + 15 | **Resolved** | `git show HEAD -- decisions.md \| grep -c '^+## '` = 10, `mistakes.md` = 15; `^-## ` = 0 and `^-[^-]` = 0 for both files. Claims now read "10 `decisions.md` + 15 `mistakes.md` entries" (`tasks.md` T6) and "10 decisions + 15 mistakes entries" (AC-003) and match the diff |
| F6 | Two guard categories (flow-collection aliases, alias-shaped mapping keys) asserted in neither direction | **Resolved as ruled (documentation, not test)** | Amendment item 1 (`:28-33`) states the block-context-only boundary and the reason: "flow-collection aliases … and alias-shaped mapping keys are no longer rejected and cannot be covered without a real YAML parser; they are inert because no product code path ever feeds imported bytes to a YAML parser". Accepted: no test was added for the inert categories; the live exposure is zero (bodies are treated as text by loader, schema validation and digests). The block-context regression test is intact — see §4 for one unpinned branch found inside it (R1) |

## 2. AC-002 wording check (the F1 consequence the finding was about)

`requirements.md` AC-002 now claims only: ids equal the schema `source_type` enum, "each pinned version
has a loadable unmodified-shape parser test", README rows match config, observation ≤90 days, no
third-party content outside declared prefixes. None of those clauses is carried by status-hint
behaviour. `change-spec.yaml` AC-002 (typed authority) claims format-subset corrections, existence and
passing of latest-version fixtures, and one machine-readable pin contract; its evidence entries are the
`tests/test_workflow_artifacts.py` and adversarial modules as a whole, which do prove shipped behaviour
independently of the hints — `_native_framework_tasks` is called from `compile_task_graph`
(`.grok-stack/adaptive_grok/workflow_artifacts.py:652-680`, `770+`), so heading-level, dotted-id, task-row
and guard assertions are live product evidence; only the four hint assertions
(`tests/test_workflow_artifacts.py:711,715,759,784`) are characterization. AC-002 no longer over-relies on
unwired code. The superseded "no drift" sentence that used to sit next to it is the remaining claim defect
(R2).

## 3. Upstream re-confirmation (`gh api`, single pass, v1.0.7)

```
$ gh api -H 'Accept: application/vnd.github.raw' \
    'repos/github/spec-kit/contents/templates/spec-template.md?ref=v1.0.7' | sed -n '94,98p'
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]

$ gh api -H 'Accept: application/vnd.github.raw' \
    'repos/github/spec-kit/contents/templates/plan-template.md?ref=v1.0.7' | sed -n '38,43p'

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on constitution file]
```

`templates/spec-template.md:96` and `templates/plan-template.md:41` match the two fixture lines at
`tests/test_workflow_artifacts.py:603-608` character for character, and `NEEDS CLARIFICATION` is
upstream's unresolved-requirement token (`spec-template.md:98`). The docstring's byte-verbatim tier is
accurate. The `1.2a` letter suffix and `in-review` remain honestly labelled as extension/tier-3 in the
test; the audit's own grounding for `1.2a` is upstream's story regex (`sprint_plan.py:44-47` at v6.12.0,
`analysis-docs_researcher-upstream-formats.md:184,302`), i.e. grammar, not a template instance — consistent
with how the amendment words it.

## 4. Mutation probes (module copies in `/tmp`; repository tree untouched)

```
A heading-widening mutant (h1-only):  tasks = ['epic-unscoped-001', 'epic-unscoped-002']
A baseline (shipped):                 tasks = ['story-1-1-001', 'story-1-2-001']
B dotted-id mutant (one .segment):    tasks = ['story-1-1-001', 'story-1-1-001']   <-- collision
B baseline (shipped):                 tasks = ['story-1-1-1-001', 'story-1-1-2-001']
C sprint-status mutant (no `done`), sprint=in-progress: hints = []
C sprint-status mutant (no `done`), sprint=done:        hints = []                 <-- assert fails
C baseline,                              sprint=done:    hints = ['story-9-9-001']
D emphasis-guard mutant (re-widened alias branch): raised WorkflowArtifactError    <-- assert fails
D baseline shipped: sources = 1
```

Probe A corrects one detail of the first-round report: under the pre-change H1-only grammar the epics
fixture did not yield an empty list, it yielded `epic-unscoped-*` keys; the new key-identity assertion
fails against that either way, so the widening claim is now falsified by a test. Probe C confirms the
isolation the F2 remedy asked for (only the `development_status:` value changes between the two
assertions). Probe D confirms the narrowing cannot silently re-widen.

Guard-branch mapping for the five hostile inputs at `tests/test_workflow_artifacts.py:618-626`
(against the six branches of `FORBIDDEN_SOURCE`, `.grok-stack/adaptive_grok/workflow_artifacts.py:113-121`):

| Branch | Rejected form | Hit by a test input |
| --- | --- | --- |
| 1 | `(?:^|\s)!!` document tags | yes (`type: !!python/object:evil`) |
| 2 | `(?:^|\s)<<:` merge keys | yes (`auth:\n  <<: *defaults`) |
| 3 | `^[ \t]*(?:-[ \t]+)?&name` anchor at document/sequence node position | **no** |
| 4 | `:[ \t]+&name` anchor in mapping-value position | yes (`base: &anchor`) |
| 5 | `^[ \t]*-[ \t]+\*name$` whole-value alias in a sequence entry | yes (`- *anchor`) |
| 6 | `:[ \t]+\*name$` whole-value alias in a mapping value | yes (`name: *anchor`) |

## 5. New findings

### R1 — Low: one branch of the narrowed YAML-authority guard has no adversarial input anywhere

`FORBIDDEN_SOURCE` branch 3 (`^[ \t]*(?:-[ \t]+)?&[A-Za-z0-9_.-]+`, document- and sequence-position
anchors, `.grok-stack/adaptive_grok/workflow_artifacts.py:116`) is exercised by no test in the tree:
`grep -c '&'` over `tests/test_workflow_artifacts.py`,
`tests/test_workflow_artifacts_adversarial.py` and `tests/test_workflow_artifacts_cli.py` returns 1, 0, 0
— the single occurrence being the mapping-value form `base: &anchor`. Deleting branch 3 (or narrowing it
to `: &`) leaves the whole suite green while `&anchor\n`, `  &anchor\n` and `- &anchor value\n` start
loading; they are rejected today (verified in-process). The amendment lists "block anchors (`&name` at node
position)" among the forms that "still fail closed", so the category is documented and only one of its two
positions is pinned.
*Failure scenario:* a future regex tidy-up drops the node-position anchor branch; the suite stays green and
imported BMAD/spec-kit files carrying a document-level anchor stop failing closed.
*Remedy:* add two entries to the existing hostile tuple — `"&anchor\n"` and `"- &anchor value\n"` — which
covers branch 3 with no new test and no fixture invention.

### R2 — Low: package documents still carry the superseded audit conclusion and a stale test count

- `requirements.md:17` — "Upstream drift discovered by format audit → literals fixed or ruling recorded
  (audit: no parser-visible drift at pinned tags)". The full audit found parser-visible drift in four
  places and `evidence/upstream-format-spot-check-2026-09-15.md:3` opens by retracting exactly that
  sentence ("Supersedes an earlier interim spot-check by this author that concluded 'no parser-visible
  drift'; that conclusion was wrong for BMAD"). T9 and the amendment both record the corrections, so the
  parenthetical is now a contradiction inside the same package.
- `tasks.md` T9 — "five new verbatim-upstream-shape tests in `CurrentUpstreamFormatTests`". The class holds
  9 tests, 7 of which assert upstream shape (the other two are `test_receipt_kind_sets_match_and_domain_kinds_validate`
  and the placeholder-token test), and under the rescoped provenance only one fixture is byte-verbatim.
  The word "verbatim" is the one the F3 remedy deliberately removed.
*Failure scenario:* the PR body assembled from these two files re-asserts "no parser-visible drift" and an
"verbatim upstream" test set that the shipped docstring contradicts, which is the same claim-accuracy class
recorded in the new `mistakes.md` entry about placeholder-shaped fixtures.
*Remedy:* reword the parenthetical to name the four accepted corrections, and state the count/tier plainly
(e.g. "seven current-upstream-shape tests, two fixtures byte-verbatim").

### R3 — Low: `in-review` attribution and the misleading test name

- `.grok-stack/adaptive_grok/workflow_artifacts.py:138-141` comments "Total BMAD story-status vocabulary as
  of bmad-code-org/BMAD-METHOD v6.12.0" over a set that includes `ready-for-review`, which the audit names
  only as a token this parser already accepted (`analysis-docs_researcher-upstream-formats.md:68-69,272`);
  the test docstring at `tests/test_workflow_artifacts.py:580-585` classifies `ready-for-review` correctly as
  a parser-side extension. The code comment and the test provenance now disagree about which tokens are
  upstream.
- `test_bmad_v612_front_matter_and_sprint_shape_together`
  (`tests/test_workflow_artifacts.py:717-759`) has no `sprint-status` document in its fixture; nested-key
  shape coverage lives in `test_sprint_status_advances_only_from_nested_key_values`. The name promises
  coverage that a maintainer would then not look for in the right place.
*Failure scenario:* a maintainer either "corrects" the vocabulary toward the comment's upstream claim, or
assumes the nested-key branch is doubly covered and deletes the isolation test.
*Remedy:* append "(superset: `ready-for-review` retained from the pre-v6.12 parser)" to the code comment, and
rename the test to `..._front_matter_status_and_letter_suffix_heading_together` (or add the sprint doc).

No Medium or Critical item is open. R1–R3 are single-line edits and none of them can let a wrong result
reach a user; they should land with the remaining paperwork or be named as follow-ups in the PR body.

## 6. Evidence — runs on `3d19067`

```
$ timeout 200 python3 -m unittest tests.test_workflow_artifacts.CurrentUpstreamFormatTests -v 2>&1 | tail -25
test_bmad_bare_status_line_vocabulary_is_total ... ok
test_bmad_dotted_story_ids_do_not_collide ... ok
test_bmad_v612_front_matter_and_sprint_shape_together ... ok
test_bmad_v612_heading_levels_produce_tasks_the_h1_parser_missed ... ok
test_placeholder_vocabulary_covers_spec_kit_clarification_token ... ok
test_receipt_kind_sets_match_and_domain_kinds_validate ... ok
test_spec_kit_emphasis_loads_but_yaml_authority_fails_closed ... ok
test_spec_kit_tasks_under_specs_prefix_parse_current_grammar ... ok
test_sprint_status_advances_only_from_nested_key_values ... ok
----------------------------------------------------------------------
Ran 9 tests in 0.108s

OK

$ timeout 300 python3 -m unittest tests.test_workflow_artifacts tests.test_workflow_artifacts_adversarial \
    tests.test_workflow_artifacts_cli tests.test_workflow_sources tests.test_change_receipts 2>&1 | tail -12
.......................................................................................
----------------------------------------------------------------------
Ran 87 tests in 18.022s

OK
```

Paperwork re-count:

```
$ for f in decisions.md mistakes.md; do git show HEAD -- $f | grep -c '^+## '; \
      git show HEAD -- $f | grep -c '^-[^-]'; done
10   # decisions.md added headings
0    # decisions.md removed content lines
15   # mistakes.md added headings
0    # mistakes.md removed content lines
```

Unchanged cosmetic residual from the first round (not counted as a finding): three added headings
(`## 2026-09-15 Grok alongside primary Qwen`, `## 2026-09-15 Grok merged-release preparation`,
`## 2026-09-15 Public current-state drift after live activation`) still use no ` — ` separator, and four
headings in the two files still sit without a preceding blank line (`decisions.md:18,482`,
`mistakes.md:28,717`). No content is lost; AC-003's zero-removal claim holds.

## 7. Verdict rationale

All six prior findings are addressed: F2 is closed with assertions that demonstrably fail under the
pre-change parser (three independent mutation probes), F3's provenance is tiered and re-confirmed against
the live tag, F4 and F5 are closed as specified, and F1 and F6 were closed by explicit rulings recorded in
the amendment plus the spot-check, with AC-002 reworded so no acceptance claim rests on unwired code. The
suite is green (9 focused format tests, 87 tests across the adapter surface and receipts), deterministic,
and fast. The three new items are one unpinned guard branch, two stale/contradictory claim sentences, and a
misleading name — none of them changes the guard's live behaviour, the authority boundary, or the version
contract, so the test surface supports merge preparation once the claim wording is refreshed.
