# Release plan — Add Factory v1.5 decision accounting boundary behavior from source commit 531089f to the PR2 persistence foundation: enforce bounded cost and duration values and exact persisted accounting invariants as a new feature slice, with regression tests and isolated PR delivery

## Deployment

No deployment. Deliver as a stacked PR based on PR231.

## Feature flags / staged rollout

No flag needed; helper currently has test-only consumers and the change rejects only out-of-range input.

## Metrics and alerts

ContractError field identity and dual discovery tests are the observable signals for this slice.

## Go/no-go criteria

Go only with exact-tree full verifier, independent code/test reviews, zero evidence gaps and App-owned Trust CI on the pushed PR head. Merge remains owner-controlled.
