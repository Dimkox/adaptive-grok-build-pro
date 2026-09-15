# ADR 0001 — Workflow source version contract for third-party document formats

- Status: accepted
- Date: 2026-09-15
- Change: `20260915-update-third-party-workflow-components-superpowe-1b0c02`
- Upstream observation (2026-09-15, `gh api repos/<repo>/releases/latest`):
  `obra/superpowers v6.3.0 (2026-08-12)`, `bmad-code-org/BMAD-METHOD v6.12.0 (2026-09-04)`,
  `github/spec-kit v1.0.7 (2026-09-15)`

## Context

The workflow artifact adapters ingest GitHub Spec Kit, BMAD Method, and Superpowers documents as
untrusted advisory data. `WorkflowSourceV1.source_version` is deliberately a free-form bounded
string: rejecting unknown versions would turn an advisory anti-corruption layer into a version gate
and break historical fixtures. The product still needs a falsifiable, machine-readable claim of the
form "we are current with the upstream document formats".

## Decision

Express currency as three separable assertions, pinned in one place:

- **C1 declared versions** — the `workflow_sources` block of `.grok-stack/config/toolchain.json`
  records, per component: `id` equal to the closed `source_type` enum, `pinned`/`upstream_tag`,
  `release_published_at`, `observed_latest`, `observed_at`, the accepted `roles`, the repository
  `tracked_prefixes`, and `verification_tests` (closed `SAFE_UNITTEST_TARGET` shape).
- **C2 verified shape coverage** — every pinned version names at least one committed, importable
  unittest that parses unmodified upstream document shape; a pin without a live named test is a
  red build (`tests/test_workflow_sources.py`).
- **C3 dated currency observation** — README table plus config `observed_at`, refreshed by an
  operator re-running the quoted `gh api` commands. The freshness bound is 90 days; failing on a
  stale observation is intended, failing on somebody else's release train is not: no assertion here
  compares against live upstream.

Rejected: making the manifest loader reject unknown `source_version` values; vendoring upstream
trees into the product.

## Consequences

- Bumping a supported component version is a normal reviewed source change: refresh config, README
  rows, and at least one shape test, and re-observe upstream. `CHANGELOG`/`VERSION` identity stays
  a release-time decision.
- Adapters must keep parsing documented subsets; `ROLE_MAP`, `PATH_PREFIXES`, parser regexes, and
  `source_version` validation carry no version allowlists and must not gain any (INV-001 advisory
  boundary).
- BMAD v6.12.0 content availability (not a parser break): `persistent_facts` ships empty and
  `project-context.md` is no longer auto-loaded, so a fresh 6.12 project may simply provide no
  `project-context` source; missing manifest entries already fail closed. Recorded in config
  `breaking_notes`.
- Watch item, not yet actionable: upstream documents `/speckit.taskstoissues` as planned to leave
  Spec Kit core in a future release; no repository surface depends on it.
- `_bmad/`, `_bmad-output/`, `.specify/`, `specs/`, `docs/superpowers/`, `.superpowers/` may only
  contain files reachable from a declared `tracked_prefixes` entry; wholesale vendoring fails the
  contract test.
