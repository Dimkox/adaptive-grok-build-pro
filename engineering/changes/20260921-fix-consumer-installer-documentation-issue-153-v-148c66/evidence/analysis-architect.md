# Installer consumer documentation design

Route `148c66d20768`; architect analysis only; 2026-09-21. Baseline frozen PR170 `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. Read route, bootstrap/state, contract, assigned architect instructions, issue153/161 snapshots, prior repo-explorer research and current installer/doctor source. Adaptive-delivery and route bugfix/API skills apply; implementation belongs only to general_implementer. No product changes or execution-success claim.

## Decision and source evidence

Use purpose-built consumer instruction and factory README templates; keep `factory/README.md` a managed output at its existing path. `scripts/install_into.py:548-555` and `:584-597` independently wrap the entire factory root AGENTS text today. Both must render the same consumer template through the existing bounded descriptor-backed source reader, rather than bypassing source-snapshot safety with direct Path reads. A dedicated template under `.grok-stack/templates/` is already inside the managed inventory. Tests must cover the public helper and actual payload to avoid divergent behavior.

A purpose-built README is preferable to transforming arbitrary source Markdown: current factory README also mentions runtime templates and a config under factory/runtime that the installer does not ship, and embeds this factory's historical service observations. Merely replacing ../ links leaves other unavailable local instructions. Keep a concise installed-package explanation, local links only to payload members, and explicit HTTPS upstream documentation links for noninstalled runtime/deployment material. Do not copy factory runtime facts or portray installation as activation. A source-pinned upstream URL is ideal when the source version can be obtained without weakening installer portability; an explicit upstream documentation URL is acceptable without adding Git/network dependencies to payload construction.

## Existing installation and ownership boundary

This installer no longer overwrites an existing target: legacy invocation and `plan_install` produce a read-only plan; `--materialize-new` requires an absent target. `_make_plan:772-831` honors explicit kept-local records and rejects conflicting stack updates. There is no current in-place managed-block updater to extend. Preserve this behavior, and test that planning against an existing AGENTS file containing user text before/after old managed markers leaves its exact bytes unchanged. Do not add an implicit migration or strip user text. Existing consumers require a separately reviewed application of the planned new block, preserving surrounding user content.

Retaining the README path lets future reviewed sync replace its content normally. Simply removing the README from MANAGED_FILES would leave formerly installed broken README files in existing consumers without a deletion/ownership protocol. No destructive retirement is required by the recommended design.

## Consumer instruction contents

- Bootstrap from AGENTS, installed route/status/change tools and durable engineering/changes packages. Missing runtime route is normal; route the task rather than inventing state. Mention consumer START_HERE/PROJECT_STATE/architecture/governance files only conditionally when the consumer has adopted them. Do not ship this factory's state or a fabricated consumer milestone.
- Preserve route-selected roles, one writer, independent reviews, exact fingerprint freshness, PR-only delivery and explicit operation/resource consent. Retain the principle that local evidence/grants are not merge authority and agents cannot handle human approval private keys or change external policy/trust stores.
- Describe external merge checks as the consumer repository's configured authoritative controls. Never transplant this factory's App ID, policy hash, deployment host, mandatory trust-ci directory or immutable factory release observations.
- Preserve secrets/production restrictions and named approval boundaries. Protected policy path patterns can name nonexistent paths: protection is prospective, not a filesystem dependency. Do not delete controls merely because their targets are absent.
- Self-learning files and README/version/architecture obligations must be either actually supplied or explicitly consumer-owned/optional. Do not mandate reading absent mistakes.md or decisions.md. No new hook-platform integration or product-language verification promises in this slice.

## Acceptance and verification design

1. Materialize an absent generic consumer fixture and assert every mandatory consumer bootstrap input is installed; optional files are described as optional. No mandatory factory-only state/trust/runbook obligations remain.
2. Audit links in the installed factory README against the installed tree, not the source tree; every relative file target exists. Upstream links are explicit HTTPS links; no network call is necessary in tests.
3. Verify managed README remains in the payload and manifests match rendered bytes. Root source AGENTS/README stay factory-specific and unchanged.
4. Existing-target plan is read-only with arbitrary user prefix/suffix and old managed markers; kept_local conflicts still refuse. Materialize-new still refuses an existing target. Repeated payload construction is deterministic.
5. Generic and Bitrix payloads retain their existing safety controls and local/AGENTS behavior. Add a targeted check that both managed_agents_text and payload use identical managed content.
6. Run focused installer tests first. Coordinator owns full PR verification and route reviews afterward. Do not expand doctor to parse unrestricted prose: either align the new mandatory list with doctor’s installed baseline, or add a small explicit constant/list for concrete extra required shipped files if one is genuinely introduced.

Rollback is a normal code/template revert for subsequent plans; existing consumers remain untouched until their own reviewed update. Shared-memory fact for coordinator: the current installer is absent-target-only, so upgrade safety means preserving read-only planning and existing user bytes, not introducing an unrequested in-place block mutator.
