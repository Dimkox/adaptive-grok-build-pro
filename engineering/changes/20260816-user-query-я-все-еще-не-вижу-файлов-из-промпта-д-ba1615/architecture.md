# Architecture

The original prompt named root files. This repo put the sinks under `engineering/` so agents would not create root files. That is the bug the user is looking at.

Move, do not copy:

1. `engineering/decisions.md` → `decisions.md`
2. `engineering/mistakes.md` → `mistakes.md`
3. Replace the old paths with two-line stubs: “Moved to /decisions.md” / “Moved to /mistakes.md”.
4. `AGENTS.md` bullets use the prompt filenames.
5. `tests/test_structure.py` asserts root files exist and that the prefix before `## Mandatory entrypoint` contains `log it in decisions.md` and `record it in mistakes.md`, and does **not** treat `engineering/decisions.md` as the live path.

Installer and packager do not special-case these files. Root markdown is packed automatically. No installer seed in this change.
