# Integration analysis: consumer installer docs (#153, #161)

Status: ready for the selected single writer. Read-only analysis against the frozen `1f7aedb8` wave base; no gate or install was run.

## Boundary and mechanism

`scripts/install_into.py:17-75` explicitly includes `factory/README.md` in `MANAGED_FILES`, while `MANAGED_DIRS` contains only the factory contracts/source subtrees. The README points at `../engineering/runbooks/*`, `../DARK_FACTORY_ROADMAP.md`, and the factory root README. Those files are absent from the consumer payload, so its relative links cannot resolve. `build_payload()` at lines 574-609 separately reads the repository-root `AGENTS.md` verbatim, wraps it in managed markers, and installs it as consumer `AGENTS.md`. That contract names `START_HERE.md`, `PROJECT_STATE.json`, `mistakes.md`, `VERSION`, `architecture/*`, and `trust-ci/*` as mandatory/current files or locations although they are not installed. It also describes factory-only release and Trust CI operation as though the consumer owns them.

The safe seam is consumer-specific generated content in `build_payload`, not editing the factory-root `AGENTS.md` into a less precise contract. A portable README should be an installed managed entry with working links to either other delivered files or stable source URLs. The consumer contract should name only shipped files or clearly state when a target-owned file is optional. Preserve the explicit trust boundary: local verification/receipts never substitute for the App-owned exact-SHA check or signed security approvals. Do not copy factory `PROJECT_STATE.json`, deployed policy, runbooks, or factory release obligations into a consumer just to satisfy a link.

## Installer compatibility and ownership

`_make_plan()` at lines 772-826 is read-only for existing targets and honors `.grok-stack/AGBP_SYNC.json` `kept_local`; `_materialize_new()` at 1242-1320 atomically writes only an absent target. Therefore removing `factory/README.md` from the payload does **not** uninstall an older managed copy in an existing consumer. Document that carry-forward explicitly or keep a repaired portable README at the same managed path. The latter gives fresh installs a useful file without pretending that old installs update automatically. A new managed consumer file also changes the plan manifest; `tests/test_installer.py:197-213` recomputes source parity except synthesized `AGENTS.md`, and `:301-320` currently requires `factory/README.md`. Adjust the test expectation deliberately if dropping it. Keep managed marker preservation and `kept_local` ownership intact; no target-owned AGENTS text may be rewritten by this factory-side change.

`policy.json`'s `control_plane_paths` includes factory names absent from consumer installs. That list is a protection-pattern policy, not proof that those files ship. Issue #161 is satisfied by making the installed *instructions* honest about the payload; a broad policy rewrite is outside this bounded documentation fix. If a validator is added later, it must compare consumer-required paths to the actual installed manifest, not the factory source tree.

## Focused acceptance

Build both generic and Bitrix payloads and inspect the synthesized `AGENTS.md` plus `factory/README.md` entry. Assert all mandatory consumer paths exist in the payload or are explicitly target-owned/optional; all relative links in installed Markdown resolve within payload, with external source links treated separately. Assert factory root `AGENTS.md` remains authoritative for factory work, user-owned AGENTS content remains outside managed markers, `kept_local` plan behavior is unchanged, and existing-target execution stays read-only. No Docker or external consumer write is needed for these tests.
