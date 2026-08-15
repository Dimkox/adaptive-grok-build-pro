# Free MIT commercial product positioning

Change ID: `20260815-free-mit-commercial-product-positioning-bb6ab3`
Risk: low (route high is a false positive: `'прод' in 'продукт'`)
Domains: generic

## Problem

The product should be run as a **commercial product** that is **free** and **MIT**. The last pass stripped commercial language. This route was classified high-risk / `production_action_approval` because `_risk` matches `'прод'` inside `'продукт'`.

## Outcome

README presents a commercial-grade product that is free, public, and MIT. No EULA or paid tier. `'продукт'` does not trip production risk.

## Gates

- Scope: the user sentence is the approval.
- `production_action_approval` is **not** consumed. No publish.
