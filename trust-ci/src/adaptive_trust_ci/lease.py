from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable

from .models import utc_now
from .store import Store


@dataclass
class LeaseKeeper:
    store: Store
    job_id: str
    worker_id: str
    lease_seconds: int
    now_fn: Callable = utc_now
    _stop: threading.Event = field(init=False, default_factory=threading.Event)
    _thread: threading.Thread | None = field(init=False, default=None)
    _error: BaseException | None = field(init=False, default=None)

    def __enter__(self) -> "LeaseKeeper":
        interval = max(1.0, self.lease_seconds / 3)

        def loop() -> None:
            while not self._stop.wait(interval):
                try:
                    self.store.heartbeat(
                        self.job_id,
                        self.worker_id,
                        self.lease_seconds,
                        now=self.now_fn(),
                    )
                except BaseException as exc:  # surfaced in the trusted worker thread
                    self._error = exc
                    self._stop.set()
                    return

        self._thread = threading.Thread(target=loop, name=f"lease-{self.job_id}", daemon=True)
        self._thread.start()
        return self

    def check(self) -> None:
        if self._error is not None:
            raise RuntimeError(f"job lease heartbeat failed: {self._error}") from self._error

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(2.0, self.lease_seconds / 2))
        if exc_type is None:
            self.check()
