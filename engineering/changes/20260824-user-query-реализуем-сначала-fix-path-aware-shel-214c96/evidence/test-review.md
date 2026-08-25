# Test review — PR #6 path-aware shell policy / circuit breaker

- Route: `214c96b43d3f`
- Change: `20260824-user-query-реализуем-сначала-fix-path-aware-shel-214c96`
- Reviewer: `test_reviewer` (read-only)
- Product code: not edited
- Claimed verification (not re-run here): `python3 -m unittest discover -s tests` → 198 OK; `python3 scripts/grok_verify.py --mode pr` PASS (bandit, unittest, coverage 74%)

## Scope inspected

| Artifact | Role vs implementation |
|---|---|
| `tests/test_policy_shell_targets.py` | Direct `evaluate_pre_tool` (`tool_name=Bash`) against `.grok-stack/adaptive_grok/policy.py` + `shell_targets.py` |
| `tests/test_pre_tool_circuit_breaker.py` | Hook path: `.grok/hooks/pre_tool_use.py` fingerprints + breaker text |
| `tests/test_protected_write_hook.py` | Same hook; `run_terminal_command` aliased to `Bash` in `.grok/hooks/_lib.py` |

Tests drive policy in-process or a local `python3` hook subprocess on a `project_copy()` tree. They do not execute `docker`, `curl`, or `wget`.

## Required scenarios

### docker / `/tmp` false positive — covered

`ShellTargetPolicyTest.test_names_outside_repo_do_not_trigger_control_plane` uses the compound command:

`docker cp probe.py adaptive-trust-ci-worker-1:/tmp/probe.py && curl -o /tmp/trust-ci-live.body http://127.0.0.1/health/live`

Implementation: destinations are outside the repo (`safe_relative_path` → `None`); opaque token match does not fire on hyphenated `adaptive-trust-ci-worker-1`. GET `curl -o` is not `_http_write_resource`. Test asserts `allowed is True`.

### Named `AGENTS.md` — covered for redirect; weaker for argv extractors

`test_real_control_plane_target_is_blocked_and_named` asserts deny and `'AGENTS.md' in reason` for `printf x >> AGENTS.md`, matching `policy.evaluate_pre_tool` text `targeting {targets}`.

`test_argv_mutation_commands_name_control_plane_targets` exercises `sed -i`, `rm`, `touch`, `tee`, `curl -o README.md`, `bash -c` redirect, `cp`/`install`/`rsync`, `wget -O`, `perl -i` — all must deny. It does **not** assert the reason names `AGENTS.md` / `README.md` despite the test name. Residual: a regression that denied opaquely without naming would still pass this case.

### `grok_protected_write` guidance — covered

`ProtectedWriteHookTests`:

- Opaque `printf x >> AGENTS.md` via `run_terminal_command` → `decision=deny`, reason contains `grok_protected_write.py` and `exact protected-path grant` (`_actionable_reason` + `_CONTROL_PLANE_BATCH_GUIDANCE`).
- Validated `python3 scripts/grok_protected_write.py --manifest /tmp/control-plane.json` → `allow` (shell gate must not treat the writer as opaque mutation). The writer is not executed.
- Writer chained with `&& printf x >> AGENTS.md` → `deny`.

### Circuit breaker — exact-repeat covered; same-objective rewrite not

`DenialCircuitBreakerTest.test_second_identical_denial_stops_retry_loop` double-invokes the hook with the same Bash `curl -X POST ... http://127.0.0.1:18080/webhooks/github`. First deny is legacy `_http_write_resource` (external-write), not control-plane. Second response must include `exact tool invocation was denied again` and `objective BLOCKED`.

Not characterized: rewritten argv with the same `reason` (objective fingerprint), 15-minute window, cap 128, schema v1 `entries` migration, lock/IO fallback `(1,1)`.

## Safety: no GitHub, no keys

- `project_copy` copies `.grok`, `.agents`, `.grok-stack`, and a few repo files; runtime is wiped. No `.env`, no private keys, no GitHub App material.
- `run_hook` runs the copied hook with stdin JSON; no network client.
- Loopback and `example.invalid` URLs appear only as **policy input strings**.
- Secret-read policy is exercised elsewhere (`tests/test_policy.py` Read of `config/.env` as a **path string**). These three files do not open credentials.

## Adequacy vs change

The two user-visible bugs (substring false positive on docker/`/tmp` `trust-ci*`; named control-plane target + grant guidance; exact-repeat breaker) have automated characterization. Parser edges (`$VAR/AGENTS.md`, unresolved opaque, `cp -t`, absolute `root/AGENTS.md`, threading of `_LEGACY_SHELL_GUARD`) remain untested; that is residual risk, not a miss of the stated checklist.

## Verdict

PASS
