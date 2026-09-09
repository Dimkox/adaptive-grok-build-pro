# SEO Landing for Codex

Repository-scoped Codex skill for generating, auditing, and making targeted
repairs to fast static SEO landing pages. Invoke it explicitly with
`$seo-landing`, or describe an SEO landing generation, read-only audit, or
optimization request and let Codex select the matching mode.

## Modes

- `generate`: collects verified brief facts, writes a new project under
  `side-projects/seo-landings/<project-slug>/` by default, and stops for explicit
  HTML approval before validation.
- `audit-only`: reads the supplied URL or local page and returns evidence without
  creating or modifying project files.
- `fix-existing`: changes only the named defects, preserves unrelated content,
  and uses the same HTML approval stop before validation.

Missing domain or keywords stop generation before a project directory is
created. The skill does not invent claims, legal copy, endpoints, asset rights,
schema facts, canonical origins, or measured scores.

## Codex usage

```text
$seo-landing Собери статический SEO-лендинг из этого проверенного брифа
$seo-landing Аудируй https://example.test/ без изменений
$seo-landing Исправь CLS в этом локальном index.html
```

Detailed performance, accessibility, server, video, and map contracts live in
`references/` and are loaded only when the selected mode needs them. Generated
files stay in a dedicated project directory; the skill never deploys, publishes,
submits forms, reads secrets, or mutates production systems without separate
exact authorization.

## Validation and evidence

Validation reports only measured output and records blockers for unavailable
checks. Lighthouse is lab evidence, automated accessibility checks are not WCAG
certification, and valid structured data is not a promise of a search feature.

## Provenance and license

The technical baseline comes from `aleksandr-alhoff/seo-landing` at the exact
commit recorded in [UPSTREAM.md](UPSTREAM.md). The upstream MIT license is
retained in [LICENSE](LICENSE); the Codex-facing documentation and safety
adaptations in this package are local to this repository.

Security reporting guidance is in [SECURITY.md](SECURITY.md).
