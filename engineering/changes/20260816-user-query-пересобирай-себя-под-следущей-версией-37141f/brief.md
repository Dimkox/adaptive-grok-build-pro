# Rebuild as 2.0.8, self-check, push if green

Change ID: `20260816-user-query-пересобирай-себя-под-следущей-версией-37141f`
Route ID: `37141fbe6302`
Risk: low
Complexity: micro (route); treated as a durable identity bump because it ships a zip

## Problem

HEAD `02376cc` is published 2.0.7. Working tree has the AGENTS.md self-learning restore (first section + structure test + mistakes.md). That work is unpublished. User: rebuild under the next version, check the tree against our own instructions, git push if it is OK.

## Outcome

Identity is 2.0.8. The zip in `packages/` unpacks `VERSION=2.0.8` and includes the first-section self-learning rule. `origin/main` has that commit after a green verify + independent code review.

## Scope

### In scope

- Bump identity 2.0.7 → 2.0.8 on every pin surface.
- Rebuild zip via `package_stack` after the bump; copy siblings into `packages/`.
- Keep the AGENTS.md first-section self-learning rule; lock stays in `test_structure`.
- Self-check against `AGENTS.md` (no GHA, no `pyproject.toml`, one write owner, log this decision).
- Commit only 2.0.8 product files + this change package.
- `git push origin main` only after verify + code review pass. User prompt is the production go for **push**.

### Out of scope

- GitHub Release / tag unless the controller later runs printed `grok_deploy` commands after push is green. This prompt said git push, not `gh release create`.
- Retag 2.0.7. No GitHub Actions. No `pyproject.toml`.
- Committing leftover dirt from other change packages.

## Constraints

- `VERSION` is the source of truth. Pack after the bump, never before.
- Do not force-push. Do not touch `v2.0.7`.
