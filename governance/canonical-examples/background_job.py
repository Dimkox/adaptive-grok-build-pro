"""Bounded background-job retry loop with correlation propagation."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar


Result = TypeVar("Result")


class RetryableJobError(RuntimeError):
    """A retryable failure explicitly raised by a job."""


class BackgroundJobError(RuntimeError):
    """A safe terminal job failure."""


def run_background_job(
    job: Callable[[str], Result],
    *,
    max_attempts: int,
    correlation_id: str,
) -> Result:
    if isinstance(max_attempts, bool) or not 1 <= max_attempts <= 3:
        raise BackgroundJobError("max_attempts must be between 1 and 3")
    if not correlation_id:
        raise BackgroundJobError("correlation_id is required")
    for attempt in range(1, max_attempts + 1):
        try:
            return job(correlation_id)
        except RetryableJobError as exc:
            if attempt == max_attempts:
                raise BackgroundJobError("job exhausted retry budget") from exc
    raise BackgroundJobError("job did not produce a result")
