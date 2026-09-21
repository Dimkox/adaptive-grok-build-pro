# Security review — prepared Trust CI ingress bridge

**Verdict: pre-activation GO for the corrected continuation.** No unresolved security finding remains in the final reviewed candidate. The four files are installed and the bridge remains inactive; resume at the corrected read-only gate only after the other selected reviews and a fresh exact delegated grant bind this plan. Do not repeat installation. This verdict does not establish packet enforcement, recovery, real webhook intake, or merge eligibility.

- Reviewer: independent route-selected `security_reviewer`.
- Route: `68274cb876e4`.
- Repository HEAD observed during re-review: `4d3e1c059448fa3dc106602465335de6b3cbb07e`.
- Final operation-plan SHA-256: `7b97645e9852ad772d60cf009b0636fcc6f9b7fc7c6f9558281b1b848bc281a3`, superseding the previous `23c6bd21137951d96a41510dfdb34bed8baef1ee95d4f3e073026ccdc183cb5e` review binding.
- Manifest SHA-256: `b4b45a7c453812942cbc33a2b88239613be7079435a445c9b208ab00f54f714d`; the repository evidence copy and host-local staging copy agree.
- Scope: actual four staged and installed resource files, exact operation commands, route/brief/specification, four analysis reports, preparation and installation/refusal evidence, and surrounding API authentication implementation. Current tracked changes are confined to the change package's operation plan, its hash, and implementation report. The operations-only product-verifier exemption applies.

## Exact resources inspected

Files were read directly from `/home/pall/.cache/agbp-run/issues-wave-20260921/ci-ingress/artifacts/`. Independent byte-count/hash calculation matched every manifest entry, including after the plan corrections. During this re-review I also read the four exact installed destinations from the manifest: every installed byte count/hash matches, and metadata records `root:root` ownership and mode `0644`. No host configuration was written or executed by this reviewer.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `adaptive-trust-ci-webhook-bridge-guard.service` | 871 | `60596d1771aed4ee0a9431ead99e7636f98a38aaa1f3ce0a0ab68477e6d3f1a1` |
| `adaptive-trust-ci-webhook-bridge.nft` | 747 | `c68534932c19799421c4bd5c0a8fad57deeb3804fcbbd76e918f738f77aa989a` |
| `adaptive-trust-ci-webhook-bridge.service` | 812 | `d2280ce0802191817da64061005d69b53a165d644b34987eee912d4a502fba6c` |
| `adaptive-trust-ci-webhook-bridge.socket` | 581 | `3163be692b5319f13cb165abd46e2186d9ca6deeb7d7ab40a687ef35dd8249d0` |

## Findings resolved before GO

The original conflict scan checked exact unit drop-in directories and incoming dependency links. It did not establish the absence of inherited dash-prefix/type-wide overrides or outgoing `.wants/` and `.upholds/` dependencies. These are supported systemd configuration mechanisms, so approved file bytes alone do not establish effective unit behavior. See the [systemd 255 unit manual](https://raw.githubusercontent.com/systemd/systemd/v255/man/systemd.unit.xml).

The final plan requires all three units loaded and inactive with exact fragment paths and empty effective `DropInPaths`. Only after those identity checks does it inspect narrow command properties. It uses named, typed D-Bus reads to distinguish a real empty command array from a missing/failed read and to retain literal device-unit escapes. Executable/argument vectors, error-ignore flags, listener/device, and complete activation/ordering dependency sets are compared explicitly. Unexpected values refuse activation; the same gate repeats before reactivation. I inspected the final command body. No runtime resource bytes changed.

The original all-empty service `Wants` expectation was too strict: the reviewed `PrivateTmp=yes` setting itself adds a weak `tmp.mount` dependency in [systemd 255's implementation](https://github.com/systemd/systemd/blob/v255/src/core/unit.c#L1227-L1241). The corrected exception is limited to exactly that edge for the two services; socket `Wants` and every `Upholds` remain empty. The target must independently be `not-found`, inactive, non-transient, and free of fragment, drop-ins, `Requires`, `Wants`, `Upholds`, and `BindsTo`. Thus this allowance admits no existing mount definition or additional activation chain. A real definition or any extra edge refuses. The exception does not authorize creating, altering, or explicitly starting `tmp.mount`.

The preserved host-local `operation-result-01.json` and `02.json` record successful exclusive installation and syntax/reload; `03.json` records the previous gate's missing-property refusal before any start. Its root cause was assuming formatter output represented typed arrays and inferring implicit dependencies from current mount topology. The implementation report records a corrected read-only diagnostic pass in `0.471165461` seconds. I inspected the command and evidence without re-executing the gate; the coordinator must rerun it after the new review/grant freeze. The original preparation evidence remains a historical record, not the current installation state.

## Security assessment

The network actor admitted to the bridge is source `10.200.200.2` arriving on `veth-vpn-h`, for destination `10.200.200.1:18080` only. The socket independently binds that exact address and device. The nft rules drop wrong interfaces before wrong sources and count the permitted peer; other destination/port traffic is unaffected. No security claim relies on the unavailable systemd BPF address filter.

This is a network boundary, not process authentication. Any process able to originate traffic as the permitted namespace peer can reach all backend API paths through the TCP relay. That exposure is explicit in the scoped design. The public boundary remains the existing sole Funnel handler `/webhooks/github`, whose private-path negative controls are mandatory. The relay neither filters HTTP paths nor grants API authority.

Inspection of `trust-ci/src/adaptive_trust_ci/api.py` and `webhooks.py` confirms the source verifies the raw-body HMAC before event parsing/enqueueing, checks the allowed repository policy, validates approval envelopes against exact job/policy identity, and protects job/attestation/metrics reads with a bearer token. The prepared resources alter none of those paths or credentials. The relay needs no secret, human approval key, deployed policy, holdout, image, database, or GitHub App configuration.

The proxy runs the fixed installed binary against `127.0.0.1:18080`, using a dynamic identity, no capabilities, no new privileges, and filesystem/kernel restrictions. It intentionally retains the host network namespace. The separate root guard has only `CAP_NET_ADMIN` in its capability bounding set and fixed nft commands; its configuration contains no includes, shell expansion, or broad firewall flush.

The nft transaction exclusively creates its dedicated table. A pre-existing name is refused rather than adopted. Installation pins the manifest, hashes all payloads into memory, checks conflicts, and exclusively creates the four exact destinations with no final-component symlink following. Partial installation cleanup is limited to recorded created inode identities. Normal rollback closes both listener owners before removing the guard table, then removes only unchanged files created by this operation.

The socket and proxy both bind their lifecycle to the guard; the proxy is ordered after the socket, which is ordered after the guard. The planned inverse stop order is therefore proxy, socket, guard. The actual dependency-stop exercise remains required. An externally deleted/replaced firewall table is outside the oneshot guard's detection guarantee; unexpected live rules or ownership require stopping the bridge and coordinator review. No automatic device-return or cold-boot success is claimed.

## Mandatory runtime conditions

1. Bind all four selected reviews to this final plan and unchanged manifest, then obtain a fresh exact delegated grant covering only the enumerated continuation/resources and current repository fingerprint. Freeze/extract the corrected command bytes; do not execute stale operation blocks, repeat installation, or overwrite results `01`–`03`. This review is not a grant, external Trust CI attestation, or human-signed approval.
2. Refresh the namespace/veth addresses and reciprocal identity, active namespace unit, loopback readiness/listener, exact Funnel mapping, absence of conflicts, and current firewall topology. Any mismatch refuses this candidate; do not modify existing resources to fit it.
3. Resume with the corrected effective-unit gate against the already reloaded installation, before the guard or socket starts. It must reverify installed bytes/ownership, inactive/disabled-or-static state, absent enablement links/table, exact typed configuration, and the absent/inactive `tmp.mount` target. Do not insert another reload or configuration change between this gate and activation; changed state requires reassessment. A refusal must return to review without reading secret/environment/credential properties, removing foreign overrides, or widening the gate.
4. Start and inspect the guard before the socket. Record the exact rules, exact address/device listener, and actual proxy sandbox startup. Prove allowed-peer success and both negative controls with the corresponding nft counter increases. A timeout without its drop-counter increase does not establish enforcement.
5. Require peer readiness 200, peer/public webhook GET 405, and 404 for all listed private public paths. Preserve host-loopback readiness 200. Public 000/timeouts are inconclusive. Any private-path exposure, unexpected listener, or ineffective filter requires immediate bounded rollback; do not enable persistence on failed acceptance.
6. Execute the planned guard-stop/disable check, establishing both listening owners inactive, dedicated table absent, and original loopback API healthy. Recheck hashes and effective units before same-byte reactivation, then repeat acceptance. Remove files only when their recorded ownership and hashes still agree.
7. Keep a real GitHub event separate from transport probes. Its PR action needs its own exact grant; HMAC intake, durable job/check identity, and the App-owned `adaptive-trust-ci/verified@06ecf1c875bc` result on the current exact head require their own evidence. No synthetic webhook, key access, or local receipt can substitute for them.

The preparation and coordinator records report successful systemd/nft syntax checks; I did not rerun them. This review performed file/source inspection, installed-file metadata/hash calculation, and primary documentation lookup only. No host mutation, network/packet probe, test suite, Docker command, secret read, or external write was performed by this reviewer. Installation/reload and the writer's read-only diagnostic have occurred; freshly bound gate execution, activation, packet enforcement, stop/recovery, and real event intake remain outstanding.

Shared-memory fact for the coordinator: validate effective systemd configuration with named typed reads and measured implicit dependencies. Exact fragment hashes miss inherited overrides; human-readable formatting and current mount layout are insufficient to infer empty arrays or dependency sets.
