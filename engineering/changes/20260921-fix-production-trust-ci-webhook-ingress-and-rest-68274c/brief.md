# Restore the existing Trust CI webhook ingress

The healthy API publishes only host `127.0.0.1:18080`. Tailscale runs in network namespace `vpn`, where the existing public `/webhooks/github` mapping targets `10.200.200.1:18080`. No listener exists there, and the public endpoint returns502. This is a host networking operation; no application or Trust CI source behavior needs to change.

Use exactly one host bridge: `adaptive-trust-ci-webhook-bridge.socket` listens on `10.200.200.1:18080` bound to `veth-vpn-h`; its service runs the installed systemd-socket-proxyd to unchanged `127.0.0.1:18080`. The actual VPN peer is10.200.200.2. Installed systemd255 IPAddressAllow cannot be relied on (-BPF_FRAMEWORK), so a dedicated nftables table must enforce interface AND source before the listener starts. The table has no effect on other destinations or ports. A oneshot guard service loads/removes only that table and the socket/proxy depend on it. Existing wg-vpn-namespace.service creates the network namespace and is active/exited; require/order after it. No current nft input base chain exists at inspection.

The sole writer prepares host-local operation artifacts outside Git plus their durable plan and hashes here. Host-local installation scratch is intentionally not product Git content under AGENTS.md. No reusable product template, dependency, public API, Tailscale setting or existing container is added or edited. Independent code/test/security/release reviewers inspect the exact proposed artifacts before activation. No competing CPU suites or CI enqueue event while another full verifier owns this host.

## Authority

The user requested all remaining issues in parallel, then said «все исправленные issues в гитхабе закрывай». After the missing webhook bridge and intention to repair it were explained, the user instructed «делай всё и закрывай». This standing authorization covers completing the discussed bounded ingress repair and verified PR delivery/closure. It does not authorize arbitrary production work, bypassing external checks, human approval keys or deployed trust policy changes. The scope/design and production-operation gates are satisfied only for this minimal recorded plan and enumerated bridge resources, with passing independent reviews and a fresh exact delegated local grant before activation. A new trust-boundary decision returns to the coordinator rather than expanding this consent.

The separate GitHub state operation is marking the already reviewed PR170 ready for review to generate a real supported event after ingress works. It needs its own exact grant and does not change its tested head. Any subsequent required external approval remains external.

## Completion boundary

A405 probe establishes route connectivity, not queue membership or merge eligibility. Observe a real supported GitHub event and the required App-owned exact-head Check Run separately. Close source issues only after their fixes are delivered. An operations-only record skips the product verifier per AGENTS.md; record actual static/packet/HTTP/recovery evidence without claiming unexecuted product checks.
