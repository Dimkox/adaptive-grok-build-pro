# Independent installer test re-review

Verdict: **PASS for test adequacy and the recorded focused evidence; final full verification remains pending.** Selected reviewer `test_reviewer`, route `148c66d20768`. Reviewed head `8ef4625d5401556c7d2230c9f18cd0e0bc2c8852`, the correction since `03fbaa91895bffe616d6a61884a7564e6057839a`, and the complete four-file product diff against `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. No remaining test-review blocker was found. The original request-changes verdict remains in [test-review-first.md](test-review-first.md); this report does not relabel that earlier result.

## Prior blocker resolved

The source-relocation fixture at `tests/test_installer.py:756` now creates the required consumer template and includes it in `MANAGED_FILES`. Before injecting either relocation, it successfully materializes an unrelocated consumer and checks its managed file and rendered AGENTS content. The subsequent refusal must match the anchored error `directory component is unsafe: source` or `directory component is unsafe: .grok`, as appropriate. A missing-template error cannot satisfy the positive control or the refusal assertion. The fixture still checks that relocation occurred, no target was published, no owned stage remains and outside bytes are unchanged.

The retained correction RED log demonstrates the intended defect: both new unrelocated controls reject the former invalid fixture with `missing consumer template`, before any relocation assertion. The repaired positive control and exact-error checks therefore address the reported false-positive risk directly.

## Coverage assessed

- Installed generic and Bitrix fixtures audit both rendered documents in their actual destination directories, check required versus optional consumer-owned handoffs, reject known upstream deployment identity, and compare AGENTS output with the shared helper. Bitrix materialization intentionally uses the existing payload injection seam; no public Bitrix materializer option is claimed.
- The link checker has an existing-file/fragment control, an HTTPS control, a missing-path control and an existing destination outside the consumer root. Both missing and escaping paths are rejected. This covers the inline-link syntax used by the new documents, without claiming general Markdown parsing or fragment validation.
- Both profiles compare deterministic payloads, expected rendered bytes and manifest hashes. The existing real materializer test checks installed sizes, modes and SHA-256 values against its plan, so substituting generated documents does not leave the former raw-source-parity exception uncovered.
- `test_installed_template_artifacts_are_explicit_reusable_source` checks the exact installed `consumer-*.md.tmpl` input names and their destination/link-context comments. It rejects retained raw `.md` copies, audits rendered destinations and verifies that the current installer can rebuild the complete generic payload from the materialized consumer. The installed source also produces identical AGENTS through `managed_agents_text`. The RED artifact assertion failed specifically on the two old `.md` filenames. The inputs remain descriptor-validated managed files; no source-reader bypass or link-check suppression was introduced.
- Existing-consumer planning preserves exact prefix/suffix/marker bytes, including CRLF and non-UTF-8 user text. Snapshot checks cover successful planning, existing-target materialization refusal and a divergent `kept_local` README conflict. README remains managed. Existing planning tests additionally reject filesystem mutation and dependency execution.
- Source-read race cases cover both renamed templates, the AGENTS helper, ordinary managed payloads, Bitrix guidance and toolchain advice. The corrected inventory-relocation case now complements those tests with a valid baseline and specific refusal evidence.
- Manual reading confirms optional consumer bootstrap/state/version/shared-memory/architecture guidance and the retained one-writer, independent-review, PR-only, exact-consent, secret/private-key and external-merge-authority boundaries. Upstream factory AGENTS, factory README and Bitrix local guidance have no diff against the review base. No updater, hook-registration or live-activation result is claimed.

## Evidence and identity

No tests, lint, compiler or Docker were started by this reviewer; the coordinator retained the CPU slot for another full gate. The following raw correction logs were read from `/home/pall/.cache/agbp-run/issues-wave-20260921/installer/`, and their SHA-256 values were independently recomputed:

| Log | Observed unittest output | SHA-256 |
| --- | --- | --- |
| `installer-review-red.log` | 2 tests in 1.011s; `FAILED (failures=1, errors=2)` | `c7e8f21742d0d511c3ba294257d481d2a6343f98c59b8470deda4e53874199f6` |
| `installer-review-green.log` | 33 tests in 15.931s; `OK` | `98dbad5c8e2d8279cc79d9af3b50c1d768ef7742eddb1126de2a8ccf6642a8ed` |

The implementation report records numeric exits 1 and 0, respectively. The RED command selected the artifact and relocation tests; GREEN ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack python3 -m unittest discover -s tests -p 'test_installer.py'`. The earlier 32-test run and full verifier on `03fbaa9` remain historical evidence and are not reused as verification of this corrected head.

Independently computed current product hashes match the corrected implementation report:

| File | SHA-256 |
| --- | --- |
| `scripts/install_into.py` | `3262984eb74233afb926f6656f9ca11312f0479e3d8a11a2985c0cb5ac63ac49` |
| `tests/test_installer.py` | `cffe0aa66f99648516f00583bcbbb68d5813e72ac51b33c2e156c62ff85cd1e5` |
| `.grok-stack/templates/consumer-AGENTS.md.tmpl` | `5b36af586bc7593021ad4c18b568d0e77c952467a1ee22a1b66a69d9365452b0` |
| `.grok-stack/templates/consumer-factory-README.md.tmpl` | `9f4bbcd60b6f4ed1f5b41e880af9983a2f89594866624a25de4539bffa6b87dc` |

Only this report was written by the reviewer. The coordinator must run the mandatory full verifier on the final tree and bind fresh review receipts before declaring local completion. This bounded PASS supplies no external HTTP availability, live consumer operation, exact-head Trust CI result or merge authority.
