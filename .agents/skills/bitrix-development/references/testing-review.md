# Bitrix testing and review

Use the strongest available layer:

- pure unit tests for isolated services/value objects;
- integration tests with Bitrix bootstrap for ORM, events, options, and module behavior;
- component/API tests for request contracts and permissions;
- browser E2E for critical admin/user flows;
- install/update/uninstall smoke tests for custom modules;
- repeatable CLI scripts when the existing project has no test harness yet.

Independent review must inspect core safety, D7/legacy boundaries, permissions, cache, module lifecycle, agents, query count, update compatibility, and error handling.
