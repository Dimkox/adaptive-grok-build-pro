# Implementation — prepare-only deploy through 2.0.4

Route `99b743830b0e`. Write owner: `general_implementer`. Fail-first tests landed, then prepare-only deploy + this-repo CI + docs.

`production_action_approval` is **not** granted. No tag, push, or GitHub Release was run. VERSION stays `2.0.4`. No 2.0.4 zip was added to `packages/`.

## Changed files

- `tests/test_deploy.py` — fail-first cases for no route, missing evidence, implementing status, dry-run, `--record` with/without production approval, PreToolUse allow, installer copy, CI template contract
- `.grok-stack/adaptive_grok/deploy.py` — `prepare_deploy(root, *, record)` (no subprocess)
- `scripts/grok_deploy.py` — thin CLI: `--record`, `--json`; default dry-run
- `.grok-stack/templates/ci/github-actions.yml` — keep verify; add conditional `package` job; no publish
- `.github/workflows/adaptive-grok.yml` — byte-for-byte copy of the template
- `.grok-stack/templates/ci/README.md` — optional workflow; local `make verify` is source of truth
- `scripts/install_into.py` — `MANAGED_FILES` includes `scripts/grok_deploy.py`
- `.grok-stack/config/managed.json` — scripts includes `grok_deploy.py`
- `Makefile` — `deploy:` → `python3 scripts/grok_deploy.py`
- `.grok/skills/release-readiness/SKILL.md` and `.agents/skills/release-readiness/SKILL.md` — after go/no-go run grok_deploy; `--record` only with production approval
- `.grok/skills/adaptive-delivery/SKILL.md` and `.agents/skills/adaptive-delivery/SKILL.md` — last mile is grok_deploy.py; humans own printed commands
- `README.md` — loop includes deploy prepare; scripts table adds `grok_deploy.py` + `grok_approve.py`
- `QUICKSTART.md` — after verify: `/release-readiness` and `grok_deploy.py`
- `CHANGELOG.md` — 2.0.4 bullets (VERSION not bumped)
- `engineering/runbooks/publish-v2.0.4.md` — checks, printed commands, rollback, agent never runs push

## Fail-first (current tree, before implementation)

```text
test_no_route_is_not_ok ... ERROR
  ModuleNotFoundError: No module named 'adaptive_grok.deploy'
test_missing_evidence_is_not_ok ... ERROR
  ModuleNotFoundError: No module named 'adaptive_grok.deploy'
test_implementing_status_is_not_ok ... ERROR
  ModuleNotFoundError: No module named 'adaptive_grok.deploy'
test_dry_run_ready_is_ok_without_receipt ... ERROR
  ModuleNotFoundError: No module named 'adaptive_grok.deploy'
test_record_without_approval_is_not_ok ... ERROR
  ModuleNotFoundError: No module named 'adaptive_grok.deploy'
test_record_with_production_approval_writes_prepared_receipt ... ERROR
  ModuleNotFoundError: No module named 'adaptive_grok.deploy'
```

## Post-fix

```bash
python3 -m unittest tests.test_deploy -v
# Ran 14 tests in 3.045s
# OK

python3 -m unittest discover -s tests
# Ran 125 tests in 14.425s
# OK
```

`git push` / `gh release` appear only as printed command strings in `deploy.py`. Neither new file imports or runs subprocess. Template YAML has `hashFiles('scripts/package_stack.py')` and does not contain `gh release` / `docker push` / `git push`.

## Residual risk

- `hashFiles` is specified at job `if` as designed; GitHub may only evaluate it in step context. Local `make verify` remains source of truth.
- `--record` writes receipt status `prepared` (not `pass`); it is not a `required_evidence` kind.
- Printed publish commands are still human-owned. Policy continues to block real `git push` / `gh release create` Bash invocations without production approval.

## Rollback

Revert the files listed above. Do not bump VERSION, do not add a 2.0.4 zip to `packages/`, and do not tag or push from this change.
