---
name: bitrix-development
description: Use for any 1C-Bitrix or Bitrix24 repository task involving modules, components, events, agents, ORM, CRM, REST, cache, permissions, or legacy APIs.
---

# Bitrix Development Pack

Read `references/architecture.md`, `references/modules.md`, `references/events-agents-cache.md`, and `references/testing-review.md` as relevant.

## Default architecture

- Put custom code under `local/`.
- Prefer D7 APIs for new code.
- Keep Bitrix-facing adapters thin; domain logic should be testable without a full page request.
- Use services, repositories, value objects, and explicit DTOs where they reduce global/static coupling.
- Keep component classes thin and templates presentation-only.

## Mandatory impact scan

Identify affected:

- custom module or component;
- events and handler registration;
- Bitrix agents/cron/queues;
- ORM tables, migrations, highload blocks, iblocks, CRM entities;
- managed/tag/composite cache;
- permissions and current-user assumptions;
- localization and multisite behavior;
- install/update/uninstall path;
- REST/webhook/external integration contracts.

## Forbidden default

Do not edit `bitrix/modules`, `bitrix/components`, or `bitrix/js`. Implement an extension under `local/`. A protected-path approval is only for a documented temporary exception with update risk and rollback.

## Completion

Run the `bitrix` quality profile and dispatch `bitrix_reviewer`. Core safety, lifecycle symmetry, cache behavior, permissions, and update compatibility are release-blocking concerns.
