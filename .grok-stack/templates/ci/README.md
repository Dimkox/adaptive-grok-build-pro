# CI templates

No GitHub Actions.

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
