"""Pure authorization decision with no ambient or import-time effects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    actor_id: str
    permissions: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class Resource:
    resource_type: str
    resource_id: str


def authorize(actor: Actor, action: str, resource: Resource) -> bool:
    if not actor.actor_id or not action or not resource.resource_id:
        return False
    return (action, resource.resource_type) in actor.permissions
