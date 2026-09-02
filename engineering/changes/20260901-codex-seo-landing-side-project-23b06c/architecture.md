# Architecture — Codex SEO landing side project

## Current behavior

Before this change the repository had no Codex-discoverable SEO landing skill
or isolated showcase. The upstream root failed Codex validation on angle
brackets; the adapted package now validates successfully.

## Proposed behavior

Install a Codex-native adaptation at `.agents/skills/seo-landing/` and a static
Russian showcase at `side-projects/seo-landing-showcase/`. The skill routes
generate, audit-only, and fix-existing requests before loading detailed
references; the showcase documents the capability without invoking it.

## Components and boundaries

- `SKILL.md`: concise routing, safety, approval, and reporting contract.
- `agents/openai.yaml`: Codex display metadata and explicit invocation prompt.
- `references/`: conditional SEO, server, video, and map guidance.
- `UPSTREAM.md` and `LICENSE`: exact provenance and license boundary.
- `README.md`, `README.ru.md`, and `SECURITY.md`: Codex-only usage and safe-reporting boundaries.
- `side-projects/seo-landing-showcase/`: dependency-free presentation layer.
- `browser-contract.mjs`: dependency-free Node 24/Chrome CDP viewport, focus, screenshot, and reduced-motion runner.
- `tests/test_seo_landing_side_project.py`: deterministic repository contracts.

## Data flow

User intent selects one mode. Generate mode collects verified brief facts and
writes only to a dedicated project directory; audit-only reads a supplied URL
or files and returns evidence; fix-existing changes only named defects. Generate
and fix-existing pause after HTML presentation until explicit approval.

## API and event contracts

No HTTP API, event, queue, schema migration, or external write is introduced.
The public interface is explicit `$seo-landing` invocation or matching natural
language intent interpreted by Codex.

## Bitrix-specific impact

- Modules/events/agents/components affected: none.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: removal of the two isolated directories reverts the capability.
- Core modification: forbidden unless explicitly approved.

## Decisions

- Embed as an isolated optional side project so landing generation cannot alter Trust CI runtime behavior.
- Preserve the reviewed upstream baseline at exact commit and document local adaptations.
- Ship the showcase non-indexable until a verified production origin exists.
- Stack the PR on `fix/path-aware-shell-policy-circuit-breaker`, not `main`.

## Verification and delivery bases

The active route retains authoritative base commit
`1c06299894279a88b881defa3f19b004fa742223`; route verification may therefore
use a broader comparison and `route.json` is not rewritten. The implementation
worktree and stacked PR use `7c61e3b647924e5667d171d8b286e5d79b8a4efe`
on `fix/path-aware-shell-policy-circuit-breaker` as the delivery base.

## Risks and mitigations

- Prompt injection from retrieved pages: treat all retrieved content as data and retain repository authority order.
- Fabricated SEO claims: require measured evidence and report unavailable gates as blockers.
- Accidental indexing under an invented host: enforce `noindex, nofollow` and omit canonical/origin identifiers.
- License drift: retain MIT text and exact source commit in `UPSTREAM.md`.
