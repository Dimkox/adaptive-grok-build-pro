"""Bounded local lifecycle observations and control requests, emitted as JSON."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.agent_lifecycle import ACTIVITIES, CHECKPOINTS, RESULTS, record_terminal_report, update_agent, watchdog
from adaptive_grok.state import get_agent_state, record_agent_start, record_agent_stop
from adaptive_grok.util import find_root


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # Argument values can contain private material; never echo them on failure.
        print(json.dumps({'error': 'invalid-arguments'}))
        raise SystemExit(2)


def parser() -> argparse.ArgumentParser:
    result = Parser(description=__doc__)
    result.add_argument('--root', type=Path)
    commands = result.add_subparsers(dest='action', required=True, parser_class=Parser)
    start = commands.add_parser('start')
    start.add_argument('--agent-id', required=True)
    start.add_argument('--agent-type', required=True)
    start.add_argument('--generation')
    for action in ('heartbeat', 'progress', 'activity', 'status-request', 'status-ack',
                   'interrupt-request', 'interrupt-ack', 'resume', 'terminated', 'report'):
        command = commands.add_parser(action)
        for field in ('agent-id', 'generation', 'route-id', 'task-id'):
            command.add_argument('--' + field, required=True)
        if action == 'progress':
            command.add_argument('--checkpoint', required=True, choices=sorted(CHECKPOINTS))
        if action == 'activity':
            command.add_argument('--activity', required=True, choices=sorted(ACTIVITIES))
            command.add_argument('--duration-seconds', type=int)
        if action.endswith('-request'):
            command.add_argument('--ack-seconds', type=int, default=60)
        if action.endswith('-ack'):
            command.add_argument('--request-id', required=True)
        if action == 'report':
            command.add_argument('--result', required=True, choices=sorted(RESULTS))
    for action in ('watchdog', 'watch'):
        command = commands.add_parser(action)
        command.add_argument('--heartbeat-seconds', type=int, default=180)
        command.add_argument('--progress-seconds', type=int, default=600)
        if action == 'watch':
            command.add_argument('--iterations', type=int, required=True)
            command.add_argument('--interval', type=float, default=5)
    return result


def run(args: argparse.Namespace, root: Path) -> dict | None:
    if args.action in {'watchdog', 'watch'}:
        iterations = getattr(args, 'iterations', 1)
        interval = getattr(args, 'interval', 0)
        if not 1 <= iterations <= 120 or not 0 <= interval <= 30 or iterations * interval > 3600:
            raise ValueError('invalid-watch-bound')
        for index in range(iterations):
            if index:
                time.sleep(interval)
            print(json.dumps(watchdog(root, heartbeat_seconds=args.heartbeat_seconds,
                                      progress_seconds=args.progress_seconds)), flush=True)
        return None
    if args.action == 'start':
        return record_agent_start(root, args.agent_id, args.agent_type, generation=args.generation)
    if args.action == 'report':
        record_terminal_report(root, args.agent_id, args.generation, args.route_id, args.task_id, args.result)
        return {'reported': True}
    if args.action == 'terminated':
        record = get_agent_state(root).get('active', {}).get(args.agent_id) or {}
        if record.get('route_id') != args.route_id or record.get('task_id') != args.task_id:
            raise ValueError('stale-or-mismatched-instance')
        stopped = record_agent_stop(root, args.agent_id, record.get('agent_type'),
                                    generation=args.generation, final=True)
        if not stopped:
            raise ValueError('termination-not-recorded')
        return {'terminated': True}
    values = {field: getattr(args, field) for field in
              ('checkpoint', 'activity', 'duration_seconds', 'request_id', 'ack_seconds') if hasattr(args, field)}
    return update_agent(root, args.agent_id, args.generation, args.route_id, args.task_id, args.action, **values)


def main() -> int:
    args = parser().parse_args()
    try:
        response = run(args, args.root.resolve() if args.root else find_root())
        if response is not None:
            print(json.dumps(response, ensure_ascii=True))
        return 0
    except (ValueError, TypeError, OSError, TimeoutError):
        print(json.dumps({'error': 'lifecycle-operation-rejected'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
