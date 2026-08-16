# Local verification

This product never uses GitHub Actions.

Do not add `.github/workflows/` or Dependabot.

Source of truth:

```bash
make doctor
make verify
python3 scripts/grok_verify.py --mode pr
```

Do not add another CI vendor. Local `python3 scripts/grok_verify.py --mode pr` is the only gate.
