# Requirements — Fix issue157 repository language classifier: bounded Swift and other language signal detection, symlink-safe manifests, truncation and unknown reporting without suppressing detected signals.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- AC-001: recognized extensions and weak manifest evidence survive disclosure even when another language is confirmed.
- AC-002: canonical Swift metadata or nonempty readable Swift source confirms Swift within all scan/read bounds; symlinks and nonregular paths are refused.
- AC-003: each budget and unreadable boundary discloses incomplete status; exact-bound inventory remains complete.
- AC-004: readable supported canonical manifests, Bitrix modules and downstream routing retain compatible results; unknown/case/vendor/empty cases are explicit.

## Failure and edge cases

- File/directory symlink swaps before open, file mutation during read, FIFO manifests, unsupported/oversized/weak metadata, nonmapping Node scripts and irrelevant source files under contract directories.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: repository AGENTS.md startup, isolated writer, bounded evidence and PR-only delivery contract.
- Canonical-example deviations and evidence: no architecture component or external contract change.
- Intentional debt created, repaid, or accepted: full language/compiler validation remains out of scope; extension and textual metadata detection is explicitly advisory.

## Non-functional requirements

- Security: descriptor-rooted NOFOLLOW/NONBLOCK reads of regular files; identity verified before/after reads. Never execute manifests.
- Reliability: incomplete inventory cannot silently claim completeness. Unknown language classification is distinct from complete filesystem enumeration.
- Performance: explicit global and per-file bounds; deterministic sorted complete directories and canonical bounded root probes.
- Observability: additive language_scan counters/reasons and existing signals carry disclosure into persisted route profiles.
