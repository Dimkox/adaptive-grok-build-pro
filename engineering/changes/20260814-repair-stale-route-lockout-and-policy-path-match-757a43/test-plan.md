# Test plan — Repair stale-route lockout and policy path matching

## Characterization / failing first

1. Path and echo/cat argument text must be allowed (`test_policy.py`).
2. `scripts/grok_approve.py` with a scope argument must be allowed.
3. Real invocations stay denied without approval and allowed with it; chained `cd … && git push` still denied.
4. `build_route("repair yourself")` is bugfix / `general_implementer`.
5. `should_reuse_active_route` is false for non-follow-ups, true for `делай` / `continue`.
6. Hook rematch: leftover route + repair / non-keyword prompt → new `route_id`; follow-up keeps `route_id`.
7. Child payload / `You are …` brief does not change `route_id`.
8. Stop hook warns and does not set `decision=block`.
9. `adaptive.json` commands are path-qualified; root hook scripts are absent.

## Verification

```bash
python3 -m unittest discover -s tests
python3 scripts/grok_doctor.py
python3 scripts/grok_verify.py --mode pr
```

## Residual

Wrapped shells that hide `git push` are not matched. Do not add a shell parser in this change.
