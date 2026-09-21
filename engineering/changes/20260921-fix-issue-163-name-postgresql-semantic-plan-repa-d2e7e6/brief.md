# Issue #163: named semantic repair planning refusals

Typed scope: [change-spec.yaml](change-spec.yaml). User delegated remaining issue repair, isolated PR delivery and closure after delivered evidence.

The current SQL function returns anonymous NULL from fifteen refusal sites; request_repair calls the success parser and misreports those preconditions as stored corruption. The adopted [design](design.md) adds only migration022 and a strict plan-specific reader before the unchanged success parser. Historical migrations, security predicates, successful/persisted responses and HTTP contracts remain unchanged.

Prerequisites: frozen PR170 and locally verified PR171/#166 are integrated through commit23eb62dc. No production migration or deployment is part of this source task.
