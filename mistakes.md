# Mistakes

Root causes, not symptoms. Record only mistakes that caused a real problem.

## 2026-09-01 — Browser runner lifecycle was not executed

**Symptom:** The browser contract could report `passed: true` and then exit nonzero with `ENOTEMPTY` during cleanup.
**Root cause:** The source-only contract failed to execute the real Chrome child lifecycle, allowing immediate profile deletion while the child was still writing; its replacement execution test then omitted the optional-dependency availability boundary and mistook local host capabilities for the immutable Trust runner contract.

## 2026-08-24 — Misread «приложуха» as a public website

**Symptom:** Agents treated «приложуха» as a public website instead of GitHub App `https://github.com/apps/adaptive-trust-ci`.
**Root cause:** Overloaded Russian «приложение» means both a GitHub App and a public website, so the two were collapsed into one live target. Operator truth is `https://github.com/apps/adaptive-trust-ci`.

## 2026-08-24 — Treated a ChatGPT hostname as the live webhook URL

**Symptom:** Operator packages and `decisions.md` pointed GitHub App webhook and Apache TLS at `https://trust-ci.ii-tonya.ru/webhooks/github`.
**Root cause:** A ChatGPT-invented hostname was copied as operator truth. That hostname is a ChatGPT invention, not the GitHub App and not Trust CI on claw; do not configure, probe, or complete TLS for it.

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
