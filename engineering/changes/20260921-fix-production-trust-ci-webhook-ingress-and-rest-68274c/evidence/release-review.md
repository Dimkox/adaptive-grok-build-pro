# Independent release review — stopped installation continuation

Route: `68274cb876e4`. Reviewer: selected `release_reviewer`, independent of `integration_implementer`. Date: 2026-09-21. Repository: `/home/pall/grok-projects/adaptive-grok-build-ci-ingress`; inspected HEAD: `4d3e1c059448fa3dc106602465335de6b3cbb07e`, with the revised operation plan below pending its new commit/grant binding.

**Continuation recommendation: conditional GO. No blocking release defect remains in the revised frozen candidate.** Exclusive installation and syntax/reload have recorded success; the previous pre-start gate safely refused before activation. Resume at the corrected read-only gate only after all reviews rebind and a fresh exact grant covers the newly committed state. Do not reinstall or overwrite the earlier results. Activation, enforcement, recovery, real GitHub intake, and final delivery remain unexecuted; AC-003 still requires the coordinator's live evidence.

## Reviewed inputs and immutable identity

Read the repository contract, bootstrap and current handoff, active route, typed change specification, brief, test/recovery plans, full [operation plan](../operation-plan.md), [artifact manifest](artifact-manifest.json), [preparation evidence](preparation-verification.json), and [implementation report](implementation-report.md). Inspected all four actual staged resource files. The populated typed acceptance criteria and operation plan supply the operative criteria; the unfilled generated requirements/release headings do not add authority or prove acceptance.

Independently recomputed these SHA-256 values by reading the files; each matched the frozen values:

| Reviewed file | SHA-256 |
| --- | --- |
| `operation-plan.md` | `7b97645e9852ad772d60cf009b0636fcc6f9b7fc7c6f9558281b1b848bc281a3` |
| Repository and host-local `artifact-manifest.json` | `b4b45a7c453812942cbc33a2b88239613be7079435a445c9b208ab00f54f714d` |
| `adaptive-trust-ci-webhook-bridge.socket` | `3163be692b5319f13cb165abd46e2186d9ca6deeb7d7ab40a687ef35dd8249d0` |
| `adaptive-trust-ci-webhook-bridge.service` | `d2280ce0802191817da64061005d69b53a165d644b34987eee912d4a502fba6c` |
| `adaptive-trust-ci-webhook-bridge-guard.service` | `60596d1771aed4ee0a9431ead99e7636f98a38aaa1f3ce0a0ab68477e6d3f1a1` |
| `adaptive-trust-ci-webhook-bridge.nft` | `c68534932c19799421c4bd5c0a8fad57deeb3804fcbbd76e918f738f77aa989a` |

The staged files reside under `/home/pall/.cache/agbp-run/issues-wave-20260921/ci-ingress/artifacts/`. I rechecked their hashes, the revised plan, and both manifest copies. The recorded `systemd-analyze verify` and `nft --check` exited zero without diagnostics. I inspected recorded results only; I did not rerun checks or perform host probes, network requests, tests, Docker operations, installation, or activation. The inspected revision is confined to the operation plan/evidence documents. The operations-only product-verifier exemption in `AGENTS.md` applies to this scope; it does not waive operational evidence.

## Executed boundary and preserved refusal

Directly inspected these host-local results under `/home/pall/.cache/agbp-run/issues-wave-20260921/ci-ingress/`:

| Result | Observed outcome | SHA-256 |
| --- | --- | --- |
| `operation-result-01.json` | 08:10:45 UTC: exclusive four-file installation, exit 0, `activated=false` | `beb36a4f7bf7380160a16650b674cb5baecff1d39266a9b67457e09b9fffcdcd` |
| `operation-result-02.json` | 08:10:46 UTC: syntax/reload block, exit 0, no diagnostics | `57a35cba7a9ddc25c565c51ca2fbf439fa87372b9581843772eb68a095807294` |
| `operation-result-03.json` | 08:10:46 UTC: three loaded/inactive identities with exact fragments and empty drop-ins; gate exit 1 before any start because an effective property was omitted | `089408e8e4710908c1f5a8a675b62295717e05615e54f62e968b279ad102a05a` |

The original preparation record remains historical: its installation/reload entries were unexecuted at its own timestamp. It must not override these later results or be relabeled as activation evidence. The implementation report records a subsequent corrected-gate read-only diagnostic passing with exit 0 in 0.471165461 seconds. That diagnostic supports the gate correction only; it does not substitute for the coordinator's freshly bound pre-start execution or for packet/lifecycle acceptance.

## Release assessment

The four installed destinations, three unit names, socket enablement link, and dedicated `inet adaptive_trust_ci_webhook_bridge` table remain the entire mutation scope. The completed exclusive installation is preserved. The continuation verifies the pinned manifest and all four installed hashes/byte counts through no-follow descriptors, regular-file type, `root:root` ownership, and mode `0644`. It then requires all three units inactive, socket disabled, services static, no bridge enablement/dependency links, and no owned nft table. This is a continuation of the existing stopped installation, not a collision override or a second installation.

Inherited drop-ins remain forbidden: all three loaded identities must have exact installed fragments and empty effective `DropInPaths` before command reads. The corrected check uses named typed D-Bus properties for command/dependency arrays, listener tuples, and booleans; successful reads with the expected signatures are required. It does not infer empty commands from omitted text output or split human-formatted escaped device names. Main command executable/argument vectors, error-ignore flags, empty extra execution hooks, address/device, `BindsTo`, `Requires`, `After`, and default-dependency properties are checked against exact expectations. An unknown property value returns to review without reading or changing foreign configuration.

The only service `Wants` exception is the measured implicit `tmp.mount` edge from `PrivateTmp=true`; the socket still requires no `Wants`, and all three units require no `Upholds`. This exception is conditional on the target remaining `not-found`, inactive, non-transient, with no fragment/drop-ins or activation dependencies, and both temporary paths resolving to the root mount. It therefore does not authorize creating, mounting, changing, or starting an existing mount definition. An actual `tmp.mount` definition or any other activation edge refuses continuation. The revised dependency sets and typed reads correct the earlier gate assumptions while preserving the operational resource boundary. The same complete gate repeats after stop/disable and before reactivation.

The guard's nft transaction uses `create table`, so an existing table causes refusal rather than takeover. Every drop rule is limited to IPv4 destination `10.200.200.1`, TCP port `18080`; the exact veth and peer are required. The listener binds that address and `veth-vpn-h`. Guard dependencies and ordering precede both listener owners, and reverse stop ordering is designed to stop proxy and socket before guard table deletion. The proposed guard-stop exercise tests that lifecycle explicitly. Static ordering analysis remains a prediction until the operation records its result.

The existing `wg-vpn-namespace.service` and reciprocal veth pair are prerequisites. The plan requires the namespace already healthy, with its observed oneshot/active/exited state and unchanged addresses, before activation or recovery. An existing namespace failure is a stop condition; the operation does not repair/restart it. Existing API/Tailscale configuration, containers, deployed trust policy, holdout, images, databases, and trust material are outside the mutation boundary.

The byte proxy forwards all API paths available to the admitted peer; it is not an HTTP path filter. The existing Funnel mapping supplies the public `/webhooks/github` restriction, and the unchanged backend retains its authentication/HMAC responsibilities. Public private-path checks therefore remain required. No migration, application upgrade, version bump, release tag, or GitHub Release publication is part of this operation.

## Conditions before resumed activation

1. Receive passing selected code, test, and security reviews for these same bytes and command bodies. Any artifact or operational command change returns to the sole writer and requires refreshed relevant verification and independent review.
2. Leave the real PR event/CI enqueue deferred until the coordinator confirms release of the current full-verification CPU lane. Connectivity or an estimated finish time does not release that reservation.
3. Refresh the operation freeze with the final plan and all four current report digests, commit the handoff, then materialize a fresh exact delegated local grant. The existing freeze/grant belongs to the earlier plan and cannot authorize this changed command. Bind repository, route, change, current HEAD/tree fingerprint, operation-plan/manifest identity, TTL, and the remaining named actions/resources for start/stop, enable/disable, same-byte reactivation, and owned-resource rollback/its reload. The brief records bounded ingress-repair and PR-delivery consent; the grant records it without creating wider authority. Do not reuse a grant after a tree/commit change or expiry.
4. Refresh the unchanged healthy namespace/topology, loopback readiness, source/route, and existing Funnel mapping immediately before activation. Resume at the corrected read-only gate: its installed-file/identity checks replace the initial absent-destination requirement for this continuation. Require no bridge enablement links or filter table and exact effective configuration. Preserve results 01–03; do not rerun installation or the completed syntax/reload block merely to resume. Refuse a changed prerequisite rather than modifying an existing resource.

## Evidence required to accept the operation

- After the fresh binding, record a new `effective_unit_gate=pass` from the complete continuation gate before starting anything. Then start the guard, inspect its exact rules, and start the socket. A failed step stops progression. Persistence is enabled only after initial acceptance. The writer's diagnostic and old successful installation/reload do not replace this new gate result.
- Record allowed-peer readiness 200, peer and public webhook GET 405, and 404 for every enumerated private public path. Record the socket's exact address/device, all three unit states, only the expected loopback and veth listeners, and unchanged loopback readiness 200.
- Require each expected filter counter to increase during its corresponding bounded probe. Both wrong-interface and correct-interface/wrong-source probes must produce the specified rejection outcome and matching drop-counter increment. A timeout alone does not establish enforcement; public HTTP 000 is inconclusive, not an expected HTTP status.
- Exercise the guard stop, then socket disable. Record both listener owners inactive, socket disabled, dedicated table absent, loopback-only listener and ready 200, bridge connection refusal, and actual public webhook failure. Stop/disable status alone does not prove the network outcomes. A lingering listener or failed dependency propagation rejects the candidate and requires containment before any table removal.
- Confirm the namespace is healthy and all four installed hashes unchanged, repeat the effective-unit gate for all three inactive units, then enable/start only the socket. Repeat the full bounded acceptance and counter checks. This proves only the exercised same-byte reactivation. Cold boot and device-loss/device-return automatic recovery remain untested and must not be claimed.
- If full rollback is chosen, establish both listener owners stopped before guard/table teardown, verify the four installed files still match this operation's owned bytes, and remove only those files and the socket's own enablement. Preserve foreign/changed files and any fail-closed residual table for explicit coordinator handling. Recheck original API readiness and bridge/public failure; never repair by changing the namespace, API, Tailscale, or global firewall.

## Delivery and claim boundary

The coordinator must retain live operation results and final fingerprint-bound local receipts before declaring local completion. This report cannot be used as evidence that activation, packet enforcement, recovery, or AC-003 already succeeded. Full file removal is optional rollback, not an exercised result unless actually selected and observed.

A 405 GET establishes reachability only. A separately granted, current-head PR `ready_for_review` action may supply a real supported GitHub event after connectivity acceptance and release of the CPU reservation. Correlate real delivery/API/job/check identifiers where authorized readbacks expose them; otherwise mark that evidence unobserved. Never infer intake, queue membership, job success, or merge eligibility from a 405.

Merge authority remains the external App-owned exact-head policy-epoch Check Run, currently `adaptive-trust-ci/verified@06ecf1c875bc` from App ID `4694114`, together with any required external signed scopes. Neither this report nor a delegated local grant replaces it. Refresh exact head/base/policy requirements before PR delivery or issue closure.
