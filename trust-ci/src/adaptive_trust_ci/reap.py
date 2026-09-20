"""Reaping for children the worker adopts but never tracks.

Why this module exists
----------------------
The deployed ``adaptive-trust-ci worker`` is the ``worker`` service of
``trust-ci/compose.yaml``: it runs as **PID 1 of its own PID namespace** (measured
on the live host as ``NStgid: 1234679 1`` / ``NSpid: 1234679 1``).  PID 1 of a
PID namespace is the kernel-designated reaper for that namespace, so every process
inside the container whose spawner exits is *reparented to the worker*.  When such
an adopted child exits, its entry stays in the PID table as a zombie until the
worker itself calls ``waitpid()``.  No call site can reap it: the process that
forked it is already gone, so ``subprocess`` holds no object for it.

That is the leak in issue #158.  ``git`` leaves children behind (``git
remote-https``, ``git index-pack``) whenever one of those helpers outlives the
``git`` that forked it, so a long-lived worker accumulates one unreaped child per
check run and has no self-healing path short of a restart.

Why this is a janitor and not a ``wait()`` at a call site
--------------------------------------------------------
Call sites already reap the children they own, and adding another ``wait()`` there
is a no-op: ``workspace._run_bounded_process`` reaps on success
(``process.wait(timeout=remaining)``) and on every exception
(``except BaseException: _terminate_process(...); raise``), and
``_terminate_process`` ends with ``poll()`` + ``wait()`` that raises
``'bounded process leader was not reaped'``.  Only *adopted* children are invisible
to that machinery.

No SIGCHLD handler is installed here, deliberately
-------------------------------------------------
``subprocess`` collects status with ``waitpid()`` on a *specific* pid.  A
``SIGCHLD`` handler performing ``waitpid(-1, WNOHANG)`` can harvest the status of a
child that a ``Popen.wait()``/``communicate()`` is still owed, and
``Popen._try_wait`` turns the resulting ``ECHILD`` into a fabricated exit status of
``0`` -- a killed command would be reported as a passing one, which is exactly the
misclassification family of issues #103/#132.  A handler also fires asynchronously
in the main thread at arbitrary bytecode boundaries, i.e. precisely between a
``Popen`` construction and its ``wait()``.  A loop-boundary sweep is different in
kind: it runs only where this package provably has no spawn in flight, which the
``guarded_spawn``/``spawn_in_progress`` counter below makes checkable rather than
assumed.  ``SIGCHLD`` is neither ignored nor handled by this service; this module
keeps it that way.

Coverage rule: every function in this package that creates a child process and
reaps it before returning is decorated with :func:`guarded_spawn`, so the sweep
can prove that no ``Popen`` in this process is mid-wait.
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Iterator, TypeVar

_F = TypeVar('_F', bound=Callable[..., Any])

# One lock guards the spawn counter, the statistics and the sweep itself, so a
# child cannot be born while a sweep is in progress: ``spawn_in_progress`` must
# acquire this lock before its ``Popen`` exists, and it cannot be acquired while
# the sweep holds it.  It is an ``RLock`` so a guarded region that drains (or
# nests another guarded region, as ``sandbox`` does for container cleanup) can
# never self-deadlock a merge-gating service.
_LOCK = threading.RLock()
_SPAWNS_IN_PROGRESS = 0
_STATS = {'sweeps': 0, 'reaped': 0, 'declined': 0, 'errors': 0}


@contextmanager
def spawn_in_progress() -> Iterator[None]:
    """Declares that this process owns a child that still has to be waited on."""
    global _SPAWNS_IN_PROGRESS
    with _LOCK:
        _SPAWNS_IN_PROGRESS += 1
    try:
        yield
    finally:
        with _LOCK:
            _SPAWNS_IN_PROGRESS -= 1


def guarded_spawn(func: _F) -> _F:
    """Wraps a helper that spawns a child and reaps it before it returns."""

    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> object:
        with spawn_in_progress():
            return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def spawns_in_progress() -> int:
    with _LOCK:
        return _SPAWNS_IN_PROGRESS


def reap_adopted_children(*, _waitpid=os.waitpid, _wnohang=os.WNOHANG) -> int:
    """Harvest adopted children that already exited.  Never raises.

    Returns the number of adopted children reaped by this call, ``0`` when the
    sweep declined or found nothing due.  Exit statuses of *adopted* orphans are
    not observable to any consumer (their spawner is gone), so discarding them is
    safe; a status that a live ``Popen`` is still owed is never touched.
    """
    with _LOCK:
        if _SPAWNS_IN_PROGRESS > 0:
            # A child of this process is still awaited by its own spawner; a
            # ``waitpid(-1)`` here could take that status first.  The next
            # boundary re-runs the same non-blocking sweep.
            _STATS['declined'] += 1
            return 0
        reaped = 0
        try:
            while True:
                try:
                    pid, _status = _waitpid(-1, _wnohang)
                except ChildProcessError:
                    break  # ECHILD: this process has no children left
                if pid == 0:
                    break  # children exist, none has exited yet
                reaped += 1
        except OSError:
            _STATS['errors'] += 1
        _STATS['sweeps'] += 1
        _STATS['reaped'] += reaped
        return reaped


def reap_stats() -> dict[str, int]:
    """Cumulative reaping counters for diagnostics (``sweeps``/``reaped``/
    ``declined``/``errors``)."""
    with _LOCK:
        return dict(_STATS)
