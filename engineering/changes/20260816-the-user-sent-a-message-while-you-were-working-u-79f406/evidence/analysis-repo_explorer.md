# Analysis — repo_explorer

Change: `20260816-the-user-sent-a-message-while-you-were-working-u-79f406`  
Route: `79f406e449de` · write owner: `ai_implementer`  
Question: list every root/product file a new LLM agent must open for current-state context. Note what current README omits.

Identity now: `VERSION` = **2.0.8**. README title is 2.0.8. Graph is already **K10 / 45 edges** (locked by `tests/test_structure.py`). README has **zero markdown links**. Stay on 2.0.8; do not explode mermaid.

## Read first (order)

A new agent should open these **in this order** before writing anything:

| # | File | Why |
| --- | --- | --- |
| 1 | [`VERSION`](../../../../VERSION) | Product identity. Must stay `2.0.8`. |
| 2 | [`README.md`](../../../../README.md) | Intended map. Incomplete today. |
| 3 | [`QUICKSTART.md`](../../../../QUICKSTART.md) | Human/TUI install + `/hooks-trust`. |
| 4 | [`CHANGELOG.md`](../../../../CHANGELOG.md) | What 2.0.8 / 2.0.7 / 2.0.6 actually shipped. **Stale on 2.0.8 log paths** (see below). |
| 5 | [`AGENTS.md`](../../../../AGENTS.md) | Contract. First heading is Agent self-learning. Entrypoint: read active-route, invoke `/adaptive-delivery`. |
| 6 | [`decisions.md`](../../../../decisions.md) | Canonical “what worked”. Root file, not `engineering/`. |
| 7 | [`mistakes.md`](../../../../mistakes.md) | Canonical root causes. Root file, not `engineering/`. |
| 8 | [`.grok-stack/runtime/active-route.json`](../../../../.grok-stack/runtime/active-route.json) | This session’s authority (agents, evidence, write owner). |
| 9 | [`.grok/skills/adaptive-delivery/SKILL.md`](../../../../.grok/skills/adaptive-delivery/SKILL.md) | Delivery loop. |

Then the maps below. Stubs [`engineering/decisions.md`](../../../../engineering/decisions.md) and [`engineering/mistakes.md`](../../../../engineering/mistakes.md) say “Moved / Do not append here”.

## Root product files

| Path | Role | In README today |
| --- | --- | --- |
| `VERSION` | Single version source. `__version__` must match. | Title only; **no file link**. |
| `README.md` | Human/LLM front door. | Self. |
| `QUICKSTART.md` | 7-step install / verify / trust. | **Omitted.** |
| `CHANGELOG.md` | Release history 2.0.0–2.0.8. | **Omitted.** |
| `AGENTS.md` | Engineering contract + self-learning. | Named in prose + graph node; **no `[AGENTS.md](AGENTS.md)`**. |
| `decisions.md` | Live decision log. | Named + graph; **no link**. |
| `mistakes.md` | Live mistake log. | Named + graph; **no link**. |
| `LICENSE` | MIT. | Word “MIT”; **no file link**. |
| `Makefile` | `doctor` / `verify` / `status` / `package` / `deploy`. | Mentions `make doctor` / `make verify` only. |
| `ruff.toml` | Ruff config. No `pyproject.toml`. | **Omitted.** |
| `bandit.yaml` | Bandit excludes + skips. | **Omitted.** |
| `.coveragerc` | Coverage.py; `fail_under = 74`. | Number 74 only; **no file**. |
| `user_prompt_submit.py` `pre_tool_use.py` `post_tool_use.py` `pre_compact.py` `session_start.py` `session_end.py` `stop_gate.py` `subagent_start.py` `subagent_stop.py` | Root fail-open shims → `.grok/hooks/`. No root `_lib.py`. | Hooks section never names the shims. |

Do **not** add `pyproject.toml` / `requirements.txt` / `setup.py` / `.github/workflows/`.

## Scripts

| Path | Role | In README scripts table |
| --- | --- | --- |
| `scripts/grok_route.py` | Classify / show route | yes |
| `scripts/grok_change.py` | Durable change package | yes |
| `scripts/grok_status.py` | Runtime status | yes |
| `scripts/grok_verify.py` | Quality gate | yes |
| `scripts/grok_review.py` | Review receipt | yes |
| `scripts/grok_approve.py` | Short-lived approval | yes |
| `scripts/grok_deploy.py` | Prepare-only last mile | yes |
| `scripts/grok_doctor.py` | Toolchain health | yes |
| `scripts/install_into.py` | Install stack + deps | yes |
| `scripts/package_stack.py` | Build zip | later section only |
| `scripts/generate_manifest.py` | Emit package manifest | **no** |
| `scripts/verify_manifest.py` | Check manifest | **no** |
| `scripts/bootstrap.sh` | Doctor + install self + unittest | **no** |
| `scripts/bootstrap.ps1` | Windows twin | **no** |

`managed.json` scripts list is the eight `grok_*.py` files (no installer/packager).

## Skills (15) — `.grok/skills/<name>/SKILL.md` and mirror `.agents/skills/`

| Skill | Use |
| --- | --- |
| `adaptive-delivery` | Every routed delivery. Controller. |
| `task-triage` | Ambiguous / classify first. |
| `feature-workflow` | New behavior. |
| `bugfix-workflow` | Defect + failing regression test. |
| `verification-evidence` | Bind tests/reviews to fingerprint. |
| `release-readiness` | Go/no-go, last mile. |
| `ai-rag-change` | LLM / RAG / eval. |
| `api-event-change` | HTTP / events / queues. |
| `data-change` | SQL / migrations / search / CH. |
| `frontend-change` | Browser UI. |
| `bitrix-development` | Bitrix/D7 (+ `references/`). |
| `enterprise-integration` | 1C / SAP / ERP / payments. |
| `security-sensitive-change` | Auth / secrets / PII / prod. |
| `incident-response` | Outage / containment first. |
| `legacy-modernization` | Behavior-preserving rewrite. |

Bitrix extras: `references/architecture.md`, `events-agents-cache.md`, `modules.md`, `testing-review.md`.  
README: one ellipsis line. **No skill names, no links.**

## Agents (21) — `.grok/agents/<name>.toml` + `.md`

`repo_explorer`, `task_analyst`, `architect`, `docs_researcher`, `ai_architect`, `bitrix_architect`, `data_architect`, `integration_architect`, `ai_implementer`, `bitrix_implementer`, `data_implementer`, `frontend_implementer`, `general_implementer`, `integration_implementer`, `php_implementer`, `code_reviewer`, `test_reviewer`, `security_reviewer`, `release_reviewer`, `bitrix_reviewer`, `data_reviewer`.

Floors live in [`.grok-stack/config/routing.json`](../../../../.grok-stack/config/routing.json) (`max_parallel_analysis` = 10, exactly one write owner). Roster: [`managed.json`](../../../../.grok-stack/config/managed.json).  
README: “multi-agent discipline in AGENTS.md”. **No roster.**

## Hooks

Canonical: [`.grok/hooks/`](../../../../.grok/hooks/). Register in both [`.grok/hooks.json`](../../../../.grok/hooks.json) and [`.grok/hooks/adaptive.json`](../../../../.grok/hooks/adaptive.json).

Events: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `SubagentStart`, `SubagentStop`, `Stop`, `SessionEnd`.

Read: [`.grok/hooks/README.md`](../../../../.grok/hooks/README.md), `_lib.py`, the nine `*.py` implementations, plus the nine root shims. Policy: [`.grok-stack/adaptive_grok/policy.py`](../../../../.grok-stack/adaptive_grok/policy.py) + [`config/policy.json`](../../../../.grok-stack/config/policy.json). Project config: [`.grok/config.toml`](../../../../.grok/config.toml).

README: trust + fail-open paragraph. **No event list, no shim list, no `hooks/README.md` link.**

## Runbooks / engineering / docs / examples

| Path | Role | In README |
| --- | --- | --- |
| `engineering/runbooks/publish-v2.0.4.md` … `publish-v2.0.8.md` | Human last-mile publish (CLI, not GHA) | **Omitted.** |
| `engineering/changes/` | Durable change packages | Named, no current-package pointer |
| `engineering/adr/` | ADR tree (empty) | **Omitted.** |
| `engineering/contracts/{openapi,asyncapi,schemas}/` | Empty contract scaffolds | **Omitted.** |
| `engineering/reviews/` | Review report sink (installer ENSURE) | **Omitted.** |
| `docs/bitrix-local-AGENTS.md` | Copied to consumer `local/AGENTS.md` | **Omitted.** |
| `examples/bitrix-module/` | D7 reference module | one line |
| `examples/contracts/` | Sample OpenAPI / AsyncAPI / JSON Schema | **Omitted.** |
| `packages/README.md` | Tracked zips 2.0.0–2.0.8 | `packages/` named only |
| `.grok-stack/templates/change/` | New-package templates | **Omitted.** |
| `.grok-stack/templates/ci/README.md` | “Never GitHub Actions” | **Omitted.** |
| `.grok-stack/templates/hook_root_shim.py` | Shim template | **Omitted.** |

## Config / runtime / tests (needed for current state)

| Path | Role | In README |
| --- | --- | --- |
| `.grok-stack/config/toolchain.json` | Pins (min / built / fallback) | yes (one line) |
| `.grok-stack/config/routing.json` | Analysis/review floors | **Omitted.** |
| `.grok-stack/config/quality-profiles/{base,ai,bitrix,contracts,data,frontend,infra,integration,php}.json` | Check sets | “quality profiles” unnamed |
| `.grok-stack/adaptive_grok/*.py` | Product runtime | Policy path only |
| `tests/test_*.py` (13 + `_support.py`) | Characterization / structure locks | **Omitted.** |
| Runtime `active-route.json`, `active-change.json`, `receipts/`, `last-fingerprint.json` | Live session | “active-route” in table only |

## What current README omits

1. **No markdown links at all.** Paths are backticks. A human or agent cannot click through. Architecture for this change: add **Current state** + **Read first** + **Map** with real links; keep K10.
2. **No read-first order.** An LLM landing on README does not know to open `VERSION` → contract → logs → active-route → `/adaptive-delivery`.
3. **No current-state block.** Missing: `VERSION` file, `CHANGELOG` 2.0.8 bullets, no GitHub Actions, coverage 74 from `.coveragerc`, local-only gate, published zip at `packages/adaptive-grok-build-pro-v2.0.8.zip`.
4. **Does not name or link** `QUICKSTART.md`, `CHANGELOG.md`, `LICENSE`, `Makefile`, `ruff.toml`, `bandit.yaml`, `.coveragerc`, runbooks, `routing.json`, quality-profile files, `managed.json`, `policy.json`, `docs/bitrix-local-AGENTS.md`, `tests/`, bootstrap, manifest scripts, engineering stubs, ADR/contracts scaffolds.
5. **Skills/agents/hooks are not enumerated.** 15 skills, 21 agents, 9 hook events + 9 root shims are the product. README has a K10 blob and a Bitrix one-liner.
6. **Copy-list lie.** README tells the reader to copy `decisions.md` / `mistakes.md`. `scripts/install_into.py` `MANAGED_FILES` does **not** copy them (only merges `AGENTS.md` and ENSUREs empty `engineering/` dirs). Either fix the installer or stop claiming the copy.
7. **“Never GitHub Actions” is not in README.** Locked in tests, `install_into --with-ci`, `templates/ci/README.md`, `decisions.md`. Architecture wants that wording in README.
8. **Stale sibling doc:** `CHANGELOG.md` 2.0.8 still says AGENTS.md logs to `engineering/decisions.md` / `engineering/mistakes.md`. Live `AGENTS.md` + tests require **root** `decisions.md` / `mistakes.md`. 2.0.4 changelog still mentions this-repo GitHub Actions.

## Impact (write owner)

- Primary edit: `README.md` (Current state + Read first + linked Map; keep 10 nodes / 45 `---` edges; stay 2.0.8).
- Tests: extend `tests/test_structure.py` per `architecture.md` / `test-plan.md` (names/links + existing K10 + self-learning + no GHA).
- Optional honesty fix (only if README keeps the copy-list claim): `scripts/install_into.py` + `tests/test_installer.py` for root logs.
- Optional sibling fix: `CHANGELOG.md` 2.0.8 path line. Do not bump `VERSION`.
