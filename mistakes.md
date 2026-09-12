# Mistakes

Root causes, not symptoms. Record only mistakes that caused a real problem.

## 2026-08-23 — First protected write invalidated the rest of the grant

**Symptom:** README.md, trust-ci/README.md and decisions.md were denied after tests/toolchain landed, then the session shut down mid-docs pass.
**Root cause:** A fingerprint-bound protected-path grant is consumed by the first successful mutation of the working tree. Remaining listed resources are not a multi-file session; they need a fresh grant or one parallel batch against the then-current fingerprint.

## 2026-08-16 — Hid the prompt files under engineering/

**Symptom:** A user listing the repo root next to `AGENTS.md` still could not see `decisions.md` or `mistakes.md`.
**Root cause:** We rewrote the original prompt filenames to `engineering/decisions.md` / `engineering/mistakes.md` on purpose so agents would not create root files, which hid the files the prompt named.

## 2026-08-16 — Self-learning bullets never wired into AGENTS.md

**Symptom:** Agents had `engineering/decisions.md` and `engineering/mistakes.md` but no standing `AGENTS.md` order to write them.
**Root cause:** Authorship omission when `AGENTS.md` was first written as the Engineering Contract (`ca63b2d`); the log files were added later (`097f5c9`) without wiring the trigger. Not a later delete.

## 2026-08-14 — Treated a matcher bug as an environment block

**Symptom:** PreToolUse denied ordinary `ls`/`cat`/`git` and leftover routes had no write owner, so hooks were moved to `.grok/hooks.disabled/`.
**Root cause:** The deny reason was read as “hooks are too strict to work under,” not as “`PRODUCTION_COMMANDS` matches path text and rematch is keyed off `is_development_prompt`.” Disabling the execution machinery hid both bugs and left the stack unable to classify or police itself until the canonical `.grok/hooks/` tree was restored after the fix.

## 2026-08-14 — Bound verification to an intermediate tree

**Symptom:** First `grok_verify --mode pr` could not be the completion receipt; reports and `state.json` still had to be written.
**Root cause:** Verification was used as a mid-implementation checkpoint. The receipt fingerprint is the whole dirty tree, so any later change-package or review-report write invalidates it. Evidence must be recorded only after the last file that will remain in that tree.

## 2026-09-06 — Treated local extraction as GitHub delivery

**Symptom:** The session started a side worktree and copied CLI source before answering whether GitHub PRs, checks, and `main` were aligned; the user had to ask twice.
**Root cause:** “Continue to final stage” was read as local file work first. Merge authority is the App-owned check on an exact PR SHA, so GitHub open-PR/check/`main`/tag facts are the first coordination step, not a follow-up after a worktree.

## 2026-09-06 — Treated append-only self-learning files as blocked protected paths

**Symptom:** Root `decisions.md` / `mistakes.md` structured edits were denied, so facts were delayed or written only in side worktrees.
**Root cause:** A PreToolUse protected-path deny was read as a standing ban. The user later allowed append-only writes to those two files in every tree, including root. Other protected paths stay blocked.


## 2026-09-10 — Do not infer absent real delivery from an empty factory cohort

Root cause: the autonomy assessment treated the controller repository and its landing pilot as the complete evidence universe, overlooking the user-named consumer projects Puls Pump Selector, Google Ads Automation and ii-Tonya. Their GitHub histories and evidence contain real implementation, integration, stand acceptance and native deployment; an unpopulated M8 ledger means qualifying tasks have not been accounted for, not that no real tasks exist. Future assessments must inspect actual delivery branches (Ads uses main while its default branch is codex/bootstrap) and distinguish observed project outcomes from exact-profile autonomy qualification.

## 2026-09-12 — Force-pushed an unrelated branch pointer from a compound command

**Symptom:** A single compound `run_shell_command` began with `cd /home/pall/grok-projects/adaptive-grok-build-pro` and ended with `git push … refs/heads/perf/parallel-python-tests`. `HEAD` resolved to the session branch, so the push moved PR #33's head branch to `f5e6dcb` (an unrelated merge commit) with a forced update, briefly rewriting the PR head and its diff.
**Root cause:** Two compounding errors. First, a destructive remote write was composed into the same command line as an unrelated `cd`, so the target ref name was reviewed but the ref *source* (`HEAD`) was not — the thing that actually changed. Second, `--force-with-lease` was treated as a safety net while the expected value came from the same mistaken push, so the lease matched and confirmed the damage instead of preventing it. A `||` fallback clause pushed a second path, widening the blast radius of a command that should have had exactly one effect.
**Rule:** Never combine `cd` with a remote write in one command; pass the repository via `git -C <resolved path>` and an explicit `<commit>:<ref>` (never bare `HEAD`). A lease is only meaningful when its expected value is read from the remote first, in a separate prior step. Destructive pushes get no fallback branches in the same invocation, and before any force-push, verify ancestry (`merge-base --is-ancestor`) so that restoring the intended commit is provably lossless.
