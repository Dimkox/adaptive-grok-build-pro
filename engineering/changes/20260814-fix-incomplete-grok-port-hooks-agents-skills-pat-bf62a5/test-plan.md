# Test plan — Fix incomplete Grok port

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Full unit suite passes | `python3 -m unittest discover -s tests` |
| P0 | Doctor has no FAIL items | `python3 scripts/grok_doctor.py` |
| P0 | Hook lifecycle contracts | `tests/test_hooks.py` |
| P0 | Installer conflict/force/custom agent | `tests/test_installer.py` |
| P1 | Policy still blocks secrets/core/destructive | `tests/test_policy.py` |
| P1 | Verify still records receipts | `python3 scripts/grok_verify.py --mode pr` |

## Automated checks

- Unit: existing structure, hooks, installer, policy, router, doctor tests (characterization)
- Static: `python3 scripts/grok_verify.py --mode pr`

## Manual checks

- Confirm `.env` is not staged
- Confirm `git check-ignore -v .env`
