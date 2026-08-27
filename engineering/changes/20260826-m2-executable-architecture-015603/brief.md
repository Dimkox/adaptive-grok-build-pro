# M2-A — Executable Architecture

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260826-m2-executable-architecture-015603`

Route: `0156034c05bd`

Adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`

Risk: red

Domains: API, data, event, security

## Problem

Before M2-A, the README K16 clique inventoried pieces but could not represent direction, trust, data, secrets, contracts, or deployment boundaries. The repository had no strict architecture model, deterministic drift/diff, explicit fitness applicability, or digest that later factory milestones could bind.

## Outcome

M2-A implements a strict target-owned architecture contract, explicit adoption marker, deterministic local validator/CLI/diagrams/diff/fitness evidence, and receipt staleness. It does not change Trust CI source. M2-B consumes the frozen contract in a separate task for independent enforcement.

## In scope

- canonical schemas, model, rules, public contract baselines, parser, digest, diff, drift and fitness;
- five reproducible text diagrams;
- local verification/receipt and installer integration;
- complete red-risk M2-A package and source verification; independent route reviews and receipts remain coordinator-owned pending work.

## Out of scope

- all `trust-ci/**` mutations and deployed policy/holdout changes;
- M4+ runtime, PostgreSQL additions, migrations, services, queues, frameworks, providers, systemd, external writes;
- claiming local source or receipts are merge authority.

## Constraints

- Backward compatibility: preserve M1 v2, historical v1 read support, and current receipt behavior for repositories without architecture adoption.
- Data/privacy: only stable secret-class metadata; never secret values, credential paths, source bodies, or raw payloads in evidence.
- Performance: bounded documents, inventories, findings, Git output, AST analysis, and generated artifacts.
- Operational: local source only; exact M2 evidence uses the frozen adoption base and an exact clean head.
- Adoption: installer-delivered examples are non-authoritative; operators review target models and then manually add canonical `architecture/adoption.json`. The installer never manages those three target-owned files.
