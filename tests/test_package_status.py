from __future__ import annotations

import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.change import start_change, transition
from adaptive_grok.receipts import validate_evidence, write_receipt
from adaptive_grok.router import build_route
from adaptive_grok.spec import SpecError, _parse_canonical_json
from adaptive_grok.state import get_active_change, get_active_route, set_active_change, set_active_route
from tests._support import project_copy, run_hook


class PackageStatusTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(
            importlib.util.find_spec('adaptive_grok.package_status'),
            'bounded package diagnostics are missing',
        )
        return importlib.import_module('adaptive_grok.package_status')

    def prepare_route(self, root: Path):
        (root / 'schemas').mkdir(exist_ok=True)
        shutil.copy2(ROOT / 'schemas/change-spec.schema.json', root / 'schemas/change-spec.schema.json')
        if (root / '.git').is_dir() and not self.git(root, 'ls-files', '--', 'schemas/change-spec.schema.json'):
            self.git(root, 'add', 'schemas/change-spec.schema.json')
            self.git(root, 'commit', '-qm', 'fixture schema baseline')
        route = build_route(root, 'Fix interrupted local work', 'package-status').to_dict()
        route['required_evidence'] = ['verification', 'code_review', 'test_review']
        set_active_route(root, route)
        return route

    def prepare(self, root: Path, *, complete: bool = False):
        self.prepare_route(root)
        state = start_change(root)
        active = get_active_change(root)
        package = root / active['path']
        if complete:
            spec_path = package / 'change-spec.yaml'
            spec = json.loads(spec_path.read_text())
            spec['objective'].update(success_metric='recoverable_work', target='all fixtures')
            spec['acceptance_criteria'] = [
                {'id': 'AC-001', 'statement': 'Expose unfinished work', 'evidence': [{'receipt': 'test_review'}]},
            ]
            spec_path.write_text(json.dumps(spec), encoding='utf-8')
            (package / 'requirements.md').write_text('# Requirements\nResolved typed scope.\n', encoding='utf-8')
        return get_active_route(root), active, state, package

    @staticmethod
    def update_state(package: Path, **fields):
        path = package / 'state.json'
        state = json.loads(path.read_text())
        state.update(fields)
        path.write_text(json.dumps(state), encoding='utf-8')
        return state

    def inspect(self, root: Path):
        return self.module().inspect_package(root, get_active_route(root), get_active_change(root))

    @staticmethod
    def codes(result):
        return {item['code'] for item in result['findings']}

    @staticmethod
    def git(root: Path, *args: str) -> str:
        proc = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, check=True)
        return proc.stdout.strip()

    @staticmethod
    def install_cli(root: Path):
        (root / 'scripts').mkdir(exist_ok=True)
        for name in ('grok_status.py', 'grok_review.py', 'grok_change.py'):
            shutil.copy2(ROOT / 'scripts' / name, root / 'scripts' / name)
        (root / 'schemas').mkdir(exist_ok=True)
        shutil.copy2(ROOT / 'schemas/change-spec.schema.json', root / 'schemas/change-spec.schema.json')

    @staticmethod
    def inventory(root: Path):
        result = {}
        for path in sorted(root.rglob('*')):
            info = path.lstat()
            result[path.relative_to(root).as_posix()] = (
                info.st_mode, info.st_size, info.st_mtime_ns,
                path.read_bytes() if path.is_file() else None,
            )
        return result

    def cli(self, root: Path, script='grok_status.py', *args):
        env = os.environ.copy()
        env.pop('PYTHONDONTWRITEBYTECODE', None)
        return subprocess.run(
            [sys.executable, str(root / 'scripts' / script), *args],
            cwd=root, env=env, capture_output=True, text=True, timeout=20, check=False,
        )

    def test_fresh_status_never_creates_runtime_bytecode_or_changes_index(self):
        with project_copy(git=True) as root:
            self.install_cli(root)
            shutil.rmtree(root / '.grok-stack/runtime')
            before = self.inventory(root)
            for _ in range(2):
                proc = self.cli(root)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                value = json.loads(proc.stdout)
                self.assertEqual(value['route'], None)
            self.assertEqual(self.inventory(root), before, 'a status read changed the repository')
            self.assertEqual(value['package_completeness']['status'], 'unknown')
            self.assertIn('no_active_package', self.codes(value['package_completeness']))

    def test_populated_status_is_additive_and_nonmutating_even_with_receipts(self):
        with project_copy(git=True) as root:
            self.install_cli(root)
            route, _, _, _ = self.prepare(root, complete=True)
            for kind in route['required_evidence']:
                write_receipt(root, kind, 'pass')
            before = self.inventory(root)
            for _ in range(2):
                proc = self.cli(root)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                value = json.loads(proc.stdout)
                self.assertTrue({'route', 'change', 'agents', 'evidence_gaps'} <= value.keys())
                self.assertIn('package_completeness', value)
                self.assertIn('worktree', value)
                self.assertEqual(value['package_incomplete'], value['package_completeness']['findings'])
                self.assertEqual(value['evidence_gaps'], [])
            self.assertEqual(self.inventory(root), before)

    def test_status_does_not_reopen_unsafe_package_through_receipt_validation(self):
        with project_copy(git=True) as root:
            self.install_cli(root)
            route, active, _, package = self.prepare(root, complete=True)
            write_receipt(root, 'code_review', 'pass')
            outside = root.parent / 'outside'
            outside.mkdir()
            spec = json.loads((package / 'change-spec.yaml').read_text())
            spec['DO_NOT_EXPOSE_SENTINEL'] = 'secret metadata'
            (outside / 'change-spec.yaml').write_text(json.dumps(spec), encoding='utf-8')
            set_active_change(root, {**active, 'path': str(outside)})
            proc = self.cli(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            value = json.loads(proc.stdout)
            self.assertIn('file_unsafe', self.codes(value['package_completeness']))
            self.assertTrue(value['evidence_gaps'])
            self.assertNotIn('DO_NOT_EXPOSE_SENTINEL', proc.stdout + proc.stderr)
            self.assertEqual(value['route']['route_id'], route['route_id'])

    def test_draft_omissions_become_errors_after_scope_and_remain_errors_when_blocked(self):
        with project_copy() as root:
            _, _, state, package = self.prepare(root)
            draft = self.inspect(root)
            self.assertEqual(draft['status'], 'draft')
            self.assertTrue({'objective_unresolved', 'acceptance_criteria_missing'} <= self.codes(draft))
            self.assertFalse(any(item['severity'] == 'error' for item in draft['findings']))
            for target in ('scoped', 'approved', 'implementing', 'blocked'):
                transition(root, state['change_id'], target, 'test stage')
                result = self.inspect(root)
                self.assertEqual(result['status'], 'incomplete', target)
                self.assertTrue(any(item['severity'] == 'error' for item in result['findings']))
            self.assertEqual(json.loads((package / 'state.json').read_text())['status'], 'blocked')

    def test_not_run_accounts_for_obligations_without_satisfying_receipts(self):
        with project_copy(git=True) as root:
            route, _, state, package = self.prepare(root, complete=True)
            self.update_state(package, status='implementing')
            result = self.inspect(root)
            self.assertEqual(result['status'], 'complete', result)
            self.assertEqual({item['status'] for item in result['obligations']}, {'not_run'})
            self.assertEqual(len(validate_evidence(root, route)), 3)
            self.assertIn('evidence_accounting', state)

    def test_required_obligation_cannot_disappear_or_have_empty_not_run_reason(self):
        with project_copy() as root:
            _, _, state, package = self.prepare(root, complete=True)
            self.assertIn('evidence_accounting', state)
            accounting = state['evidence_accounting']
            accounting['obligations'][0]['reason'] = '  '
            accounting['obligations'].pop()
            self.update_state(package, status='implementing', evidence_accounting=accounting)
            result = self.inspect(root)
            self.assertTrue({'obligation_invalid', 'obligation_missing'} <= self.codes(result))
            self.assertEqual(result['status'], 'incomplete')

    def test_recorded_run_requires_real_reference_and_measured_metadata_but_can_fail(self):
        with project_copy(git=True) as root:
            route, _, state, package = self.prepare(root, complete=True)
            self.assertIn('evidence_accounting', state)
            row = {'id': 'db-1', 'kind': 'run', 'status': 'recorded', 'reference': 'evidence/db.md'}
            state['evidence_accounting']['obligations'].append(row)
            self.update_state(package, status='implementing', evidence_accounting=state['evidence_accounting'])
            self.assertEqual(self.inspect(root)['status'], 'incomplete')
            row.update(outcome='fail', recorded_at='2026-09-21T00:00:00+00:00', command=['python3', 'check.py'])
            (package / 'evidence/db.md').write_text('Command exited 1; dependency unavailable.\n', encoding='utf-8')
            self.update_state(package, evidence_accounting=state['evidence_accounting'])
            self.assertEqual(self.inspect(root)['status'], 'complete')
            self.assertEqual(len(validate_evidence(root, route)), 3)
            (package / 'evidence/db.md').unlink()
            self.assertIn('file_missing', self.codes(self.inspect(root)))

    def test_only_current_markers_are_findings_and_unrelated_evidence_is_not_crawled(self):
        with project_copy() as root:
            _, _, _, package = self.prepare(root, complete=True)
            self.update_state(package, status='implementing')
            evidence = package / 'evidence/README.md'
            evidence.write_text(
                '# Current evidence\nTODO and TBD explain historical work.\n'
                '> <!--RUNTABLE-->\n```md\n<!--RUNTABLE-->\n```\n'
                '    <!--RUNTABLE-->\nThe old marker was `<!--RUNTABLE-->`.\n'
                '``<!--RUNTABLE-->``\nAn old field was `{{TITLE}}`.\n', encoding='utf-8',
            )
            (package / 'evidence/old.md').write_text('<!--RUNTABLE-->\n', encoding='utf-8')
            self.assertEqual(self.inspect(root)['status'], 'complete')
            with evidence.open('a', encoding='utf-8') as handle:
                handle.write('\n<!--RUNTABLE-->\n')
            result = self.inspect(root)
            self.assertIn('template_unexpanded', self.codes(result))
            self.assertEqual(result['status'], 'incomplete')

    def test_missing_malformed_and_oversized_selected_inputs_are_not_complete(self):
        cases = (
            ('state.json', None, 'file_missing'),
            ('state.json', b'{"status":"draft","status":"ready"}', 'state_invalid'),
            ('change-spec.yaml', b'{"schema_version":2,"schema_version":2}', 'spec_invalid'),
            ('change-spec.yaml', b'[]', 'spec_invalid'),
            ('requirements.md', b'\xff', 'invalid_encoding'),
            ('evidence/README.md', b'x' * 262145, 'file_too_large'),
        )
        for name, content, code in cases:
            with self.subTest(name=name, code=code), project_copy() as root:
                _, _, _, package = self.prepare(root, complete=True)
                target = package / name
                if content is None:
                    target.unlink()
                else:
                    target.write_bytes(content)
                result = self.inspect(root)
                self.assertNotEqual(result['status'], 'complete')
                self.assertIn(code, self.codes(result))

    def test_selected_path_cannot_escape_and_symlink_ancestors_or_fifo_are_not_read(self):
        for kind in ('traversal', 'absolute', 'ancestor', 'leaf', 'fifo'):
            with self.subTest(kind=kind), project_copy() as root:
                route, active, _, package = self.prepare(root, complete=True)
                outside = root.parent / 'outside'
                outside.mkdir()
                secret = outside / 'secret.md'
                secret.write_text('DO_NOT_EXPOSE_SENTINEL', encoding='utf-8')
                if kind in ('traversal', 'absolute'):
                    active['path'] = '../outside' if kind == 'traversal' else str(outside)
                elif kind == 'ancestor':
                    shutil.rmtree(package / 'evidence')
                    (package / 'evidence').symlink_to(outside, target_is_directory=True)
                    (outside / 'README.md').symlink_to(secret)
                else:
                    target = package / 'requirements.md'
                    target.unlink()
                    if kind == 'leaf':
                        target.symlink_to(secret)
                    else:
                        os.mkfifo(target)
                result = self.module().inspect_package(root, route, active)
                self.assertIn('file_unsafe', self.codes(result))
                self.assertNotIn('DO_NOT_EXPOSE_SENTINEL', json.dumps(result))

    def test_legacy_accounting_and_mismatched_identity_are_explicit_without_rewriting(self):
        with project_copy() as root:
            _, _, _, package = self.prepare(root, complete=True)
            state = json.loads((package / 'state.json').read_text())
            state.pop('evidence_accounting', None)
            (package / 'state.json').write_text(json.dumps(state), encoding='utf-8')
            before = (package / 'state.json').read_bytes()
            self.assertIn('legacy_evidence_accounting', self.codes(self.inspect(root)))
            self.assertEqual((package / 'state.json').read_bytes(), before)
            self.update_state(package, change_id='different-package')
            self.assertIn('package_identity_mismatch', self.codes(self.inspect(root)))

    def test_invalid_typed_state_and_obligation_values_remain_bounded_diagnostics(self):
        for fields in (
            {'status': ['implementing']},
            {'status': 'not-a-stage'},
            {'history': ['not-an-event']},
            {'evidence_accounting': {'schema_version': 1, 'obligations': [{'id': 'run', 'kind': []}]}},
            {'checkpoints': 'not-a-list'},
        ):
            with self.subTest(fields=fields), project_copy() as root:
                _, _, _, package = self.prepare(root, complete=True)
                self.update_state(package, **fields)
                self.assertEqual(self.inspect(root)['status'], 'incomplete')

    def test_aggregate_bound_and_permission_failure_never_become_completeness(self):
        with project_copy() as root:
            _, _, _, package = self.prepare(root, complete=True)
            for name in ('brief.md', 'architecture.md', 'tasks.md', 'test-plan.md', 'release.md'):
                (package / name).write_text('x' * 250000, encoding='utf-8')
            result = self.inspect(root)
            self.assertIn('inspection_limit', self.codes(result))
            self.assertEqual(result['status'], 'incomplete')
            module = self.module()

            def denied_open(*args, **kwargs):
                raise PermissionError(13, 'permission denied')

            with patch.object(module.os, 'open', new=denied_open), patch.object(
                module.os, 'supports_dir_fd', module.os.supports_dir_fd | {denied_open},
            ):
                result = self.inspect(root)
            self.assertIn('file_unavailable', self.codes(result))

    def test_replaced_file_is_detected_before_its_bytes_are_accepted(self):
        with project_copy() as root:
            _, active, _, package = self.prepare(root)
            target = package / 'requirements.md'
            replacement = package / 'replacement.md'
            replacement.write_text('replacement\n', encoding='utf-8')
            module = self.module()
            original_read = module.os.read
            replaced = False

            def replace_during_read(descriptor, limit):
                nonlocal replaced
                data = original_read(descriptor, limit)
                if not replaced:
                    os.replace(replacement, target)
                    replaced = True
                return data

            with patch.object(module.os, 'read', side_effect=replace_during_read):
                with self.assertRaises(module.InspectionError) as error:
                    module.read_package_file(root, active['path'] + '/requirements.md')
            self.assertEqual(error.exception.code, 'file_changed')

    def test_start_and_first_implementation_preserve_initial_checkpoint_on_resume(self):
        with project_copy(git=True) as root:
            route, _, state, package = self.prepare(root, complete=True)
            self.assertIn('checkpoints', state)
            initial = state['checkpoints'][0]
            self.assertEqual(initial['kind'], 'initial')
            self.assertEqual(initial['head'], self.git(root, 'rev-parse', 'HEAD'))
            self.assertEqual(initial['route_id'], route['route_id'])
            before = self.inventory(package)
            start_change(root)
            self.assertEqual(self.inventory(package), before)
            with self.assertRaises(ValueError):
                transition(root, state['change_id'], 'ready', 'invalid')
            self.assertEqual(self.inventory(package), before)
            (root / 'feature.py').write_text('work = True\n', encoding='utf-8')
            for target in ('scoped', 'approved', 'implementing', 'blocked', 'implementing'):
                state = transition(root, state['change_id'], target, 'continue work')
            self.assertEqual([row['kind'] for row in state['checkpoints']], ['initial', 'implementation'])
            self.assertEqual(state['checkpoints'][0], initial)
            self.assertIn('feature.py', state['checkpoints'][1]['dirty_product_paths'])
            text = (package / 'evidence/README.md').read_text()
            self.assertIn(initial['head'], text)
            self.assertIn('implementation not started', text)
            self.assertIn('feature.py', text)

    def test_checkpoint_mirror_failure_preserves_canonical_record_and_retry_is_idempotent(self):
        with project_copy(git=True) as root:
            _, _, state, package = self.prepare(root)
            for target in ('scoped', 'approved'):
                transition(root, state['change_id'], target, 'scope ready')
            change = importlib.import_module('adaptive_grok.change')
            self.assertTrue(hasattr(change, 'atomic_write_text'), 'checkpoint mirror writer is missing')
            with patch.object(change, 'atomic_write_text', side_effect=OSError('mirror unavailable')):
                with self.assertRaisesRegex(OSError, 'mirror unavailable'):
                    transition(root, state['change_id'], 'implementing', 'start work')
            stored = json.loads((package / 'state.json').read_text())
            self.assertTrue(stored['checkpoint_mirror_pending'])
            self.assertEqual(len(stored['checkpoints']), 2)
            resumed = transition(root, state['change_id'], 'implementing', 'retry mirror')
            self.assertFalse(resumed['checkpoint_mirror_pending'])
            self.assertEqual(resumed['history'], stored['history'])
            self.assertEqual(len(resumed['checkpoints']), 2)

    @staticmethod
    def byte_file(root: Path, name: bytes):
        descriptor = os.open(os.fsencode(root) + b'/' + name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)

    def checkpoint_path_bytes(self, paths):
        decoded = []
        for name in paths:
            if isinstance(name, str):
                decoded.append(name.encode('utf-8', 'strict'))
            else:
                self.assertEqual(set(name), {'encoding', 'value'})
                self.assertEqual(name['encoding'], 'hex')
                decoded.append(bytes.fromhex(name['value']))
        self.assertEqual(len(set(decoded)), len(decoded), 'distinct filesystem names were collapsed')
        return decoded

    def canonical_checkpoint_state(self, package: Path):
        path = package / 'state.json'
        return _parse_canonical_json(path.read_bytes(), path)

    @unittest.skipUnless(os.name == 'posix', 'raw-byte filesystem names are a POSIX fixture')
    def test_raw_byte_start_persists_distinct_names_and_reloads_through_cli(self):
        with project_copy(git=True) as root:
            self.install_cli(root)
            route = self.prepare_route(root)
            initial_head = self.git(root, 'rev-parse', 'HEAD')
            subprocess.run([b'git', b'checkout', b'-qb', b'branch-\xff'], cwd=root, check=True)
            names = (
                b'raw-\xff.py', b'raw-\xfe.py', br'raw-\xff.py', br'raw-\udcff.py',
                b'hex:7261772dff2e7079', b'{"encoding":"hex","value":"7261772dff2e7079"}',
                'raw-\ufffd.py'.encode('utf-8'), 'raw-ÿ.py'.encode('utf-8'),
            )
            for name in names:
                self.byte_file(root, name)
            started = self.cli(root, 'grok_change.py', 'start')
            self.assertEqual(started.returncode, 0, started.stderr)
            state = json.loads(started.stdout)
            active = get_active_change(root)
            package = root / active['path']
            self.assertEqual(self.canonical_checkpoint_state(package), state)
            initial = state['checkpoints'][0]
            self.assertEqual(initial['head'], initial_head)
            self.assertEqual(initial['branch'], {'encoding': 'hex', 'value': '6272616e63682dff'})
            self.assertEqual(initial['route_id'], route['route_id'])
            self.assertTrue(set(names) <= set(self.checkpoint_path_bytes(initial['dirty_product_paths'])))
            self.assertEqual(initial['dirty_product_state'], 'dirty')
            self.assertEqual(self.inspect(root)['status'], 'draft')
            before = self.inventory(package)
            self.assertEqual(start_change(root), state)
            self.assertEqual(self.inventory(package), before)
            status = self.cli(root)
            self.assertEqual(status.returncode, 0, status.stderr)
            observed = json.loads(status.stdout)
            self.assertEqual(observed['package_completeness']['status'], 'draft')
            self.assertEqual(observed['worktree']['head'], initial_head)
            self.assertEqual(observed['worktree']['route_base'], route['base_commit'])
            self.assertEqual(observed['worktree']['base_source'], 'initial_checkpoint')
            self.assertEqual(observed['worktree']['branch'], initial['branch'])
            self.assertTrue(set(names) <= set(self.checkpoint_path_bytes(observed['worktree']['dirty_product_paths'])))
            self.assertTrue(observed['worktree']['uncommitted_product_zero_ahead'])
            self.assertTrue(observed['evidence_gaps'], 'an unavailable receipt fingerprint cannot become passing evidence')
            self.assertEqual(self.inventory(package), before)
            with self.assertRaises(SpecError):
                _parse_canonical_json(b'{"name":"raw-\\udcff.py"}', Path('strict-spec.json'))

    @unittest.skipUnless(os.name == 'posix', 'raw-byte filesystem names are a POSIX fixture')
    def test_raw_byte_first_implementation_persists_and_resume_keeps_initial_identity(self):
        with project_copy(git=True) as root:
            self.install_cli(root)
            route, _, state, package = self.prepare(root, complete=True)
            initial = state['checkpoints'][0]
            for target in ('scoped', 'approved'):
                state = transition(root, state['change_id'], target, 'scope ready')
            approved_history = state['history']
            for name in (b'wip-\xff.py', b'wip-\xfe.py', br'wip-\xff.py', 'wip-\ufffd.py'.encode('utf-8')):
                self.byte_file(root, name)
            moved = self.cli(root, 'grok_change.py', 'transition', state['change_id'], 'implementing', '--reason', 'begin work')
            self.assertEqual(moved.returncode, 0, moved.stderr)
            state = json.loads(moved.stdout)
            self.assertEqual(self.canonical_checkpoint_state(package), state)
            self.assertEqual(state['status'], 'implementing')
            self.assertEqual(state['checkpoints'][0], initial)
            self.assertEqual(state['history'][:-1], approved_history)
            implementation = state['checkpoints'][1]
            self.assertIn(b'wip-\xff.py', self.checkpoint_path_bytes(implementation['dirty_product_paths']))
            self.assertIn(br'wip-\xff.py', self.checkpoint_path_bytes(implementation['dirty_product_paths']))
            self.assertEqual(self.inspect(root)['status'], 'complete')
            for target in ('blocked', 'implementing'):
                state = transition(root, state['change_id'], target, 'resume')
            self.assertEqual(state['checkpoints'], [initial, implementation])
            self.assertEqual(self.canonical_checkpoint_state(package), state)
            repeated = self.cli(root, 'grok_change.py', 'start')
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual(json.loads(repeated.stdout), state)
            status = self.cli(root)
            self.assertEqual(status.returncode, 0, status.stderr)
            observed = json.loads(status.stdout)
            self.assertEqual(observed['package_completeness']['status'], 'complete')
            self.assertEqual(observed['worktree']['route_base'], route['base_commit'])
            self.assertTrue(observed['evidence_gaps'])

    @unittest.skipUnless(os.name == 'posix', 'raw-byte filesystem names are a POSIX fixture')
    def test_raw_byte_representation_limit_persists_an_unknown_observation(self):
        with project_copy(git=True) as root:
            self.install_cli(root)
            route = self.prepare_route(root)
            # Below Git's output/path-count caps, but hexadecimal path records would
            # exceed the canonical state reader's byte cap if persisted in full.
            directory = os.fsencode(root)
            for number in range(8):
                directory += b'/' + str(number).encode('ascii') + b'-' + b'd' * 210
                os.mkdir(directory)
            for number in range(100):
                descriptor = os.open(directory + b'/raw-\xff-' + str(number).encode('ascii'), os.O_CREAT | os.O_WRONLY, 0o600)
                os.close(descriptor)
            started = self.cli(root, 'grok_change.py', 'start')
            self.assertEqual(started.returncode, 0, started.stderr)
            state = json.loads(started.stdout)
            package = root / get_active_change(root)['path']
            self.assertEqual(self.canonical_checkpoint_state(package), state)
            initial = state['checkpoints'][0]
            self.assertEqual(initial['dirty_product_state'], 'unknown')
            self.assertEqual(initial['dirty_product_paths'], [])
            self.assertIn('git_path_representation_limit', initial['git_findings'])
            self.assertEqual(initial['head'], route['base_commit'])
            self.assertEqual(self.inspect(root)['status'], 'draft')
            for target in ('scoped', 'approved', 'implementing'):
                state = transition(root, state['change_id'], target, 'continue with unknown paths')
            self.assertEqual(state['checkpoints'][0], initial)
            self.assertEqual(state['checkpoints'][1]['dirty_product_state'], 'unknown')
            self.assertEqual(self.canonical_checkpoint_state(package), state)
            status = self.cli(root)
            self.assertEqual(status.returncode, 0, status.stderr)
            observed = json.loads(status.stdout)
            self.assertEqual(observed['worktree']['dirty_product_state'], 'unknown')
            self.assertIsNone(observed['worktree']['uncommitted_product_zero_ahead'])
            self.assertEqual(observed['worktree']['head'], initial['head'])
            self.assertEqual(observed['worktree']['route_base'], route['base_commit'])
            self.assertNotIn('state_invalid', self.codes(observed['package_completeness']))
            self.assertTrue(observed['evidence_gaps'])

    def test_stacked_branch_uses_initial_checkpoint_without_overwriting_route_base(self):
        with project_copy(git=True) as root:
            base = self.git(root, 'rev-parse', 'HEAD')
            (root / 'inherited.py').write_text('old = True\n', encoding='utf-8')
            self.git(root, 'add', 'inherited.py')
            self.git(root, 'commit', '-qm', 'inherited work')
            route, _, state, _ = self.prepare(root)
            route['base_commit'] = base
            self.assertIn('checkpoints', state)
            (root / 'feature.py').write_text('new = True\n', encoding='utf-8')
            result = self.module().collect_worktree(root, route, state['checkpoints'][0])
            self.assertEqual(result['base_source'], 'initial_checkpoint')
            self.assertEqual(result['route_base'], base)
            self.assertEqual(route['base_commit'], base)
            self.assertEqual(result['commits_ahead'], 0)
            self.assertEqual(result['dirty_product_paths'], ['feature.py'])
            self.assertTrue(result['uncommitted_product_zero_ahead'])

    def test_git_paths_are_lossless_for_staging_renames_deletions_and_untracked_files(self):
        with project_copy(git=True) as root:
            (root / 'old name.py').write_text('same\n', encoding='utf-8')
            (root / 'delete.py').write_text('delete\n', encoding='utf-8')
            self.git(root, 'add', 'old name.py', 'delete.py')
            self.git(root, 'commit', '-qm', 'paths')
            route, _, _, _ = self.prepare(root)
            self.git(root, 'mv', 'old name.py', 'new\nимя.py')
            (root / 'delete.py').unlink()
            (root / 'tab\tname.py').write_text('new\n', encoding='utf-8')
            result = self.module().collect_worktree(root, route)
            self.assertEqual(set(result['dirty_product_paths']), {'old name.py', 'new\nимя.py', 'delete.py', 'tab\tname.py'})
            self.assertEqual(result['commits_ahead'], 0)
            self.assertTrue(result['uncommitted_product_zero_ahead'])

    def test_only_package_paperwork_is_clean_but_product_markdown_is_dirty(self):
        with project_copy(git=True) as root:
            route, _, _, package = self.prepare(root)
            (package / 'evidence/work.md').write_text('local notes\n', encoding='utf-8')
            result = self.module().collect_worktree(root, route)
            self.assertEqual(result['dirty_product_state'], 'clean')
            self.assertFalse(result['uncommitted_product_zero_ahead'])
            (root / '.agents/skills/extra').mkdir()
            (root / '.agents/skills/extra/SKILL.md').write_text('# Product instructions\n', encoding='utf-8')
            result = self.module().collect_worktree(root, route)
            self.assertIn('.agents/skills/extra/SKILL.md', result['dirty_product_paths'])
            self.assertTrue(result['uncommitted_product_zero_ahead'])

    def test_unknown_git_or_base_never_becomes_a_zero_ahead_claim(self):
        with project_copy(git=True) as root:
            route, _, _, _ = self.prepare(root)
            (root / 'feature.py').write_text('dirty\n', encoding='utf-8')
            for base in (None, 'f' * 40, '--malicious-option'):
                with self.subTest(base=base):
                    result = self.module().collect_worktree(root, {**route, 'base_commit': base})
                    self.assertIsNone(result['commits_ahead'])
                    self.assertIsNone(result['uncommitted_product_zero_ahead'])
            result = self.module().collect_worktree(root, route, {'head': None, 'kind': 'initial'})
            self.assertEqual(result['base_source'], 'initial_checkpoint')
            self.assertIsNone(result['commits_ahead'])
            self.git(root, 'checkout', '--detach', '-q')
            result = self.module().collect_worktree(root, route)
            self.assertTrue(result['detached'])
            self.assertEqual(result['head'], route['base_commit'])
        with project_copy() as root:
            result = self.module().collect_worktree(root, {})
            self.assertIsNone(result['commits_ahead'])
            self.assertEqual(result['dirty_product_state'], 'unknown')
            self.git(root, 'init', '-q')
            result = self.module().collect_worktree(root, {})
            self.assertIsNone(result['head'])
            self.assertIsNone(result['commits_ahead'])

    def test_one_commit_ahead_is_dirty_without_zero_ahead_warning(self):
        with project_copy(git=True) as root:
            route, _, _, _ = self.prepare(root)
            (root / 'feature.py').write_text('first\n', encoding='utf-8')
            self.git(root, 'add', 'feature.py')
            self.git(root, 'commit', '-qm', 'first task commit')
            (root / 'feature.py').write_text('second\n', encoding='utf-8')
            result = self.module().collect_worktree(root, route)
            self.assertEqual(result['commits_ahead'], 1)
            self.assertEqual(result['dirty_product_state'], 'dirty')
            self.assertFalse(result['uncommitted_product_zero_ahead'])

    def test_git_failure_truncation_and_path_limit_are_unknown_observations(self):
        with project_copy(git=True) as root:
            route, _, _, _ = self.prepare(root)
            module = self.module()
            with patch.object(module, '_run_capped', side_effect=module.ArchitectureError('timeout', code='timeout')):
                result = module.collect_worktree(root, route)
            self.assertIsNone(result['commits_ahead'])
            self.assertIsNone(result['uncommitted_product_zero_ahead'])
            original_git = module._git_read

            def truncated_status(repository, arguments):
                if arguments[0] == 'status':
                    return 0, b' M truncated.py'
                return original_git(repository, arguments)

            with patch.object(module, '_git_read', side_effect=truncated_status):
                result = module.collect_worktree(root, route)
            self.assertEqual(result['dirty_product_state'], 'unknown')
            self.assertIsNone(result['uncommitted_product_zero_ahead'])
            for number in range(260):
                (root / f'product-{number}.py').touch()
            result = module.collect_worktree(root, route)
            self.assertIn('git_status_limit', self.codes(result))
            self.assertEqual(result['dirty_product_state'], 'unknown')
            self.assertIsNone(result['uncommitted_product_zero_ahead'])

    def test_stop_warns_on_incomplete_package_even_without_receipt_obligations(self):
        with project_copy(git=True) as root:
            route, _, _, package = self.prepare(root)
            route['required_evidence'] = []
            set_active_route(root, route)
            self.update_state(package, status='implementing')
            code, result, error = run_hook(root, 'stop_gate.py', {'cwd': str(root)})
            self.assertEqual(code, 0, error)
            self.assertNotEqual(result.get('decision'), 'block')
            self.assertIn('objective_unresolved', result.get('systemMessage', ''))
            self.assertNotEqual(get_active_route(root)['status'], 'completed')

    def test_stop_does_not_hide_incomplete_package_behind_current_receipts(self):
        with project_copy(git=True) as root:
            route, _, _, package = self.prepare(root)
            self.update_state(package, status='implementing')
            for kind in route['required_evidence']:
                write_receipt(root, kind, 'pass')
            code, result, error = run_hook(root, 'stop_gate.py', {'cwd': str(root)})
            self.assertEqual(code, 0, error)
            self.assertNotEqual(result.get('decision'), 'block')
            self.assertIn('acceptance_criteria_missing', result.get('systemMessage', ''))
            self.assertNotEqual(get_active_route(root)['status'], 'completed')

    def test_review_preflight_refuses_pass_before_receipt_write_but_preserves_failed_review(self):
        with project_copy(git=True) as root:
            self.install_cli(root)
            route, _, _, package = self.prepare(root, complete=True)
            self.update_state(package, status='reviewing')
            report = package / 'evidence/review.md'
            report.write_text('Concrete review findings.\n', encoding='utf-8')
            args = ('code_review', '--report', report.relative_to(root).as_posix())
            passed = self.cli(root, 'grok_review.py', *args, '--status', 'pass')
            self.assertEqual(passed.returncode, 0, passed.stderr)
            receipt = root / '.grok-stack/runtime/receipts' / route['route_id'] / 'code_review.json'
            before = receipt.read_bytes()
            (package / 'requirements.md').write_text('- [ ] Given ..., when ..., then ...\n', encoding='utf-8')
            refused = self.cli(root, 'grok_review.py', *args, '--status', 'pass')
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn('template_unexpanded', refused.stderr)
            self.assertEqual(receipt.read_bytes(), before)
            failed = self.cli(root, 'grok_review.py', *args, '--status', 'fail')
            self.assertEqual(failed.returncode, 0, failed.stderr)
            self.assertEqual(json.loads(receipt.read_text())['status'], 'fail')


if __name__ == '__main__':
    unittest.main()
