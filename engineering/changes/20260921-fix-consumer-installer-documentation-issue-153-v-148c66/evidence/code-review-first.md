# Independent installer code review

Status: **CHANGES_REQUESTED** — one P2 finding. No passing review receipt is authorized by this report.

Reviewed by the selected `code_reviewer` for route `148c66d20768` on 2026-09-21. Implementation belongs to the separate `general_implementer`; this reviewer changed only this report. Read the bootstrap/state, repository contract, active route, selected role, adaptive-delivery/bugfix/API/verification skills, typed change specification, analysis reports, actual product diff and surrounding installer implementation.

## Reviewed identity

- Worktree: `/home/pall/grok-projects/adaptive-grok-build-wave-installer`.
- Product head: `03fbaa91895bffe616d6a61884a7564e6057839a`.
- Review base: `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48` (frozen PR170 head).
- Saved full-gate fingerprint: `ae7f447d3e6b95329865b1913631660aa69d88997d32c3c1297f2dafd149e63a`.
- The four product files had no worktree diff from the reviewed head. `state.json` had a coordinator-owned paperwork change during review; this report is further paperwork. Final fingerprint-bound verification and receipts remain the coordinator's responsibility after repair and final paperwork.

| Product file | Reviewed SHA-256 |
| --- | --- |
| `scripts/install_into.py` | `0e462616136d005dba1b31b198dfac92b9fc1b585e3f75055302edb1560d959f` |
| `tests/test_installer.py` | `b00a9e7851e840a3ea447c86ce81b79f01346c8e2c1230e13adc9903b9ae2dfa` |
| `.grok-stack/templates/consumer-AGENTS.md` | `81b982d71d3418295b6e7b0b511bdc1c887b2d1abd6a83336990024565219309` |
| `.grok-stack/templates/consumer-factory-README.md` | `b2295eccd7393c4dcbaeb137b4702fae90331ebf20360128eea855899bddddd4` |

## P2 — Raw template copies reintroduce broken links into the installed Markdown tree

Location: `scripts/install_into.py:597-600`, `.grok-stack/templates/consumer-AGENTS.md:9-13`, and `.grok-stack/templates/consumer-factory-README.md:3-11`.

`MANAGED_DIRS` includes all of `.grok-stack`, so both new `.md` templates enter the descriptor-validated inventory and are delivered unchanged at their template paths. The README replacement loop changes only `factory/README.md`; it retains both raw template entries. Their relative links are authored for their rendered destinations, not the template directory. Therefore a fresh consumer receives **33 new unresolved local Markdown links**: 16 in the AGENTS template and 17 in the README template.

For example, the raw README template's `src/adaptive_factory/` link resolves to `.grok-stack/templates/src/adaptive_factory/`, and its `../AGENTS.md` link resolves to `.grok-stack/AGENTS.md`; neither path is delivered. The raw AGENTS template's `.agents/skills/adaptive-delivery/SKILL.md` link resolves to `.grok-stack/templates/.agents/skills/adaptive-delivery/SKILL.md`, also absent. Static path inspection confirmed all 33 unresolved destinations; source inventory and the unchanged entries establish that the same paths are emitted to an absent target.

This matters to issue #153's stated consumer Markdown-audit problem: the rendered factory README is repaired, but a repository-wide audit remains red because the fix adds new broken Markdown under `.grok-stack/templates/`. Existing change templates keep their linked `change-spec.yaml` as a sibling, so they do not explain or require these new failures. The regression test audits only rendered `AGENTS.md` and `factory/README.md`, omitting the two new Markdown copies.

These files are intentional rendering inputs, distinct from the rendered consumer documentation, and remain necessary when a consumer is used as an installation source. Preserve those inputs in an explicitly identified template-source format rather than shipping them as Markdown with invalid destinations, or make every delivered Markdown copy's links valid for its actual location. Do not simply remove required inputs or add a blanket checker exemption. Retain descriptor-bounded source reads, deterministic rendered hashes and the managed `factory/README.md` ownership contract. Extend the installed-tree regression to account for the template artifacts as well as rendered documents.

## Other reviewed behavior

- The shared AGENTS renderer preserves marker spelling and UTF-8 handling. Payload rendering consumes validated inventory bytes; it does not add unrestricted `Path.read_*` source reads or reopen templates after snapshot validation. The existing duplicate-path, collision, no-follow and size-bound protections remain.
- `factory/README.md` remains at its managed path, retains its prior mode, and hashes the replacement bytes through `InstallEntry`. Generic/Bitrix sorting and Bitrix `local/AGENTS.md` generation are unchanged.
- Existing-target planning, kept-local conflict handling, and absent-target-only materialization are unchanged. The new preservation fixture covers user prefix/suffix bytes, CRLF, an invalid UTF-8 user byte, old markers, existing-target refusal and the old README kept-local conflict.
- The rendered consumer instructions name shipped workflow entrypoints, make consumer handoff/state/version/architecture/shared-memory files conditional, and retain one writer, independent review, PR-only delivery, exact operational consent, private-key restrictions and external merge authority. Factory-root instructions, policy, README and Bitrix local guidance are unchanged.
- Upstream references are explicitly labeled as the v2.0.18 snapshot and installation is distinguished from operational activation. No source change claims hook registration, deployment, a provider call or a consumer upgrade.

## Saved verification inspected and limits

Read the raw evidence under `/home/pall/.cache/agbp-run/issues-wave-20260921/installer/`; independently checked its hashes rather than relying only on the writer report.

- `installer-red.log`: 32 tests, `FAILED (failures=3, errors=2)`, including the nine original installed README link failures. SHA-256 `fe988a18c67ba24758d5f75392425fb3b840e3a003681eebfa24b87b1da3989f`. The original wrapper did not preserve a numeric unittest exit; the failure is explicit in the log.
- `installer-green.log`: 32 tests, 14.757 seconds, `OK`. SHA-256 `3160794321e1c585e0af5ce831746ba57a3515b1366e15f8a5832503ce4b202a`.
- `verify-initial-meta.json`: exact reviewed head, `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json`, exit 0, 07:26:34–07:34:45 UTC. SHA-256 `49f883ad03b1e658d7baa3720579d391def02431299c5c32db9b194188a9d592`.
- `verify-initial.json`: route matches; `base`/`contracts` profiles and overall `pass`; source-stability pass at the fingerprint above. Checks include lint, unit, coverage and disposable PostgreSQL verification; workflow artifacts are explicitly not configured. SHA-256 `be158ecf55768707542f7de6006a70ea348c8d729e05911bd88fabecf42d34b6`.

No tests, linter, compiler, Docker, host operation, network lookup, secret read or GitHub write was run by this reviewer. Review helpers only inspected source, Git identity/diffs, static link destinations and saved logs. These saved passing suites do not cover the raw-template link regression. Repair must return to the sole implementation owner, followed by appropriate verification and independent re-review. This report is local workflow evidence only and supplies no external Trust CI, signed approval or merge authority.
