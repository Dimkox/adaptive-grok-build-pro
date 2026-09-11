# Token Cache Cost Accounting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make provider usage token-category-aware and calculate durable cost from a versioned immutable price table.

**Architecture:** A small pure pricing module validates and canonicalizes the price table, then computes micro-USD cost from five token fields. Protocol and broker validation pass the expanded fact to the store, whose migration preserves the component breakdown and existing task-budget aggregates.

**Tech Stack:** Python 3.12 stdlib, PostgreSQL migrations, JSON Schema/OpenAPI, unittest.

**Spec:** `docs/superpowers/specs/2026-09-11-token-cache-cost-accounting-design.md`

## Global Constraints

- All rates and totals are nonnegative integers in micro-USD; floating-point pricing is forbidden.
- Price-table digest is SHA-256 over canonical JSON and must be validated before cost calculation.
- No provider credentials, prompts, native streams, or live calls enter durable usage data.
- Legacy observations stay readable; no destructive/backfill migration runs.

---

### Task 1: Pure pricing contract

**Files:**
- Create: `factory/src/adaptive_factory/pricing.py`
- Test: `factory/tests/test_pricing.py`

**Interfaces:**
- Produces `UsageTokens`, `PriceTableV1`, `price_table_digest`, and `calculate_cost_usd_micros`.

- [ ] **Step 1: Write failing tests** for a five-rate table, zero cache values, digest mismatch, and fractional micro-USD flooring.
- [ ] **Step 2: Run** `python -m unittest factory.tests.test_pricing` and confirm import failure.
- [ ] **Step 3: Implement** frozen validated dataclasses and integer `tokens * rate // 1_000_000` summation.
- [ ] **Step 4: Re-run** the pricing tests and confirm pass.
- [ ] **Step 5: Commit** the pricing module and its tests.

### Task 2: Versioned event and broker validation

**Files:**
- Modify: `factory/src/adaptive_factory/protocol.py`
- Modify: `factory/src/adaptive_factory/brokers.py`
- Modify: `factory/contracts/openapi/factory-execution.v2.json`
- Test: `factory/tests/test_protocol.py`
- Test: `factory/tests/test_brokers.py`

**Interfaces:**
- Consumes `PriceTableV1`/`UsageTokens`; produces a `UsageProposal` containing components and server-derived cost.

- [ ] **Step 1: Write failing protocol/broker tests** for cache fields, missing price table, and forged total cost.
- [ ] **Step 2: Run** focused unittest cases and confirm the old payload validator rejects the new contract.
- [ ] **Step 3: Implement** v2-only closed payload validation and broker pricing; remove caller-supplied cost acceptance.
- [ ] **Step 4: Update** OpenAPI with required token component and price-table fields.
- [ ] **Step 5: Re-run** protocol and broker tests, then commit.

### Task 3: Durable migration and accounting store

**Files:**
- Create: `factory/src/adaptive_factory/resources/019_usage_token_components.sql`
- Modify: `factory/src/adaptive_factory/store.py`
- Test: `factory/tests/test_execution_persistence_postgres.py`
- Test: `factory/tests/test_postgres_integration.py`

**Interfaces:**
- Consumes priced `UsageProposal`; persists five component columns plus derived cost under existing `(run_id, provider_call_id)` idempotency.

- [ ] **Step 1: Write failing persistence tests** asserting component columns, duplicate equality, and budget aggregation.
- [ ] **Step 2: Run** focused PostgreSQL tests and confirm schema/arguments are missing.
- [ ] **Step 3: Add** a forward-only migration with `NOT NULL DEFAULT 0` cache columns and update store insert/select/idempotency paths.
- [ ] **Step 4: Re-run** focused persistence tests and confirm pass.
- [ ] **Step 5: Commit** migration, store changes, and tests.

### Task 4: End-to-end contract evidence

**Files:**
- Modify: `factory/tests/test_api.py`
- Modify: `factory/tests/test_structure.py`
- Modify: `README.md`

**Interfaces:**
- Consumes the expanded v2 usage body and exposes durable, provider-neutral accounting behavior.

- [ ] **Step 1: Write failing API/structure tests** for cache quantities and server-derived cost.
- [ ] **Step 2: Run** focused tests and confirm contract drift.
- [ ] **Step 3: Update** API adapter path and concise current-state documentation.
- [ ] **Step 4: Run** focused suites plus `python3 scripts/grok_verify.py --mode pr`.
- [ ] **Step 5: Commit** final contract/docs evidence.
