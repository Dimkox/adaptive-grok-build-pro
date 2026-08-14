# Requirements — v2.0.0 release

## Acceptance criteria

- [ ] `main` contains hooks, 21 agents, `.agents/skills`, installer fix
- [ ] `python3 -m unittest discover -s tests` is 80/80
- [ ] `python3 scripts/grok_doctor.py` has no FAIL
- [ ] Zip exists and `MANIFEST.sha256` verifies
- [ ] Public GitHub Release `v2.0.0` includes the zip
- [ ] `.env` is not in git

## Non-functional

- Security: no tokens in the tree or release notes
- Rollback: delete tag/release; revert commit
