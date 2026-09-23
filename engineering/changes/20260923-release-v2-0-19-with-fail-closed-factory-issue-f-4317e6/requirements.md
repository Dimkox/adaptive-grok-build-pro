# Requirements — Release v2.0.19 with fail-closed factory issue fixes

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] #35-related repository-owned guard: every selected existing `.sh` file is parsed by its
  own `bash -n <path>` process, empty selection fails closed, and a syntax error in a later file
  names that file. This does not claim an external `verify:deploy` owner exists.
- [x] #39-related repository-owned guard: fast lint uses only changed owned Python files;
  PR/release lint uses tracked plus changed owned files, never `.` or unbounded scratch/generated
  paths, and reports its scope. The filed ESLint/JavaScript report remains external through #186.
- [x] #48-related repository-owned Trust CI smoke guard: health/readiness/metrics/Compose
  observations are captured, non-empty, and matched from captured text; required tool discovery
  and unavailable/empty outputs fail closed. The external guard's remaining traps remain linked
  through #186.
- [ ] #73: new grants use `grant_binding_digest`, legacy `tree_fingerprint` reads remain valid,
  conflicting dual fields fail closed, and historical probe files remain byte-identical.
- [ ] #167: an unambiguous landing-only change can use the explicit focused mode; mixed, unknown,
  unsafe, or runtime/configuration changes fail closed to full PR verification.
- [ ] Release metadata, README current-state text, and version identity match only the final
  verified candidate tree.
- [x] #36 is not represented as a fabricated product fix; its no-owner disposition links to #186.

## Failure and edge cases

- Empty or unavailable command output must never yield PASS.
- A new commit or evidence file invalidates prior fingerprint-bound local evidence.
- The external App-owned exact-SHA Trust CI check remains the merge authority.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: no private key/credential access; local grant bindings remain exact and fail closed.
- Reliability: failure paths retain real command status and identify the checked scope/path.
- Performance: avoid scanning unrelated worktrees and scratch trees; do not weaken release-wide
  verification.
- Observability: check summaries identify scope, selected files, and empty/unavailable evidence.
