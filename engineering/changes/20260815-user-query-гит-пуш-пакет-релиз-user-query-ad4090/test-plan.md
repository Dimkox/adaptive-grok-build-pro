# Test plan

`python3 scripts/grok_verify.py --mode pr` on the tree that will be tagged. After packaging, confirm zip sha256 matches the sibling file and `MANIFEST.sha256` inside the zip does not list `.env` or `err.log`.
