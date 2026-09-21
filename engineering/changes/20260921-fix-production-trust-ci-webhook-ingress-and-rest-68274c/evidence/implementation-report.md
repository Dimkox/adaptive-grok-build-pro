# Integration implementer preparation report

Route `68274cb876e4`, sole write owner `integration_implementer`. Prepared host-local resource files only: three systemd units and one nft file at `/home/pall/.cache/agbp-run/issues-wave-20260921/ci-ingress/artifacts/`. [The exact manifest](artifact-manifest.json) and [operation plan](../operation-plan.md) are ready for the four selected independent reviews. No resource was installed or activated and no delivery claim is made.

## Results actually observed

- `git fetch --all --prune` succeeded; branch remains `fix/trust-ci-webhook-bridge`. No commit, route transition, push, or GitHub mutation was made.
- Read-only namespace/veth checks confirm `wg-vpn-namespace.service` active/exited, oneshot with `RemainAfterExit=yes`; host `10.200.200.1/30` on `veth-vpn-h`; peer `10.200.200.2/30` on reciprocal `veth-vpn-n`.
- Existing namespace source `100.119.249.65` routes to `10.200.200.1` through `veth-vpn-n`. Host all/veth `rp_filter=2` is loose; the active wrong-source test can use an ordinary source-bound curl and must measure the nft drop counter. No packet from that source was sent during preparation.
- Existing Funnel status has exactly the public `/webhooks/github` handler to `http://10.200.200.1:18080/webhooks/github`. Its settings were read, never modified.
- Only `127.0.0.1:18080` listens; loopback ready GET is 200; VPN bridge GET receives immediate connection refusal (curl 7, HTTP 000); public webhook GET was 502.
- A later read-only baseline helper attempt timed out on public HTTPS (curl 28, HTTP 000) and did not complete. An unchanged-timeout timing diagnostic then observed 502, DNS 0.089520 s, TCP 0.179004 s, TLS 0.603679 s, first byte 0.771688 s, total 0.771730 s. The transient cause is unestablished; it is retained as a limitation, not converted into success or attributed to the proposed bridge.
- No conflicting bridge unit, enablement, exact-unit drop-in directory, destination file, or dedicated table was found. This pre-install scan did not establish absence of inherited effective drop-ins; the security-review correction below supplies a mandatory post-reload gate. There are no existing nft input base chains. Other firewall rules/tables remain untouched.
- `systemd-analyze verify` on all three staged units returned 0 with no diagnostics. `sudo -n nft --check --file <staged .nft>` returned 0 with no diagnostics. Neither check changed host resources.

## Decisions and boundaries for reviewers

The installed binary is the only server/proxy process introduced. The firewall guard owns only its dedicated table, refuses a pre-existing table, and filters only the exact destination/port. Socket and proxy bind to the guard so orderly guard stop closes both before filter deletion. Device binding and explicit late socket startup avoid widening ingress or creating a normal-service/sockets-target cycle; sysinit/shutdown edges are retained.

No product, Trust CI source, configuration, dependency, or unit template was added to Git. Temporary read-only preflight/probe helpers used during preparation were removed in favor of the small four-resource candidate and explicit bounded command bodies in the plan; no installer framework is delivered. The durable additions are plan, manifest/hash, and evidence documents. Root-level shared memory files are untouched to honor the parent's write scope; [shared-memory facts](shared-memory-facts.md) give the coordinator the fact to record there.

The plan grants no authority by itself. Parent review/grant binding must cover the exact manifest and command bodies. Installer copying, actual firewall enforcement, sandboxed proxy startup, guard-stop propagation, persistence, reactivation, public private-route checks, real webhook intake, and external exact-head CI are all still unexecuted. No product verifier, compiler, lint suite, Docker command, synthetic event, private key, environment file, credential store, or queue database was used.

## Handoff

Parent dispatches the route-selected code/test/security/release reviewers against the manifest's exact external files and the operation plan. Any artifact or command fix returns to this writer, refreshes hashes/static checks as applicable, and receives fresh review before operation. Activation, stop/recovery evidence, real GitHub intake, fingerprint-bound receipts, and final delivery remain coordinator work.

## Security-review command-plan correction

The initial exact `<unit>.d` check omitted systemd's documented dash-prefix and type-wide drop-in search. The revised operation plan now requires a read-only effective-unit gate after `daemon-reload` and before any start: all three exact installed fragments must be loaded, inactive, and free of effective `DropInPaths`, followed by explicit comparisons of commands, listener/device, and dependency properties with only documented implicit edges. A security-review follow-up additionally requires empty effective `Wants` and `Upholds`, because outgoing dependency links can otherwise start unrelated units without a drop-in. Any unknown override or property returns to review without reading its contents or modifying it; reactivation repeats the gate. The four resource bytes and their manifest remain unchanged; this gate has not been executed because those resources are still uninstalled.

The installed manuals confirmed the drop-in search and implicit dependencies; `findmnt` measured both `/tmp` and `/var/tmp` on `/`. A supplementary read-only mount metadata command mistakenly put `--property` after `--`, making systemctl treat it as a unit name and print broad mount/default metadata; no host mutation or credential-file read occurred. The corrected plan always places its explicit property selector before the unit name, and never requests environment/credential properties. This is a command-construction mistake for the coordinator's shared mistake log, not operational success evidence.
