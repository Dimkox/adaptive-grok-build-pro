# Рабочий релиз v2.0.0: пакеты и выкат

Change ID: `20260814-рабочий-релиз-v2-0-0-пакеты-и-выкат-e86e93`
Created: 2026-08-14T20:50:37+00:00
Risk: high
Complexity: high-risk
Domains: generic

## Problem

The public repo still has only the incomplete initial commit. The working tree already contains a green Grok port (hooks, agents, skills, installer) that was never committed or packaged.

## Outcome

A public `v2.0.0` GitHub Release exists on `Dimkox/adaptive-grok-build-pro` with a self-verifying zip, and `main` matches that tag.

## Scope

### In scope

- Commit already-implemented harness files
- Release notes / README-QUICKSTART accuracy
- Manifest + zip package
- Tag, push, GitHub Release

### Out of scope

- New product features
- Renaming the zip *internal* prefix (`adaptive-codex-pro/` is test-locked)
- Hosted CI requirement
- Committing `.env`

## Constraints

- `write_agent: none` — no new application behavior
- Production and GitHub writes only under recorded approvals
