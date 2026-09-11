# Requirements — lazy Trust CI CLI imports on 2.0.15

## Acceptance criteria

- [ ] AC-A1: Successor branch has ancestor `fd51dcfed6b33f4a8707c0db602328146df17cc9` and is not `fix/path-aware-shell-policy-circuit-breaker`.
- [ ] AC-A2: Product diff vs `origin/main` is limited to `trust-ci/src/adaptive_trust_ci/cli.py`, `trust-ci/tests/test_cli.py`, `trust-ci/README.md`, this change package/evidence, and short `decisions.md`/`mistakes.md` appends. No `compose.yaml`, `policy.py`, `api.py`, `worker.py`, `VERSION`, packages ZIP, or `.github/workflows/`.
- [ ] AC-A3: New PR to `main`. PR #28 is neither merged nor used as base. PRs #12/#13/#15 are not closed by this route.
- [ ] AC-A4: No merge, tag, deploy, live API write, or human-key use.
- [ ] AC-B1: Fresh process with server modules + fastapi/psycopg/uvicorn/cryptography blocked: `--help`, `approval-create --help`, `approval-submit --help` exit 0.
- [ ] AC-B3: `approval-submit` posts fixture bytes to loopback `/approvals` with `Content-Type: application/json` and `User-Agent: adaptive-trust-ci-human/2.1.0` while blocking server graph and cryptography.
- [ ] AC-B4: Importing `adaptive_trust_ci.cli` does not load `api`/`worker`/`store`/`migrations`/`backup`/`github`/`github_app`/`fastapi`/`uvicorn`/`psycopg`.
- [ ] AC-B5: Each of the 17 non-human commands, with fake modules, loads only its import slice and a mocked safe effect (no live DB/Docker/GitHub; `keygen` must not write PEM).
- [ ] AC-B7: Tests never read `~/.config` or `trust-ci/runtime` keys and do not call `Signer.generate()`.
- [ ] AC-C1: README human-approval section uses current envelope fields (`pr_number`, `schema_version`, `approval_id`, `reason`) and `PYTHONPATH=… python -m adaptive_trust_ci.cli`.
- [ ] AC-D1: `python3 scripts/grok_verify.py --mode pr` PASS on the successor tree.
- [ ] AC-E1: `VERSION` remains `2.0.15`; published ZIP bytes unchanged.

## Failure and edge cases

- Implementing on 2.0.12 checkout → hard fail.
- Basing on PR #28 → hard fail.
- Cherry-picking `0f7f508` wholesale → log/package conflicts; reconstruct the unique slice.
- Isolation tests in a process that already imported `api` → false pass; use a fresh subprocess + sitecustomize guard.
- New tests that generate PEM → forbidden.
- Expanding into `policy.py`/`api.py` → stop; that is PR #13.

## Non-functional requirements

- Security: stay inside CLI isolation; this route has no security_reviewer.
- Reliability: server command behavior after dispatch is unchanged.
- Performance: human commands should start without the server graph.
- Observability: HTTP acceptance is not merge authority.
