# Workflow upstream observation — 2026-09-30

Stable release identity and main observations are distinct. `upstream_commit` is a peeled tag's commit, not its annotated tag object. Main SHAs describe only the observed public repository head and do not create stable release or install targets.

| Source | Stable tag | Peeled stable commit | Observed main commit | Release date |
| --- | --- | --- | --- | --- |
| obra/superpowers | v6.4.2 | 8ca22dba9a94f28898bbce59f2537ff4d87c747d | 8ca22dba9a94f28898bbce59f2537ff4d87c747d | 2026-09-25 |
| bmad-code-org/BMAD-METHOD | v6.12.0 | 05bfbd46d00766ec88eb9b42e76be2c575d64d7b | 1cbcfa272fe65787c06a1fa164a901f46117cca7 | 2026-09-04 |
| github/spec-kit | v1.0.13 | f1a548a39dba4e5e8600de1d2e0d3ff0c468d2a9 | d2ddd910266ad14afe79c5414c88ee316aca6e9a | 2026-09-29 |

Official release pages: [Superpowers](https://github.com/obra/superpowers/releases/tag/v6.4.2), [BMAD](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.12.0), [Spec Kit](https://github.com/github/spec-kit/releases/tag/v1.0.13). Ref identities were independently supplied by the coordinator's read-only upstream research, and exact source excerpts were retrieved by the implementer with `curl -fsSL` against the URLs below.

## Exact-revision parser samples

- `test_superpowers_v642_spec_pointer_and_interfaces_stay_opaque_advisory`: assembled verbatim header/Spec/Interfaces/checkbox excerpts from [skills/writing-plans/SKILL.md](https://raw.githubusercontent.com/obra/superpowers/8ca22dba9a94f28898bbce59f2537ff4d87c747d/skills/writing-plans/SKILL.md). Intervening template prose/code is omitted. The referenced spec is deliberately absent; loading retains one source, invents no native tasks and produces only advisory candidates.
- `test_spec_kit_v1013_exact_task_rows_preserve_phase_dependencies`: assembled verbatim heading and task-row excerpts from [templates/tasks-template.md](https://raw.githubusercontent.com/github/spec-kit/f1a548a39dba4e5e8600de1d2e0d3ff0c468d2a9/templates/tasks-template.md). Blank/prose regions and unused task rows are omitted; literal IDs and placeholders are retained. Verifies phase dependencies and `[P]`/`[US1]` markers without receipt authority.
- `test_bmad_v612_exact_template_tasks_preserve_nested_subtasks`: exact status/task excerpts from [src/bmm-skills/v6-shims/bmad-create-story/template.md](https://raw.githubusercontent.com/bmad-code-org/BMAD-METHOD/05bfbd46d00766ec88eb9b42e76be2c575d64d7b/src/bmm-skills/v6-shims/bmad-create-story/template.md), with only the heading placeholders instantiated as `1.1` and `Template sample`. Verifies four pending nested task rows and their dependency chain.
- `test_bmad_observed_main_ticket_shape_remains_advisory_without_native_tasks`: contiguous example excerpt from [skills/bmad-ticket/assets/story-template.md](https://raw.githubusercontent.com/bmad-code-org/BMAD-METHOD/1cbcfa272fe65787c06a1fa164a901f46117cca7/skills/bmad-ticket/assets/story-template.md). This main-only ticket shape has no native task rows or status. The bounded source version uses `main@1cbcfa272fe6`; this document retains the full exact commit. It is supported as advisory context, not claimed as a stable BMAD story format.

Existing 6.3-era Superpowers, Spec Kit 1.0.7 and BMAD 6.12.0 tests remain unchanged and named in config. No full upstream files, installed framework, source-manifest schema expansion or runtime parser changes are included. Samples characterize accepted shapes, not execution of the upstream skills or all upstream templates.
