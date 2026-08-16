# Requirements

- [x] No `.github/workflows/` files
- [x] No `.github/dependabot.yml`
- [x] `install_into --with-ci` does not write a workflow (exits with forbidden)
- [x] Tests lock the ban
- [x] `python3 scripts/grok_verify.py --mode pr` PASS
- [x] Zip rebuilt; in-zip VERSION 2.0.6; no workflow in zip
- [ ] GitHub Latest v2.0.6 after last mile
