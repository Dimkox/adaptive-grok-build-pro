# Requirements

- [ ] Given current `main`, when cleanup finishes, then `HEAD` is still `975ccb2` / `v2.0.10`.
- [ ] Given `git status -sb`, when cleanup finishes, then there are no leftover sibling change-package modifications or untracked evidence. This package may remain as the active change dir.
- [ ] Given tags, when cleanup finishes, then `v2.0.8`/`v2.0.9`/`v2.0.10` still peel to `0284241`/`f72c0fc`/`975ccb2`.
- [ ] No force-push. No VERSION bump.
