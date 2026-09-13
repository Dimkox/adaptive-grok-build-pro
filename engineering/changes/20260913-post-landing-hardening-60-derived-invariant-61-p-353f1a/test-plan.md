# Test plan

- `python3 -m unittest tests.test_architecture_model -q` (root; 67 tests incl. derived inventory block)
- `PYTHONPATH=.:factory/src python3 -m unittest factory.tests.test_landing_artifact -q` (9 tests incl. 2 new)
- `PYTHONPATH=.:factory/src python3 -m unittest factory.tests.test_landing_pdf_worker -v` (7 tests; 4 pypdf-dependent run only on the pinned runner image, skipped honestly elsewhere)
- full `python3 scripts/grok_verify.py --mode pr` (receipt `verification`)
- reviews: code/test/security/release receipts via `scripts/grok_review.py`
