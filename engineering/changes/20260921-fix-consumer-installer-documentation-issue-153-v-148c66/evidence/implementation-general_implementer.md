# Consumer installer implementation evidence

Route `148c66d20768`; sole selected `general_implementer`; baseline `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. Implemented the scoped design after reading all four analysis reports. No named human gate applies. This report establishes focused local behavior only; it is not independent review, a route receipt, external Trust CI, or merge authority.

The initial implementation and 32-test evidence below are historical: the first independent code and test reviews requested changes. The appended review-correction section records the resulting repair and current 33-test focused result; the original failures are not relabeled as passing reviews.

## Change and cause

The installer copied factory-root instructions and README links into a smaller consumer tree. The missing destinations and factory-only bootstrap obligations were a payload contract defect, not missing consumer milestones. Four product files changed:

- `scripts/install_into.py`: render consumer AGENTS from its template through the same renderer used by `managed_agents_text`; substitute the retained managed `factory/README.md` content from its consumer template. Payload construction consumes descriptor-validated inventory bytes, preserving bounded/no-follow source reads and hashing the emitted bytes. README mode retains the existing managed source mode.
- `.grok-stack/templates/consumer-AGENTS.md`: installed entrypoints and route/change workflow; explicitly optional consumer handoffs and architecture files; one writer, independent review, PR delivery, fresh fingerprint evidence, exact operational consent, secret restrictions and independent external merge authority.
- `.grok-stack/templates/consumer-factory-README.md`: local links only to shipped destinations; clearly labeled upstream-only HTTPS references pinned to immutable `v2.0.18`; retained ownership and read-only existing-target update semantics.
- `tests/test_installer.py`: installed-tree link audit with missing/escape controls; generic/Bitrix document checks; deterministic rendering and manifest hashes; helper/payload parity; user prefix/suffix/marker preservation; old README kept-local conflict; source-read race checks extended to both templates and the helper.

Factory-root AGENTS/README, doctor and policy are unchanged. No factory state or deployed policy is installed. The public materializer remains generic by default; the Bitrix document fixture feeds a real explicitly built Bitrix payload into the same constructor without adding an API option.

## Focused evidence

Command, run from the worktree root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack python3 -m unittest discover -s tests -p 'test_installer.py'
```

Regression-first baseline: 32 tests, 14.191s, `FAILED (failures=3, errors=2)`. Both profile fixtures found nine unresolved installed README links; the old README was incorrectly identical to the planned README and therefore did not conflict when kept-local; both new template parity cases failed because the consumer template did not exist. The red command's shell wrapper printed its log with `tail` and returned 0, so a separate numeric unittest exit was not captured; the retained unittest output records the failure explicitly.

Final green command redirected stdout/stderr directly to its log without a trailing command: **exit 0**, 32 tests, 14.757s, `OK`. `git diff --check` returned **0**. Read-only `git cat-file -e v2.0.18:<path>` returned **0** for all five upstream README destinations: `factory/README.md`, `DARK_FACTORY_ROADMAP.md`, `factory/runtime`, `engineering/runbooks/l5-production-runtime.md`, and `engineering/runbooks/m4-v2.0.13-local-control-plane.md`. This checks the immutable local Git objects, not remote HTTP availability.

Raw logs remain outside the repository at `/home/pall/.cache/agbp-run/issues-wave-20260921/installer/`:

| Log | SHA-256 |
| --- | --- |
| `installer-red.log` | `fe988a18c67ba24758d5f75392425fb3b840e3a003681eebfa24b87b1da3989f` |
| `installer-green.log` | `3160794321e1c585e0af5ce831746ba57a3515b1366e15f8a5832503ce4b202a` |

Product bytes tested:

| File | SHA-256 |
| --- | --- |
| `scripts/install_into.py` | `0e462616136d005dba1b31b198dfac92b9fc1b585e3f75055302edb1560d959f` |
| `tests/test_installer.py` | `b00a9e7851e840a3ea447c86ce81b79f01346c8e2c1230e13adc9903b9ae2dfa` |
| `.grok-stack/templates/consumer-AGENTS.md` | `81b982d71d3418295b6e7b0b511bdc1c887b2d1abd6a83336990024565219309` |
| `.grok-stack/templates/consumer-factory-README.md` | `b2295eccd7393c4dcbaeb137b4702fae90331ebf20360128eea855899bddddd4` |

## Limits and recovery

No full PR gate, Docker, bootstrap, commit, push, external write or agent dispatch was performed by this implementation task. The coordinator still owns full verification, the selected independent reviews and fresh fingerprint-bound receipts. These tests do not establish CLI hook registration or live consumer deployment.

Future fresh installations receive the corrected templates. Existing consumers remain byte-for-byte unchanged by planning and require a separately reviewed consumer update. Rollback is a normal revert of these four source files for subsequent plans; it is not an automatic rewrite of any existing consumer. Retaining managed README ownership avoids stranding an old copy through an implicit deletion protocol.

Shared-memory candidate: auditing the materialized consumer rather than the factory source exposed all nine missing README destinations, while rendering both docs from already validated template bytes kept payload hashes deterministic. Initial fixture correction: the test assumed a public `profile_kind` argument without checking `materialize_new`'s signature; using the existing explicit payload seam corrected the test without expanding the product API. Coordinator owns append-only decisions/mistakes updates.

## Review correction — explicit template artifacts and valid relocation fixture

Both first-review findings were confirmed against the product source. Because `.grok-stack` is managed recursively, the new raw `.md` templates were installed beside rendered documents with 33 links authored for the wrong directory. Also, the source-relocation fixture had not adopted the newly required input; its broad exception assertion could pass for a missing template instead of the intended binding refusal. The original `code-review.md` and `test-review.md` retain those failed verdicts until the coordinator archives them for independent re-review.

The coordinator approved renaming the two newly introduced inputs to `.md.tmpl`, with a leading HTML comment declaring the rendered destination and output-relative links. They remain actual managed rendering inputs read through the existing bounded descriptor inventory; no link-check exemption or source-reader bypass was added. Rendering still emits `AGENTS.md` and managed `factory/README.md` at their existing paths and hashes their full output bytes. The template paths are first introduced in this PR, so there is no released consumer migration or new update mutator.

The new artifact regression materializes a consumer, checks the exact two explicit template-source filenames and destination comments, verifies rendered local links, and proves `build_payload(installed_consumer)` reproduces the original generic payload exactly. It also checks the installed source works with `managed_agents_text`. Thus dropping the inputs, retaining misleading `.md` copies, or making the installed source incomplete fails the contract.

The relocation fixture now supplies and inventories the required template, successfully materializes an unrelocated positive control, and then requires `directory component is unsafe: source` or `directory component is unsafe: .grok` for the appropriate relocation. A missing-template exception no longer satisfies it. Source/target snapshots, outside bytes and stage-cleanup checks remain in place.

Testing waited until the coordinator explicitly opened the CPU slot. Focused RED command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack:tests python3 -m unittest test_installer.InstallerTests.test_installed_template_artifacts_are_explicit_reusable_source test_installer.InstallerTests.test_source_inventory_rejects_bound_root_or_managed_dir_relocation
```

RED: **exit 1**, 2 tests, 1.011s, `FAILED (failures=1, errors=2)`: the artifact assertion found the two raw `.md` names, and both unrelocated controls exposed the absent template. After correction, the full focused installer command documented above returned **exit 0**, 33 tests, 15.931s, `OK`. `git diff --check` returned **0**. The CPU slot was explicitly released; no full PR gate, Docker, lint/compiler, commit, push or external operation was run by the writer.

Review-correction logs, in the same external cache directory:

| Log | SHA-256 |
| --- | --- |
| `installer-review-red.log` | `c7e8f21742d0d511c3ba294257d481d2a6343f98c59b8470deda4e53874199f6` |
| `installer-review-green.log` | `98dbad5c8e2d8279cc79d9af3b50c1d768ef7742eddb1126de2a8ccf6642a8ed` |

Corrected product bytes tested:

| File | SHA-256 |
| --- | --- |
| `scripts/install_into.py` | `3262984eb74233afb926f6656f9ca11312f0479e3d8a11a2985c0cb5ac63ac49` |
| `tests/test_installer.py` | `cffe0aa66f99648516f00583bcbbb68d5813e72ac51b33c2e156c62ff85cd1e5` |
| `.grok-stack/templates/consumer-AGENTS.md.tmpl` | `5b36af586bc7593021ad4c18b568d0e77c952467a1ee22a1b66a69d9365452b0` |
| `.grok-stack/templates/consumer-factory-README.md.tmpl` | `9f4bbcd60b6f4ed1f5b41e880af9983a2f89594866624a25de4539bffa6b87dc` |

Coordinator-owned shared-memory facts: distinguish shipped rendering inputs from rendered Markdown, and prove installed-source reuse when retaining those inputs. Root cause of the review miss: verification covered rendered destinations but omitted duplicated source artifacts; the relocation fixture likewise lacked a positive control after a new required input was introduced. Both gaps now have explicit regression coverage. Full verification, independent re-review and fresh fingerprint-bound receipts remain pending with the coordinator.
