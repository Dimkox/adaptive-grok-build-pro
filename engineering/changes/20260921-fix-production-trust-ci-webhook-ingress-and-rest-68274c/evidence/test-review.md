# Independent test review — continuation and partial runtime evidence

Reviewer: route-selected `test_reviewer`, independent of `integration_implementer`.
Route: `68274cb876e4`. Initial review at `2026-09-21T07:52:58Z`; final plan re-review on `2026-09-21`.

**Verdict: PASS for the corrected continuation plan. Runtime acceptance: PARTIAL.** No blocking test-design finding remains in the final exact candidate below. The bridge has been activated, positive HTTP probes passed, and the DNS-isolated private-path probes passed; counter-based enforcement and persistence/recovery are not yet established by the reviewed evidence. This report does not declare AC-001, AC-002, or AC-003 fully accepted, authorize new operations, prove queue intake, or supply merge authority.

## Exact review binding

- Worktree: `/home/pall/grok-projects/adaptive-grok-build-ci-ingress`; final continuation-review HEAD `de966c932fff54c25df3f16dd3ade903975b9787` (initial review HEAD was `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`).
- [Operation plan](../operation-plan.md) SHA-256: `3108b0077dc1643363ea21ddf70ee86d06d49b39ca80ab08a1f25812abc13e28`.
- [Artifact manifest](artifact-manifest.json) SHA-256: `b4b45a7c453812942cbc33a2b88239613be7079435a445c9b208ab00f54f714d`. The host-local manifest is byte-identical to this reviewed copy.
- Independently read and hashed all four actual staged files under `/home/pall/.cache/agbp-run/issues-wave-20260921/ci-ingress/artifacts/`; each byte count and digest matches the manifest:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `adaptive-trust-ci-webhook-bridge-guard.service` | 871 | `60596d1771aed4ee0a9431ead99e7636f98a38aaa1f3ce0a0ab68477e6d3f1a1` |
| `adaptive-trust-ci-webhook-bridge.nft` | 747 | `c68534932c19799421c4bd5c0a8fad57deeb3804fcbbd76e918f738f77aa989a` |
| `adaptive-trust-ci-webhook-bridge.service` | 812 | `d2280ce0802191817da64061005d69b53a165d644b34987eee912d4a502fba6c` |
| `adaptive-trust-ci-webhook-bridge.socket` | 581 | `3163be692b5319f13cb165abd46e2186d9ca6deeb7d7ab40a687ef35dd8249d0` |

Also inspected the contract, active route, typed change specification, brief, test/recovery plans, implementation report, analysis reports, and preparation verification. Surrounding source inspection covered `trust-ci/src/adaptive_trust_ci/api.py` and `webhooks.py`. The final operation-plan diff contains exactly four read-only nft option corrections and the DNS-isolation paragraph; artifacts and mutation commands are unchanged. This review ran no test suite, live probe, service operation, Docker command, credential read, or external mutation. I read `nft --help` to confirm the JSON/stateless flags. Static checks, the corrected gate diagnostic, activation, and HTTP outcomes are attributed to the retained execution evidence rather than new executions by this reviewer.

## Resolved finding from effective-unit gate re-review

**F-01 — reject outgoing `Wants`/`Upholds` before starting units.** Superseded plan `2e6356d028f0b739a253e53285f0d2db7ce403bc7e37f9857c145f04467955b1` correctly rejected inherited drop-ins and compared `Requires`, `BindsTo`, and `After`, but its `dependency_fields` omitted `Wants` and `Upholds`. A pre-existing directory such as `adaptive-trust-ci-webhook-bridge.socket.wants/foreign.service` creates an outgoing dependency without appearing in `DropInPaths`; the installation scan only checks incoming `*.wants/<bridge-unit>` links. The same gap exists for `.upholds/`. Those dependencies could start unrelated units while that earlier gate still printed pass, violating the enumerated operation scope.

The installed `/usr/share/man/man5/systemd.unit.5.gz` documents accompanying `.wants/`, `.requires/`, and `.upholds/` directories and the activation semantics. This finding was based on the actual command plan and local documentation; no unit or dependency was created to demonstrate it. Revision `23c6bd21137951d96a41510dfdb34bed8baef1ee95d4f3e073026ccdc183cb5e` required both properties empty. The current measured correction instead requires typed empty `Upholds` everywhere and empty socket `Wants`, allowing exactly `tmp.mount` for the two `PrivateTmp` services only under the strict target-absence checks below. It still refuses any foreign outgoing dependency and repeats before recovery. All four artifact hashes remain unchanged; F-01 remains resolved.

The final gate runs after daemon reload and before either guard or socket start. It requires all three exact fragments loaded and inactive with empty effective `DropInPaths`, checks actual commands/listener/device/dependencies, and refuses missing fields, foreign overrides, unexpected dependencies, timeouts, or nonzero exits. It also repeats before reactivation. Execution must stop before any start on refusal; neither an earlier `not-found` observation nor the file checksum substitutes for this effective-unit check.

## Measured gate repair and stopped-installation continuation

I inspected the preserved host-local results under `/home/pall/.cache/agbp-run/issues-wave-20260921/ci-ingress/`: result `01` reports exclusive installation of the four files, exit 0, and `activated: false`; result `02` reports the static/reload block exit 0; result `03` reports exit 1 and `missing effective property` after all three exact loaded/inactive identities passed. The corresponding historical block `03` still contains the earlier text parser. No earlier result is overwritten or promoted into an activation success.

The corrected command removes the representation assumptions that caused that safe refusal:

- Every named D-Bus read uses `check=True`, a ten-second deadline, successful JSON decoding, an exact signature, and a required `data` member. An absent/failed property cannot become an empty array. Empty hooks must equal typed `[]` with signature `a(sasbttttuii)`; nonempty service commands must have one complete ten-field record with the exact executable, argument vector, and `ignore_errors=False`. Execution timestamps/status fields are correctly excluded from configuration comparison so the check also works after a stop.
- Dependency values use typed `as` arrays and set equality, preserving literal escaped device names instead of whitespace-splitting formatted text. Listener tuples use `a(ss)` and exact address comparison; device strings and `Accept`, `DefaultDependencies`, and service `PrivateTmp` booleans are compared explicitly.
- The only service `Wants` exception is exactly `tmp.mount`, with a corresponding exact ordering edge. Before permitting it, the gate requires the target to be not-found/inactive, non-transient, without fragment, drop-ins, or any `Requires`, `Wants`, `Upholds`, or `BindsTo` entries. Both temporary paths must still resolve to `/`. A real or changed mount definition, another weak dependency, or any `Upholds` entry refuses before start. This is a bounded correction from measured configuration, not an unrestricted dependency allowance.
- The continuation verifies the pinned manifest and every installed file's length/hash, regular-file identity, `root:root` ownership, and mode `0644` without following a final symlink. It requires disabled socket/static services, inactive identities, no incoming enablement/dependency links, and no dedicated nft table. It deliberately resumes at the corrected gate instead of repeating exclusive installation or the completed reload.

The implementation report records the exact corrected read-only gate returning `effective_unit_gate=pass`, exit 0, in `0.471165461` seconds. That earlier diagnostic is retained in the writer's tool result and implementation report, not a separate raw evidence file; I did not rerun it. The original preparation JSON remains a historical pre-install snapshot. The coordinator's separate `continuation-result-03.json`, recorded at `08:29:54Z`, now supplies raw typed output and an exit-0 pass before activation; `continuation-result-04.json` records the guarded start block returning 0 and the exact narrow table at `08:29:55Z`. Neither record proves the still-pending negative controls or recovery.

The stopped-installation continuation described above has now been executed; it is not an instruction to reinstall or restart an already active bridge. The current continuation is the corrected acceptance readback followed by separately bound persistence/stop/recovery. Repeat the inactive-unit gate only at its prescribed stopped recovery stage, using the latest reviewed command rather than the preserved historical `operation-block-03.sh`. Preserve original results and use fresh evidence names. A prior diagnostic pass does not replace a required fresh gate. The full-verification CPU lane remains a separate prerequisite before a real PR event.

## Final nft readback and DNS-isolation correction

The final plan changes four nft read-only queries from `-json` to `--json`. Installed help identifies `-j/--json` as JSON output and `-s/--stateless` as omission of stateful information; the single-dash `-json` cluster unintentionally includes `-s`. This explains why the counter parser received a null counter instead of packet/byte fields. `acceptance-initial-counters.json` preserves the original exit-1 `TypeError` with no completed case output; it establishes no allowed-peer or negative-control result. The corrected query keeps the existing strict per-rule counter-delta and curl-exit assertions, so an absent counter or wrong-cause timeout still cannot pass. Actual enforcement remains pending until that full block succeeds.

I inspected the following retained HTTP records under the same host-local stage:

| Evidence | Observed outcome | Accepted scope |
| --- | --- | --- |
| `acceptance-initial-http.json` | Peer readiness 200, peer webhook 405, public webhook 405; each curl exit 0. The first public ready-path probe exited 28/000 with `Resolving timed out after 3001 milliseconds`. | Positive connectivity only; the private-path attempt is inconclusive. |
| `acceptance-private-http-retry.json` | A second public ready-path attempt exited 28/000 with the same explicit resolver timeout. | Preserved failure; no private-path result. |
| `acceptance-public-http-resolved.json` | At `08:35:13Z`–`08:35:16Z`, public webhook 405 and all six private paths 404 through `176.58.88.108`; every curl exit is 0, elapsed times are 0.580–0.659 seconds, and the record identifies a fresh resolver observation and TLS hostname verification. | HTTP path reachability/isolation after DNS resolution is isolated; host resolver health remains unproven. |

The new fallback is correctly bounded to one successful five-second resolver lookup and the same seven public GETs. The chosen address must be public and come from that fresh result. `--resolve` leaves the HTTPS URL hostname, SNI, and certificate verification intact; no redirects, insecure TLS switch, wider path, changed service configuration, or POST is authorized. The original no-proxy setting, connection/total deadlines, and 405/404 expectations remain. Lookup failure, a non-public result, or any unexpected HTTP outcome refuses. The successful isolated probes do not rewrite either DNS timeout as a pass or prove normal resolver reliability.

## Acceptance quality

| Boundary | Review result and required runtime evidence |
| --- | --- |
| Root-cause baseline | The retained evidence distinguishes healthy loopback 200, absent bridge listener/VPN refusal, and public 502. The intervening curl 28/HTTP 000 remains inconclusive; the later 502 does not explain that transient timeout. No failed baseline is rewritten as success. |
| Positive connectivity | VPN source `10.200.200.2` must obtain ready 200 and webhook GET 405 through the bridge; public webhook GET must separately obtain 405. This exercises both proxy startup and Funnel reachability. Host-local traffic to the veth address is correctly excluded as a positive oracle. |
| Private public routes | The plan checks `/health/ready`, `/approvals`, `/jobs/nonexistent`, `/attestations/nonexistent`, `/metrics`, and `/v1/jobs` for public 404 while confirming the exact path-only Funnel mapping. The actual ready/approval/authenticated endpoints distinguish accidental backend exposure. `/v1/jobs` is only an additional missing-route control and cannot prove isolation by itself. |
| Interface/source enforcement | The allowed-peer request requires curl 0, HTTP 200, and an allowed-rule counter increase. Host/local-interface and correct-veth/wrong-source controls each require curl 28, HTTP 000, and an increase in their own named drop counter. Source `100.119.249.65` ownership and routing are checked without changing addresses or routes. An unrelated timeout or `BindToDevice` refusal cannot satisfy the counter requirement. |
| Scope/preservation | Exact address/device, narrow table rules, all three unit states, and unchanged loopback readiness are inspected after activation. Unexpected listeners or exposed private paths require rollback. No synthetic webhook is needed to test the bridge. |
| Stop and recovery | Stopping the guard, before disabling the socket, meaningfully exercises dependency propagation to both listening owners. Acceptance requires all three inactive, table absent, loopback-only listener, backend 200, VPN refusal, and the expected public failure; a remaining listener fails the exercise. Same-byte reactivation repeats the positive, private-path, and counter controls. Cold boot/device recreation are explicitly outside the exercised claim. |
| Real intake | `ready_for_review` is a supported source event, but GET 405 only proves connectivity. The plan separately requires a refreshed PR head, real delivery ID/time/status, correlated API POST and job/check identities, and the exact-head App-owned policy-epoch check. Missing readback stays unobserved. |

## Evidence rules for execution

The HTTP commands have explicit connect/total bounds: peer probes 2/5 seconds, public probes 3/8 seconds, and each enforcement curl 2/2 seconds with an outer five-second subprocess deadline. Their results still need individual operator evaluation: the first shell block prints statuses rather than asserting them, and the private-path loop's aggregate shell exit is not an all-probes verdict. Retain each probe's curl exit, HTTP status, and elapsed time in the runtime record. Success requires transport exit 0 with each expected 200/405/404; timeout/000, other statuses, and missing observations do not pass. Enforcement controls use their explicitly expected timeout exits and counter deltas instead.

After the guard-stop command, record the states before accepting recovery. Final inactive states prove propagation and restored exposure boundaries; a claim about the temporal stop sequence should be supported by the dependency graph and retained unit transition evidence, not inferred from a single final `ss` snapshot. Public timeout remains inconclusive during recovery as it does during activation.

The source webhook handler can return HTTP 200 with `accepted: false` for an ignored event. Consequently, an access-log 2xx alone is not job evidence. Correlate an accepted response/job identity or another authorized job readback with the real delivery and subsequent exact-head App check; `created: false` may represent deduplication and must not be relabeled a newly queued job. Historical or unrelated checks do not prove this delivery. A check's presence is separate from its successful conclusion and any required external approvals.

The coordinator owns these runtime results and final fingerprint-bound receipts. A changed plan or staged artifact requires refreshed review binding. The operations-only product-verifier exception is appropriate here; no full product verification is claimed or required by this report.
