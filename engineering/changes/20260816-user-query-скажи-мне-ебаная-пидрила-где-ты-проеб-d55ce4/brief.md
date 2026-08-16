# Restore agent self-learning as first AGENTS.md rule

Change ID: `20260816-user-query-скажи-мне-ебаная-пидрила-где-ты-проеб-d55ce4`
Route ID: `d55ce4cd4015`
Risk: low
Complexity: standard
Domains: generic

## Problem

The compounding loop was never in committed `AGENTS.md`. The file was authored as the Engineering Contract in `ca63b2d` (2026-08-14) without the two bullets. `engineering/decisions.md` and `engineering/mistakes.md` were added later in `097f5c9` (v2.0.4) and agents already write them, but nothing in `AGENTS.md` tells them to.

The sinks exist. The trigger does not. User: put the instruction back as the first point for agents.

## Outcome

Every agent that reads `AGENTS.md` sees the self-learning rule first, before routing, and writes durable patterns to `engineering/decisions.md` / root-cause mistakes to `engineering/mistakes.md`.

## Scope

### In scope

- Put the two bullets as the first section in `AGENTS.md`, immediately after the H1.
- Name the real paths: `engineering/decisions.md` and `engineering/mistakes.md`.
- Lock the wording with a structure test so the next rewrite cannot drop it again.

### Out of scope

- Version bump, publish, installer seed of the two log files for consumers.
- Rewriting existing decision/mistake entries.
- Adding the loop to every agent `.md` file.

## Constraints

- Backward compatibility: additive docs + one assertion.
- Data/privacy: none.
- Performance: none.
- Operational: no publish.
