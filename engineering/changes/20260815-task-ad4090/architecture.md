# Architecture

Write owner for leftover publish-prep is `general_implementer` (active route `e85418e33648`). Prepare-only `grok_deploy.py` still does not execute publish. Last mile remains the human-owned printed commands.

Sequence:

1. Record `production_action_approval` (`git push` + package + release).
2. Verify, then code_review + test_review on the 2.0.5 tree (route `e85418e33648` required evidence).
3. `python3 scripts/package_stack.py` → copy zip+sha256 into `packages/`.
4. Commit tracked 2.0.5 files (no `err.log`, no `.env`).
5. Annotated tag `v2.0.5`.
6. Push `main` and the tag; `gh release create` with the tracked artifacts.

Credentials come from `.env` (`GIT_FINE_GRAIN_TOKEN`, `GIT_LOGIN`, `GIT_EMAIL`) and are never printed.
