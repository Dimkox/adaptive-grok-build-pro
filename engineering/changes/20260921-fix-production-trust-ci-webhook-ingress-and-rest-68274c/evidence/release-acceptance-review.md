# Independent release acceptance review — bounded ingress operation

Route `68274cb876e4`; independent selected `release_reviewer`; reviewed 2026-09-21. Repository `/home/pall/grok-projects/adaptive-grok-build-ci-ingress`; inspected HEAD `2b4b20339ce7dfba758e29fc28d0f7f5c52c6f8f`, with final handoff/evidence additions awaiting the coordinator's freeze and receipt binding.

**PASS for the measured host operation.** The evidence closes the remaining source-filter, enablement, guard-stop/disable, and same-byte reactivation conditions from [the command review](release-review.md). No further host operation is required to establish this bounded acceptance. External CI completion, exact-head merge eligibility, and issue closure remain separate and pending; this report does not approve a merge or release publication.

## Reviewed identity and scope

The command plan remains SHA-256 `3108b0077dc1643363ea21ddf70ee86d06d49b39ca80ab08a1f25812abc13e28`; the four-file manifest remains `b4b45a7c453812942cbc33a2b88239613be7079435a445c9b208ab00f54f714d`. I inspected the copied evidence listed below and independently compared the final snapshot's four artifact names, SHA-256 values, owner `root:root`, and mode `0644` with the manifest: all matched. The repeated typed gate independently recorded those same installed hashes before reactivation.

The prior command review is preserved unchanged at SHA-256 `b6fb6af7f27d9d39ef79ca38c24b8320666e1364be04437a188c0c90e199e83f`. This report accepts the subsequent measured outcomes; it does not rewrite that earlier review's then-pending conditions.

This audit read repository/evidence files and calculated their hashes only. It executed no host probe, test suite, service/network operation, or external request and read no credentials. The inspected delivery remains operation documentation/evidence rather than a product change, so the `AGENTS.md` no-product verifier exception applies. The final documentation freeze, commit, and current fingerprint-bound local receipts remain coordinator work.

## Measured conditions closed

| Condition | Evidence and conclusion |
| --- | --- |
| Exact peer and interface enforcement | The initial corrected counter run at 08:36:55 UTC and repeated run at 08:42:17 both exited 0. In each, the allowed peer returned 200 with accept-counter delta **6**; wrong-interface and wrong-source probes returned curl 28/HTTP 000 with their respective drop-counter deltas **2** and **2**. The distinct matching counters establish the tested enforcement, beyond a timeout alone. |
| Guard-stop propagation and bounded shutdown | The reviewed block enabled only the socket, stopped the guard, and disabled the socket without explicitly stopping the proxy/socket. The result records all three inactive, the socket disabled, the dedicated nft table absent, and only `127.0.0.1:18080` listening. Together with the already reviewed dependency ordering, this supports the exercised guard-stop lifecycle. The record establishes the completed transaction, not a separate packet-level trace of every instant during shutdown. |
| Original API preserved during stop | Stopped-state probes returned loopback readiness **200**, peer connection refusal (curl **7**, HTTP **000**), and public webhook **502**. These are actual outcomes; no timeout was relabeled as an HTTP status. |
| Same-byte reactivation | At 08:41:35 the full typed gate exited 0 with the four original installed hashes, root ownership/mode, exact inactive fragments and empty drop-ins, disabled/static states, exact commands/dependencies, and the strictly absent `tmp.mount` prerequisite. The reviewed enable/start block then exited 0 and returned `enabled`. |
| Repeated HTTP controls | After reactivation, peer readiness and loopback readiness returned **200**, peer/public webhook GETs returned **405**, and all six public private-path controls returned **404**. Every recorded request exited 0. Public checks used the reviewed DNS-isolation method; they establish those HTTP outcomes without establishing resolver reliability. |
| Accepted final runtime | At 08:44:41 the socket was active and enabled; proxy active/running; guard active/exited. The listener set was exactly loopback plus `10.200.200.1%veth-vpn-h:18080`. The dedicated table retained only the reviewed destination/port/interface/source rules, and the original HTTPS Funnel mapping still exposed only `/webhooks/github`. All four installed hashes/owners/modes matched the manifest. |

AC-001's tested interface/source restriction and AC-003's bounded activation/stop/disable/reactivation conditions are satisfied. AC-002's public/private GET controls are satisfied, and a real PR event plus the resulting exact-head App check is recorded separately below. The 405 probes alone are not used as intake evidence.

## Real intake and external trust boundary

The saved GitHub record identifies PR #170 `ready_for_review` timeline event **31514855119** at **08:42:50 UTC**. This is a timeline event ID, not a webhook delivery ID. The operational summary reports a real webhook POST 200 in API access logs at 08:42:52; that summary is the supplied evidence for the access-log observation, not a protected job-body readback.

The separately inspected check record has ID **106268338358**, App ID **4694114**, name `adaptive-trust-ci/verified@06ecf1c875bc`, exact head `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`, start time **08:42:53 UTC**, and external/job identifier `30b1f243-8dde-41cb-90ac-671af377fc8e`. At its 08:43:37 observation, status was `in_progress`, conclusion was null, and completion time was null. This supplies real event/check-creation evidence beyond connectivity; it does not prove completed CI, a successful job result, or eligibility to merge this or another head.

The coordinator records that the event followed release of the local CPU lane and that the lane is now reserved for the external job. No additional event is required by this acceptance review. Refresh the exact current head/base, external App-owned check, and any required signed approval scopes before merge or issue closure. Local acceptance and local grants never replace that external authority.

## Remaining limits

- GitHub webhook delivery ID and protected API job-body readback remain unobserved. The timeline ID and Check Run external ID must not be substituted for either.
- The original formatter-gate refusal, counter-read failure, and DNS-resolution timeouts remain preserved as failures/inconclusive results. Later corrected checks do not change what those earlier records proved.
- Socket enablement and the exercised stop/reactivation prove the measured persistence configuration and recovery path. Cold boot, device loss/recreation or automatic return, full owned-file removal, sustained availability, global DNS reliability, and general CI capacity were not exercised by this operation.
- No assertion is made that every existing host resource was independently reaudited. The accepted mutation scope remains the reviewed bridge files, units, enablement link, and dedicated table; the runtime snapshot confirms the specified listener/Funnel/hash boundaries.

## Evidence fingerprints

These hashes bind the files actually inspected. Any changed artifact, command plan, or material acceptance evidence requires renewed review; final repository receipt binding follows the coordinator's completed documentation freeze.

| Evidence file | SHA-256 |
| --- | --- |
| `operational-acceptance.md` | `1e4bc4cc644dcf241d2440e3d9f65a39cc19eaea084971fbb2fbc0de3043fbac` |
| `acceptance-measured-counters.json` | `cc41424015f19829e067843f4a16590c1e6f2b3a23fdd4a37f335203d0e14b59` |
| `recovery-stop-result.json` | `b9ef6b6f1ee8e941054cad17358f76672119d330f3f89dcf73bdd506242051e1` |
| `recovery-stopped-http.json` | `e74756101044cd8f4a2b0a3c0ad8f4da64a3b1fbb4f5df102fa12205129e38c9` |
| `recovery-restart-block-03.json` | `93114bb7f737fb41ff6dd9dd30149fe6f16bea0d24335b6e8396dcc34e785b4a` |
| `recovery-restart-block-08.json` | `bcb3640e231e9db7d4b85a54c3b9f0fca41bdb843a9bbef33352228188bbfc57` |
| `recovery-http-acceptance.json` | `cc0e1e787920e376bba1c0ee6bdb119fef47442c1b505baeb34864b672b343c1` |
| `recovery-counter-acceptance.json` | `7bed14b9686af3ddbe229a5e1bb00abcdbf274566a420f5bdc512d7657f935fb` |
| `accepted-runtime-snapshot.json` | `38543eb6081ebfce6596f6f5b64040a0d59c16e7b1eaf75f213cf6106dbc77c9` |
| `pr170-external-check.json` | `58bda2969c802c5b9f20ec503d2c4827d5190b5c70c5a54304d350aea674b9aa` |
