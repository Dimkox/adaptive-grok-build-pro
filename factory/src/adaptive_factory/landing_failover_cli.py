"""Common operator entrypoint, independent of every provider host process."""

import argparse
import json
from pathlib import Path

from .landing_contracts import MAX_INPUT_BYTES, LandingContractError
from .landing_failover import FailoverCoordinator, MEDIA
from .landing_failover_config import load_failover_config
from .landing_failover_journal import CallerJournal
from .settings import SettingsError, read_private_file


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bounded Qwen → Grok → OpenAI → Claude → OpenRouter submission")
    parser.add_argument("--config", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    submit = commands.add_parser("submit")
    submit.add_argument("--job-id", required=True)
    submit.add_argument("--input", required=True, type=Path)
    submit.add_argument("--media-type", choices=tuple(MEDIA), default="text/plain")
    for name in ("status", "resume"):
        commands.add_parser(name).add_argument("--job-id", required=True)
    args = parser.parse_args(argv)
    try:
        config = load_failover_config(args.config)
        with CallerJournal(config) as journal:
            caller = FailoverCoordinator(config, journal)
            if args.command == "submit":
                protected = {args.config, *(item.token_file for item in config.backends)}
                if args.input in protected or any(root == args.input or root in args.input.parents
                                                  for root in (config.control_repository, config.source_path, config.journal_path)):
                    raise SettingsError("caller input must be outside protected roots")
                payload = read_private_file(args.input, MAX_INPUT_BYTES[MEDIA[args.media_type]])
                result = caller.submit(args.job_id, payload, args.media_type)
            else:
                result = getattr(caller, args.command)(args.job_id)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if result["state"] == "artifact_ready" else 2
    except (SettingsError, LandingContractError, OSError, ValueError):
        print(json.dumps({"schema_version": 1, "state": "stopped", "reason": "caller_request_rejected"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
