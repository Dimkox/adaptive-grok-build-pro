# Events, agents, and cache

## Events

Use `Bitrix\Main\EventManager` for new D7-style handlers when supported. Keep handlers thin and delegate to services. Avoid recursive event loops and hidden writes. Register/unregister module-dependent handlers explicitly.

## Agents

Bitrix agents can execute more than once or later than expected. Agent functions must be idempotent, bounded, observable, and return/retain the correct schedule contract. Heavy jobs should use cron/queue processing rather than page-hit execution. Remove module agents during uninstall.

## Cache

Identify managed cache, tag cache, component cache, composite pages, and application-level projections. A write without correct invalidation is incomplete. Avoid global cache clears as a routine repair. Include multisite and permission-sensitive cache keys where relevant.
