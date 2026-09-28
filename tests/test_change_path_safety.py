from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.change import start_change, transition
from adaptive_grok.package_status import read_package_file
from adaptive_grok.router import build_route
from adaptive_grok.state import get_active_change, set_active_route, update_route
from tests._support import project_copy

DRIVE_PREFIX = re.compile(r'(?<![0-9A-Za-z])[A-Za-z]:[\\/]')
# A historical package name, used as a fixture so the guard does not depend on how many
# Cyrillic directories the checkout happens to keep (issue #52 may rename them all).
HISTORICAL_CYRILLIC = '20260814-рабочий-релиз-v2-0-0-пакеты-и-выкат-e86e93'


def route_for(root: Path, task: str, tag: str) -> dict:
    route = build_route(root, task, tag).to_dict()
    set_active_route(root, route)
    return route


def component_block_reasons(component: str, *, allow_slash: bool = False) -> list[str]:
    """The expected contract, written independently of the implementation under test."""
    reasons: list[str] = []
    if not component:
        reasons.append('empty component')
    if component in {'.', '..'}:
        reasons.append('directory traversal marker')
    if component != component.strip():
        reasons.append('outer whitespace')
    for char in component:
        code = ord(char)
        if code < 0x20 or code == 0x7f or 0x80 <= code <= 0x9f:
            reasons.append(f'control byte \\x{code:02x}')
            break
    if not allow_slash and '/' in component:
        reasons.append('path separator inside one component')
    if '\\' in component:
        reasons.append('backslash')
    if ':' in component:
        reasons.append("drive or alternate-stream prefix ':'")
    if any(0xd800 <= ord(char) <= 0xdfff for char in component):
        reasons.append('non-UTF-8 filesystem byte')
    if len(component.encode('utf-8', 'surrogateescape')) > 255:
        reasons.append('over the 255-byte filesystem component limit')
    return reasons


def unsafe_package_entries(root: Path) -> dict[str, list[str]]:
    """Every entry created under the packages directory that is not one safe component."""
    base = root / 'engineering/changes'
    if not base.is_dir():
        return {}
    found: dict[str, list[str]] = {}
    for dirpath, dirnames, _filenames in os.walk(base):
        for name in dirnames:
            relative = str(Path(dirpath, name).relative_to(base))
            reasons = component_block_reasons(relative)
            if reasons:
                found[relative] = reasons
    return found


def unsafe_tracked_paths(paths: list[str]) -> dict[str, list[str]]:
    """Tracked entries whose *name* carries the #53 artifact signature (``/`` is the separator)."""
    found: dict[str, list[str]] = {}
    for path in paths:
        reasons: list[str] = []
        for component in path.split('/'):
            reasons.extend(component_block_reasons(component, allow_slash=True))
        if DRIVE_PREFIX.search(path):
            reasons.append('drive prefix')
        if reasons:
            found[path] = sorted(set(reasons))
    return found


def control_bytes_in(text: str) -> list[str]:
    """Control bytes a terminal would act on. JSON line breaks are not one of them."""
    found: list[str] = []
    for char in text:
        code = ord(char)
        if (code < 0x20 and char not in '\n\r\t') or code == 0x7f or 0x80 <= code <= 0x9f:
            found.append(f'\\x{code:02x}')
    return sorted(set(found))


class ChangePathSafetyTests(unittest.TestCase):
    """The boundary that materialises a change package must fail closed on an unusable target."""

    def assert_refused(self, root: Path, title: str) -> str:
        """Refuse ``title`` and prove nothing was materialised, not only that it raised."""
        with self.assertRaises(ValueError) as caught:
            start_change(root, title)
        self.assertEqual(unsafe_package_entries(root), {}, 'a directory was created')
        self.assertEqual(list((root / 'engineering/changes').iterdir()), [], 'a directory was created')
        return str(caught.exception)

    def test_backslash_title_creates_no_directory(self) -> None:
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-backslash')
            hostile = r'trust-ci/C:\Users\someone\Documents\Codex\2026-09-24\new-chat'
            message = self.assert_refused(root, hostile)
            self.assertIn('backslash', message)

    def test_backslash_alone_leaks_no_host_identity(self) -> None:
        """No drive letter and no control byte: the backslash rule must be the one that bites."""
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-unc')
            message = self.assert_refused(root, r'sync brief from \\fileserv\pall\promotion-notes')
            self.assertIn('backslash', message)

    def test_control_byte_title_creates_no_directory(self) -> None:
        for index, hostile in enumerate(('fix promotion\x01 now', 'a\x00b', 'tail\x7f', 'nul\x1b escape')):
            with self.subTest(title=repr(hostile)):
                with project_copy() as root:
                    route_for(root, 'Promote only after human approval', f'issue53-ctrl-{index}')
                    self.assert_refused(root, hostile)

    def test_surrogateescaped_title_is_refused_before_scaffolding(self) -> None:
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-surrogate-title')
            message = self.assert_refused(root, 'safe\udc85title')
            self.assertIn('non-printable', message)
            self.assertIn('\\udc85', message)
            self.assertNotIn('\udc85', message)

    def test_ordinary_whitespace_in_a_title_is_not_a_control_byte(self) -> None:
        """A pasted multi-line or CRLF prompt is prose, not an unusable target."""
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-crlf')
            state = start_change(root, 'line one\r\nline two\ttabbed\n')
            self.assertTrue((root / 'engineering/changes' / state['change_id'] / 'state.json').is_file())

    def test_rejection_is_reported_with_the_offending_input_printably(self) -> None:
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-print')
            # Trips the control-byte rule only: no backslash, no drive prefix.
            message = self.assert_refused(root, 'promotion \x1b[31m tint')
            self.assertTrue(message.isprintable(), repr(message))
            self.assertNotIn('\x1b', message)
            self.assertIn('\\x1b', message)
            self.assertIn('promotion', message)
            self.assertNotIn('\n', message)

    def test_cli_reports_path_refusals_as_usage_errors_without_a_traceback(self) -> None:
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-cli-refusal')
            scripts = root / 'scripts'
            scripts.mkdir()
            shutil.copy2(ROOT / 'scripts/grok_change.py', scripts / 'grok_change.py')

            cases = (
                ('start', '--title', r'C:\Users\someone\promotion-notes'),
                ('start', '--title', 'bad\\path\u202e'),
                ('transition', '../../outside', 'scoped', '--reason', 'unsafe probe'),
            )
            for args in cases:
                with self.subTest(args=args):
                    proc = subprocess.run(
                        [sys.executable, str(scripts / 'grok_change.py'), *args],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(proc.returncode, 2, proc.stderr)
                    self.assertEqual(proc.stdout, '')
                    self.assertIn('error: refusing to', proc.stderr)
                    self.assertNotIn('Traceback', proc.stderr)
                    self.assertNotIn('\u202e', proc.stderr)
                    self.assertEqual(control_bytes_in(proc.stderr), [])
                    self.assertEqual(list((root / 'engineering/changes').iterdir()), [])

    def test_printable_value_escapes_bounds_and_keeps_non_ascii_visible(self) -> None:
        from adaptive_grok.change import printable_value

        self.assertEqual(printable_value('a\tb\nc\x1bд'), 'a\\tb\\nc\\x1bд')
        self.assertEqual(printable_value('рабочий \x00'), 'рабочий \\x00')
        self.assertNotIn('\x85', printable_value('c1 \x85 tail'))
        self.assertIn('\\x85', printable_value('c1 \x85 tail'))
        for hostile, unsafe, escaped in (
            ('right-to-left \u202e tail', '\u202e', '\\u202e'),
            ('line-separator \u2028 tail', '\u2028', '\\u2028'),
            ('isolate \u2066 tail', '\u2066', '\\u2066'),
        ):
            with self.subTest(hostile=repr(hostile)):
                rendered = printable_value(hostile)
                self.assertNotIn(unsafe, rendered)
                self.assertIn(escaped, rendered)
        long_value = printable_value('k' * 4000)
        self.assertLess(len(long_value), 250, 'the refused prompt must not be echoed whole')
        self.assertTrue(long_value.endswith('[truncated]'), long_value[-20:])
        self.assertEqual(printable_value('short'), 'short')

    def test_route_components_cannot_inject_a_path_into_the_derived_id(self) -> None:
        cases = {
            'route-id-backslash': ({'route_id': 'a\\b\\c\\d\\e\\f'}, 'unsafe route id prefix'),
            'route-id-slash': ({'route_id': 'aa/bb/cc'}, 'unsafe route id prefix'),
            'route-id-colon': ({'route_id': 'C:\\Users\\x'}, 'unsafe route id prefix'),
            'created-at-control-byte': ({'created_at': '2026-09\x01-24T00:00:00+00:00'}, 'unsafe created_at date'),
            'created-at-empty': ({'created_at': ''}, 'unsafe created_at date'),
            'created-at-malformed': ({'created_at': 'not-a-dateT00:00:00Z'}, 'unsafe created_at date'),
            'route-id-outside-schema-alphabet': ({'route_id': 'αβγδεζ123456'}, 'unsafe route id prefix'),
            'route-id-missing': ({'route_id': None}, 'is not text'),
            'created-at-missing': ({'created_at': None}, 'is not text'),
        }
        for label, (mutation, expected) in cases.items():
            with self.subTest(case=label):
                with project_copy() as root:
                    route = route_for(root, 'Promote only after human approval', label)
                    route.update(mutation)
                    (root / '.grok-stack/runtime/active-route.json').write_text(
                        json.dumps(route, ensure_ascii=True), encoding='utf-8'
                    )
                    with self.assertRaises(ValueError) as caught:
                        start_change(root, 'safe title')
                    self.assertIn(expected, str(caught.exception))
                    self.assertEqual(unsafe_package_entries(root), {}, label)
                    self.assertEqual(list((root / 'engineering/changes').iterdir()), [], label)

    def test_full_route_id_cannot_escape_runtime_snapshot_paths(self) -> None:
        for index, route_id in enumerate((
            'abcdef/../../../../../victim',
            r'abcdef\child',
            'a' * 300,
        )):
            with self.subTest(route_id=repr(route_id)):
                with project_copy() as root:
                    route = route_for(root, 'Promote only after human approval', f'issue53-route-{index}')
                    route['route_id'] = route_id
                    (root / '.grok-stack/runtime/active-route.json').write_text(
                        json.dumps(route, ensure_ascii=True), encoding='utf-8'
                    )
                    message = self.assert_refused(root, 'safe title')
                    self.assertIn('unsafe route id', message)

    def test_route_snapshot_writers_reject_an_escaping_route_id(self) -> None:
        with project_copy() as root:
            safe = route_for(root, 'Promote only after human approval', 'issue53-route-snapshot')
            victim = root.parent / 'victim.json'
            victim.write_bytes(b'ORIGINAL\n')
            hostile = dict(safe)
            hostile['route_id'] = 'abcdef/../../../../../victim'

            with self.assertRaises(ValueError):
                set_active_route(root, hostile)
            self.assertEqual(victim.read_bytes(), b'ORIGINAL\n')

            (root / '.grok-stack/runtime/active-route.json').write_text(
                json.dumps(hostile, ensure_ascii=True), encoding='utf-8'
            )
            with self.assertRaises(ValueError):
                update_route(root, change_id='20260926-safe-title-abcdef')
            self.assertEqual(victim.read_bytes(), b'ORIGINAL\n')

    def test_route_snapshot_writer_enforces_the_complete_id_alphabet_and_length(self) -> None:
        for index, route_id in enumerate((r'abcdef\child', 'a' * 129)):
            with self.subTest(route_id=repr(route_id)):
                with project_copy() as root:
                    safe = route_for(root, 'Promote only after human approval', f'issue53-state-id-{index}')
                    active = root / '.grok-stack/runtime/active-route.json'
                    original_active = active.read_bytes()
                    original_snapshots = sorted(path.name for path in active.parent.joinpath('routes').iterdir())
                    hostile = dict(safe)
                    hostile['route_id'] = route_id

                    with self.assertRaisesRegex(ValueError, 'unsafe route id'):
                        set_active_route(root, hostile)

                    self.assertEqual(active.read_bytes(), original_active)
                    self.assertEqual(
                        sorted(path.name for path in active.parent.joinpath('routes').iterdir()),
                        original_snapshots,
                    )

    def test_route_snapshot_root_symlinks_are_refused_before_a_write(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Promote only after human approval', 'issue53-route-root').to_dict()
            routes = root / '.grok-stack/runtime/routes'
            routes.parent.mkdir(parents=True, exist_ok=True)
            outside = root.parent / 'external-routes'
            outside.mkdir()
            routes.symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, 'resolves outside'):
                set_active_route(root, route)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertFalse((root / '.grok-stack/runtime/active-route.json').exists())

        with project_copy() as root:
            route = build_route(root, 'Promote only after human approval', 'issue53-route-loop').to_dict()
            routes = root / '.grok-stack/runtime/routes'
            routes.parent.mkdir(parents=True, exist_ok=True)
            routes.symlink_to(routes.name, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, 'cannot be resolved'):
                set_active_route(root, route)
            self.assertFalse((root / '.grok-stack/runtime/active-route.json').exists())

    def test_refused_start_does_not_write_active_change_through_an_external_runtime(self) -> None:
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-runtime-symlink')
            runtime = root / '.grok-stack/runtime'
            outside = root.parent / 'outside-runtime'
            outside.mkdir()
            active = (runtime / 'active-route.json').read_bytes()
            shutil.rmtree(runtime)
            runtime.symlink_to(outside, target_is_directory=True)
            (outside / 'active-route.json').write_bytes(active)
            before = sorted(path.name for path in outside.iterdir())

            with self.assertRaises(ValueError) as caught:
                start_change(root, 'safe summary for the probe')

            message = str(caught.exception)
            self.assertIn('outside the repository', message)
            self.assertNotIn(str(outside), message)
            self.assertNotIn(str(root), message)
            self.assertEqual(sorted(path.name for path in outside.iterdir()), before)
            self.assertFalse((outside / 'active-change.json').exists())

    def test_update_route_does_not_create_an_external_runtime_directory(self) -> None:
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-stack-symlink')
            stack = root / '.grok-stack'
            outside = root.parent / 'outside-stack'
            outside.mkdir()
            stack.rename(root.parent / 'kept-stack')
            stack.symlink_to(outside, target_is_directory=True)

            with self.assertRaises(ValueError) as caught:
                update_route(root, status='draft')

            message = str(caught.exception)
            self.assertIn('resolves outside', message)
            self.assertNotIn(str(outside), message)
            self.assertNotIn(str(root), message)
            self.assertEqual(list(outside.iterdir()), [])

        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-runtime-loop')
            runtime = root / '.grok-stack/runtime'
            shutil.rmtree(runtime)
            runtime.symlink_to(runtime.name, target_is_directory=True)

            with self.assertRaises(ValueError) as caught:
                update_route(root, status='draft')

            message = str(caught.exception)
            self.assertIn('cannot be resolved', message)
            self.assertNotIn(str(root), message)
            self.assertNotIn('\n', message)

    def test_transition_does_not_import_outside_json_through_a_state_symlink(self) -> None:
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-state-symlink')
            state = start_change(root, 'Normal scoped work')
            package = root / 'engineering/changes' / state['change_id']
            state_path = package / 'state.json'
            outside = root.parent / 'outside-state.json'
            payload = json.loads(state_path.read_text(encoding='utf-8'))
            payload['secret'] = 'OUTSIDE-MARKER'
            payload['status'] = 'draft'
            payload['checkpoint_mirror_pending'] = False
            outside.write_text(json.dumps(payload), encoding='utf-8')
            before = outside.read_bytes()
            state_path.unlink()
            state_path.symlink_to(outside)

            with self.assertRaises(ValueError) as caught:
                transition(root, state['change_id'], 'scoped', 'child symlink')

            message = str(caught.exception)
            self.assertIn('symlink', message)
            self.assertNotIn('OUTSIDE-MARKER', message)
            self.assertNotIn(str(outside), message)
            self.assertEqual(outside.read_bytes(), before)
            self.assertTrue(state_path.is_symlink())

    def test_cli_refuses_an_escaping_full_route_id_without_external_write(self) -> None:
        with project_copy() as root:
            route = route_for(root, 'Promote only after human approval', 'issue53-cli-route-id')
            victim = root.parent / 'victim.json'
            victim.write_bytes(b'ORIGINAL\n')
            route['route_id'] = 'abcdef/../../../../../victim'
            (root / '.grok-stack/runtime/active-route.json').write_text(
                json.dumps(route, ensure_ascii=True), encoding='utf-8'
            )
            scripts = root / 'scripts'
            scripts.mkdir()
            shutil.copy2(ROOT / 'scripts/grok_change.py', scripts / 'grok_change.py')

            proc = subprocess.run(
                [sys.executable, str(scripts / 'grok_change.py'), 'start', '--title', 'safe title'],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertNotIn('Traceback', proc.stderr)
            self.assertEqual(victim.read_bytes(), b'ORIGINAL\n')
            self.assertEqual(list((root / 'engineering/changes').iterdir()), [])

    def test_cli_refuses_malformed_persisted_route_roots_without_a_traceback(self) -> None:
        for index, payload in enumerate(({}, [], 'route', 1, None)):
            with self.subTest(payload=repr(payload)):
                with project_copy() as root:
                    route_for(root, 'Promote only after human approval', f'issue53-root-{index}')
                    (root / '.grok-stack/runtime/active-route.json').write_text(
                        json.dumps(payload), encoding='utf-8'
                    )
                    scripts = root / 'scripts'
                    scripts.mkdir()
                    shutil.copy2(ROOT / 'scripts/grok_change.py', scripts / 'grok_change.py')

                    with self.assertRaises(ValueError):
                        start_change(root, 'safe title')
                    proc = subprocess.run(
                        [sys.executable, str(scripts / 'grok_change.py'), 'start', '--title', 'safe title'],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    self.assertEqual(proc.returncode, 2, proc.stderr)
                    self.assertNotIn('Traceback', proc.stderr)
                    self.assertEqual(list((root / 'engineering/changes').iterdir()), [])

    def test_hostile_route_payload_is_refused_before_scaffolding(self) -> None:
        cases = {
            'task-surrogate': ('task', 'unsafe\udc85task', '\udc85', '\\udc85'),
            'risk-surrogate': ('risk', 'low\udc85', '\udc85', '\\udc85'),
            'task-escape': ('task', 'unsafe\x1btask', '\x1b', '\\x1b'),
        }
        for tag, (field, hostile, unsafe, escaped) in cases.items():
            with self.subTest(case=tag):
                with project_copy() as root:
                    route = route_for(root, 'Promote only after human approval', f'issue53-{tag}')
                    route[field] = hostile
                    set_active_route(root, route)
                    message = self.assert_refused(root, 'safe title')
                    self.assertIn('active route', message)
                    self.assertIn(escaped, message)
                    self.assertNotIn(unsafe, message)
        with project_copy() as root:
            route = route_for(root, 'Promote only after human approval', 'issue53-nested-route')
            route['repo']['signals'] = ['unsafe\u2066signal']
            set_active_route(root, route)
            message = self.assert_refused(root, 'safe title')
            self.assertIn("route['repo']['signals'][0]", message)
            self.assertIn('\\u2066', message)
        with project_copy() as root:
            route = route_for(root, 'Promote only after human approval', 'issue53-nonfinite-route')
            route['repo']['threshold'] = float('inf')
            set_active_route(root, route)
            message = self.assert_refused(root, 'safe title')
            self.assertIn('not a finite JSON number', message)
        from adaptive_grok.change import route_payload_block_reason

        blocked_key = route_payload_block_reason({1: 'unsafe'})
        self.assertIsNotNone(blocked_key)
        self.assertIn('non-text key', blocked_key[1])

    def test_cli_refuses_hostile_route_payload_without_partial_package(self) -> None:
        with project_copy() as root:
            route = route_for(root, 'Promote only after human approval', 'issue53-cli-route-data')
            route['task'] = 'unsafe\x1btask'
            set_active_route(root, route)
            scripts = root / 'scripts'
            scripts.mkdir()
            shutil.copy2(ROOT / 'scripts/grok_change.py', scripts / 'grok_change.py')

            proc = subprocess.run(
                [sys.executable, str(scripts / 'grok_change.py'), 'start', '--title', 'safe title'],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertNotIn('Traceback', proc.stderr)
            self.assertNotIn('\x1b', proc.stderr)
            self.assertIn('\\x1b', proc.stderr)
            self.assertEqual(list((root / 'engineering/changes').iterdir()), [])

    def test_wrong_shaped_route_fields_are_refused_before_scaffolding(self) -> None:
        cases = {
            'domains-item': {'domains': [None]},
            'domains-not-list': {'domains': 1},
            'required-evidence-not-list': {'required_evidence': 1},
            'human-gates-not-list': {'human_gates': 1},
            'risk-not-text': {'risk': 1},
            'complexity-missing': {'complexity': None},
        }
        for tag, mutation in cases.items():
            with self.subTest(case=tag):
                with project_copy() as root:
                    route = route_for(root, 'Promote only after human approval', f'issue53-{tag}')
                    route.update(mutation)
                    set_active_route(root, route)
                    message = self.assert_refused(root, 'safe title')
                    self.assertIn('active route field', message)

    def test_cli_refuses_wrong_shaped_route_fields_without_partial_package(self) -> None:
        for tag, mutation in (
            ('domains-none', {'domains': [None]}),
            ('required-evidence-int', {'required_evidence': 1}),
        ):
            with self.subTest(case=tag):
                with project_copy() as root:
                    route = route_for(root, 'Promote only after human approval', f'issue53-cli-{tag}')
                    route.update(mutation)
                    set_active_route(root, route)
                    scripts = root / 'scripts'
                    scripts.mkdir()
                    shutil.copy2(ROOT / 'scripts/grok_change.py', scripts / 'grok_change.py')

                    proc = subprocess.run(
                        [sys.executable, str(scripts / 'grok_change.py'), 'start', '--title', 'safe title'],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    self.assertEqual(proc.returncode, 2, proc.stderr)
                    self.assertNotIn('Traceback', proc.stderr)
                    self.assertEqual(list((root / 'engineering/changes').iterdir()), [])

    def test_transition_cannot_write_outside_the_packages_directory(self) -> None:
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-escape')
            state = start_change(root, 'Normal scoped work')
            outside = root / 'outside'
            outside.mkdir()
            payload = dict(state)
            payload.update({'change_id': 'outside', 'status': 'draft', 'history': [], 'checkpoints': [],
                            'checkpoint_mirror_pending': False})
            (outside / 'state.json').write_text(json.dumps(payload), encoding='utf-8')
            before = (outside / 'state.json').read_bytes()
            packages = root / 'engineering/changes'
            for hostile in ('../../outside', 'a/b', r'a\b', 'a:b', '..', '', 'x' * 300):
                with self.subTest(change_id=repr(hostile)):
                    with self.assertRaises(ValueError):
                        transition(root, hostile, 'scoped', 'caller supplied a path')
            over_link = '20260925-over-link-abc123'
            (packages / over_link).symlink_to(Path('..') / '..' / 'outside')
            with self.subTest(change_id='symlink to outside'):
                with self.assertRaises(ValueError):
                    transition(root, over_link, 'scoped', 'the name is safe, the link is not')
            loop_a_id = '20260925-loop-a-abc123'
            loop_b_id = '20260925-loop-b-abc123'
            loop_a, loop_b = packages / loop_a_id, packages / loop_b_id
            loop_a.symlink_to(loop_b.name)
            loop_b.symlink_to(loop_a.name)
            with self.subTest(change_id='symlink loop'):
                with self.assertRaises(ValueError) as caught:
                    transition(root, loop_a_id, 'scoped', 'resolve must not answer with a traceback')
                self.assertNotIn(str(packages.resolve()), str(caught.exception))
                self.assertNotIn('\n', str(caught.exception))
            self.assertEqual((outside / 'state.json').read_bytes(), before)
            self.assertTrue((packages / state['change_id'] / 'state.json').is_file())

    def test_package_root_symlink_cannot_redirect_creation(self) -> None:
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-package-root-link')
            packages = root / 'engineering/changes'
            shutil.rmtree(packages)
            outside = root.parent / 'external-changes'
            outside.mkdir()
            packages.symlink_to(outside, target_is_directory=True)

            with self.assertRaises(ValueError) as caught:
                start_change(root, 'safe title')

            self.assertEqual(list(outside.iterdir()), [], 'the symlinked root received a write')
            self.assertNotIn(str(outside), str(caught.exception))

    def test_package_root_symlink_loop_has_a_bounded_refusal(self) -> None:
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-package-root-loop')
            packages = root / 'engineering/changes'
            shutil.rmtree(packages)
            packages.symlink_to(packages.name, target_is_directory=True)

            with self.assertRaises(ValueError) as caught:
                start_change(root, 'safe title')

            message = str(caught.exception)
            self.assertIn('cannot be resolved', message)
            self.assertNotIn(str(root), message)

    def test_ordinary_punctuation_in_a_title_is_still_accepted(self) -> None:
        """Colons and slashes are ordinary prose in task text; refusing them would regress routing."""
        with project_copy() as root:
            route = route_for(root, 'fix: bind evidence to scripts/grok_verify.py', 'issue53-prose')
            title = 'fix: bind cited notes -- see scripts/grok_verify.py, pass 2'
            state = start_change(root, title)
            change_id = state['change_id']
            self.assertEqual(component_block_reasons(change_id), [], change_id)
            self.assertEqual(Path(change_id).name, change_id)
            self.assertTrue((root / 'engineering/changes' / change_id / 'state.json').is_file())
            # The verbatim title stays in package state; the slug is not its storage place.
            self.assertEqual(state['title'], title)
            self.assertEqual(route['route_id'][:6], change_id.rsplit('-', 1)[-1])

    def test_task_style_titles_are_not_mistaken_for_paths(self) -> None:
        accepted = (
            '/goal keep going until the gate is green',
            'api/v1 vs api/v2 payload drift',
            'mirror https://example.com/x into the holdout bundle',
            'compare the two copies in the engineering/changes tree',
            'Исправить баг в D7 обработчике события и добавить PHPUnit тест',
        )
        for index, title in enumerate(accepted):
            with self.subTest(title=title):
                with project_copy() as root:
                    route_for(root, 'Promote only after human approval', f'issue53-ok-{index}')
                    state = start_change(root, title)
                    self.assertTrue((root / 'engineering/changes' / state['change_id']).is_dir())

    def test_a_path_handed_as_a_title_is_refused_in_either_dialect(self) -> None:
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-drive')
            message = self.assert_refused(root, 'write it to D:/exports/promotions/new-chat')
            self.assertIn('drive prefix', message)
        with project_copy() as root:
            route_for(root, 'Promote only after human approval', 'issue53-abs')
            message = self.assert_refused(root, '/home/pall/secrets/new-chat/notes')
            self.assertIn('absolute path', message)
            message = self.assert_refused(root, '~/workspace/.aws/credentials')
            self.assertIn('absolute path', message)
        for index, title in enumerate((
            '/home/палл/secrets/notes',
            '//home/pall/secrets/notes',
            '/home/pall+ops/secrets/notes',
        )):
            with self.subTest(title=title):
                with project_copy() as root:
                    route_for(root, 'Promote only after human approval', f'issue53-abs-{index}')
                    message = self.assert_refused(root, title)
                    self.assertIn('absolute path', message)

    def test_historical_non_ascii_package_stays_writable_readable_and_printable(self) -> None:
        """#52 owns transliteration; #53 must not start refusing valid non-ASCII packages."""
        from adaptive_grok.change import change_id_block_reason

        title = 'рабочий релиз v2.0.0: пакеты и выкат'
        with project_copy() as root:
            route_for(root, 'Выкатить рабочий релиз', 'issue53-cyrillic')
            state = start_change(root, title)
            packages = root / 'engineering/changes'
            # Rename the fresh package to a literal historical name inside this throwaway
            # copy: the guard must hold for the shipped name, whatever charset a future
            # slug rule produces for a new one.
            (packages / state['change_id']).rename(packages / HISTORICAL_CYRILLIC)
            state_path = packages / HISTORICAL_CYRILLIC / 'state.json'
            recorded = json.loads(state_path.read_text(encoding='utf-8'))
            recorded['change_id'] = HISTORICAL_CYRILLIC
            state_path.write_text(json.dumps(recorded), encoding='utf-8')
            active_path = root / '.grok-stack/runtime/active-change.json'
            active_path.write_text(
                json.dumps({'change_id': HISTORICAL_CYRILLIC,
                            'path': f'engineering/changes/{HISTORICAL_CYRILLIC}'}),
                encoding='utf-8',
            )
            self.assertIsNone(change_id_block_reason(HISTORICAL_CYRILLIC), HISTORICAL_CYRILLIC)
            moved = transition(root, HISTORICAL_CYRILLIC, 'scoped', 'scope the historical package')
            self.assertEqual(moved['status'], 'scoped')
            self.assertTrue(any(ord(char) > 127 for char in HISTORICAL_CYRILLIC))
            relative = get_active_change(root)['path']
            self.assertEqual(Path(relative).name, HISTORICAL_CYRILLIC)
            self.assertTrue(relative.isprintable())
            decoded = read_package_file(root, f'{relative}/state.json').decode('utf-8', 'strict')
            self.assertEqual(control_bytes_in(decoded), [])
            self.assertEqual(json.loads(decoded)['change_id'], HISTORICAL_CYRILLIC)
            self.assertEqual(json.loads(decoded)['title'], title)

    def test_every_historical_package_name_is_still_acceptable(self) -> None:
        """No shipped package directory may become unreachable through over-tight validation."""
        from adaptive_grok.change import change_id_block_reason

        base = ROOT / 'engineering/changes'
        names = sorted(entry.name for entry in base.iterdir() if entry.is_dir())
        self.assertGreater(len(names), 20, 'historical packages are missing from the checkout')
        for name in names:
            with self.subTest(name=name):
                self.assertIsNone(change_id_block_reason(name), name)

    def test_tracked_tree_has_no_backslash_colon_or_control_byte_path(self) -> None:
        """Reject the issue signature in both the index and untracked working-tree litter."""
        proc = subprocess.run(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            self.skipTest('git inventory is unavailable')
        repository_paths = [os.fsdecode(item) for item in proc.stdout.split(b'\0') if item]
        self.assertGreater(len(repository_paths), 500, 'the repository inventory looks truncated')
        self.assertEqual(unsafe_tracked_paths(repository_paths), {})

    def test_structure_guard_rejects_an_untracked_unsafe_path(self) -> None:
        with project_copy(git=True) as root:
            tests = root / 'tests'
            tests.mkdir()
            (tests / '__init__.py').write_text('', encoding='utf-8')
            shutil.copy2(ROOT / 'tests/_support.py', tests / '_support.py')
            shutil.copy2(ROOT / 'tests/test_change_path_safety.py', tests / 'test_change_path_safety.py')
            fixtures = root / 'tracked-fixtures'
            fixtures.mkdir()
            for index in range(400):
                (fixtures / f'{index:03d}.txt').write_text('safe\n', encoding='utf-8')
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'install structure fixture'], cwd=root, check=True)
            hostile = root / r'trust-ci/C:\Users\someone\new-chat/probe.py'
            hostile.parent.mkdir(parents=True)
            hostile.write_text('# untracked path-safety probe\n', encoding='utf-8')

            proc = subprocess.run(
                [
                    sys.executable,
                    '-m',
                    'unittest',
                    'tests.test_change_path_safety.ChangePathSafetyTests.'
                    'test_tracked_tree_has_no_backslash_colon_or_control_byte_path',
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0, 'the untracked unsafe path escaped the guard')
            self.assertIn('C:', proc.stderr)

    @unittest.skipUnless(os.name == 'posix', 'raw-byte filename semantics are POSIX-specific')
    def test_structure_guard_rejects_an_untracked_non_utf8_path_without_crashing(self) -> None:
        with project_copy(git=True) as root:
            tests = root / 'tests'
            tests.mkdir()
            (tests / '__init__.py').write_text('', encoding='utf-8')
            shutil.copy2(ROOT / 'tests/_support.py', tests / '_support.py')
            shutil.copy2(ROOT / 'tests/test_change_path_safety.py', tests / 'test_change_path_safety.py')
            fixtures = root / 'tracked-fixtures'
            fixtures.mkdir()
            for index in range(400):
                (fixtures / f'{index:03d}.txt').write_text('safe\n', encoding='utf-8')
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'install structure fixture'], cwd=root, check=True)
            raw_path = os.fsencode(root / 'engineering/changes') + b'/raw-\x85-note.md'
            descriptor = os.open(raw_path, os.O_WRONLY | os.O_CREAT, 0o600)
            os.write(descriptor, b'unsafe raw filename\n')
            os.close(descriptor)

            proc = subprocess.run(
                [
                    sys.executable,
                    '-m',
                    'unittest',
                    'tests.test_change_path_safety.ChangePathSafetyTests.'
                    'test_tracked_tree_has_no_backslash_colon_or_control_byte_path',
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0, 'the raw unsafe path escaped the guard')
            self.assertNotIn('UnicodeEncodeError', proc.stderr)
            self.assertIn('non-UTF-8 filesystem byte', proc.stderr)

    def test_historical_non_ascii_paths_are_readable_and_printable(self) -> None:
        from adaptive_grok.change import change_id_block_reason

        base = ROOT / 'engineering/changes'
        historical = sorted(
            entry.name for entry in base.iterdir()
            if entry.is_dir() and any(ord(char) > 127 for char in entry.name)
        )
        if not historical:
            self.skipTest('no non-ASCII historical package remains in this checkout')
        checked = 0
        for name in historical:
            relative = f'engineering/changes/{name}/state.json'
            if not (ROOT / relative).is_file():
                continue
            checked += 1
            with self.subTest(package=name):
                self.assertIsNone(change_id_block_reason(name), name)
                decoded = read_package_file(ROOT, relative).decode('utf-8', 'strict')
                self.assertTrue(name.isprintable())
                self.assertEqual(control_bytes_in(decoded), [], name)
                self.assertEqual(json.loads(decoded)['change_id'], name)
        self.assertGreater(checked, 0, 'no historical non-ASCII package state.json was readable')


if __name__ == '__main__':
    unittest.main()



# The rule sets overlap on purpose - a control byte is also non-alphanumeric, a Windows
# drive also contains a colon - so asserting only "refused" cannot tell a live rule from a
# coincidence. These tables drive the reason class, which is what kills the three mutants an
# example spot-check left alive.
ID_REFUSAL_CASES: tuple[tuple[str, str], ...] = (
    ('nul', 'windows'),
    ('nul.txt', 'windows'),
    ('NUL', 'windows'),
    ('con', 'windows'),
    ('aux.doc', 'windows'),
    ('20260925-safe.', 'windows'),
    ('-rf', 'dash'),
    ('20260925-a\u001bb', 'control byte'),
    ('C:\\Users\\x', ':'),
    ('20260925-a:b', ':'),
    ('..', 'traversal'),
)

TITLE_REFUSAL_CASES: tuple[tuple[str, str], ...] = (
    (r'trust-ci/C:\Users\someone\notes', 'backslash'),
    (r'sync from \\fileserv\share\notes', 'backslash'),
    ('write a brief\u0001here', 'control byte'),
    ('/home/user/project/promote the gate', 'absolute path'),
)

# The other half of the boundary: words that merely look hostile must still be accepted, or
# the guard would "pass" by refusing everything.
HARMLESS_TITLE_CASES: tuple[str, ...] = (
    'nul',
    '-rf',
    'promotion:production',
    'promotion:production:' + 'x' * 300,
    'rename brief.md to hidden',
    'https://example.invalid/a/b',
)


class RuleDifferentialTests(unittest.TestCase):
    """Drives the reason classes, not just the refusal, through both entry channels."""

    def test_each_id_shape_is_refused_by_the_rule_that_owns_it(self) -> None:
        from adaptive_grok.change import change_id_block_reason

        for value, marker in ID_REFUSAL_CASES:
            with self.subTest(value=value):
                reason = change_id_block_reason(value)
                self.assertIsNotNone(reason, f'{value!r} was accepted as a package id')
                self.assertIn(marker.lower(), reason.lower(),
                              f'{value!r} refused for the wrong reason: {reason}')

    def test_harmless_looking_titles_are_still_accepted(self) -> None:
        from adaptive_grok.change import title_block_reason

        for value in HARMLESS_TITLE_CASES:
            with self.subTest(value=value):
                self.assertIsNone(title_block_reason(value), 'the guard over-refused a plain title')

    def test_each_title_shape_is_refused_before_anything_is_materialised(self) -> None:
        for value, marker in TITLE_REFUSAL_CASES:
            with self.subTest(value=value):
                with project_copy() as root:
                    route_for(root, 'Promote only after human approval', f'diff-{abs(hash(value)) % 10**6}')
                    with self.assertRaises(ValueError) as caught:
                        start_change(root, value)
                    self.assertEqual({}, unsafe_package_entries(root), 'a directory was created')
                    self.assertEqual([], list((root / 'engineering/changes').iterdir()))
                    message = str(caught.exception)
                self.assertIn(marker.lower(), message.lower(),
                              f'{value!r} refused for the wrong reason: {message}')

    def test_writer_and_schemas_reject_the_same_unsafe_id_shapes(self) -> None:
        from adaptive_grok.change import package_id_block_reason

        historical = sorted(
            entry.name for entry in (ROOT / 'engineering/changes').iterdir() if entry.is_dir()
        )
        for relative in ('schemas/change-spec.schema.json', 'schemas/change-spec-v1.schema.json'):
            schema = json.loads((ROOT / relative).read_text(encoding='utf-8'))
            compiled = re.compile(schema['properties']['change_id']['pattern'])
            for value in (
                '20260925-ab:cd',
                '20260925-ab.',
                '20260926-safe-αβγδεζ',
                'notadate-safe-title-abc123',
                'safe',
            ):
                with self.subTest(schema=relative, value=value):
                    self.assertIsNotNone(package_id_block_reason(value), 'the writer became lenient')
                    self.assertFalse(compiled.fullmatch(value), 'the schema still admits an unsafe id')
            for value in historical:
                with self.subTest(schema=relative, historical=value):
                    self.assertIsNone(package_id_block_reason(value), value)
                    self.assertTrue(compiled.fullmatch(value), 'a historical package was orphaned')

    def test_reserved_device_names_are_not_sufficiently_covered_by_the_slug_rules(self) -> None:
        # Proves the `nul` addition is load-bearing: every other reserved name already trips
        # a different rule, so only a dedicated assertion can show this one was open.
        from adaptive_grok.change import change_id_block_reason

        self.assertIsNotNone(change_id_block_reason('nul'))
        self.assertIn('windows', (change_id_block_reason('nul') or '').lower())
