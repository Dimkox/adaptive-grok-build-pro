# Requirements

## After design approval (not executed yet)

- [x] `python3 scripts/grok_deploy.py` with no route fails
- [x] Missing/stale evidence fails; no receipt
- [x] Change not `ready`/`released` fails
- [x] Dry-run with green evidence: exit 0, prints commands, no receipt
- [x] `--record` without production approval fails
- [x] `--record` with approval + ready: receipt `deploy`/`prepared`
- [x] Script source contains no production-invocation subprocess
- [x] `install_into` copies `scripts/grok_deploy.py`
- [x] `.github/workflows/adaptive-grok.yml` equals the CI template
- [x] Template `package` job is conditional and has no `gh release` / `docker push` / `git push`

## Human later (not this change)

- [ ] `production_action_approval` then tag / push / GitHub Release v2.0.4
