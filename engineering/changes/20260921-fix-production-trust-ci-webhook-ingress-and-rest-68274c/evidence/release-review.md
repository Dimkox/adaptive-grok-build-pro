# Independent release review — prepared ingress operation

Route: `68274cb876e4`. Reviewer: selected `release_reviewer`, independent of `integration_implementer`. Date: 2026-09-21. Repository: `/home/pall/grok-projects/adaptive-grok-build-ci-ingress`; inspected HEAD: `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`.

**Pre-operation recommendation: conditional GO. No blocking release defect remains in the revised frozen candidate.** The earlier hold for inherited systemd drop-ins is resolved at the plan level by the mandatory effective-unit gate reviewed below. This is approval of the bounded operation design, subject to the conditions below. Installation, activation, enforcement, recovery, real GitHub intake, and final delivery have not passed this review as executed outcomes. AC-003 still requires the coordinator's live evidence.

## Reviewed inputs and immutable identity

Read the repository contract, bootstrap and current handoff, active route, typed change specification, brief, test/recovery plans, full [operation plan](../operation-plan.md), [artifact manifest](artifact-manifest.json), [preparation evidence](preparation-verification.json), and [implementation report](implementation-report.md). Inspected all four actual staged resource files. The populated typed acceptance criteria and operation plan supply the operative criteria; the unfilled generated requirements/release headings do not add authority or prove acceptance.

Independently recomputed these SHA-256 values by reading the files; each matched the frozen values:

| Reviewed file | SHA-256 |
| --- | --- |
| `operation-plan.md` | `23c6bd21137951d96a41510dfdb34bed8baef1ee95d4f3e073026ccdc183cb5e` |
| Repository and host-local `artifact-manifest.json` | `b4b45a7c453812942cbc33a2b88239613be7079435a445c9b208ab00f54f714d` |
| `adaptive-trust-ci-webhook-bridge.socket` | `3163be692b5319f13cb165abd46e2186d9ca6deeb7d7ab40a687ef35dd8249d0` |
| `adaptive-trust-ci-webhook-bridge.service` | `d2280ce0802191817da64061005d69b53a165d644b34987eee912d4a502fba6c` |
| `adaptive-trust-ci-webhook-bridge-guard.service` | `60596d1771aed4ee0a9431ead99e7636f98a38aaa1f3ce0a0ab68477e6d3f1a1` |
| `adaptive-trust-ci-webhook-bridge.nft` | `c68534932c19799421c4bd5c0a8fad57deeb3804fcbbd76e918f738f77aa989a` |

The staged files reside under `/home/pall/.cache/agbp-run/issues-wave-20260921/ci-ingress/artifacts/`. The recorded `systemd-analyze verify` and `nft --check` both exited zero without diagnostics. I inspected those recorded results; I did not rerun them or perform host probes, network requests, tests, Docker operations, installation, or activation. Local Git inspection showed only the new change package as untracked; no tracked product modification was present. The operations-only product-verifier exemption in `AGENTS.md` applies to this scope; it does not waive operational evidence.

## Release assessment

The four installed destinations, three unit names, socket enablement link, and dedicated `inet adaptive_trust_ci_webhook_bridge` table are enumerated. The installer pins the manifest and payload hashes, checks unit paths/drop-ins/enablement collisions, rejects changed input-firewall topology, and uses exclusive no-follow creation. Its partial-install cleanup records device/inode ownership before removing its own creations. It neither replaces existing files nor activates a partial installation.

The original exact-unit directory scan could miss dash-prefix/type-wide inherited drop-ins. The revised plan closes that gap before execution: after manager reload and before any unit start, it first requires all three exact unit identities to be loaded, inactive, sourced from their pinned destination fragments, and free of effective `DropInPaths`. Only after those checks does it request command properties. The gate compares the socket address/device, empty extra execution hooks, exact proxy/nft commands, `BindsTo`, required/order edges, and default-dependency settings, admitting only the documented implicit edges and the recorded temporary-mount topology. Empty effective `Wants` and `Upholds` are also mandatory for all three units, so outgoing dependency links cannot silently activate unrelated units. Missing properties, unknown edges, or overrides refuse activation without reading foreign override/environment/credential contents or editing them. It repeats before reactivation. This revision changes no installed artifact or manifest bytes. The gate has not run against installed units; an unexpected platform value must return to review, not be silently allowed.

The guard's nft transaction uses `create table`, so an existing table causes refusal rather than takeover. Every drop rule is limited to IPv4 destination `10.200.200.1`, TCP port `18080`; the exact veth and peer are required. The listener binds that address and `veth-vpn-h`. Guard dependencies and ordering precede both listener owners, and reverse stop ordering is designed to stop proxy and socket before guard table deletion. The proposed guard-stop exercise tests that lifecycle explicitly. Static ordering analysis remains a prediction until the operation records its result.

The existing `wg-vpn-namespace.service` and reciprocal veth pair are prerequisites. The plan requires the namespace already healthy, with its observed oneshot/active/exited state and unchanged addresses, before activation or recovery. An existing namespace failure is a stop condition; the operation does not repair/restart it. Existing API/Tailscale configuration, containers, deployed trust policy, holdout, images, databases, and trust material are outside the mutation boundary.

The byte proxy forwards all API paths available to the admitted peer; it is not an HTTP path filter. The existing Funnel mapping supplies the public `/webhooks/github` restriction, and the unchanged backend retains its authentication/HMAC responsibilities. Public private-path checks therefore remain required. No migration, application upgrade, version bump, release tag, or GitHub Release publication is part of this operation.

## Conditions before the first host write

1. Receive passing selected code, test, and security reviews for these same bytes and command bodies. Any artifact or operational command change returns to the sole writer and requires refreshed relevant verification and independent review.
2. Finish the competing full-verifier/installer CPU reservation before live operation and before any real CI enqueue action, as required by the coordinator's shared-host boundary.
3. Materialize a fresh exact delegated local grant after review reports and the repository tree are frozen. Bind repository, route, change, current HEAD/tree fingerprint, operation-plan/manifest identity, TTL, and every named action/resource needed for installation, daemon reload, start/stop, enable/disable, same-byte reactivation, and owned-resource rollback. The brief records the user's bounded ingress-repair and PR-delivery consent; the grant records that consent without creating wider authority. Do not reuse it after a tree/commit change or expiry.
4. Refresh the plan's preflight immediately before installation and again before activation. Require exact file hashes, absent destination/unit/drop-in/enablement/table names, unchanged firewall topology, healthy namespace and reciprocal interfaces, loopback-only port 18080 with ready status 200, the observed negative-control source/route, and the exact existing Funnel mapping. Refuse a changed prerequisite rather than modifying an existing resource.

## Evidence required to accept the operation

- Install only the four pinned files; verify their installed bytes and ownership/mode. Run the specified syntax checks, reload unit definitions, and require the recorded `effective_unit_gate=pass` before starting anything. Then start the guard, inspect its exact rules, and start the socket. A failed step stops progression. Persistence is enabled only after initial acceptance.
- Record allowed-peer readiness 200, peer and public webhook GET 405, and 404 for every enumerated private public path. Record the socket's exact address/device, all three unit states, only the expected loopback and veth listeners, and unchanged loopback readiness 200.
- Require each expected filter counter to increase during its corresponding bounded probe. Both wrong-interface and correct-interface/wrong-source probes must produce the specified rejection outcome and matching drop-counter increment. A timeout alone does not establish enforcement; public HTTP 000 is inconclusive, not an expected HTTP status.
- Exercise the guard stop, then socket disable. Record both listener owners inactive, socket disabled, dedicated table absent, loopback-only listener and ready 200, bridge connection refusal, and actual public webhook failure. Stop/disable status alone does not prove the network outcomes. A lingering listener or failed dependency propagation rejects the candidate and requires containment before any table removal.
- Confirm the namespace is healthy and all four installed hashes unchanged, repeat the effective-unit gate for all three inactive units, then enable/start only the socket. Repeat the full bounded acceptance and counter checks. This proves only the exercised same-byte reactivation. Cold boot and device-loss/device-return automatic recovery remain untested and must not be claimed.
- If full rollback is chosen, establish both listener owners stopped before guard/table teardown, verify the four installed files still match this operation's owned bytes, and remove only those files and the socket's own enablement. Preserve foreign/changed files and any fail-closed residual table for explicit coordinator handling. Recheck original API readiness and bridge/public failure; never repair by changing the namespace, API, Tailscale, or global firewall.

## Delivery and claim boundary

The coordinator must retain live operation results and final fingerprint-bound local receipts before declaring local completion. This report cannot be used as evidence that activation, packet enforcement, recovery, or AC-003 already succeeded. Full file removal is optional rollback, not an exercised result unless actually selected and observed.

A 405 GET establishes reachability only. A separately granted, current-head PR `ready_for_review` action may supply a real supported GitHub event after connectivity acceptance and release of the CPU reservation. Correlate real delivery/API/job/check identifiers where authorized readbacks expose them; otherwise mark that evidence unobserved. Never infer intake, queue membership, job success, or merge eligibility from a 405.

Merge authority remains the external App-owned exact-head policy-epoch Check Run, currently `adaptive-trust-ci/verified@06ecf1c875bc` from App ID `4694114`, together with any required external signed scopes. Neither this report nor a delegated local grant replaces it. Refresh exact head/base/policy requirements before PR delivery or issue closure.
