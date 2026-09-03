# Test plan — External Observer truth projection v1

All network behavior uses fixtures/fake transport; tests fail if DNS/socket/GitHub access occurs. Exact fixtures mirror documented GitHub REST compare shape and never invent a `head_commit` member.

## Adversarial matrix

| Priority | Scenario | Expected evidence |
| --- | --- | --- |
| P0 | Config missing/unknown/cross-swapped repo, branch, PR, check or App ID; invalid bounds/IDs | closed schema/parser rejects before I/O |
| P0 | Main or exact PR base/head changes between opening and closing reads | whole snapshot mismatch/stale; no mixed fresh projection |
| P0 | Check absent, duplicate, conflicting, queued, wrong name/App/head or unsuccessful | `check_verified=false|unknown`, never delivered implication |
| P0 | PR open/closed/draft/unmerged, wrong base/ref/SHA, merged with missing/wrong/non-ancestor merge commit | delivered false/unknown with fixed reason |
| P0 | Direct and 1..4-hop annotated tags; moved tag, cycle, non-commit, bad SHA, draft/prerelease/missing release | only valid newest stable release resolves |
| P0 | Release equals main; structurally valid release-behind; diverged/rewound/inconsistent compare or mere unequal SHA | current/behind only with exact compare proof; otherwise unknown/mismatch |
| P0 | 401/403/429, 404, 5xx, timeout/trickle deadline, redirect, wrong content type, duplicate JSON, non-UTF-8, non-finite/oversize/deep/cardinality overflow | first unavailable/unknown, later stale; fixed redacted error |
| P0 | Corrupt/digest-forged/oversized/symlink/FIFO state or claims; lock contention; crash before/after atomic rename | fail closed, contender no I/O, authoritative last-valid recovery |
| P1 | PROJECT_STATE labels historical claim, typed evidence/receipts exact/stale/malformed, README prose contains fake current SHA | prose ignored; stages stay independent and exact-bound |
| P1 | Historical M0-M9 entries and optional PR discovery list | remain `evidence_claimed`/partial, never remote-delivered proof |
| P1 | No signed public attestation endpoint | exact `attestation_unobservable`; Check Run cannot substitute |
| P1 | Same normalized fixtures/time in shuffled response order | byte-identical JSON/digest/text and stable finding order |
| P1 | Attempted POST/PATCH/DELETE, Authorization/cookie/proxy/userinfo/arbitrary host/path, raw-body persistence | rejected before transport; tracked tree unchanged |
| P1 | CLI observe/status/render/verify-state errors and optional inert service | fixed exit/output, no activation/install/Factory/Trust edge |

## Automated checks

- Unit: frozen records, bounds, claims, stage lattice, compare topology, canonical digest/rendering, state/crash/lock/path safety.
- Integration: fake GitHub request transcript for main→PR→checks→release/tag→compare→final reread, first-failure/later-stale and runtime restart.
- Contract: config/example and `PUBLIC_STATUS.v1` schemas are closed, self-compatible and match fixtures.
- Architecture: validate/drift/diagram plus ownership and only one allowlisted GitHub read edge; no controller/Factory/Trust/production edge.
- Static/full: Ruff, Bandit, secret scan, changed-tree mutation check, root suite and `python3 scripts/grok_verify.py --mode pr` after implementation freeze.

Manual live GitHub traffic is not required for GREEN. Shared-IP anonymous quota is currently exhausted; a live anonymous result must fail closed as rate-limited/stale rather than be interpreted as no change.
