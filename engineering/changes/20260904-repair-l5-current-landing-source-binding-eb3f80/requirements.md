# Requirements — Repair L5 current landing source binding

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] **AC-001:** current exact SHA/tree succeeds; old and mixed tuples return
  `409 source_identity` before blob/provider/artifact work.
- [x] **AC-002:** source HTML has one exact `/index.css`, zero inline styles;
  rendered HTML retains it and adds one exact `/content.css` while preserving
  robots, canonical, hreflang, and JSON-LD facts.
- [x] **AC-003:** the candidate Git delta stays exactly `index.html` and
  `content.css`; `index.css` and `.htaccess` retain source mode/object identity.
- [x] **AC-003:** two seals produce identical 20-member ZIP/manifest/sidecar;
  `index.css` occurs once with source provenance and identical source/candidate
  object IDs.
- [x] **AC-004:** the landing OpenAPI remains byte-identical at published
  version `1.0.0` and is explicitly non-deployed/non-authoritative for current
  runtime configuration; a config-neutral successor contract is deferred.
- [x] **AC-005:** published `v2.0.14` bytes and identities are unchanged, and
  provider calls, publisher calls, target writes, and live URLs remain zero.

## Failure and edge cases

- Missing, duplicate, queried, remote, or third stylesheet; any inline style.
- Old SHA, old tree, or a mixed source tuple.
- `index.css` deletion, mode/object drift, candidate provenance, or archive
  omission.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: existing exact-SHA, bounded-write, deterministic
  artifact, and no-external-effect rules already governing L5.
- Canonical-example deviations and evidence: none.
- Intentional debt: a config-neutral successor OpenAPI is separately scoped;
  operational provider, persistence, and publishing remain separate tasks.

## Non-functional requirements

- Security: fail closed on any unrecognized stylesheet surface; provider data
  cannot select HTML, CSS, scripts, paths, or origins.
- Reliability: the exact source epoch moves atomically across renderer and
  service checks; the frozen OpenAPI is never treated as runtime authority.
- Performance: no new process, network call, dependency, or unbounded scan.
- Observability: manifest and API evidence bind source tuple, two-path delta,
  20-member count, provenance, and digests.
