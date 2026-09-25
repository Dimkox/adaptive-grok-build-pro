#!/usr/bin/env python3
"""Run mandatory API/PostgreSQL/actual-restart evidence in one disposable container.

Two cleanup facts are load-bearing here and neither is obvious from the code:

1. A `finally` in this file only runs if an exception propagates. A gate cancelled by
   signal — the observed way this host loses a run (see `mistakes.md` and issue #119,
   where a cancelled `grok_verify` recorded nothing at all) — never reaches it. So the
   harness installs signal handlers that convert cancellation into a raised exception
   before any container exists, and `verify()` must keep raising on SIGTERM for this
   path to stay reachable at all.
2. Ownership begins at `docker run`, not at a successful binding check. A container this
   process minted is reclaimed even when its binding later fails to verify, otherwise a
   rejected bind leaks exactly the running PostgreSQL plus volume the gate exists to bound.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid


_CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
DISPOSABLE_LABEL = "adaptive-factory.disposable-exit"
# The reclaim predicate must be at least as strict as the identity contract the probe
# already enforces (`postgres_restart_probe.py`): a name prefix plus "any non-empty nonce"
# would delete a labelled container this class never minted, e.g. a persistent database
# someone started by hand with a name like `adaptive-factory-exit-cache-prod`.
CONTAINER_NAME_PREFIX = "adaptive-factory-exit-"
CONTAINER_NAME = re.compile(r"^adaptive-factory-exit-[0-9a-f]{12}$")
RUN_NONCE = re.compile(r"^[0-9a-f]{32}$")
DISPOSABLE_IMAGE = "postgres:17-alpine"

# An interrupted run is only distinguishable from a healthy concurrent one by age: the
# harness cannot see another worktree's live process. Two hours is far beyond the readiness
# wait plus the bounded suite and restart probes this file drives, so an orphan older than
# the bound is dead weight while a sibling run in flight is never touched.
ORPHAN_MIN_AGE_SECONDS = 2 * 60 * 60
# Age is only trustworthy inside a plausible window. A container reporting itself as years
# old is either a real orphan or a daemon whose clock/`Created` field cannot be believed;
# the latter must not be destroyed, because an over-stated age is exactly what would let a
# reclaim delete a LIVE sibling's PostgreSQL and its anonymous PGDATA volume.
ORPHAN_MAX_AGE_SECONDS = 30 * 24 * 60 * 60
# Named so the age bound is compared against the real durations rather than a literal
# restated in a test. Readiness deadline + bounded suite + the two restart probes are the
# longest a healthy run can go without touching its container, which is what the orphan
# bound must exceed.
READY_DEADLINE_SECONDS = 30
SUITE_TIMEOUT_SECONDS = 480
RESTART_PROBE_TIMEOUT_SECONDS = 300
MAX_RECLAIM_PER_RUN = 24
# The only caller gives this harness a 600 s wall clock and answers its timeout with
# SIGKILL, which no signal handler can catch. Reclaim therefore gets its own budget well
# inside that ceiling, so cleaning up somebody else's graveyard can never consume the gate.
RECLAIM_TIME_BUDGET_SECONDS = 120


class HarnessCancelled(RuntimeError):
    """Cancellation arrived as a signal; cleanup must run before the process exits."""


def _minted_container_id(value: str) -> str | None:
    container_id = value.strip()
    return container_id if _CONTAINER_ID.fullmatch(container_id) else None


def reclaim_orphan_runs(
    current_nonce: str,
    *,
    now: float | None = None,
    min_age_seconds: int = ORPHAN_MIN_AGE_SECONDS,
    max_age_seconds: int = ORPHAN_MAX_AGE_SECONDS,
    limit: int = MAX_RECLAIM_PER_RUN,
    time_budget_seconds: int = RECLAIM_TIME_BUDGET_SECONDS,
    runner=None,
    clock=None,
) -> list[dict[str, object]]:
    """Remove labelled disposable runs inside the trusted age window, and report each one.

    Nothing is deleted silently: every candidate yields an entry with its age and the
    post-removal observation, and a container that cannot be re-inspected is reported as
    still present rather than assumed gone.

    `runner`/`clock` are resolved at call time, never bound at import: a default of
    `subprocess.run` captured here would let `main()` keep calling the real binary even
    while a unit test patched the module attribute, i.e. a test could delete a live
    container on the machine running the suite.
    """
    docker_run = subprocess.run if runner is None else runner
    monotonic = time.time if clock is None else clock
    started_at = monotonic()
    observed_at = started_at if now is None else now
    listed = docker_run(
        [
            "docker", "ps", "--all", "--quiet", "--no-trunc",
            "--filter", f"label={DISPOSABLE_LABEL}",
        ],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if listed.returncode != 0:
        return []
    candidates = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
    reclaimed: list[dict[str, object]] = []
    attempted = 0
    for container_id in candidates:
        if not _CONTAINER_ID.fullmatch(container_id):
            # A daemon listing short ids means this pass cannot reason about identities.
            # Say so instead of silently reclaiming nothing.
            reclaimed.append({
                'container': container_id[:64],
                'action': 'skipped',
                'reason': 'listing is not a full 64-hex container id; cannot prove ownership',
            })
            continue
        if attempted >= limit:
            reclaimed.append({
                'container': container_id,
                'action': 'skipped-limit',
                'reason': f'reclaim budget of {limit} reached; a later run continues',
            })
            continue
        if monotonic() - started_at > time_budget_seconds:
            reclaimed.append({
                'container': container_id,
                'action': 'skipped-timeout',
                'reason': f'reclaim time budget of {time_budget_seconds}s reached; the rest is left to a later run',
            })
            continue
        record = _reclaim_candidate(
            container_id, current_nonce, observed_at, min_age_seconds,
            max_age_seconds, docker_run,
        )
        if record is not None:
            reclaimed.append(record)
            if record.get('action') not in {'skipped', 'skipped-limit', 'skipped-timeout'}:
                attempted += 1
    return reclaimed


def _reclaim_candidate(
    container_id: str,
    current_nonce: str,
    observed_at: float,
    min_age_seconds: int,
    max_age_seconds: int,
    runner,
) -> dict[str, object] | None:
    inspected = runner(
        [
            "docker", "inspect",
            "--format",
            '{{.Id}}\t{{.Name}}\t{{.Config.Image}}\t'
            '{{index .Config.Labels "adaptive-factory.disposable-exit"}}\t'
            '{{.Created}}\t{{.State.Running}}',
            container_id,
        ],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    if inspected.returncode != 0 or len(inspected.stdout.strip().split("\t")) != 6:
        return {'container': container_id, 'action': 'skipped', 'reason': 'cannot inspect'}
    identity, name, image, nonce, created, running = inspected.stdout.strip().split("\t")
    name = name.lstrip("/")
    if identity != container_id:
        return {'container': container_id, 'action': 'skipped', 'reason': 'identity mismatch'}
    if nonce == current_nonce:
        return None
    age = _observed_age_seconds(created, observed_at)
    if age is None:
        return {'container': container_id, 'action': 'skipped', 'reason': 'unparsable creation time'}
    if (
        image != DISPOSABLE_IMAGE
        or CONTAINER_NAME.fullmatch(name) is None
        or RUN_NONCE.fullmatch(nonce) is None
    ):
        return {'container': container_id, 'action': 'skipped', 'reason': 'foreign run shape'}
    if age < min_age_seconds:
        return None
    if age > max_age_seconds:
        return {'container': container_id, 'action': 'skipped', 'reason': 'age outside the trusted window'}
    removed = runner(
        ["docker", "rm", "-f", "-v", container_id],
        text=True, capture_output=True, timeout=60, check=False,
    )
    after = runner(
        ["docker", "inspect", container_id],
        text=True, capture_output=True, timeout=15, check=False,
    )
    return {
        'container': container_id,
        'name': name,
        'nonce': nonce,
        'age_seconds': int(age),
        'was_running': running == 'true',
        'action': 'reclaimed' if after.returncode != 0 else 'leaked',
        'removal_exit': removed.returncode,
    }


def _observed_age_seconds(created: str, observed_at: float) -> float | None:
    """Age from Docker's RFC3339-nanosecond UTC `.Created`, without trusting local clocks."""
    text = created.strip()
    if not text:
        return None
    try:
        normalized = re.sub(r'(\.\d{6})\d*', r'\1', text.replace('Z', '+00:00'))
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, observed_at - parsed.timestamp())


def _report_reclaimed(records: list[dict[str, object]]) -> int:
    """Print one line per decision and return the count that still holds its container."""
    if not records:
        # Nothing was listed, so there is nothing to account for. A summary on every clean
        # run would add a line to each gate and make the harness's own single-PASS-announcement
        # contract ambiguous.
        return 0
    counts: dict[str, int] = {}
    for record in records:
        action = str(record.get('action') or 'unknown')
        counts[action] = counts.get(action, 0) + 1
        if action in {'reclaimed', 'leaked'}:
            print(
                f"RECLAIM {action} container={record.get('container')} name={record.get('name')} "
                f"age_seconds={record.get('age_seconds')} was_running={record.get('was_running')} "
                f"removal_exit={record.get('removal_exit')}"
            )
            continue
        print(
            f"RECLAIM {action} container={record.get('container')} "
            f"reason={record.get('reason', record.get('code', 'unspecified'))}"
        )
    summary = ' '.join(f'{key}={counts[key]}' for key in sorted(counts))
    print(f"RECLAIM summary {summary or 'no-candidates'}")
    return counts.get('leaked', 0)


def _cancel_on_signal(signum: int, _frame: object) -> None:  # pragma: no cover - raised below
    raise HarnessCancelled(f'received signal {signum}')


class _CancellationScope:
    """Turn SIGTERM/SIGINT into a raised exception so the cleanup `finally` is reachable."""

    def __init__(self) -> None:
        self.previous: dict[int, object] = {}

    def install(self) -> "_CancellationScope":
        if threading.current_thread() is not threading.main_thread():
            return self
        for signum in (signal.SIGTERM, signal.SIGINT):
            if signal.getsignal(signum) is _cancel_on_signal:
                continue
            try:
                self.previous[signum] = signal.getsignal(signum)
                signal.signal(signum, _cancel_on_signal)
            except (OSError, ValueError):
                self.previous.pop(signum, None)
        return self

    def restore(self) -> None:
        for signum, handler in list(self.previous.items()):
            try:
                signal.signal(signum, handler)
            except (OSError, ValueError):
                pass
        self.previous.clear()


def _binding_matches(
    container_id: str,
    name: str,
    nonce: str,
    *,
    require_running: bool,
) -> bool:
    if not _CONTAINER_ID.fullmatch(container_id):
        return False
    inspected = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            '{{.Id}}\t{{.Name}}\t{{.Config.Image}}\t{{.State.Running}}\t'
            '{{index .Config.Labels "adaptive-factory.disposable-exit"}}',
            container_id,
        ],
        text=True,
        capture_output=True,
        timeout=10,
    )
    if inspected.returncode != 0:
        return False
    fields = inspected.stdout.strip().split("\t")
    if len(fields) != 5:
        return False
    identity_matches = fields[:3] == [
        container_id,
        f"/{name}",
        "postgres:17-alpine",
    ] and fields[3] in {"true", "false"} and fields[4] == nonce
    return identity_matches and (not require_running or fields[3] == "true")


def _remove_bound_container(
    container_id: str,
    name: str,
    nonce: str,
    *,
    minted: bool = False,
) -> None:
    if not _CONTAINER_ID.fullmatch(container_id):
        raise RuntimeError(
            f"refusing to delete a container id this process did not mint; id={container_id[:16]}"
        )
    if not minted and not _binding_matches(
        container_id, name, nonce, require_running=False
    ):
        raise RuntimeError(
            f"refusing to delete unbound container; leaked id={container_id}"
        )
    # `minted` means the id came straight from this process's own `docker run` stdout. No
    # stranger can own it, so a failed binding check must not become a second leak: the
    # old shape of that refusal is exactly what issue 128 reports.
    subprocess.run(
        ["docker", "rm", "-f", "-v", container_id],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )


def _run(command: list[str], *, environment: dict[str, str] | None = None, timeout: int = 300) -> None:
    subprocess.run(command, check=True, env=environment, timeout=timeout)


def _published_loopback_port(value: str) -> int:
    lines = value.strip().splitlines()
    if len(lines) != 1:
        raise RuntimeError("disposable PostgreSQL port mapping is ambiguous")
    match = re.fullmatch(r"127\.0\.0\.1:([0-9]{1,5})", lines[0])
    if match is None:
        raise RuntimeError("disposable PostgreSQL port is not loopback-only")
    port = int(match.group(1))
    if not 1 <= port <= 65_535:
        raise RuntimeError("disposable PostgreSQL port is invalid")
    return port


def _final_postgres_ready(container_id: str) -> bool:
    final_postmaster = subprocess.run(
        [
            "docker", "exec", container_id, "sh", "-c",
            'test "$(sed -n "1p" "$PGDATA/postmaster.pid")" = 1',
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    if final_postmaster.returncode != 0:
        return False
    ready = subprocess.run(
        ["docker", "exec", container_id, "pg_isready", "-U", "factory_exit", "-d", "factory_exit"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    return ready.returncode == 0


def main() -> int:
    name = f"{CONTAINER_NAME_PREFIX}{uuid.uuid4().hex[:12]}"
    nonce = uuid.uuid4().hex
    password = f"local-{uuid.uuid4().hex}"
    environment = os.environ.copy()
    environment["FACTORY_TEST_POSTGRES_CONTAINER"] = name
    import_roots = (str(Path.cwd() / "factory"), str(Path.cwd()))
    environment["PYTHONPATH"] = os.pathsep.join(
        (*import_roots, environment.get("PYTHONPATH", ""))
    ).rstrip(os.pathsep)
    bound_container_id: str | None = None
    # Handlers go in before anything exists to clean up, so a cancellation that lands
    # during `docker run` itself cannot leave an ownerless container behind.
    cancellation = _CancellationScope()
    cancellation.install()
    try:
        _report_reclaimed(reclaim_orphan_runs(nonce))
        created = subprocess.run([
            "docker", "run", "--name", name,
            "--label", f"{DISPOSABLE_LABEL}={nonce}",
            "-e", "POSTGRES_DB=factory_exit",
            "-e", "POSTGRES_USER=factory_exit",
            "-e", f"POSTGRES_PASSWORD={password}",
            "-p", "127.0.0.1::5432",
            "-d", DISPOSABLE_IMAGE,
        ], check=True, text=True, capture_output=True, timeout=60)
        container_id = _minted_container_id(created.stdout)
        if container_id is None:
            raise RuntimeError(
                "disposable container id is unparsable; "
                f"leaked output={created.stdout.strip()[:120]!r}"
            )
        # Ownership begins here: from this line the finally below answers for this
        # container whether or not its binding ever verifies.
        bound_container_id = container_id
        environment["FACTORY_TEST_POSTGRES_CONTAINER_ID"] = container_id
        environment["FACTORY_TEST_POSTGRES_NONCE"] = nonce
        if not _binding_matches(
            container_id, name, nonce, require_running=True
        ):
            raise RuntimeError(
                f"disposable container binding failed; reclaimed id={container_id}"
            )
        published = subprocess.run(
            ["docker", "port", container_id, "5432/tcp"],
            check=True,
            text=True,
            capture_output=True,
            timeout=10,
        ).stdout.strip()
        port = _published_loopback_port(published)
        environment["FACTORY_TEST_DATABASE_URL"] = f"postgresql://factory_exit:{password}@127.0.0.1:{port}/factory_exit"
        deadline = time.monotonic() + READY_DEADLINE_SECONDS
        while True:
            if _final_postgres_ready(container_id):
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("disposable PostgreSQL final postmaster did not become ready")
            time.sleep(0.25)
        with tempfile.TemporaryDirectory(prefix="adaptive-factory-exit-venv-") as environment_root:
            environment["UV_PROJECT_ENVIRONMENT"] = environment_root
            uv = ["uv", "run", "--project", "factory"]
            _run(
                [
                    *uv,
                    "python",
                    "factory/tests/postgres_restart_probe.py",
                    "--preflight-only",
                ],
                environment=environment,
            )
            _run(
                [
                    *uv,
                    "python",
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "factory/tests",
                    "-t",
                    ".",
                    "-v",
                ],
                environment=environment,
                timeout=SUITE_TIMEOUT_SECONDS,
            )
            _run([*uv, "python", "factory/tests/postgres_restart_probe.py"], environment=environment)
        print("PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation")
        return 0
    except HarnessCancelled as cancelled:
        # A cancelled run is not a passed run and never was: report it, reclaim below, and
        # leave a non-zero exit so no receipt can call this a pass.
        print(f"CANCELLED: {cancelled}", file=sys.stderr)
        raise SystemExit(130)
    finally:
        try:
            if bound_container_id is not None:
                # This id came from this process's own `docker run` stdout, so it is
                # authoritative regardless of whether the later binding check ever passed:
                # a transient daemon failure must not refuse to delete our own container.
                _remove_bound_container(bound_container_id, name, nonce, minted=True)
        finally:
            # Handler restore cannot sit behind the removal. The factory suites call
            # `main()` in-process, so a leaked `_cancel_on_signal` handler would turn an
            # unrelated later SIGTERM into an exception inside another test.
            cancellation.restore()


if __name__ == "__main__":
    raise SystemExit(main())
