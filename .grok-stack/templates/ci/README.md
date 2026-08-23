# Trusted verification

Local checks are the fast feedback path:

```bash
make doctor
make verify
python3 scripts/grok_verify.py --mode pr
```

The authoritative repository check is GitHub Actions workflow `trusted-ci`:

```bash
python3 scripts/grok_verify.py --mode pr --strict --json
```

Strict mode fails when Ruff, Bandit, or Coverage.py is unavailable. Configure branch protection to require both Python matrix jobs and the package job. Release publication belongs to the separately protected `production` Environment workflow; this template does not run publish, push, or deployment commands.
