# Release plan — v2.0.1

Human-owned publish. Agent only prepares the tree and `dist/` artifacts.

1. Commit version bump on `main`
2. `python3 scripts/package_stack.py`
3. Human: tag `v2.0.1`, push, `gh release create` using `dist/HANDOFF.md`

Do not publish from Grok Build.
