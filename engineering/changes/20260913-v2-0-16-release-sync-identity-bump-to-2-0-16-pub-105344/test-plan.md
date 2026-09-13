# Test plan
- `python3 -m unittest tests.test_project_state tests.test_structure tests.test_manifest_package -q` (lockstep trio)
- full parallel harness `/tmp/pverify/pverify.sh <tree> --unit-timeout 320` -> RESULT PASS (245+ units, coverage 79%)
- authoritative serial `python3 scripts/grok_verify.py --mode pr` on the frozen final tree -> verification receipt
- security_review + release_review + code/test advisory receipts via scripts/grok_review.py
