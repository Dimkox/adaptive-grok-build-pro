# Independent code review — split E

Verdict: PASS for the dedicated Unix landing host/private configuration slice. No blocking correctness or security finding identified in the actual E diff and surrounding implementation. Corrected D ownership/path behavior remains present.

## Exact identity and scope

- Route: `ae4f5afb69ca`; change: `20260913-l5-split-e-private-configuration-and-dedicated-u-ae4f5a`.
- Immutable source HEAD: `d33e8d8b2aa06a76f32724d08d79a21f3604ce42`.
- Genuine route predecessor: `d1fdb7aec61b242c1a2fc5fc0ced1809e1b79c76`.
- Actual corrected stacked-PR predecessor: D `bb93885034e52b80653efd96602fec182f7db10a`.
- Independently recomputed clean-tree fingerprint: `51779c0ff12044c794cd706c892e6881c194c9fb13af84c6f147f5e921dbe885`.
- Independent reviewer: `code_reviewer`; application/test write owner: `integration_implementer`.

Read the active route, reviewer role, requirements, architecture, test plan, rollback and delivery documentation. Inspected all eight E product/test changes against corrected D and the genuine route diff, distinguishing the inherited D repair from the E vertical. Reviewed the complete dedicated host/configuration implementation and host tests, surrounding API middleware/authentication/route registration, common actor/private-file/socket helpers and durable composition lifecycle.

## Findings and reasoning

The private configuration loader accepts a closed version-1 object with exact boolean enablement and one of three explicit capability profiles. Every configured path and the configuration file itself reject `//` anchors and parent traversal. The seven directory roots are checked for equality and either ancestry direction; configuration, actor configuration and socket paths must be outside them. File reading uses the existing bounded descriptor-based private-file checks, including no-follow traversal, ownership and mode requirements. Default-off config selects the unavailable provider while retaining the declared capability for explicit future enablement; no ambient database URL is used by this host.

The added host composes the existing durable SQLite landing service after validating the publication-state directory. Optional Qwen credential paths are checked against all host roots, and D's live path further validates normalized paths before source/ownership/credential work. The actual default-off host test patches PostgreSQL constructors, source validation and credential acquisition to fail if invoked; it submits an authenticated request through FastAPI, persists a terminal unavailable job to real SQLite, verifies input quarantine cleanup, then reopens the database after lifespan exit. This is a working offline host path and makes no claim of a real provider operation.

`landing_only` is a guarded API composition mode: it requires only a landing service with execution disabled. The same authentication, correlation, body and repository/tenant checks remain attached to landing routes. Application construction returns before task/worker routes are registered; metrics returns 404 and readiness explicitly identifies the local landing component with `production_verified: false`. The dedicated app creates no PostgreSQL store or readiness-discovery call. Existing full Factory composition remains the default when the flag is absent.

Lifecycle ownership is explicit. Actor-loading/authenticator/application-build failures and BaseException during construction close the acquired runtime. The dedicated lifespan closes it on normal or exceptional exit. Main closes the listener, then the owned runtime, then checks the socket path through independent cleanup stages. Unlink requires the captured device/inode, socket type and current effective owner; regular-file, symlink, different-socket and owner-change replacements remain intact. Failure to capture the startup identity does not authorize deleting an unidentified socket. Repeated store close remains harmless. Tests use real temporary Unix sockets and real SQLite writer locks for the relevant resource checks, with mocked Uvicorn execution and synthetic authentication data.

The exact architecture inventory increases from 19 to 20 modules by adding `landing_host.py` to the existing host boundary and LOCAL-API ownership; its independent test gets the same explicit owner. `landing_host_config.py` stays in the offline group. Only the `adaptive-landing-server` console entry point is added; E adds no service installer, publication operation or backup module.

Independently compared inherited D `settings.py`, `server.py`, `landing_sqlite_store.py` and `test_landing_server.py` byte-for-byte against corrected D `bb93885034e52b80653efd96602fec182f7db10a`. All match. Therefore the shared `//` rejection, existing-server independent cleanup and SQLite constructor fixes are retained rather than relying on the dedicated loader to hide an earlier defect.

## Verification examined

The completed `split-e-full-final.json` reports PASS for this exact route, HEAD and fingerprint. All mandatory recorded checks pass, including architecture/drift/diagrams, governance, contracts/static/security checks, 653 core tests, coverage, factory checks, PostgreSQL verification (655 run, one skipped) with two actual restarts and exact-role recovery/reconciliation, and source stability. Historical package descriptions of verification as pending were not treated as fresh results.

A bounded independent rerun of four host regression methods passed in 0.895 seconds: actual offline API/SQLite persistence, replacement file/symlink/socket preservation, listener-close failure cleanup and runtime-close failure cleanup. The complete host test module was inspected, including closed config/path matrices, authentication exposure, credential ordering, competing writers, build/lifespan/startup failures, ownership changes and missing socket identity. No full suite was repeated.

## Limits

PASS is independent local code-review evidence for E; it is not external exact-SHA App Trust CI, a signed approval or merge authority. Configuration and filesystem ownership remain trusted local operator inputs; the application checks do not claim protection against a malicious process with the same operating-system identity. No F publication/G backup/runtime installation was required or assumed. Rollback stops the dedicated host and retains compatible D V1/V2 readers and durable state rather than replaying ambiguous provider work. No real credential, provider request, deployment, external write, source edit or self-issued receipt was performed by this reviewer.

## SHA-256 inventory of the eight E product/test changes

- `architecture/rules.yaml`: `7c9fe6b4d83badf7bab9d329321077af4cdf9de5f3925ca6540972d66d8572e6`
- `architecture/system.yaml`: `7da4656d765d815861a476f7b83464d4c3c97dd11f24966a033732427825f44f`
- `factory/pyproject.toml`: `ed1909b4db850de77164b2bede110174331fc644e8dec4a31b610c0ea9a9293d`
- `factory/src/adaptive_factory/api.py`: `057319cdbe6b36483da18ae0a20cda858eafd0dfb52ab380be42b684189153ed`
- `factory/src/adaptive_factory/landing_host.py`: `e6a81070e98d3a85769c5213c0cd9a3df2751387d1965b1805432053b4c59ebf`
- `factory/src/adaptive_factory/landing_host_config.py`: `eaafbfb3de12a1813090dc4a3f3f8be1d7ef82b6e46a9fb2efd6b3b7c15ee945`
- `factory/tests/test_landing_host.py`: `6d4e8942adbc5e918d3db7f4fe428e67d4a1d98ee56aa8dd330caa9cd7f2552e`
- `tests/test_landing_architecture_boundaries.py`: `225bd365e0ec121065b464dcfa57c273d06471cf4edb06c8cde4a77b3279cedf`

## Verified inherited D repair bindings

- `factory/src/adaptive_factory/settings.py`: `0241a3e27200444bc3114da6e9c2940c6551d6db9e2112e74d6ab4c056c6dd02`
- `factory/src/adaptive_factory/server.py`: `825e594624e35b4459cf66d35873eaf62c854391aba70ea31f94c7ec41dae358`
- `factory/src/adaptive_factory/landing_sqlite_store.py`: `7b9e677d1d1b04a87b62a2c985be026c71420c64eb559bab9d5fb6bb3f44806a`
- `factory/tests/test_landing_server.py`: `1a70c29bc8a5436017cb1b25d5b7ec2d780f90a15210af3249e5e1885dfcd671`
