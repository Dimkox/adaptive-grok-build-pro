# Documentation research — local investor demo

Route: `befa117340b9`
Role: `docs_researcher` (read-only)
Repository state inspected: `mvp/investor-ready` at `d4cc01fe8d6ec82cce93106191774fc32e8dbb46`

## Finding

The current product has real, local, dependency-free Python capabilities for route construction, typed change-spec inspection, executable-architecture summaries, governance summaries, and local verification. It does **not** yet contain a browser application or `scripts/grok_demo.py`. Documentation must therefore describe the proposed browser feature as available only after its implementation and verification; it must not present this analysis or the change package as a shipped demo.

The documentation has a strong existing authority distinction to preserve:

- `python3 scripts/grok_verify.py --mode pr` plus route-selected reviews are local, fingerprint-bound **preflight evidence**.
- The deployed Trust CI service, when actually deployed for an exact pull-request head, is the system that can publish the GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run.
- A local receipt, route, fixture, architecture/governance summary, browser badge, or delegated local grant never creates, replaces, or proves that external check, signed approvals, merge eligibility, merge, deployment, or release publication.

## Truthful product claims for the demo

These claims are supported by the existing source and are appropriate once the proposed adapter displays their output with provenance.

| Dashboard area | Safe claim | Evidence/source | Required qualifier |
| --- | --- | --- | --- |
| Route | “This local preview uses Adaptive Grok Build Pro’s repository routing logic to classify the entered demo prompt and select skills/roles.” | `.grok-stack/adaptive_grok/router.py`; `scripts/grok_route.py --show --json` | It is a preview only; it must not activate or write a route. |
| Typed intent | “This panel validates/summarizes the bundled typed change specification and its criterion coverage.” | `.grok-stack/adaptive_grok/spec.py`; `scripts/grok_spec.py summary|coverage` | Call a prompt-generated spec a **draft** and show `design required` for placeholders/missing criteria. |
| Architecture | “This checkout’s canonical executable architecture currently summarizes to 14 nodes, 14 edges, 5 contracts, 7 trust domains, and 17 rules.” | `python3 scripts/grok_architecture.py summary --json` in the inspected checkout | Label it `Live repository model` and show its digest/time; values can change with the checkout. It is source-model evidence, not deployment proof. |
| Governance | “This checkout’s canonical governance summary currently passes with no active/candidate rules and no open debt.” | `python3 scripts/grok_governance.py summary --now 2026-08-30T00:00:00Z --json` | Show the evaluation time/digest. Markdown projections and a pass result are not external authority. |
| Verification | “This panel summarizes bundled sample local evidence/check results.” | Bundled fixture validated through product summary logic | Persistently label `Sample evidence`; specify the fixture identity and digest. Do not call it live CI. |
| Product boundary | “The demo is a loopback, read-only product tour: no account, database, provider execution, GitHub call, or external write is needed.” | Proposed standard-library adapter boundary and task scope | State this as a property verified by tests after implementation, not as a claim about deployed service availability. |

The exact route currently loaded by the workspace (`befa117340b9`) is a useful development example, but it should not be marketed as a universal product result: its route is `architecture`, medium risk, `frontend`/`api`, and requires the named design gate. A bundled primary scenario and a contrasting low-risk scenario should be used instead, with the inputs and output provenance visible.

## Prohibited or misleading language

Do not use any of the following on a green local/sample panel, in the demo guide, or in release notes unless the separately named external condition has actually been proved for the exact PR head:

- “Verified by Trust CI”, “Trust CI passed”, “merge eligible”, “approved”, “production verified”, “deployed”, “protected main”, “live GitHub check”, or “autonomous release”.
- The exact check name `adaptive-trust-ci/verified@<policy-sha12>` as the dashboard’s own status badge. It may appear only in an explanatory trust-boundary sentence saying that it is an external, App-owned exact-SHA check, not this demo result.
- “Real-time”, “live CI”, or “current PR” for a bundled fixture. Use `Bundled sample`, `Local preview`, `Live repository model`, or `Not run` instead.
- Any implication that the route preview created a change package, selected/running agents, recorded a receipt, ran the verifier, pushed code, opened a PR, signed an approval, or contacted GitHub/Trust CI.

Recommended persistent wording:

> Local demo only — route and repository-model summaries are read from this checkout; verification results are bundled sample evidence. Local evidence is not merge authority. An App-owned exact-SHA Trust CI check and required external approvals remain separate operator-controlled steps.

For a prompt preview, use:

> Draft route/spec preview — verification not run.

## Required user-facing command contract

`scripts/grok_demo.py` does not exist at the inspected baseline. The implementer should make the following the documented contract, then run it during verification before documentation states it works:

```bash
cd /path/to/adaptive-grok-build-pro
python3 scripts/grok_demo.py --open
```

The command should require only the repository’s documented Python baseline (currently Python 3.10 or newer), bind to `127.0.0.1`, print the exact local URL, and perform no dependency installation, network access, credential lookup, or repository mutation. If `--open` cannot open a browser, it should still print the URL. The documentation must give the no-browser alternative, using the final implemented default/port exactly; the proposed default is:

```bash
python3 scripts/grok_demo.py
# Open the printed http://127.0.0.1:8765/ URL in a browser.
```

Document `Ctrl-C` as the shutdown action and an occupied-port remedy only if the shipped CLI supports an explicit `--port`, e.g.:

```bash
python3 scripts/grok_demo.py --port 8766
```

Do not document `grok_route.py <task>` or `grok_verify.py` as part of the browser demo: their normal CLI paths can write active route state or record local receipts. The dashboard should use pure read/compute adapters, while the docs may offer the existing read-only inspection commands separately for developers:

```bash
python3 scripts/grok_route.py --show --json
python3 scripts/grok_architecture.py summary --json
python3 scripts/grok_governance.py summary --json
python3 scripts/grok_verify.py --mode pr
```

The final command is explicitly a local preflight, not a prerequisite that the demo runs on behalf of the user.

## Documentation changes required after implementation

### README.md

1. In **Current state**, add a narrowly scoped bullet only after implementation/testing: a local browser demo exists, starts with the documented command, binds loopback, and shows repository-derived routing/spec/architecture/governance plus bundled sample verification evidence. Include the persistent local/sample versus external-authority disclaimer in this bullet or link to the demo guide.
2. Add a concise **Local browser demo** section before the generic scripts inventory: prerequisites, the exact command above, printed URL, `Ctrl-C`, offline/read-only/no-secret statement, and the four provenance labels (`bundled_sample`, `computed_preview`, `live_repository`, `not_run`) as implemented.
3. Add actual shipped paths to **Map** and the **Scripts** table: at minimum `scripts/grok_demo.py`, the static/sample directory, and `engineering/contracts/openapi/adaptive-demo.v1.json`, if those are the implemented paths. Do not list speculative paths.
4. Preserve the README K16 complete-graph invariant. If browser and demo-server are introduced as new core graph nodes, update the graph to a complete K18 graph (153 `---` edges; 33 more than K16) and its inventory explanation. If the graph remains intentionally about the pre-existing core inventory, state the demo’s connection in the new demo section instead of silently making the graph claim cover an unlisted core node.
5. Keep product identity tied to `VERSION`; do not call this feature published or change the stated published release merely because it is in a local branch/package.

### QUICKSTART.md

Add a top-level **Try the local browser demo** step after tool checking and before installer/workflow instructions:

```bash
cd /path/to/adaptive-grok-build-pro
python3 scripts/grok_demo.py --open
```

It must say: Python-only/no install/build; loopback URL; local static/sample data plus read-only checkout summaries; no external requests/writes; and `Ctrl-C` to stop. Link to a concise `docs/demo.md` or equivalent only if it is actually added. Keep the existing PR-only and exact-SHA merge-authority language unchanged; add the same sample/evidence disclaimer immediately beside the demo instructions.

### Change release note (`release.md`) and changelog

Populate this change’s `release.md` with a local-rollout plan, not a deployment claim:

- **Delivery:** packaged/source checkout contains the local demo; operator runs the documented command on loopback.
- **Feature flags:** none; the feature is local and opt-in by launching the command.
- **Metrics/alerts:** none; telemetry is intentionally absent. Observable local signals are startup URL, bounded API error states, and automated test/verification results.
- **Go/no-go:** tests and `python3 scripts/grok_verify.py --mode pr` pass on the final fingerprint, route-selected independent reviews are fresh, fixtures/provenance labels are present, and no external action has been taken.
- **Rollback:** stop the process; remove/revert the feature in a normal PR if needed. This does not roll back a deployed authority plane because the feature neither deploys nor mutates it.

If and only if a new version is intentionally created, add a `CHANGELOG.md` entry that says “introduced a local, loopback browser demo” and repeats that its verification card is bundled/local evidence, not the App-owned Trust CI check. Do not label a local ZIP as a published GitHub Release, and do not claim a new `VERSION` before that version is actually chosen and propagated through the README/package artifacts.

## Documentation acceptance checklist

- [ ] Startup command, host, URL/default port, shutdown, and port override match the implemented CLI and a smoke test.
- [ ] Every panel visibly identifies source/provenance; sample verification cannot be mistaken for a live check.
- [ ] README and QUICKSTART use `preflight evidence` for local verification and reserve App-owned exact-SHA language for the external service.
- [ ] No version, release, deployment, merge, approval, or Trust CI status is invented from a local checkout.
- [ ] README map/stack graph either includes the new core nodes with all required edges or expressly leaves the graph inventory scoped and documents the demo elsewhere.
- [ ] The release note describes opt-in local use, no telemetry, no external writes, and reversible rollback.
