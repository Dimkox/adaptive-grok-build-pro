# Publish v2.0.10

User «релиз сделай» after `v2.0.9` is already Latest on `f72c0fc`. `AGENTS.md` Release when green: bump VERSION only if the last tag already exists. Last tag exists, so this is **2.0.10**, not a retag of 2.0.9.

Hook titled this package after a system-reminder; live task is the user query «релиз сделай».

- Identity: bump `VERSION` / `__version__` / README / CHANGELOG / package index / structure tests to 2.0.10
- Pack zip only after VERSION is 2.0.10
- Tag `v2.0.10`, push `main` + tag, `gh release create`
- Do not retag `v2.0.9` or earlier
- No GitHub Actions, no `pyproject.toml`
- `write_agent` is null; controller owns identity + last mile
