# Tasks — Repair stale-route lockout and policy path matching

- [x] Land failing policy / rematch tests and rewrite the Stop test
- [x] Invocation matcher in `policy.py`
- [x] `repair` keyword + `should_reuse_active_route` + child-payload skip
- [x] Path-qualify `adaptive.json`; restore canonical hooks under `.grok/hooks/` (disabled copies removed)
- [x] Docs: CHANGELOG 2.0.4 bullet, README Stop sentence
- [x] `python3 -m unittest discover -s tests` and `python3 scripts/grok_verify.py --mode pr`
- [x] Independent code + test review
