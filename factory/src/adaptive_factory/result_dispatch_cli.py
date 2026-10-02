from __future__ import annotations

import argparse
import signal
import time

from .result_dispatch import ResultDispatcher, UdsResultHandoffClient
from .settings import FactorySettings, SettingsError, read_token_file
from .store import PostgresResultDispatcherStore


class ResultDispatchCliError(RuntimeError):
    pass


def compose_result_dispatcher(settings: FactorySettings, store) -> ResultDispatcher:
    settings.validate_result_dispatch()
    if not settings.result_dispatch_enabled:
        raise ResultDispatchCliError("result dispatch is disabled")
    try:
        return ResultDispatcher(
            store,
            UdsResultHandoffClient(
                settings.result_dispatch_socket_path,
                read_token_file(settings.result_dispatch_token_file),
                timeout_seconds=settings.result_dispatch_timeout_seconds,
            ),
            dispatcher_id=settings.result_dispatcher_id,
            batch_size=settings.result_dispatch_batch_size,
            lease_seconds=settings.result_dispatch_lease_seconds,
            poll_seconds=settings.result_dispatch_poll_seconds,
        )
    except (SettingsError, ValueError) as exc:
        raise ResultDispatchCliError("result dispatcher configuration is invalid") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adaptive-factory-result-dispatch")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    settings = FactorySettings.from_environment()
    dispatcher = compose_result_dispatcher(
        settings, PostgresResultDispatcherStore(settings.result_dispatch_database_url)
    )
    if args.once:
        dispatcher.run_once()
        return 0
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    while not stopping:
        dispatcher.run_once()
        deadline = time.monotonic() + dispatcher.poll_seconds
        while not stopping and time.monotonic() < deadline:
            time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
