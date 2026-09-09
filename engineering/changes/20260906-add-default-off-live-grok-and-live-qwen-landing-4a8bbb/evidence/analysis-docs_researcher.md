# Docs research — live Grok/Qwen landing + Python/system pins

Product tree: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-live` (origin/main).
Change: `engineering/changes/20260906-add-default-off-live-grok-and-live-qwen-landing-4a8bbb`.
Route: `4a8bbb4fa8a6`. No `.env` or credentials were read. Secret values are not invented; `.env.example` uses documented placeholders only.

## Task as documented

Change brief/requirements are still templates. User intent (route task + brief): add **default-off live Grok and live Qwen** landing executors, and **write explicit Python/system requirements against the current host configuration**. Constraints named in the change title: **no live API calls in tests; no landing-repo mutation**.

## What already exists (do not invent APIs)

### `compose_landing_live` (factory README + `landing_runtime.py`)

- Factory README (`factory/README.md`): default-off `compose_landing_live` automatically **normalize → render → evaluate → seals** the 20-member L5 artifact **when a caller injects a live executor**. Shipped server path stays **unavailable**; every result keeps **`live_url` null**; landing source pin is unchanged.
- `decisions.md` (2026-09-06): composition runs only when a caller injects an **enabled binding and executor**. Observed landing SHA `80d6215` **fails closed** until a reviewed renderer/inventory refresh.
- `factory/src/adaptive_factory/server.py`: comment that live landing composition is **constructor-injected only** (`compose_landing_live`). Default server composition uses `UnavailableLandingProvider` when `FACTORY_LANDING_QUARANTINE_PATH` is set.
- Function signature (`compose_landing_live`): requires `binding: LandingLiveBindingV1`, `profile: CodexLandingProfile`, `executor: CodexLandingExecutor`, absolute `source_repository` / `scratch_root` / `output_directory`, `blobs`. Fail-closed errors: `live_disabled` (binding not enabled), `source_binding_unimplemented` (SHA/tree ≠ pins), `profile_unavailable`, `executor_required`, `output_path`.
- `implemented_live_binding(enabled=False)` is the default-off constructor.
- Executor protocol (`CodexLandingExecutor`): `run(CodexExecutionRequest) -> CodexExecutionResult`. `CodexLandingNormalizer` docstring: **repository ships no live executor**.
- Available profile requires `cli_version == SUPPORTED_CODEX_CLI_VERSION` (`"0.153.4"`), absolute executable, pinned prompt/output-schema SHA-256s. Profile identifiers are generic strings (`profile_id`, `provider_id`, `model_id`); they are **not** currently named grok/qwen.
- Tests (`factory/tests/test_landing_live.py`) use **`RecordingExecutor`** and fixture Codex profile (`codex-offline-fixture`), not network.

**Gap:** there is **no** live Grok executor, **no** live Qwen executor, and **no** second provider type besides `CodexLandingProfile` + injected `CodexLandingExecutor`. M5 `GrokAdapter` (`factory/src/adaptive_factory/adapters/grok.py`) is a **fixture translator** (`execution_eligible=False`, `native_version="1.0.17"`) and is **not** the landing live path.

Landing pins documented in README and renderer: source SHA `699010380f4f90a0193a9c22090c35e6aded7d2c`, tree `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`. Pilot runbook records **unmet** live precondition: observed `main` `80d621545938e24c296420d7f685f2d0b2b5785e` / tree `a1c2eff37ec808a53b2aeec089a5f6d7cb72bd55`.

### `factory/pyproject.toml`

- `requires-python = ">=3.11"`
- `setuptools==75.8.0`
- Runtime deps (exact): `fastapi==0.128.2`, `httpx==0.28.1`, `uvicorn==0.48.0`, `psycopg[binary]==3.3.4`
- Console scripts: `adaptive-factory`, `adaptive-factory-server`, `adaptive-factory-admin`
- `factory/uv.lock`: `requires-python = ">=3.11"` (lockfile present)
- Same Python floor in `delivery/pyproject.toml` and `trust-ci/pyproject.toml`

**Tension to document, not invent:** repo toolchain/README **minimum Python 3.10**, **built 3.12.3**; factory package **requires ≥3.11**. Pilot host pin is **`/usr/bin/python3.12`**.

### `factory/.env.example` (placeholders only; do not copy production)

Documented names:

| Name | Example (placeholder) |
| --- | --- |
| `FACTORY_POSTGRES_DB` | `factory_local` |
| `FACTORY_POSTGRES_USER` | `factory_owner` |
| `FACTORY_POSTGRES_PASSWORD` | `replace-owner-for-local-use` |
| `FACTORY_POSTGRES_PORT` | `55432` |
| `FACTORY_MIGRATOR_DATABASE_URL` | `postgresql://factory_owner:replace-owner-for-local-use@127.0.0.1:55432/factory_local` |
| `FACTORY_RUNTIME_LOGIN` | `factory_service` |
| `FACTORY_RUNTIME_PASSWORD` | `replace-runtime-for-local-use` |
| `FACTORY_DATABASE_URL` | `postgresql://factory_service:replace-runtime-for-local-use@127.0.0.1:55432/factory_local` |
| `FACTORY_SOCKET_PATH` | `/run/adaptive-factory/control.sock` |
| `FACTORY_ACTORS_FILE` | `/run/secrets/adaptive-factory-actors.json` |

README: never inspect an existing `.env`; placeholders only.

**Also read by code (`settings.py` / `admin.py`) but not listed in `.env.example`:** `FACTORY_ARTIFACT_ATTESTOR_DATABASE_URL`, `FACTORY_EXECUTION_ENABLED` (must be `"true"`/`"false"`, default `"false"`), `FACTORY_SEMANTIC_COORDINATOR_DATABASE_URL`, `FACTORY_SEMANTIC_VALIDATOR_DATABASE_URL`, `FACTORY_SEMANTIC_ADJUDICATOR_DATABASE_URL`, `FACTORY_LANDING_QUARANTINE_PATH` (absolute, no `..`), `FACTORY_ARTIFACT_ATTESTOR_LOGIN` / `FACTORY_ARTIFACT_ATTESTOR_PASSWORD`. Tests use `FACTORY_TEST_DATABASE_URL`. **No Grok/Qwen/XAI API key names exist in factory env.** Pilot `api_key_exec` mentions `CODEX_API_KEY` in process environment only (Codex fallback, not factory landing).

`factory/compose.yaml`: **postgres:17-alpine** only; bind `127.0.0.1:${FACTORY_POSTGRES_PORT:-55432}:5432`; required compose env `FACTORY_POSTGRES_DB/USER/PASSWORD`.

### Pilot runbook host pins (`engineering/runbooks/design-partner-pilot-v2.0.15.md`)

Observed identities for the intended first run (regular, non-symlink files, SHA-256):

| Tool | Path | SHA-256 |
| --- | --- | --- |
| Codex 0.153.4 | `/home/pall/.codex/packages/standalone/releases/0.153.4-x86_64-unknown-linux-musl/bin/codex` | `56ef98ab4032d317ab26e9b5e5a175650717351edb16ed9cde0cb6d1734d62da` |
| Python | `/usr/bin/python3.12` | `a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223` |
| Git | `/usr/bin/git` | `2a8c18fbf43da9f692d75474c72bea9dfd796c260b0f3dfe456376abc3bbd668` |
| GitHub CLI | `/snap/gh/751/gh` | `527dc63b37f57451641228fd55079140073b78e333d7bcaca33587a9e5bc97f3` |
| bubblewrap | `/usr/bin/bwrap` | `52231e1caf55bcbc667b269f49c63599a6f7db4767ae6a039580d0ff853db712` |

Config schema_version **2** also pins `python_executable` / `python_sha256` and Codex `0.153.4` / `gpt-6-astra` for `provider_mode=app_server_chatgpt`. That is the **pilot** closed profile, not a factory live Grok/Qwen API.

Other host constraints from the same runbook: umask `077`; operator-owned `0700` runtime parent; disjoint `0700` child roots; exact landing clone; config file mode `0600`, one link, ≤16 KiB.

### Repo-wide toolchain (README + `.grok-stack/config/toolchain.json`)

Policy: **minimum or newer**; `built` is the tested pin.

| Tool | Minimum | Built | Fallback | Required |
| --- | --- | --- | --- | --- |
| Python 3 | 3.10 | 3.12.3 | 3.12 | yes |
| Git | 2.34 | 2.43.0 | 2.43 | yes |
| Grok Build CLI | 1.0.0 | 1.0.5 | 1.0.5 | TUI |
| GitHub CLI | 2.40 | 2.86.0 | 2.86 | release |
| Node.js | 18 | 24.19.0 | 20 | frontend |
| npm | 9 | 11.17.0 | 10 | frontend |
| PHP | 8.1 | 8.2 | 8.2 | Bitrix |
| Composer | 2.2 | 2.7 | 2.7 | Bitrix |
| Docker | 24.0 | 29.7.2 | 29 | Trust CI optional |
| Syft | 1.0 | 1.51.0 | 1.51 | optional |
| Trivy | 0.50 | 0.74.0 | 0.74 | optional |
| Cosign | 2.0 | — | 2.4 | optional |

Factory README additionally: **PostgreSQL 17** (`transaction_timeout`); schema readiness version **17**; Unix socket default `/run/adaptive-factory/control.sock` mode `0660`; **no TCP**; actor/token files absolute, owner-pinned, mode `0600`; `FACTORY_EXECUTION_ENABLED` off by default.

`engineering/adr/` is empty in this tree. No ADR defines Grok/Qwen landing executors.

## Facts implementers must not invent

- No factory OpenAPI operation for “live grok” or “live qwen”.
- No env vars for Grok/Qwen API keys in `.env.example`.
- Live landing is **injection + `binding.enabled`**, not an env flag in the shipped server.
- Tests must keep using injected fakes; README and change title forbid live provider calls and landing-repo mutation.
- Host Python pin for pilot is **3.12** at `/usr/bin/python3.12` with the SHA above; factory packaging requires **≥3.11**; stack doctor minimum is **3.10**.

## Suggested documentation surface for this change (not an API)

If executors are added, document them as **default-off injected `CodexLandingExecutor` implementations** (or a new named protocol if contracts are extended), pin **Python ≥3.11** for factory plus host **3.12.3 / `/usr/bin/python3.12`** SHA from the pilot runbook, keep `compose_landing_live` fail-closed on SHA `80d6215…`, and list PostgreSQL 17 + the `.env.example` names without secret values.
