# Requirements — Add new browser UI functionality to Adaptive Grok Build Pro: create a one-command local HTTP demo application with a polished responsive dashboard using real repository routing, typed-spec, architecture, governance, and verification-summary logic against bundled sample data; add automated tests and user documentation. Do not perform external writes.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] AC-001: `python3 scripts/grok_demo.py --open` starts the loopback dashboard without dependency installation or a frontend build.
- [ ] AC-002: sample and prompt previews execute real router/spec logic; architecture/governance summaries use canonical loaders.
- [ ] AC-003: every panel labels bundled, computed, or live provenance; preview verification is `not_run`.
- [ ] AC-004: the closed API rejects unknown fields, traversal, oversized/invalid input, hostile Host/Origin, and unsupported methods.
- [ ] AC-005: HTTP traffic performs no repository/runtime mutation, shell/verifier invocation, network call, or external write.
- [ ] AC-006: UI covers loading, validation, partial failure, stale/offline, mobile, keyboard, reduced-motion, and high-contrast states.
- [ ] AC-007: tests prove direct equivalence, negative mutation, API security, no-write behavior, package inclusion, and safe DOM rendering.
- [ ] AC-008: product docs provide a truthful reproducible five-minute investor demo.

## Failure and edge cases

- Invalid fixtures fail before listening; architecture/governance failure degrades only that panel without fabricated zeros.
- Port conflict exits with a `--port` hint and never falls back to a non-loopback interface.
- Stopped server retains only in-memory last-good data explicitly labelled stale.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: strict same-origin loopback, Host/Origin checks, CSP, no CORS, static allowlist, text-only DOM.
- Reliability: deterministic fixtures/injected time, bounded handling, fail-closed malformed evidence.
- Performance: no remote assets or package install; bounded JSON.
- Observability: visible source/digest/time/status and stable safe errors without traceback.
