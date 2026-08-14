# Rollback plan — Fix incomplete Grok port

## Trigger conditions

- Doctor or unit suite regresses after this change
- Project hooks deny legitimate local development tools
- Installer overwrites unrelated target files

## Application rollback

Revert this change's files (hooks, agents, `.agents/skills`, installer, `_support.py`, config). The Python policy/router under `.grok-stack/adaptive_grok/` is unchanged and can remain.

```bash
git checkout HEAD -- .grok/config.toml .grok/hooks/README.md Makefile scripts/install_into.py tests/_support.py
git clean -fd .grok/hooks.json .grok/hooks/*.py .grok/hooks/adaptive.json .grok/agents .agents VERSION docs .grok-stack/templates/ci/github-actions.yml
```

Prefer a targeted revert of this change package rather than `git reset --hard` on a shared branch.

## Data recovery / forward-fix

No schema or production data. Runtime files under `.grok-stack/runtime/` can be deleted; they are gitignored.

## Verification after rollback

```bash
python3 -m unittest discover -s tests
python3 scripts/grok_doctor.py
```

Expect the pre-fix doctor/structure failures to return if the scaffold is removed.
