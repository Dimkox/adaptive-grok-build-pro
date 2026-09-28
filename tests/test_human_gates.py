from __future__ import annotations

import sys
import subprocess
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.change import start_change, transition
from adaptive_grok.human_gates import (
    gate_block_reason,
    gate_statuses,
    gate_transition_block_reason,
    record_gate_decision,
)
from adaptive_grok.policy import evaluate_pre_tool
from adaptive_grok.router import build_route
from adaptive_grok.state import add_approval, approvals_path, get_active_route, has_valid_approval, set_active_route
from tests._support import project_copy

ROUTE_PATH = '.grok-stack/runtime/active-route.json'


class HumanGateTests(unittest.TestCase):
    def _active_change(self, root: Path, gates: list[str]):
        subprocess.run(
            ['git', 'remote', 'add', 'origin', 'git@github.com:Dimkox/adaptive-grok-build-pro.git'],
            cwd=root,
            check=True,
        )
        route = build_route(root, 'Prepare production release and canary', 'gate-test').to_dict()
        route['human_gates'] = gates
        set_active_route(root, route)
        state = start_change(root)
        transition(root, state['change_id'], 'scoped', 'package scope prepared')
        return state

    def test_declared_scope_gate_is_pending_and_blocks_approved_transition(self) -> None:
        with project_copy(git=True) as root:
            state = self._active_change(root, ['scope_and_design_approval'])

            self.assertEqual(gate_statuses(root)[0]['state'], 'pending')
            with self.assertRaisesRegex(ValueError, 'scope_and_design_approval.*pending'):
                transition(root, state['change_id'], 'approved', 'approve implementation')

            record_gate_decision(
                root, 'scope_and_design_approval', 'approved', 'Scope and design reviewed', actor='human'
            )
            self.assertEqual(gate_statuses(root)[0]['state'], 'approved')
            self.assertEqual(transition(root, state['change_id'], 'approved', 'approve implementation')['status'], 'approved')

    def test_declined_and_stale_scope_decisions_never_satisfy_gate(self) -> None:
        with project_copy(git=True) as root:
            state = self._active_change(root, ['scope_and_design_approval'])
            record_gate_decision(
                root, 'scope_and_design_approval', 'rejected', 'Needs revision', actor='human'
            )
            self.assertEqual(gate_statuses(root)[0]['state'], 'rejected')
            with self.assertRaisesRegex(ValueError, 'scope_and_design_approval.*rejected'):
                transition(root, state['change_id'], 'approved', 'try rejected scope')
            record_gate_decision(
                root, 'scope_and_design_approval', 'approved', 'Revised scope accepted', actor='human'
            )
            (root / 'engineering/changes' / state['change_id'] / 'requirements.md').write_text(
                'changed scope\n', encoding='utf-8'
            )
            self.assertEqual(gate_statuses(root)[0]['state'], 'stale')
            with self.assertRaisesRegex(ValueError, 'scope_and_design_approval.*stale'):
                transition(root, state['change_id'], 'approved', 'try stale scope')

    def test_production_gate_and_exact_grant_are_independent_controls(self) -> None:
        with project_copy(git=True) as root:
            self._active_change(root, ['production_action_approval'])
            command = {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin feature'}}

            with self.assertRaisesRegex(ValueError, 'production_action_approval.*pending'):
                add_approval(root, 'production', 'ship', 5, actions=['git-push-branch'])
            record_gate_decision(
                root,
                'production_action_approval',
                'approved',
                'Approve this branch push',
                actor='human',
                action='git-push-branch',
            )
            self.assertEqual(gate_statuses(root)[0]['state'], 'approved')
            tag_allowed, tag_reason = evaluate_pre_tool(
                root,
                {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin v2.1.0'}},
            )
            self.assertFalse(tag_allowed)
            self.assertIn('production_action_approval', tag_reason or '')
            allowed, reason = evaluate_pre_tool(root, command)
            self.assertFalse(allowed)
            self.assertIn('exact delegated local grant', reason or '')

            add_approval(root, 'production', 'ship', 5, actions=['git-push-branch'])
            allowed, reason = evaluate_pre_tool(root, command)
            self.assertTrue(allowed, reason)
            tag_allowed, _ = evaluate_pre_tool(
                root,
                {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin v2.1.0'}},
            )
            self.assertFalse(tag_allowed)

    def test_external_write_gate_binds_exact_target_in_add_and_consume(self) -> None:
        with project_copy(git=True) as root:
            state = self._active_change(root, ['migration_or_external_write_approval'])
            with self.assertRaisesRegex(ValueError, 'migration_or_external_write_approval.*pending'):
                transition(
                    root,
                    state['change_id'],
                    'approved',
                    'approve migration implementation',
                )
            record_gate_decision(
                root,
                'migration_or_external_write_approval',
                'approved',
                'Approve migration plan in the change scope',
                actor='human',
                action='migration-plan',
            )
            transition(root, state['change_id'], 'approved', 'migration plan approved')
            target = 'https://api.example.test/v1/records'
            command = f'curl -X POST {target} -d "{{}}"'
            with self.assertRaisesRegex(ValueError, 'migration_or_external_write_approval.*pending'):
                add_approval(
                    root,
                    'external-write',
                    'write records',
                    5,
                    actions=['external-write'],
                    resources=[target],
                )
            record_gate_decision(
                root,
                'migration_or_external_write_approval',
                'approved',
                'Approve one endpoint write',
                actor='human',
                action='external-write',
                resource=target,
            )
            add_approval(
                root,
                'external-write',
                'write records',
                5,
                actions=['external-write'],
                resources=[target],
            )
            allowed, reason = evaluate_pre_tool(
                root,
                {'tool_name': 'Bash', 'tool_input': {'command': command}},
            )
            self.assertTrue(allowed, reason)
            other_allowed, reason = evaluate_pre_tool(
                root,
                {'tool_name': 'Bash', 'tool_input': {'command': 'curl -X POST https://api.example.test/v1/other -d "{}"'}},
            )
            self.assertFalse(other_allowed)
            self.assertIn('migration_or_external_write_approval', reason or '')

    def test_external_gate_aggregate_is_not_approved_when_any_target_is_rejected(self) -> None:
        with project_copy(git=True) as root:
            self._active_change(root, ['migration_or_external_write_approval'])
            first = 'https://api.example.test/v1/first'
            second = 'https://api.example.test/v1/second'
            for target, decision in ((first, 'approved'), (second, 'rejected')):
                record_gate_decision(
                    root,
                    'migration_or_external_write_approval',
                    decision,
                    f'{decision} this exact endpoint',
                    actor='human',
                    action='external-write',
                    resource=target,
                )

            status = gate_statuses(root)[0]
            self.assertEqual(status['state'], 'rejected')
            self.assertEqual(
                {item['state'] for item in status['targets']},
                {'approved', 'rejected'},
            )
            self.assertIn('every listed exact target', status['reason'])

    def test_revised_gate_decisions_are_append_only_and_latest_decision_is_current(self) -> None:
        with project_copy(git=True) as root:
            self._active_change(root, ['production_action_approval'])
            for decision, reason in (('approved', 'initial approval'), ('rejected', 'withdraw approval')):
                record_gate_decision(
                    root,
                    'production_action_approval',
                    decision,
                    reason,
                    actor='human',
                    action='git-push-branch',
                )

            status = gate_statuses(root)[0]
            self.assertEqual(status['state'], 'rejected')
            self.assertEqual(
                [item['decision'] for item in status['targets'][0]['decision_history']],
                ['approved', 'rejected'],
            )

    def test_missing_or_malformed_decision_is_reported_and_fails_closed(self) -> None:
        with project_copy(git=True) as root:
            state = self._active_change(root, ['production_action_approval'])
            status = gate_statuses(root)[0]
            self.assertEqual(status['state'], 'pending')
            self.assertEqual(status['evidence_path'], f"engineering/changes/{state['change_id']}/human-gates.json")

            package = root / 'engineering/changes' / state['change_id']
            (package / 'human-gates.json').write_text('{ malformed', encoding='utf-8')
            self.assertEqual(gate_statuses(root)[0]['state'], 'invalid')

    def test_local_grant_and_trust_ci_file_cannot_satisfy_gate(self) -> None:
        with project_copy(git=True) as root:
            self._active_change(root, [])
            route = json.loads((root / '.grok-stack/runtime/active-route.json').read_text(encoding='utf-8'))
            package = root / 'engineering/changes' / route['change_id']
            evidence = package / 'evidence'
            evidence.mkdir(exist_ok=True)
            (evidence / 'trust-ci.json').write_text(
                json.dumps({'scope': 'production_action_approval', 'verified': True}),
                encoding='utf-8',
            )
            add_approval(
                root,
                'protected-path',
                'unrelated protected path permission',
                5,
                actions=['protected-path-write'],
                resources=['README.md'],
            )
            add_approval(root, 'production', 'explicit ship grant', 5, actions=['git-push-branch'])
            self.assertTrue(
                evaluate_pre_tool(
                    root,
                    {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin feature'}},
                )[0]
            )
            route['human_gates'] = ['production_action_approval']
            set_active_route(root, route)
            allowed, reason = evaluate_pre_tool(
                root,
                {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin feature'}},
            )
            self.assertFalse(allowed)
            self.assertIn('route gate declaration', reason or '')

    def test_route_mismatched_decision_artifact_is_stale_and_denied(self) -> None:
        with project_copy(git=True) as root:
            state = self._active_change(root, ['production_action_approval'])
            record_gate_decision(
                root,
                'production_action_approval',
                'approved',
                'Approve one branch action',
                actor='human',
                action='git-push-branch',
            )
            artifact = root / 'engineering/changes' / state['change_id'] / 'human-gates.json'
            value = json.loads(artifact.read_text(encoding='utf-8'))
            value['route_id'] = 'another-route'
            artifact.write_text(json.dumps(value), encoding='utf-8')
            self.assertEqual(gate_statuses(root)[0]['state'], 'stale')
            with self.assertRaisesRegex(ValueError, 'production_action_approval.*stale'):
                add_approval(root, 'production', 'ship', 5, actions=['git-push-branch'])

    def test_removing_declared_gate_with_same_route_id_fails_closed_for_action_and_transition(self) -> None:
        with project_copy(git=True) as root:
            state = self._active_change(root, ['scope_and_design_approval', 'production_action_approval'])
            record_gate_decision(
                root,
                'scope_and_design_approval',
                'approved',
                'Approve current scope',
                actor='human',
            )
            record_gate_decision(
                root,
                'production_action_approval',
                'approved',
                'Approve this branch action',
                actor='human',
                action='git-push-branch',
            )
            add_approval(root, 'production', 'ship', 5, actions=['git-push-branch'])
            route = json.loads((root / '.grok-stack/runtime/active-route.json').read_text(encoding='utf-8'))
            route['human_gates'] = []
            set_active_route(root, route)

            allowed, reason = evaluate_pre_tool(
                root,
                {'tool_name': 'Bash', 'tool_input': {'command': 'git push origin feature'}},
            )
            self.assertFalse(allowed)
            self.assertIn('route gate declaration', reason or '')
            with self.assertRaisesRegex(ValueError, 'route gate declaration'):
                transition(root, state['change_id'], 'approved', 'try after mutating active route')

    def test_removing_external_write_gate_with_same_route_id_fails_closed(self) -> None:
        with project_copy(git=True) as root:
            self._active_change(root, ['migration_or_external_write_approval'])
            target = 'https://api.example.test/v1/records'
            command = f'curl -X POST {target} -d "{{}}"'
            record_gate_decision(
                root,
                'migration_or_external_write_approval',
                'approved',
                'Approve this exact endpoint',
                actor='human',
                action='external-write',
                resource=target,
            )
            add_approval(
                root,
                'external-write',
                'write this endpoint',
                5,
                actions=['external-write'],
                resources=[target],
            )
            route = json.loads((root / '.grok-stack/runtime/active-route.json').read_text(encoding='utf-8'))
            route['human_gates'] = []
            set_active_route(root, route)

            allowed, reason = evaluate_pre_tool(
                root,
                {'tool_name': 'Bash', 'tool_input': {'command': command}},
            )
            self.assertFalse(allowed)
            self.assertIn('route gate declaration', reason or '')

    def test_unknown_route_gate_fails_closed_for_protected_grants(self) -> None:
        with project_copy(git=True) as root:
            self._active_change(root, ['production_action_approval', 'future_gate'])
            self.assertEqual(gate_statuses(root)[0]['state'], 'invalid')
            with self.assertRaisesRegex(ValueError, 'unknown human gate'):
                add_approval(root, 'production', 'ship', 5, actions=['git-push-branch'])

    def test_status_cli_reports_every_gate_as_local_workflow_evidence(self) -> None:
        with project_copy(git=True) as root:
            self._active_change(root, ['scope_and_design_approval', 'production_action_approval'])
            proc = subprocess.run(
                [sys.executable, str(ROOT / 'scripts/grok_status.py')],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )
            result = json.loads(proc.stdout)
            self.assertEqual(
                [(item['gate'], item['state']) for item in result['human_gates']],
                [('scope_and_design_approval', 'pending'), ('production_action_approval', 'pending')],
            )
            self.assertTrue(all(item['evidence_path'].endswith('/human-gates.json') for item in result['human_gates']))
            self.assertFalse(result['human_gates'][0]['local_workflow_evidence_only'] is False)
            self.assertIn('not cryptographic identity', result['human_gate_notice'])

    def test_gate_decision_cli_requires_explicit_target_and_reports_local_evidence(self) -> None:
        with project_copy(git=True) as root:
            state = self._active_change(root, ['production_action_approval'])
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / 'scripts/grok_gate.py'),
                    'decide',
                    'production_action_approval',
                    'approved',
                    '--action',
                    'git-push-branch',
                    '--reason',
                    'Approve only the named branch action',
                    '--actor',
                    'operator',
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )
            result = json.loads(proc.stdout)
            self.assertEqual(result['decision']['change_id'], state['change_id'])
            self.assertEqual(result['decision']['action'], 'git-push-branch')
            self.assertTrue(result['local_workflow_evidence_only'])
            self.assertFalse(result.get('external_trust_ci_authority', False))

    def test_absent_route_record_fails_closed_on_every_gate_seam(self) -> None:
        """A fresh clone has no local route; no gate seam may read that as approval."""
        with project_copy(git=True) as root:
            self.assertFalse((root / ROUTE_PATH).exists())
            self.assertIsNone(get_active_route(root))

            production = gate_block_reason(root, 'production', 'git-push-branch')
            external = gate_block_reason(root, 'external-write', 'external-write', 'prod-db.example')
            self.assertIsNotNone(production, 'production gate laundered an absent route into a pass')
            self.assertIsNotNone(external, 'external-write gate laundered an absent route into a pass')
            self.assertIn('route', production or '')
            self.assertIn('route', external or '')
            self.assertIsNotNone(gate_transition_block_reason(root, 'approved', 'any-change'))

            statuses = gate_statuses(root)
            self.assertTrue(statuses)
            self.assertTrue(all(item['state'] in {'invalid', 'pending'} for item in statuses), statuses)
            self.assertFalse(any(item['state'] == 'approved' for item in statuses), statuses)

            self.assertFalse(has_valid_approval(root, 'production', action='git-push-branch'))
            with self.assertRaisesRegex(ValueError, 'route'):
                add_approval(root, 'production', 'ship it', 5, actions=['git-push-branch'])

            # Control case: the same repository, the same absent change package, but a
            # route that exists. The reason must change, which proves the assertions above
            # are sensitive to the route record and not incidentally satisfied by the
            # missing change package.
            self._active_change(root, ['production_action_approval'])
            restored = gate_block_reason(root, 'production', 'git-push-branch')
            self.assertIsNotNone(restored)
            self.assertNotEqual(restored, production)
            self.assertIn('pending', restored or '')

    def test_recorded_approval_does_not_outlive_the_route_that_declared_it(self) -> None:
        """Deleting the route must not launder a previously recorded decision into a pass."""
        with project_copy(git=True) as root:
            self._active_change(root, ['production_action_approval'])
            record_gate_decision(
                root,
                'production_action_approval',
                'approved',
                'Approve the named branch action',
                actor='operator',
                action='git-push-branch',
            )
            self.assertEqual(gate_statuses(root)[0]['state'], 'approved')
            self.assertIsNone(gate_block_reason(root, 'production', 'git-push-branch'))

            route_file = root / ROUTE_PATH
            saved = route_file.read_text(encoding='utf-8')
            route_file.unlink()
            self.assertIsNotNone(gate_block_reason(root, 'production', 'git-push-branch'))
            statuses = gate_statuses(root)
            self.assertEqual(statuses[0]['state'], 'invalid')
            self.assertFalse(any(item['state'] == 'approved' for item in statuses), statuses)
            self.assertFalse(has_valid_approval(root, 'production', action='git-push-branch'))

            # Control case: restoring only the route brings the recorded decision back,
            # so the denial above was caused by route loss and not by an unrelated state.
            route_file.write_text(saved, encoding='utf-8')
            self.assertIsNone(gate_block_reason(root, 'production', 'git-push-branch'))
            self.assertEqual(gate_statuses(root)[0]['state'], 'approved')

    def test_delegated_grant_does_not_count_while_route_record_is_absent(self) -> None:
        """A delegated grant must not count as valid while the route record is absent."""
        with project_copy(git=True) as root:
            subprocess.run(
                ['git', 'remote', 'add', 'origin', 'git@github.com:Dimkox/adaptive-grok-build-pro.git'],
                cwd=root,
                check=True,
            )
            route = build_route(root, 'Prepare production release and canary', 'gate-test').to_dict()
            # Null route and change ids are what has_valid_approval binds when the
            # route file is gone. The same grant therefore approves if that function
            # skips the route gate and trusts the grant alone.
            route['route_id'] = None
            route['human_gates'] = []
            set_active_route(root, route)
            add_approval(root, 'production', 'ship the branch', 5, actions=['git-push-branch'])
            self.assertIsNone(get_active_route(root).get('route_id'))
            self.assertTrue(has_valid_approval(root, 'production', action='git-push-branch'))

            (root / ROUTE_PATH).unlink()
            self.assertIsNone(get_active_route(root))
            self.assertEqual(len(json.loads(approvals_path(root).read_text(encoding='utf-8'))), 1)
            self.assertFalse(
                has_valid_approval(root, 'production', action='git-push-branch'),
                'delegated grant approved while the route record was absent',
            )

    def test_absent_route_block_reason_names_the_recovery_command(self) -> None:
        """An absent route must block with the exact way an operator restores it."""
        with project_copy(git=True) as root:
            reason = gate_block_reason(root, 'production', 'git-push-branch')
            self.assertIsNotNone(reason)
            self.assertIn('grok_route.py', reason or '')

            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / 'scripts/grok_route.py'),
                    'Prepare production release and canary',
                    '--session',
                    'test-recovery',
                    '--json',
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertEqual(json.loads(proc.stdout)['status'], 'routed')
            self.assertTrue((root / ROUTE_PATH).exists())
            reason = gate_block_reason(root, 'production', 'git-push-branch')
            self.assertIsNotNone(reason)
            self.assertNotIn('active route is missing', reason or '')


if __name__ == '__main__':
    unittest.main()
