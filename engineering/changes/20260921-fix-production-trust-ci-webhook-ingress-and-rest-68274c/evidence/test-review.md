# Independent test review — preparation only

Reviewer: route-selected `test_reviewer`, independent of `integration_implementer`.
Route: `68274cb876e4`. Initial review at `2026-09-21T07:52:58Z`; final plan re-review on `2026-09-21`.

**Verdict: PASS for pre-operation test-plan readiness; F-01 resolved. Runtime acceptance: NOT EXECUTED.** No blocking test-design finding remains in the final exact candidate below. This report does not establish that AC-001, AC-002, or AC-003 has passed at runtime, authorize activation, prove queue intake, or supply merge authority.

## Exact review binding

- Worktree: `/home/pall/grok-projects/adaptive-grok-build-ci-ingress`; observed HEAD `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`.
- [Operation plan](../operation-plan.md) SHA-256: `23c6bd21137951d96a41510dfdb34bed8baef1ee95d4f3e073026ccdc183cb5e`.
- [Artifact manifest](artifact-manifest.json) SHA-256: `b4b45a7c453812942cbc33a2b88239613be7079435a445c9b208ab00f54f714d`. The host-local manifest is byte-identical to this reviewed copy.
- Independently read and hashed all four actual staged files under `/home/pall/.cache/agbp-run/issues-wave-20260921/ci-ingress/artifacts/`; each byte count and digest matches the manifest:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `adaptive-trust-ci-webhook-bridge-guard.service` | 871 | `60596d1771aed4ee0a9431ead99e7636f98a38aaa1f3ce0a0ab68477e6d3f1a1` |
| `adaptive-trust-ci-webhook-bridge.nft` | 747 | `c68534932c19799421c4bd5c0a8fad57deeb3804fcbbd76e918f738f77aa989a` |
| `adaptive-trust-ci-webhook-bridge.service` | 812 | `d2280ce0802191817da64061005d69b53a165d644b34987eee912d4a502fba6c` |
| `adaptive-trust-ci-webhook-bridge.socket` | 581 | `3163be692b5319f13cb165abd46e2186d9ca6deeb7d7ab40a687ef35dd8249d0` |

Also inspected the contract, active route, typed change specification, brief, test/recovery plans, implementation report, analysis reports, and preparation verification. Surrounding source inspection covered `trust-ci/src/adaptive_trust_ci/api.py` and `webhooks.py`. `git diff --name-only HEAD` was empty; status showed only this untracked change package. This review ran no test suite, live probe, service operation, Docker command, credential read, or external mutation. Static systemd/nft success is attributed to the recorded preparation evidence, not to a new execution by this reviewer.

## Resolved finding from effective-unit gate re-review

**F-01 — reject outgoing `Wants`/`Upholds` before starting units.** Superseded plan `2e6356d028f0b739a253e53285f0d2db7ce403bc7e37f9857c145f04467955b1` correctly rejected inherited drop-ins and compared `Requires`, `BindsTo`, and `After`, but its `dependency_fields` omitted `Wants` and `Upholds`. A pre-existing directory such as `adaptive-trust-ci-webhook-bridge.socket.wants/foreign.service` creates an outgoing dependency without appearing in `DropInPaths`; the installation scan only checks incoming `*.wants/<bridge-unit>` links. The same gap exists for `.upholds/`. Those dependencies could start unrelated units while that earlier gate still printed pass, violating the enumerated operation scope.

The installed `/usr/share/man/man5/systemd.unit.5.gz` documents accompanying `.wants/`, `.requires/`, and `.upholds/` directories and the activation semantics. This finding was based on the actual command plan and local documentation; no unit or dependency was created to demonstrate it. The final plan now queries both properties, requires them present and empty on every unit, and repeats the mandatory gate before recovery. Direct inspection confirms this correction; all four artifact hashes remain unchanged. F-01 is resolved for preparation readiness.

The final gate runs after daemon reload and before either guard or socket start. It requires all three exact fragments loaded and inactive with empty effective `DropInPaths`, checks actual commands/listener/device/dependencies, and refuses missing fields, foreign overrides, unexpected dependencies, timeouts, or nonzero exits. It also repeats before reactivation. Execution must stop before any start on refusal; neither an earlier `not-found` observation nor the file checksum substitutes for this effective-unit check. The new gate remains unexecuted because the units are uninstalled; recorded static artifact checks do not prove that the host's effective configuration will pass it.

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
