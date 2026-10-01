# Release plan — Implement the Factory v1.5 PR2 decision persistence contour on current main: transplant the five existing decision persistence commits from the isolated branch, resolve bounded API and data persistence conflicts, preserve behavior and tests, and deliver the isolated candidate

## Deployment

PR-only source delivery. Migration 023 applies later through the existing migrator under separate deployment authority.

## Feature flags / staged rollout

Legacy behavior remains default because `decision_record` is optional and absent from HTTP v1. Enable typed producers incrementally after schema 23 readiness.

## Metrics and alerts

Migration/readiness status, transition conflict/failure counts, decision append/replay outcomes and audit correlation IDs.

## Go/no-go criteria

Current-main ancestry; bounded diff; schema parity and two-restart probe pass; full verifier and both reviews pass; zero evidence gaps; external Trust CI after PR push.
