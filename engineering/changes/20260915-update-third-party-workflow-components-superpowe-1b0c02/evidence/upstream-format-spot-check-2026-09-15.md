# Upstream format audit against the pinned tags (2026-09-15)

Supersedes an earlier interim spot-check by this author that concluded "no parser-visible drift";
that conclusion was wrong for BMAD. The full independent audit is
`analysis-docs_researcher-upstream-formats.md` in this directory; corrections applied:

## Findings accepted and fixed (code + tests in this change)

1. `FORBIDDEN_SOURCE` rejected genuine spec-kit v1.0.7 template text
   (`*Example of marking unclear requirements:*` at line start, `*GATE: ...*`) because Markdown
   emphasis looked like a YAML alias. Narrowed to YAML positions only (tags/merge/anchor/alias forms
   kept failing closed). Tests: emphasis loads; `base: &a`, `name: *a`, `- *a`, `<<: *d`, `!!tag`
   all still raise.
2. BMAD v6.11/6.12 story/epic headings are `## Epic N:` / `### Story N.M:` (with `1.2a` suffixes);
   the parser was H1-only and matched nothing. Widened to levels 1–4 with numeric dotted/letter
   ids; `specs/001-*/tasks.md` second path branch now also covered by a spec-kit test.
3. Story status carriers: bare `Status: <value>` lines (upstream story template) and leading
   front-matter `status:` (canonical build spec, including the new `in-review` token) are now
   recognized; the terminal/non-terminal vocabulary is total and documented
   (`BMAD_TERMINAL_STATUS` / `BMAD_NONTERMINAL_STATUS`).
4. `PLACEHOLDER` now includes upstream's `NEEDS CLARIFICATION` token.
5. Behavior documented rather than changed: upstream `epics.md` has zero checkboxes → structure-only
   (0 tasks); prose dependencies `(depends on T…)` and `FR-*`/`SC-*` ids stay unparsed; BMAD v6.11
   moved project context out of `_bmad/` (content availability, role kept); `.superpowers/sdd/`
   lifecycle is git-ignored scratch.

## Deliberately rejected (recorded rulings)

- Version-gating `source_version` in the loader (auditor item 12): contradicts ADR-0001/decisions
  2026-09-15 — currency is proven by `workflow_sources` + named unmodified-shape tests, not parser
  rejection. Fixtures now carry real versions (`1.0.7`, `6.12.0`) in the new tests regardless.
- Editing the content-addressed 2026-08-30 design/plan/tasks documents (auditor item 21): they are
  manifest-hashed by the `d41aa6` package; correction shipped as a separate amendment
  `docs/superpowers/specs/2026-09-15-workflow-artifact-adapters-upstream-amendment.md`, linked from
  README and QUICKSTART (auditor item 22).
- Schema role-enum closure (item 14): the closed per-source role set is enforced in code with tests;
  JSON-schema conditionals deferred until a consumer needs them (documented in the amendment's
  authority note). No `advanced-status` wiring: `_advanced_status_hints` retains no `converge()`
  call site — status advancement stays receipt-only by design; the function and its corrections are
  characterization-tested directly and the wiring is left as a separate bounded change.

## Spec Kit v0.16.5→v1.0.7 template diff

Auditor verified the five artifact templates are byte-identical across the bump (only script-output
key rename `SPECS_DIR→FEATURE_DIR` and prose rules changed); consistent with "no Spec Kit grammar
change required".
