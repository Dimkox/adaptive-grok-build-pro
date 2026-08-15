# Architecture

Grok loads `project/adaptive` from `.grok/hooks/adaptive.json`. Older copies call `python3 pre_tool_use.py` with cwd = project root. Missing file → python exit 2 → deny all tools.

1. Root hook files are dispatch shims into `.grok/hooks/` (no root `_lib`).
2. Hook commands try canonical path, then shim, then print allow/`{}`.
3. Installer copies shims so `git pull` + `install_into` heals consumer repos.
