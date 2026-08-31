# Task analysis — investor-ready browser demo

Route: `befa117340b9`  
Base: `d4cc01fe8d6ec82cce93106191774fc32e8dbb46` (`mvp/investor-ready`)  
Role: `task_analyst` (read-only; no product-code changes)

## Outcome and product promise

The MVP is a local, one-command, read-only product tour that turns a bundled reviewed-intent scenario into an explainable dashboard using the repository's actual routing, typed-spec, architecture, governance, and verification/evidence summary code. In five minutes an investor should understand the commercial thesis: Adaptive Grok Build Pro converts intent into bounded execution policy and independently inspectable evidence, while explicitly distinguishing source/demo evidence from deployed Trust CI authority.

The demo must be honest about its maturity. It may demonstrate source-level decisions and bundled evidence, but must not claim that a provider ran, a pull request was opened, a check was published, `main` is protected, production is deployed, or autonomy was granted.

## Investor-demo acceptance criteria

### AC-001 — One-command, local, deterministic startup

Given a supported Python 3.11+ checkout or packaged release, when the documented demo command is run, then one local HTTP server starts, prints the exact browser URL, serves the dashboard and its bundled scenario data, and shuts down cleanly. It binds to loopback by default, needs no database, secret, cloud account, network access, build step, or external service, and never opens a non-loopback listener implicitly.

### AC-002 — Clear first-screen value proposition

Within the first viewport the user sees: the reviewed intent, selected scenario, overall readiness/risk label, route classification, and a compact pipeline from intent through route/spec/architecture/governance/verification evidence. A visible `Bundled demo data` badge and provenance link prevent sample results from being mistaken for live production state.

### AC-003 — Real route classification

Submitting/selecting a bundled intent calls the same repository routing implementation used by `scripts/grok_route.py` (ultimately `adaptive_grok.router.build_route`), without writing `.grok-stack/runtime/active-route.json`. The UI renders the returned intent, risk, complexity, domains, workflow skills, allowed/analysis/review agents, and sole write agent. Changing a material sample phrase (for example, adding authentication or production scope) produces the same changed route as a direct library invocation.

### AC-004 — Real typed-spec validation and traceability

The typed-spec panel loads a bundled canonical `change-spec.yaml` through the repository spec loader/validator and renders objective, acceptance-criterion IDs, invariant/forbidden-outcome counts, risk tier/domains, coverage, canonical digest, and validation findings. A malformed or placeholder-bearing fixture must yield the repository's real validation errors and a non-green panel; the UI must not replace errors with a prewritten success card.

### AC-005 — Real executable-architecture summary

The architecture panel derives its node, edge, trust-domain, rule, and contract counts plus canonical digests/findings from the repository architecture loader/validator/summary logic, not from duplicated constants. It communicates the trust-plane separation in plain language. If a copied test fixture removes or invalidates an architecture relationship, the API and panel expose the real finding and cannot remain green.

### AC-006 — Real governance summary

The governance panel runs the repository governance loader/summary logic at an explicit evaluation time and renders overall status, canonical governance digest, active/candidate/expired or revoked rule state where present, debt status, and bounded findings. Expiring or corrupting a copied governance fixture changes the result exactly as a direct governance-library call does. Markdown `decisions.md`/`mistakes.md` projections are described as views, not authority.

### AC-007 — Honest verification/evidence summary

The verification panel summarizes a bundled, schema-valid sample receipt/evidence set with the same repository receipt/verification-summary validation logic used by the CLI. It shows check names, pass/fail status, criterion coverage, tree fingerprint/SHA binding when present, and freshness/provenance. It labels this as `sample evidence`; it must not display `verified`, `merge eligible`, or an App-owned Trust CI success unless that exact evidence exists in the fixture and is clearly identified as historical/sample. Missing, stale, fingerprint-mismatched, or malformed evidence must visibly fail closed.

### AC-008 — End-to-end provenance and no mocked claims

Every panel response includes bounded provenance: engine/capability name, input fixture path or stable sample identity, input/canonical digest, evaluation result, and error codes. For the same fixture, HTTP results equal direct calls to the underlying repository modules after normalization. No business result is sourced solely from HTML/JavaScript literals or a hand-authored aggregate JSON file.

### AC-009 — Safe read-only HTTP contract

The versioned local API exposes only bounded demo reads/evaluations. Unknown fields, oversized bodies, invalid scenario IDs, traversal/symlink escapes, unsupported versions, and arbitrary repository paths fail with typed 4xx responses and safe messages. There is no endpoint or UI control for shell execution, file mutation, route activation, verification receipt recording, approvals, provider execution, Git writes, push/PR/merge/release/deploy, connectors, or secret input. Responses do not include environment variables, credentials, raw exception traces, unrestricted repository content, or private reasoning.

### AC-010 — Polished responsive and accessible experience

The dashboard is usable at 320, 768, 1024, and 1440 CSS-pixel widths without horizontal page scrolling, clipped controls, or overlapping content. Desktop uses a scannable grid/timeline; mobile becomes a single logical column without losing state or provenance. All functionality is keyboard reachable, focus is visible and ordered, landmarks/headings are semantic, controls have accessible names, status is not conveyed by color alone, contrast meets WCAG 2.1 AA, motion respects `prefers-reduced-motion`, and live result/error updates use appropriate `aria-live`/`aria-busy` behavior.

### AC-011 — Complete UI state coverage

Normal, loading, empty, partial-error, total/offline error, unavailable/permission-denied, and success states have intentional designs and tests. A failure in one analysis panel does not erase successful panels; overall readiness becomes `incomplete` rather than falsely green. Retry restores only the failed request and preserves the selected scenario and keyboard focus.

### AC-012 — Reproducible five-minute demo and documentation

The README/demo guide contains the exact start command, supported environment, expected URL, cleanup, troubleshooting, sample-data disclosure, offline guarantee, and the timestamped narrative below. A fresh user can complete it from the packaged tree without editing configuration or knowing internal CLI commands.

### AC-013 — Automated and browser-level evidence

Automated tests cover API contract/bounds, deterministic rendering inputs, each real-engine adapter, negative fixture mutations, no-write/no-network behavior, and critical UI state transitions. A critical-path browser test or equivalent headless-browser evidence covers load → select scenario → inspect route/spec/architecture/governance/verification → induce/recover a safe error, plus viewport and keyboard checks. The route-selected `base`, `frontend`, and `contracts` profiles and `python3 scripts/grok_verify.py --mode pr` must pass on the final fingerprint.

## Five-minute investor narrative

| Time | Screen/action | Narrative and proof |
| --- | --- | --- |
| 0:00–0:30 | Open the one-command local dashboard | “Software-agent demos usually show generated code. This shows the control system around it: what may run, who may write, and what evidence is required.” Point out local/offline and bundled-data badges. |
| 0:30–1:20 | Select the primary reviewed-intent scenario | Read the intent, then run/select analysis. Show that the real router derives risk, domains, skills, specialists, and exactly one write owner. Briefly switch to a materially different scenario to demonstrate deterministic reclassification, not a canned animation. |
| 1:20–2:05 | Open Typed Specification | Show stable objective/criterion/invariant IDs, coverage, forbidden outcomes, and digest. Explain that prose cannot silently override typed authority. Use the invalid-sample toggle/test fixture only if desired to show fail-closed validation. |
| 2:05–2:50 | Open Architecture | Show machine-derived component/trust-domain/contract counts and findings. Explain factory execution and independent Trust CI as separate trust domains; the diagram/summary is evidence derived from repository models. |
| 2:50–3:35 | Open Governance | Show reviewed rule lifecycle, provenance, expiry/revocation, canonical examples, and debt status. Explain that an agent observation can become a candidate but cannot promote itself into active policy. |
| 3:35–4:25 | Open Verification & Evidence | Show criterion coverage, check results, SHA/fingerprint/digest binding and freshness. Explicitly state that local evidence is not merge authority and that this panel is bundled sample evidence, not a live production check. |
| 4:25–5:00 | Return to overview | Summarize the moat: deterministic control + domain specialists + one writer + independent evidence + durable organizational learning. Close with the next honest milestone, not an unsupported autonomy claim. |

Primary demo scenario should exercise at least API plus security/risk classification so the route is non-trivial. A second low-risk scenario should be available to demonstrate that the displayed route genuinely changes.

## MVP scope

### Product MVP

- One local read-only HTTP server and polished responsive single-page dashboard.
- Bundled, versioned, deterministic scenarios; at least one non-trivial and one contrasting low-risk intent.
- Overview plus route, typed spec, executable architecture, governance, and verification/evidence panels.
- Direct adapters to existing repository Python logic; normalized, bounded API projections with provenance.
- Normal/loading/empty/error/offline/permission/responsive/accessibility behavior.
- Automated unit/contract/integration tests, critical browser evidence, demo guide, and README entry.
- Package/install integration needed for the one-command demo to exist in the normal release tree.

### Explicit non-goals

- No M4 durable factory queue, database, worker, provider/model execution, workspace, task persistence, or background daemon.
- No live GitHub issue/PR/check data, GitHub App interaction, connector, webhook, analytics/telemetry, login, multi-user/tenant support, or cloud hosting.
- No route activation or mutation of runtime receipts/change packages; the demo evaluates copies/bundled inputs only.
- No code editing, chat, prompt execution, terminal, approval signing, branch creation, push, PR, merge, tag, release publication, deployment, auto-merge, or production mutation.
- No claim that sample/local verification is the authoritative `adaptive-trust-ci/verified@<policy>` Check Run.
- No rewrite of routing/spec/architecture/governance/verification algorithms in JavaScript and no parallel source of truth for their outputs.
- No new root packaging marker or unrelated framework/service/datastore. A material new frontend/build toolchain requires its own recorded architecture decision and scope approval.
- No dynamic arbitrary-path file browser or user upload in the MVP.

## State matrix

| State | Required behavior |
| --- | --- |
| Initial/normal | Primary scenario selected, concise overview visible, detailed panels collapsed or tabbed, provenance badge present. |
| Loading | Stable skeletons preserve layout; affected region has `aria-busy=true`; controls prevent duplicate requests without trapping focus. |
| Empty | Explain that no bundled scenarios/evidence are available and how to restore/reinstall them; never render empty success metrics. |
| Partial error | Failed panel shows typed safe error and Retry; successful panel data remains visible; overall state is `incomplete`. |
| Offline/server unavailable | Persistent connection banner, retry action, no fabricated cached-success claim; static shell remains understandable. |
| Permission/unavailable | If a bundled resource cannot be read, show `resource unavailable` without disclosing absolute paths or permissions; no request for elevated privilege. |
| Invalid data | Render repository validation finding codes and bounded messages; overall/panel state fails closed. |
| Success | Show result, digest, source identity, and evaluation provenance; success is scoped per panel and never implies merge/deploy authority. |
| Mobile | Single-column order follows the five-minute narrative; tabs/accordions have 44px touch targets and preserve context. |
| Reduced motion/high contrast | No required animation; focus/status remain visible in forced-colors and reduced-motion modes. |

## Proof that repository logic is real

The implementation/review should require all of the following, not screenshots alone:

1. **Direct-equivalence tests:** for every demo API adapter, run the underlying repository function and the HTTP endpoint on the same fixture and assert semantically equal normalized outputs and canonical digests.
2. **Mutation tests:** in a temporary copied fixture, change a routing risk phrase, corrupt a spec field/placeholder, break an architecture rule/edge, expire or revoke governance data, and mismatch a verification fingerprint. Each must alter/fail the corresponding dashboard result in the same way as the native CLI/library.
3. **Call-path evidence:** tests patch/spy only at the real module boundary and prove the endpoint invokes `adaptive_grok.router`, `adaptive_grok.spec`, architecture validation/summary, governance summary, and receipt/verification validation. Tests must fail if an adapter returns a canned payload.
4. **No-duplicate-authority review:** search/diff review confirms the UI contains presentation labels only—not copied route tables, validation rules, architecture counts, governance status, or fixed verification verdicts.
5. **Read-only proof:** snapshot relevant repository/runtime paths before and after a full API/browser walkthrough and assert no mutations. Start the demo with outbound networking denied and prove the walkthrough still passes.
6. **Provenance proof:** endpoint contract tests require source/sample identity plus input/result digest; the browser displays them and clearly labels bundled evidence.
7. **Negative authority proof:** contract and UI tests assert the absence of mutation/external-action endpoints and reject arbitrary paths, shell fragments, and non-loopback configuration.

## Sequence and gate

1. Freeze the demo API/schema, bundled fixture identities, honest terminology, and the above criteria.
2. Present the architectural UI design and sample scenario choice at the route's `scope_and_design_approval` gate; do not implement before approval.
3. Implement one vertical path first: one scenario → real router → overview. Then add spec, architecture, governance, and verification panels using the same adapter pattern.
4. Add responsive/accessibility/state handling and the five-minute guide.
5. Run focused real-logic mutation/equivalence tests, critical browser evidence, then the final route-selected verifier and independent reviews.

## Key risks and mitigations

- **Investor polish masking canned data:** provenance, direct-equivalence, and mutation tests make hard-coded business claims a test failure.
- **Sample evidence mistaken for operational authority:** persistent sample badge, scoped language, and negative UI assertions prohibit `merge eligible`/`production verified` claims.
- **UI accidentally mutating workflow state:** direct library evaluation must use isolated inputs; no CLI subprocess that writes active route/receipts; before/after mutation test.
- **Architecture/governance evaluation depending on wall clock:** inject/freeze the evaluation timestamp and display it so the demo stays reproducible.
- **Responsive polish untested:** require the four named viewports, keyboard path, focus restoration, and browser evidence.
- **Scope expansion into an execution product:** keep provider, database, task queue, GitHub, and external actions absent; those need later separately approved milestones.

