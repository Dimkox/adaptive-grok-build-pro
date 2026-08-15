# Requirements — Resolve contour residual contradictions

## Acceptance criteria

- [x] Given `bash -lc 'git push origin feature'` without approval, when PreToolUse runs, then deny (approval reason)
- [x] Given `bash -c "git push origin feature"` without approval, then deny
- [x] Given `sh -c 'npm publish'` without approval, then deny
- [x] Given `bash -lc 'cd dist && git push origin feature'` without approval, then deny
- [x] Given those same wrapped commands after a valid `production` approval, then allow
- [x] Given `bash -lc 'echo git push origin feature'`, then allow (inner is echo)
- [x] Given leftover route `session_id=A` status=routed and prompt `делай` with `session_id=A`, then same `route_id`
- [x] Given leftover route `session_id=A` and prompt `делай` with `session_id=B`, then new `route_id`
- [x] Given leftover route same session status=`ready` (or completed/released/cancelled/archived) and prompt `делай`, then new `route_id`
- [x] Given a child payload, leftover route is unchanged
- [x] Given `tests/nested/test_x.py` only (no top-level `tests/test*.py`), `_python` does not add `python-unittest`
- [x] Given `pyproject.toml` + `tests/` + pytest present, `_python` has `pytest` and not `python-unittest`

## Non-goals

- Recursing into `python -c`
- Changing FOLLOW_UP_RE vocabulary
- Restoring a hard Stop block
