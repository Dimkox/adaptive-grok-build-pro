# Workflow Artifact Adapters — Upstream Format Amendment (2026-09-15)

This document amends — it does not rewrite — the content-addressed design
`2026-08-30-workflow-artifact-adapters-design.md`, whose "Adapter mappings"
paragraph described the documented native subset as observed on 2026-08-30.
The original file is byte-frozen: the `20260830-implement-a-new-model-agnostic-workflow-artifact-d41aa6`
package manifests it by SHA-256 digest, so corrections live here instead.

## Verified upstream currency (2026-09-15, authenticated `gh api` against exact tags)

- github/spec-kit **v1.0.7** — task grammar, phase headings, roles and paths unchanged since
  v0.16.x; the original "Spec Kit phase headings plus `- [ ] TNNN [P] [USN] ...` task rows" sentence
  remains accurate.
- bmad-code-org/BMAD-METHOD **v6.12.0** — headings are `## Epic N:` and `### Story N.M:` (with
  letter suffixes like `1.2a`), not H1-only; story status may appear as a bare `Status: <value>`
  line (story template) or as `status:` in leading `---` front matter (canonical build spec,
  v6.12 token `in-review`); `sprint-status.yaml` key/value format is unchanged upstream.
- obra/superpowers **v6.3.0** — path lifecycle only: plan-scoped `.superpowers/sdd/<plan-basename>/`
  evidence (since v6.2.0) is git-ignored scratch in the originating workspace and may be removed on
  plan completion; absence of that directory never means absence of evidence. `docs/superpowers/**`
  bodies stay unparsed advisory documents.

## Accepted corrections in the shipped parser

1. The YAML-authority guard no longer treats Markdown emphasis (`*word ... *` at line start, e.g.
   upstream's `*Example of marking unclear requirements:*` and `*GATE: ...*`) as a forbidden alias.
   Block-context hostile forms still fail closed: document-node tags (`!!…`), merge keys (`<<:`),
   block anchors (`&name` at node position) and whole-value block aliases (`key: *name`, `- *name`).
   The guard is block-context-only by design: flow-collection aliases (e.g. a tag or alias inside
   `{...}`/`[...]` flow content) and alias-shaped mapping keys are no longer rejected and cannot be
   covered without a real YAML parser; they are inert because no product code path ever feeds
   imported bytes to a YAML parser — loader, schema validation and digests treat content as text.
2. Story/epic heading recognition accepts heading levels 1–4 and numeric ids with optional
   `.`-segments and a trailing letter (`1`, `1.2`, `1.2a`).
3. The story-status vocabulary is total: terminal tokens
   `{done, complete, completed, review, in-review, ready-for-review}`; explicitly non-terminal
   `{backlog, draft, ready-for-dev, ready, in-progress, open, optional, blocked, high-level}`.
   Status advances only advisory hints, never native verification.
4. `PLACEHOLDER` now also catches upstream's unresolved-requirement token `NEEDS CLARIFICATION`.

## Known-unparsed (advisory by design, never silently authoritative)

- Spec Kit prose dependencies (`(depends on T012, T013)`, `## Dependencies & Execution Order`) —
  the imported DAG is the documented positional/phase heuristic.
- Spec Kit `FR-*`/`SC-*` ids and BMAD numbered acceptance criteria — `covers` extraction stays
  native-id-only (`AC|INV|FORBID-nnn`); imported tasks without native ids are marked
  `enrichment_required`.
- BMAD front-matter `route:`/`deferred:` beyond `status:`, `stories.yaml` indexes, and the v6.11
  relocation of project context into root `AGENTS.md` (outside the accepted `_bmad*` prefixes):
  a manifest naming such a missing file fails closed; the roles stay declared for producers that
  still emit them.
- Upstream `blocked` status maps to non-terminal pending plus findings; no graph schema state was
  added for it.

## Authority note

`source_version` stays a bounded free-form identity (ADR-0001): version currency is asserted by the
`workflow_sources` contract (`toolchain.json` + `tests/test_workflow_sources.py` + named
unmodified-shape tests), not by parser version gates. Status-hint computation
(`_advanced_status_hints`) currently has no call site in `converge()`; the corrections above are
exercised by direct characterization tests, and wiring hints into convergence remains a separate
bounded change. `cas_write` bounds its own target names under the change's `workflow/` tree but
does not itself re-derive the active change: the active-change containment is enforced by the CLI
(`scripts/grok_artifacts.py`), and callers of the library API are first-party code only. None of
this grants imported documents route, governance, approval, receipt, or
merge authority.
