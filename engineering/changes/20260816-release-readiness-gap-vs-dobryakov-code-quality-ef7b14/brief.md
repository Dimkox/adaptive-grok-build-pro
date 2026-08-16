# Release-readiness gap vs Dobryakov code-quality toolkit

Change ID: `20260816-release-readiness-gap-vs-dobryakov-code-quality-ef7b14`
Created: 2026-08-16T16:22:06+00:00
Risk: high
Complexity: high-risk
Domains: generic
Write owner: none (this route is design-only)

## Problem

User asked to go to the release part of the product, compare the shipped contour to Dobryakov’s 57-tool / 12-category handbook, and say what can be integrated before a production dump.

## Outcome

A go/no-go split:

- **v2.0.5 stays published.** That is already the GitHub Latest release.
- **No handbook dump.** No new service, DB, or paid SaaS.
- **Approved 2026-08-16:** A on this repo later (Ruff first), then optional consumer profiles (Semgrep / Trivy image / ESLint). Not on this write-less route.

## Scope

### In scope

- Map 12 handbook categories onto this repo
- Name in-house equivalents already shipped
- Recommend A (this-repo CI/verify), B (later consumer profiles), C (never)

### Out of scope

- Implementing any scanner on this route (`write_agent: null`)
- Retagging v2.0.5 / opening 2.1.0
- Standing up SonarQube, Sentry, ELK, Datadog, ZAP, JMeter, TestRail

## Constraints

- Do not add `pyproject.toml` just to light Ruff (flips `detect_repo`, can skip unittest)
- Stdlib-only runtime stays stdlib-only
- Humans own last-mile publish
