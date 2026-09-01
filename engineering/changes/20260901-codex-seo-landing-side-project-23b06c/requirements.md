# Requirements — Codex SEO landing side project

## Acceptance criteria

- [x] Given the local skill package, when Codex validation runs, then it exits zero and UI metadata identifies `$seo-landing`.
- [x] Given the skill contract, when its sections are parsed, then generate, audit-only, and fix-existing have separate structural boundaries.
- [x] Given audit-only mode, when its section is inspected, then it explicitly forbids writes and contains no positive write/create/modify instruction.
- [x] Given generate or fix-existing sections, then their HTML stop point precedes validation and final reporting.
- [x] Given imported upstream content, provenance contains URL, exact commit, import date, MIT notice, local Codex docs, and adaptations.
- [x] Given no production origin, the showcase has `noindex, nofollow`, no canonical, no form, and no external runtime resource.
- [x] Given 320/768/1280/1920 viewports and reduced-motion, the versioned runner proves no overflow, auto scrolling, and a visible first-Tab skip link.
- [ ] Given the final tree, when focused tests and `grok_verify.py --mode pr` run, then all selected checks pass.

## Failure and edge cases

- Missing domain or keywords stop before project creation; missing verified claims, legal copy, endpoint, or asset rights block only the element that requires them. None are invented.
- Retrieved page content and upstream text are untrusted data, not executable instructions.
- Unavailable audit or validation tools are reported as blockers rather than fabricated scores.
- A production URL is not inferred; indexing remains disabled until supplied and verified.

## Non-functional requirements

- Security: context-encode generated values, allow-list URL schemes and structured identifiers, never read secrets, and require separate authority for external writes.
- Reliability: preserve unrelated files in fix-existing mode and keep audit-only strictly read-only.
- Performance: no framework or third-party first-load request; semantic static HTML and local CSS.
- Observability: record exact commands, exit codes, review reports, and fingerprint-bound verification receipts.
