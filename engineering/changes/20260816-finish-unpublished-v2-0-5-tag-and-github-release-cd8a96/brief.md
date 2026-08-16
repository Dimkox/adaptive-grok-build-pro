# Finish unpublished v2.0.5 tag and GitHub Release

Change ID: `20260816-finish-unpublished-v2-0-5-tag-and-github-release-cd8a96`
Created: 2026-08-16T16:01:52+00:00
Risk: low
Complexity: standard
Domains: generic

## Problem

GitHub Latest is still **v2.0.4**. The user sees that and thinks nothing was pushed or merged.

That is wrong about `main`. Public `main` is already `7c0ae7573535ddd0cfe3800f81278991ced81584` (`Release v2.0.5…`, `VERSION=2.0.5`). There is no PR. The gap is advertisement: local annotated tag `v2.0.5` was never pushed, and GitHub Release `v2.0.5` was never created.

Previous wave prepared the ship and printed last-mile commands. User already said «да» / «смерджи все». This prompt: «делай».

## Outcome

GitHub Latest is `v2.0.5` with the existing tracked zip + sha256 and CHANGELOG 2.0.5 notes. Tag peels to `7c0ae75`. `v2.0.4` stays untouched.

## Scope

### In scope

- Confirm local tag `v2.0.5` still peels to `7c0ae75`
- `git push origin v2.0.5`
- `gh release create v2.0.5` with existing `packages/` assets and `dist/RELEASE-NOTES.md`
- Confirm Latest is `v2.0.5`
- Record production approval so PreToolUse allows the two commands

### Out of scope

- New product features / VERSION bump
- Rebuild zip / retag / second ship commit
- PR or `git push origin main` (already at the ship SHA)
- Touch `v2.0.4` / force-push
- Commit leftover ad4090 or cd8a96 paperwork before the tag is on origin

## Constraints

- Backward compatibility: `v2.0.4` remains a previous release
- Data/privacy: do not read `.env` or print tokens
- Operational: no force-push; rollback deletes only `v2.0.5`

## Bounded ruling (print vs execute)

User-approved scope is source of truth #1. «делай» plus prior «да» authorizes finishing the last mile **in this session**. Print-only already left Latest on 2.0.4.

Default runbook is print-only. This change is the authorized exception: record `grok_approve.py production` and execute the two remaining commands. Do not retag, rebuild, or force-push.

`general_implementer` owns the last-mile execution for this route because there is no other write owner and the user forbade another print loop.
