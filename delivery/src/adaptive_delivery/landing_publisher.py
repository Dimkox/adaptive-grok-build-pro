from __future__ import annotations

from typing import Never, Protocol, runtime_checkable


class LandingPublicationUnavailable(RuntimeError):
    pass


@runtime_checkable
class LandingPublisher(Protocol):
    def publish(self, artifact: object) -> Never: ...


class UnavailableLandingPublisher:
    """The only shipped landing publication boundary; it has no transport."""

    def publish(self, artifact: object) -> Never:
        del artifact
        raise LandingPublicationUnavailable("publication_unavailable")
