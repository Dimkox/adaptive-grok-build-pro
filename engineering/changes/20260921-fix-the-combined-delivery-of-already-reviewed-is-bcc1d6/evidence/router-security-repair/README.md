# Router security regression repair

Route `bcc1d645c438`; sole writer `integration_implementer`; 2026-09-21. This is the explicit integration correction requested by the failed code, test and security reviews of source `4a8e8925478e390d7bf12f2bf4faab8fc0e0c70c`. Original reviews, imported packages and the original source-identity report remain historical evidence.

## Corrected behavior

The four-character whole-word rule had stopped treating isolated `authentication`, `authorization`, British `authorisation`, `authn`, `authz` and `ролью` as security work. Because the existing risk matcher also requires a standalone `auth`, those requests lost high risk, security/release review and evidence, the security skill, and the scope/design gate.

`.grok-stack/adaptive_grok/router.py` now recognizes a finite, documented set of whole-word aliases for the configured security terms `auth` and `роль`. It includes the concrete spellings above and explicit common authentication/authorization inflections. Other abbreviations and domains retain their matching behavior; unrelated `author`, `authority`, `authentic` and embedded alias lookalikes remain excluded. Risk, owner, reviewer and gate selection code is unchanged.

`matched_keywords` names canonical configured rules, rather than copying raw prompt tokens: an authentication alias reports `auth`, and `ролью` reports `роль`. Multiple aliases of one configured term contribute that term once. The source comments and matcher docstring state this interpretation; the existing bounded route reader needs no new field or exception.

Only the router and `tests/test_repo_router.py` intentionally differ from their exact imported #156 candidate. The [updated working-tree identity](../integration-source-identity-after-router-repair.json) proves that the other 17 manifest product paths remain byte/mode identical and protected SQL, factory production source, Trust CI, architecture/configuration and workflows have no net change. The [original import identity](../integration-source-identity.json) is preserved verbatim, including its original SHA-256 and scope.

## Measured execution

| Phase | Actual result | Wall duration | Lossless record |
| --- | --- | --- | --- |
| Tests added, router still unchanged | RED: 3 tests, 46 assertion failures, 0 errors, exit 1 | 0.318 s | [red.json](red.json) |
| Same three selectors after alias repair | GREEN: 3 tests, exit 0 | 0.222 s | [green.json](green.json) |
| Router and workflow-artifact suites | 61 tests, exit 0 | 4.223 s | [adjacent.json](adjacent.json) |

The three regression methods exercise the real route builder in empty generic repositories, check the complete high-risk security obligations for 42 literal prompts, exercise neutral prompt detection without an intent shortcut for eight inputs, and retain thirteen unrelated/embedded-token negative controls. Supported metadata overrides avoid unrelated Git discovery while leaving repository detection, domain matching and all obligation decisions real. Existing adjacent tests retain short-token boundaries, specialist routing, persistence and strict route-reader coverage.

Both GREEN runs preserved their recorded HEAD, router/test SHA-256 values and repository fingerprint `1ebd91541ec555718c3140b496b726a34a3fb68344c223ccab448a6115af80db`. No other suite, full verifier, compiler, linter, Docker workload, database operation, commit or external write was performed by this repair owner. The coordinator was notified immediately when the exclusive focused-test lane was released.

## Artifact provenance

[artifact-index.json](artifact-index.json) records source cache names, durable paths, lengths and hashes. RED/GREEN/adjacent records retain exact command arguments, environment overrides, times, exit codes, full base64 output and a readable UTF-8 view. Patches are inert, lossless base64 JSON archives to preserve whitespace without making raw patch formatting part of repository whitespace checks: [test patch](test-patch.json), [complete repair patch](repair-patch.json).

[design-before-red.md](design-before-red.md), [proposal-before-red.json](proposal-before-red.json), and [implementation-before-green.json](implementation-before-green.json) are unchanged snapshots of their named phases. Their earlier pending states are preserved deliberately; the measured records above establish the subsequent result.

Adding these durable artifacts changes the repository fingerprint after the focused runs. Full verification of the final combined tree, renewed independent reviews and final receipts remain with the coordinator; the original batch full PASS does not certify this correction. No completion or merge authority is inferred from these focused results.

For the coordinator's shared learning record: narrowing short keywords requires isolated positive tests for the security obligations carried by their legitimate expanded forms. The original matrix retained several specialist abbreviations but omitted those security inputs, allowing a green suite to hide lost reviews and a lost human gate.
