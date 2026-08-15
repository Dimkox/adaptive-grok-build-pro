# CI templates

Optional GitHub Actions workflow: `github-actions.yml`. This repository copies it to `.github/workflows/adaptive-grok.yml` (verify + conditional package; no publish).

Local `make verify` is the source of truth. Hosted CI is optional and does not publish.

This project is MIT open source and does not depend on paid hosted CI.

Local checks (free, any machine):

```bash
make doctor
make verify
python scripts/grok_doctor.py
python scripts/grok_verify.py --mode pr
```

If you self-host CI (Woodpecker, Forgejo Actions, GitLab, Drone, Jenkins, …),
wire the same commands. Do not require GitHub-hosted runners.
