from __future__ import annotations

import io
import json
import signal
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.state import get_agent_state, record_agent_start, record_agent_stop, set_active_route
from adaptive_grok.util import dump_json
from tests._support import project_copy, run_hook

T0 = datetime(2030, 1, 1, tzinfo=timezone.utc)


class AgentLifecycleTests(unittest.TestCase):
    def test_observer_failures_cannot_authorize_sensitive_tools(self) -> None:
        from adaptive_grok.router import build_route
        with project_copy(git=True) as root:
            set_active_route(root, build_route(root, 'Fix security policy boundary', 'synthetic').to_dict())
            payload = {'cwd': str(root), 'agent_id': 'child', 'generation': 'generation'}
            for state in ({'active': [], 'history': []}, {'active': {'child': []}, 'history': []},
                          {'active': {'child': {'route_id': 'synthetic', 'task_id': 'synthetic'}}, 'history': {}}):
                dump_json(root / '.grok-stack/runtime/agent-state.json', state)
                for tool, values in [('Bash', {'command': 'git push origin feature'}),
                                     ('Write', {'file_path': str(root / '.grok-stack/adaptive_grok/policy.py'), 'content': 'x'})]:
                    with self.subTest(state=state, tool=tool):
                        self.assertEqual(run_hook(root, 'pre_tool_use.py', {**payload, 'tool_name': tool, 'tool_input': values})[1]['decision'], 'deny')
            # Inject arbitrary observer Exceptions at the actual hook boundary;
            # policy evaluation and hook output remain real.
            import runpy
            from adaptive_grok import agent_lifecycle
            with patch.object(sys, 'path', [str(root / '.grok/hooks'), *sys.path]):
                hook = runpy.run_path(str(root / '.grok/hooks/pre_tool_use.py'))
            for failure in (RuntimeError('observer'), TypeError('observer'), AttributeError('observer')):
                for tool, values in [('Bash', {'command': 'git push origin feature'}),
                                     ('Write', {'file_path': str(root / '.grok-stack/adaptive_grok/policy.py'), 'content': 'x'}),
                                     ('Read', {'file_path': str(root / 'VERSION')})]:
                    results = []
                    warning = io.StringIO()
                    with patch.object(agent_lifecycle, 'observe_tool', side_effect=failure), \
                         patch.object(sys, 'stderr', warning), \
                         patch.dict(hook['main'].__globals__, {'read_payload': lambda: {**payload, 'tool_name': tool, 'tool_input': values}, 'emit': results.append}):
                        hook['main']()
                    self.assertEqual(results[-1]['decision'], 'allow' if tool == 'Read' else 'deny')
                    self.assertEqual(warning.getvalue(), 'Adaptive Grok: lifecycle observation unavailable; authorization continues.\n')
                    with patch.object(agent_lifecycle, 'observe_tool', side_effect=failure), \
                         patch.object(sys.stderr, 'write', side_effect=OSError('private-marker')), \
                         patch.dict(hook['main'].__globals__, {'read_payload': lambda: {**payload, 'tool_name': tool, 'tool_input': values}, 'emit': results.append}):
                        hook['main']()
                    self.assertEqual(results[-1]['decision'], 'allow' if tool == 'Read' else 'deny')

    def test_changed_active_task_refuses_heartbeat_ack_and_resume_without_mutation(self) -> None:
        from adaptive_grok.state import get_active_route
        for event in ('heartbeat', 'status-ack', 'interrupt-ack', 'resume'):
            with self.subTest(event=event), project_copy() as root:
                record = self.start(root)
                status = self.event(root, record, 'status-request', 1)
                interrupt = self.event(root, record, 'interrupt-request', 2)
                values = {'request_id': (status if event == 'status-ack' else interrupt)['status_request' if event == 'status-ack' else 'interrupt_request']['request_id']}
                if event == 'resume':
                    self.event(root, record, 'interrupt-ack', 3, **values)
                route = get_active_route(root)
                route['change_id'] = 'different-task'
                set_active_route(root, route)
                before = get_agent_state(root)
                with self.assertRaises(ValueError):
                    self.event(root, record, event, 4, **(values if event.endswith('ack') else {}))
                self.assertEqual(get_agent_state(root), before)

    def test_tool_receipt_invalidation_and_verifier_cancel_preserve_writer_progress(self) -> None:
        from adaptive_grok import verification as verifier
        from adaptive_grok.agent_lifecycle import update_agent
        from adaptive_grok.python_test_runner import RunCancelled
        from adaptive_grok.receipts import get_receipt, write_receipt
        with project_copy(git=True) as root:
            self.start(root)
            record_agent_stop(root, 'writer-1', 'general_implementer', now=T0)
            record = record_agent_start(root, 'writer-1', 'general_implementer')
            payload = {'cwd': str(root), 'tool_name': 'Read', 'agent_id': 'writer-1',
                       'agent_type': 'general_implementer',
                       'generation': record['generation']}
            self.assertEqual(run_hook(root, 'post_tool_use.py', payload)[0], 0)
            write_receipt(root, 'verification', 'pass')
            (root / 'source.py').write_text('source changed\n')
            self.assertEqual(run_hook(root, 'post_tool_use.py', payload)[0], 0)
            invalidated = get_receipt(root, 'route-229', 'verification')
            self.assertTrue(invalidated['stale'])
            self.assertEqual(invalidated['status'], 'pass')
            active = get_agent_state(root)['active']['writer-1']
            self.assertEqual(active['last_progress_at'], record['last_progress_at'])
            update_agent(root, 'writer-1', record['generation'], 'route-229', 'task-229',
                         'progress', checkpoint='implementation')
            before = get_agent_state(root)
            with patch.object(verifier, '_python', side_effect=RunCancelled(signal.SIGTERM)), \
                 patch.object(verifier, '_semgrep', return_value=None), \
                 patch.object(verifier, '_trivy_config', return_value=None):
                with self.assertRaises(verifier.VerificationCancelled):
                    verifier.verify(root, mode='fast', record=False)
            self.assertEqual(get_agent_state(root), before)
            with self.assertRaises(ValueError):
                record_agent_start(root, 'writer-2', 'general_implementer')
            self.assertEqual(run_hook(root, 'subagent_stop.py', payload)[1], {})
            self.assertNotIn('writer-1', get_agent_state(root)['active'])

    def start(self, root: Path) -> dict:
        set_active_route(root, {'route_id': 'route-229', 'change_id': 'task-229',
                                'write_agent': 'general_implementer',
                                'allowed_agents': ['general_implementer', 'repo_explorer']})
        return record_agent_start(root, 'writer-1', 'general_implementer', now=T0)

    def event(self, root: Path, record: dict, event: str, seconds: int = 0, **values) -> dict:
        from adaptive_grok.agent_lifecycle import update_agent
        return update_agent(root, 'writer-1', record['generation'], 'route-229', 'task-229',
                            event, now=T0 + timedelta(seconds=seconds), **values)

    def sweep(self, root: Path, seconds: int) -> dict:
        from adaptive_grok.agent_lifecycle import watchdog
        return watchdog(root, now=T0 + timedelta(seconds=seconds))

    def test_synthetic_stuck_running_warns_without_releasing_owner(self) -> None:
        with project_copy() as root:
            record = self.start(root)
            before = get_agent_state(root)
            report = self.sweep(root, 601)
            self.assertEqual(report['agents'][0]['classification'], 'suspected-stall')
            self.assertEqual(set(report['agents'][0]['warnings']), {'heartbeat-overdue', 'progress-overdue'})
            self.assertEqual(get_agent_state(root), before)
            self.assertEqual(report['agents'][0]['generation'], record['generation'])

    def test_fresh_heartbeat_and_polling_are_not_useful_progress(self) -> None:
        with project_copy() as root:
            record = self.start(root)
            self.event(root, record, 'heartbeat', 600)
            self.event(root, record, 'activity', 600, activity='polling')
            self.assertEqual(self.sweep(root, 601)['agents'][0]['warnings'], ['progress-overdue'])
            self.event(root, record, 'progress', 601, checkpoint='test-result')
            self.assertEqual(self.sweep(root, 602)['agents'][0]['warnings'], [])

    def test_bounded_activity_explains_progress_but_never_ack_or_heartbeat(self) -> None:
        with project_copy() as root:
            record = self.start(root)
            self.event(root, record, 'activity', 590, activity='test', duration_seconds=1000)
            request = self.event(root, record, 'status-request', 590)
            self.assertEqual(request['status_request']['deadline_at'], '2030-01-01T00:10:50+00:00')
            report = self.sweep(root, 651)['agents'][0]
            self.assertEqual(set(report['warnings']), {'status-ack-overdue'})
            self.assertTrue(report['bounded_activity'])
            report = self.sweep(root, 800)['agents'][0]
            self.assertEqual(set(report['warnings']), {'heartbeat-overdue', 'status-ack-overdue'})

    def test_interrupt_ack_resume_fences_old_executor_and_preserves_workspace(self) -> None:
        with project_copy() as root:
            record = self.start(root)
            work = root / 'uncommitted.txt'
            work.write_text('unfinished work\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                self.event(root, record, 'resume', 1)
            request = self.event(root, record, 'interrupt-request', 2)
            with self.assertRaises(ValueError):
                self.event(root, record, 'interrupt-ack', 3, request_id='wrong')
            with self.assertRaises(ValueError):
                self.event(root, record, 'resume', 4)
            interrupted = self.event(root, record, 'interrupt-ack', 5,
                                     request_id=request['interrupt_request']['request_id'])
            self.assertEqual(interrupted['lifecycle'], 'interrupted')
            with self.assertRaises(ValueError):
                record_agent_start(root, 'writer-2', 'general_implementer', now=T0)
            resumed = self.event(root, record, 'resume', 6)
            self.assertNotEqual(resumed['generation'], record['generation'])
            self.assertEqual(resumed['task_id'], record['task_id'])
            self.assertEqual(resumed['workspace'], str(root.resolve()))
            self.assertEqual(work.read_text(), 'unfinished work\n')
            before = get_agent_state(root)
            with self.assertRaises(ValueError):
                self.event(root, record, 'progress', 7, checkpoint='implementation')
            self.assertFalse(record_agent_stop(root, 'writer-1', 'general_implementer',
                                              generation=record['generation']))
            self.assertFalse(record_agent_stop(root, 'writer-1', 'general_implementer'))
            self.assertEqual(get_agent_state(root), before)

    def test_status_ack_requires_request_identity_and_does_not_reset_progress(self) -> None:
        with project_copy() as root:
            record = self.start(root)
            with self.assertRaises(ValueError):
                self.event(root, record, 'status-ack', 1, request_id='absent')
            request = self.event(root, record, 'status-request', 590)
            with self.assertRaises(ValueError):
                self.event(root, record, 'status-request', 600)
            updated = self.event(root, record, 'status-ack', 620,
                                 request_id=request['status_request']['request_id'])
            self.assertEqual(updated['last_progress_at'], '2030-01-01T00:00:00+00:00')
            self.assertEqual(self.sweep(root, 621)['agents'][0]['warnings'], ['progress-overdue'])

    def test_duplicate_start_cannot_reset_a_live_instance(self) -> None:
        with project_copy() as root:
            record = self.start(root)
            self.event(root, record, 'status-request', 5)
            before = get_agent_state(root)
            duplicate = record_agent_start(root, 'writer-1', 'general_implementer', now=T0)
            self.assertEqual(duplicate['generation'], record['generation'])
            self.assertEqual(get_agent_state(root), before)
            with self.assertRaises(ValueError):
                record_agent_start(root, 'writer-2', 'general_implementer', now=T0)

    def test_reused_child_id_cannot_be_stopped_by_unversioned_old_executor(self) -> None:
        with project_copy() as root:
            first = self.start(root)
            self.assertTrue(record_agent_stop(root, 'writer-1', 'general_implementer',
                                             generation=first['generation'], now=T0))
            second = record_agent_start(root, 'writer-1', 'general_implementer', now=T0)
            self.assertNotEqual(first['generation'], second['generation'])
            self.assertFalse(record_agent_stop(root, 'writer-1', 'general_implementer', now=T0))
            self.assertTrue(record_agent_stop(root, 'writer-1', 'general_implementer',
                                             generation=second['generation'], now=T0))

    def test_russian_change_identity_supports_heartbeat_ack_and_same_task_resume(self) -> None:
        from adaptive_grok.agent_lifecycle import update_agent
        with project_copy() as root:
            source = '20261002-исправить-ошибку-обработки-агента-ru229a'
            set_active_route(root, {'route_id': 'route-ru', 'change_id': source,
                                    'write_agent': 'general_implementer'})
            record = record_agent_start(root, 'ru-child', 'general_implementer', now=T0)
            task = 'task:07c97be3d028db247dc02e4dcdff082ae8ca537e1e0a47fc6ef74900d155d266'
            self.assertEqual(record['task_id'], task)
            self.assertNotIn(source, json.dumps(get_agent_state(root), ensure_ascii=False))
            binding = (root, 'ru-child', record['generation'], 'route-ru', task)
            update_agent(*binding, 'heartbeat', now=T0 + timedelta(seconds=1))
            status = update_agent(*binding, 'status-request', now=T0 + timedelta(seconds=2))
            update_agent(*binding, 'status-ack', request_id=status['status_request']['request_id'],
                         now=T0 + timedelta(seconds=3))
            interrupted = update_agent(*binding, 'interrupt-request', now=T0 + timedelta(seconds=4))
            update_agent(*binding, 'interrupt-ack', request_id=interrupted['interrupt_request']['request_id'],
                         now=T0 + timedelta(seconds=5))
            resumed = update_agent(*binding, 'resume', now=T0 + timedelta(seconds=6))
            self.assertEqual(resumed['task_id'], task)
            self.assertEqual(resumed['workspace'], record['workspace'])
            self.assertNotEqual(resumed['generation'], record['generation'])

    def test_ascii_task_identity_remains_unchanged_and_unicode_session_fallback_is_supported(self) -> None:
        from adaptive_grok.agent_lifecycle import update_agent
        with project_copy() as root:
            self.assertEqual(self.start(root)['task_id'], 'task-229')
        with project_copy() as root:
            set_active_route(root, {'route_id': 'route-ru', 'session_id': 'сеанс:229',
                                    'write_agent': 'general_implementer'})
            record = record_agent_start(root, 'ru-child', 'general_implementer', now=T0)
            self.assertRegex(record['task_id'], r'^task:[0-9a-f]{64}$')
            self.assertEqual(record_agent_start(root, 'ru-child', 'general_implementer')['task_id'],
                             record['task_id'])
            update_agent(root, 'ru-child', record['generation'], 'route-ru', record['task_id'], 'heartbeat', now=T0)
        with project_copy() as root:
            set_active_route(root, {'route_id': 'route-229', 'write_agent': 'general_implementer'})
            record = record_agent_start(root, 'writer-1', 'general_implementer', now=T0)
            self.assertEqual(record['task_id'], 'route-229')
            update_agent(root, 'writer-1', record['generation'], 'route-229', 'route-229', 'heartbeat', now=T0)

    def test_malformed_and_oversized_task_source_refuse_without_agent_state(self) -> None:
        for source in ('', None, [], 'task with spaces', 'task\nsecret', 'task@value',
                       'я' * 129, 'a' * 129):
            with self.subTest(source_type=type(source).__name__), project_copy() as root:
                set_active_route(root, {'route_id': 'route-ru', 'change_id': source,
                                        'write_agent': 'general_implementer'})
                with self.assertRaises(ValueError):
                    record_agent_start(root, 'ru-child', 'general_implementer', now=T0)
                self.assertEqual(get_agent_state(root)['active'], {})

    def test_cli_control_flow_runs_same_child_to_terminal_report(self) -> None:
        with project_copy() as root:
            set_active_route(root, {'route_id': 'route-229', 'change_id': 'task-229',
                                    'write_agent': 'general_implementer'})
            command = [sys.executable, str(ROOT / 'scripts/grok_agent.py'), '--root', str(root)]

            def call(action: str, *flags: str) -> dict:
                proc = subprocess.run(command + [action, *flags], capture_output=True, text=True, check=False)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                return json.loads(proc.stdout)

            record = call('start', '--agent-id', 'writer-1', '--agent-type', 'general_implementer')
            binding = ['--agent-id', 'writer-1', '--generation', record['generation'],
                       '--route-id', 'route-229', '--task-id', 'task-229']
            call('heartbeat', *binding)
            call('activity', *binding, '--activity', 'test', '--duration-seconds', '600')
            call('progress', *binding, '--checkpoint', 'test-result')
            request = call('status-request', *binding, '--ack-seconds', '30')
            call('status-ack', *binding, '--request-id', request['status_request']['request_id'])
            request = call('interrupt-request', *binding)
            call('interrupt-ack', *binding, '--request-id', request['interrupt_request']['request_id'])
            resumed = call('resume', *binding)
            binding[3] = resumed['generation']
            call('terminated', *binding)
            call('report', *binding, '--result', 'completed')
            report = call('watchdog')
            self.assertEqual(report['agents'], [])
            self.assertEqual(report['terminal'][0]['classification'], 'terminal-completed')

    def test_route_task_generation_and_closed_diagnostics_reject_invalid_updates(self) -> None:
        from adaptive_grok.agent_lifecycle import update_agent
        with project_copy() as root:
            record = self.start(root)
            before = get_agent_state(root)
            for generation, route, task in [('bad', 'route-229', 'task-229'),
                                            (record['generation'], 'other', 'task-229'),
                                            (record['generation'], 'route-229', 'other')]:
                with self.assertRaises(ValueError):
                    update_agent(root, 'writer-1', generation, route, task, 'heartbeat', now=T0)
            with self.assertRaises(ValueError):
                self.event(root, record, 'activity', activity='Authorization: private')
            with self.assertRaises(ValueError):
                self.event(root, record, 'heartbeat', prompt='private')
            with self.assertRaises(ValueError):
                self.event(root, record, 'activity', activity='test', duration_seconds=3601)
            self.assertEqual(get_agent_state(root), before)

    def test_missing_future_and_malformed_timestamps_are_unavailable(self) -> None:
        with project_copy() as root:
            self.start(root)
            for value in (None, 'invalid', '2031-01-01T00:00:00+00:00'):
                state = get_agent_state(root)
                state['active']['writer-1']['last_heartbeat_at'] = value
                dump_json(root / '.grok-stack/runtime/agent-state.json', state)
                self.assertIn('heartbeat-unavailable', self.sweep(root, 1)['agents'][0]['warnings'])

    def test_legacy_records_are_uninstrumented_and_stop_remains_idempotent(self) -> None:
        with project_copy() as root:
            dump_json(root / '.grok-stack/runtime/agent-state.json', {
                'active': {'old': {'agent_type': 'repo_explorer', 'started_at': T0.isoformat()}},
                'history': []})
            report = self.sweep(root, 1)['agents'][0]
            self.assertEqual(report['classification'], 'uninstrumented')
            self.assertTrue(record_agent_stop(root, 'old', 'repo_explorer'))
            self.assertFalse(record_agent_stop(root, 'old', 'repo_explorer'))

    def test_terminal_missing_report_is_distinct_and_late_report_can_be_acknowledged(self) -> None:
        from adaptive_grok.agent_lifecycle import record_terminal_report
        with project_copy() as root:
            record = self.start(root)
            self.assertTrue(record_agent_stop(root, 'writer-1', 'general_implementer',
                                             generation=record['generation'], now=T0))
            terminal = self.sweep(root, 601)['terminal'][0]
            self.assertEqual(terminal['classification'], 'terminal-report-missing')
            self.assertEqual(self.sweep(root, 601)['agents'], [])
            record_terminal_report(root, 'writer-1', record['generation'], 'route-229', 'task-229',
                                   'failed', now=T0 + timedelta(seconds=602))
            self.assertEqual(self.sweep(root, 603)['terminal'][0]['classification'], 'terminal-failed')
            record_agent_start(root, 'writer-2', 'general_implementer', now=T0)

    def test_concurrent_writer_acquisition_has_one_owner(self) -> None:
        with project_copy() as root:
            set_active_route(root, {'route_id': 'route-229', 'write_agent': 'general_implementer'})
            code = ('import sys; from pathlib import Path; '
                    'sys.path.insert(0,sys.argv[1]+"/.grok-stack"); '
                    'from adaptive_grok.state import record_agent_start; '
                    'record_agent_start(Path(sys.argv[1]),sys.argv[2],"general_implementer")')
            children = [subprocess.Popen([sys.executable, '-c', code, str(root), agent],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        for agent in ('one', 'two')]
            results = [(child.communicate(), child.returncode) for child in children]
            self.assertEqual(sorted(code for _, code in results), [0, 1], results)
            self.assertEqual(len(get_agent_state(root)['active']), 1)

    def test_hooks_require_explicit_child_generation_and_keep_stop_output_empty(self) -> None:
        with project_copy() as root:
            self.start(root)
            record_agent_stop(root, 'writer-1', 'general_implementer', now=T0)
            record = record_agent_start(root, 'writer-1', 'general_implementer')
            before = get_agent_state(root)
            run_hook(root, 'pre_tool_use.py', {'cwd': str(root), 'tool_name': 'Read',
                                             'agent_id': 'writer-1'})
            run_hook(root, 'subagent_start.py', {'cwd': str(root), 'agent_type': 'repo_explorer'})
            self.assertEqual(get_agent_state(root), before)
            run_hook(root, 'pre_tool_use.py', {'cwd': str(root), 'tool_name': 'Read',
                                             'subagentId': 'writer-1',
                                             'generation': record['generation']})
            updated = get_agent_state(root)['active']['writer-1']
            self.assertEqual(updated['activity'], 'tool')
            self.assertEqual(updated['last_progress_at'], before['active']['writer-1']['last_progress_at'])
            code, output, _ = run_hook(root, 'subagent_stop.py', {'cwd': str(root),
                'agent_id': 'writer-1', 'generation': 'stale', 'agent_type': 'general_implementer'})
            self.assertEqual((code, output), (0, {}))
            self.assertIn('writer-1', get_agent_state(root)['active'])

    def test_cli_one_shot_finite_watch_and_redacted_error(self) -> None:
        with project_copy() as root:
            self.start(root)
            command = [sys.executable, str(ROOT / 'scripts/grok_agent.py'), '--root', str(root)]
            for tail, lines in [(['watchdog'], 1), (['watch', '--iterations', '2', '--interval', '0'], 2)]:
                proc = subprocess.run(command + tail, capture_output=True, text=True, check=False)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(len(proc.stdout.splitlines()), lines)
                self.assertTrue(all(json.loads(line)['control'] == 'local-observation-only'
                                    for line in proc.stdout.splitlines()))
            proc = subprocess.run(command + ['heartbeat', '--agent-id', 'writer-1',
                '--generation', 'secret-marker', '--route-id', 'route-229', '--task-id', 'task-229'],
                capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertNotIn('secret-marker', proc.stdout + proc.stderr)


if __name__ == '__main__':
    unittest.main()
