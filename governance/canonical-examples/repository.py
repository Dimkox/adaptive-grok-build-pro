"""Parameterized repository boundary with an explicit idempotency key."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class RepositoryError(RuntimeError):
    """A safe, typed repository failure."""


class Repository:
    def __init__(self, execute: Callable[[str, tuple[object, ...]], Any]) -> None:
        self._execute = execute

    def get_by_id(self, identifier: object) -> Any:
        if identifier is None or identifier == "":
            raise RepositoryError("identifier is required")
        return self._execute(
            "SELECT payload FROM entities WHERE entity_id = $1",
            (identifier,),
        )

    def save(self, entity: object, idempotency_key: str) -> Any:
        if not idempotency_key:
            raise RepositoryError("idempotency_key is required")
        return self._execute(
            "INSERT INTO entity_commands (payload, idempotency_key) VALUES ($1, $2) "
            "ON CONFLICT (idempotency_key) DO NOTHING",
            (entity, idempotency_key),
        )
