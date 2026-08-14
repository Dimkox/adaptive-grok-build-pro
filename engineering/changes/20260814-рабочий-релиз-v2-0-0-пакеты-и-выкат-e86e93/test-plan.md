# Test plan — v2.0.0

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Full unit suite | `python3 -m unittest discover -s tests` |
| P0 | Doctor | `python3 scripts/grok_doctor.py` |
| P0 | Secret scan / verify | `python3 scripts/grok_verify.py --mode pr` |
| P0 | Package self-check | `test_manifest_package.py` + built zip `testzip` |
| P1 | `.env` not in archive or git | `git check-ignore`, zip namelist |
