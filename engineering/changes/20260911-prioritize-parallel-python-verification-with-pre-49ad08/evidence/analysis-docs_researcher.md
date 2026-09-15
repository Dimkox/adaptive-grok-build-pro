# Python parallel verification: dependency and coverage integration analysis

Route `49ad08e34053`; source base `64378d28c7b78cace463d96470c1898294b8f196`; analysis date 2026-09-11. Source/docs read only; no installations, tests, model calls, credentials or deployed-state access. Sole product writer: `general_implementer`.

## Existing locations and constraints

| Location | Current behavior / implication |
| --- | --- |
| `.grok-stack/config/toolchain.json:1` | Shared tool advice; policy is `minimum_or_newer`, `built` denotes tested version. Python minimum 3.10, built 3.12.3. No pytest, xdist, pytest-cov or coverage entries currently. |
| `.grok-stack/adaptive_grok/toolchain.py:77` | `detect_command` checks executable names and parses the first version number from command output. This cannot identify a Python plugin merely by executing `pytest --version`. |
| `README.md:443` | Requirements table and doctor install-offer documentation; `:467` identifies toolchain JSON as machine-readable local pins. |
| `scripts/bootstrap.sh`, `scripts/bootstrap.ps1` | Doctor and serial root unittest execution; no Python test-dependency installation. Shell bootstrap also contains historical `install_into.py --force`, which current installer rejects; avoid expanding this runner task into installer repair. |
| `Makefile` | `verify` calls `grok_verify.py --mode pr`; Trust CI unit target runs its own unittest suite. No general Python test-tools install or parallel test target currently. |
| `.coveragerc` | `branch=True`; sources exactly `.grok-stack/adaptive_grok` and `scripts`; existing omit list; report `fail_under=74`. Preserve this exact measurement domain and threshold. |
| `.grok-stack/adaptive_grok/verification.py:842` | Root `pyproject.toml`/`requirements.txt`/`setup.py` selects generic pytest branch, which currently skips coverage. `repo.py:82` also detects root Python metadata. README:22 explicitly prohibits these root files. |
| `trust-ci/pyproject.toml`, `factory/pyproject.toml`, `delivery/pyproject.toml` | Separate scoped products, unsuitable owners for shared local verification dependencies. |
| `scripts/install_into.py:22` | Entire `.grok-stack` is managed installer payload; scoped dependency file placed there travels with installed stack. `tests/_support.py:18` also copies `.grok-stack` into consumer fixtures. |

## Recommended pins and placement

Add a dedicated **`.grok-stack/config/python-test-requirements.txt`**, keeping root detection unchanged:

```text
pytest==9.1.1
pytest-xdist==3.8.0
pytest-cov==7.1.0
coverage==7.15.4
```

These are proposed direct dependency pins, not a complete transitive lock. Root independently verifies the actual combination. Do not label unexecuted combinations as tested `built` versions.

- Pytest 9.1.1 requires Python >=3.10, matching the repository minimum. Pytest supports existing `unittest.TestCase`, setup/teardown and skips; built-in `subTest` support exists since 9.0. `load_tests` remains unsupported. Existing suite uses `subTest`, so pinning 9.x avoids adding pytest-subtests. [Release metadata](https://pypi.org/project/pytest/9.1.1/), [unittest compatibility](https://docs.pytest.org/en/stable/how-to/unittest.html).
- Xdist 3.8.0 requires Python >=3.9, pytest >=7 and execnet >=2.1. Its metadata has no pytest upper bound; this establishes dependency compatibility, not a guarantee for this repository. No `psutil` extra is needed for an explicit worker count. [Pinned project metadata](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/pyproject.toml).
- Pytest-cov 7.1.0 requires coverage[toml] >=7.10.6, pytest >=7 and pluggy >=1.2; its 7.1.0 fix makes total/fail-under calculation consistent across report modes. Prefer it over an older available plugin for this coverage-preserving change. [Pinned metadata](https://github.com/pytest-dev/pytest-cov/blob/v7.1.0/pyproject.toml), [changelog](https://pytest-cov.readthedocs.io/en/latest/changelog.html).
- Coverage 7.15.4 supports Python 3.10+, so it preserves the current interpreter floor. [Versioned coverage documentation](https://coverage.readthedocs.io/en/7.15.4/).

Expose one explicit Makefile dependency-install target using the selected interpreter's `-m pip install -r` and document it near the README requirements table. Verification and bootstrap must not install automatically. Keep this toolset optional for consumers that never run Python verification; require actual dependencies when this parallel runner is selected.

For doctor integration, either add a small distribution-aware probe using `importlib.metadata.version` in the same interpreter as the runner, or retain plugin checks in runner preflight and have toolchain advice point at the scoped file. `pytest-xdist`/`pytest-cov` are distribution names; `xdist`/`pytest_cov` are import/plugin modules. Neither supplies a standalone plugin-version CLI. Do not use invented executables or infer plugin versions from pytest's banner. Existing toolchain policy permits newer versions; the exact requirements file supplies the repeatable installation baseline without changing that global policy.

## Coverage-preserving worker integration

Use current interpreter `-m pytest`, explicit test paths and bounded configured worker count. A command shape for the root measured suite is:

```text
<python> -m pytest -q tests -n <workers> --dist=loadscope --cov --cov-config=<absolute-root>/.coveragerc --cov-report=term-missing
```

Keep bare `--cov` immediately followed by another option so it cannot consume the next test path. Bare `--cov` preserves `.coveragerc` sources; `--cov=.` changes them, and `--cov=` removes source filtering. Explicit absolute `--cov-config` avoids cwd/config discovery drift. Pytest-cov owns worker measurement/combination; do not additionally wrap distributed pytest in `coverage run`. It reads branch mode and fail-under from the coverage config. [Configuration](https://pytest-cov.readthedocs.io/en/latest/config.html), [xdist integration](https://pytest-cov.readthedocs.io/en/latest/xdist.html).

The present gate is coverage's total percentage with branch measurement enabled and `fail_under=74`; it is not a separate branch-only-percent check. Preserve existing arithmetic, denominator, exclusions and failure exit behavior. If existing receipts need a separate `coverage` result, run the existing same-interpreter `coverage report --rcfile=<absolute path>` against the freshly combined file and propagate both failures; do not rerun tests just to report. Never report stale data after failed startup or append earlier runs with `--cov-append`.

`--dist=loadscope` keeps TestCase methods together and module-level functions together; `loadfile` is an alternative if shared module fixtures require it. Both limit distribution granularity. Explicit count avoids oversubscribing this suite's filesystem/subprocess-heavy tests; `-n 0` is serial debug mode, while `-n 1` still launches one worker. Root measurements should choose the default. [Distribution modes](https://pytest-xdist.readthedocs.io/en/stable/distribution.html).

No `[run] patch=subprocess` is necessary merely to measure xdist workers with pytest-cov. Pytest-cov 7 removed its automatic coverage of application subprocesses; opting into coverage's subprocess patch measures additional Python processes and automatically enables separate data files. Today's baseline `coverage run -m unittest` does not instrument arbitrary child interpreters, and this suite launches hooks, copied projects and deliberate process failures. Enabling the patch now would broaden measurement and alter subprocess behavior; keep it out unless required by a separate demonstrated gap. Xdist docs' generic subprocess wording must be read with the current migration guidance. [Pytest-cov subprocess migration](https://pytest-cov.readthedocs.io/en/latest/subprocess-support.html), [coverage 7.15.4 process handling](https://coverage.readthedocs.io/en/7.15.4/subprocess.html).

Prefer an isolated test environment; if plugin autoload is disabled, explicitly load `xdist.plugin` and `pytest_cov.plugin`, and include that choice in the real worker proof. Otherwise a machine-wide unrelated plugin can change collection. This is a runner implementation option, not a requirement to rewrite consumer pytest configuration. [Pytest plugin loading](https://pytest.org/en/stable/reference/reference.html#confval-PYTEST_DISABLE_PLUGIN_AUTOLOAD).

## Offline / missing-tool policy

- Dependency installation is an explicit setup action. Existing installed compatible tools run offline. For offline fresh environments, use a pre-provisioned wheel directory with direct pins and their transitive dependencies; absent wheels produce a setup failure, never a hidden network attempt from verification.
- Missing pytest/xdist/pytest-cov: report the missing distributions and exact setup command. A documented serial fallback may run the current `coverage run --rcfile=... -m unittest discover -s tests` followed by the same coverage report, if coverage exists. Label it serial fallback; do not pretend parallel execution succeeded.
- Missing coverage in PR/release for the new mandatory measured runner: return an explicit failure/incomplete result. Fast/bootstrap diagnostic execution can use stdlib unittest without coverage, labelled accordingly. Do not fall back from a failed parallel test run or worker crash to a successful serial retry automatically.
- Preserve existing generic consumer behavior unless explicitly scoped otherwise: `tests/test_verification_doctor.py:1413` currently expects coverage-missing skip; `:1191` and `:1333` protect root-project pytest precedence. New scoped dependency metadata must not silently switch those branches. The new runner's stricter mandatory gate should have its own tested boundary.

## Evidence needed before calling this ready

Root/owner should supply: same selected tests and skips under serial/parallel collection (accounting for pytest subtest reporting); actual >=2-worker coverage aggregation; branch mode/source set/74 gate preserved; deliberate under-threshold fixture returns nonzero; failing test, crash and missing-plugin cases cannot succeed via fallback; consecutive runs cannot reuse prior coverage; same-interpreter dependency probes; worker setting reaches Makefile and verifier; scoped requirements survive installer payload without introducing root project metadata. No such tests were run by this analysis agent.

Memory fact for next subtask: `.grok-stack/config` is the existing distributable place for shared test-tool configuration; root project metadata would change verification routing. Worker coverage and application-subprocess coverage are distinct capabilities, so adding xdist does not require broadening `.coveragerc` with subprocess instrumentation.
