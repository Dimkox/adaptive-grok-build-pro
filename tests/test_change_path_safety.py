from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.change import start_change, transition
from adaptive_grok.package_status import read_package_file
from adaptive_grok.router import build_route
from adaptive_grok.state import get_active_change, set_active_route
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
    if len(component.encode('utf-8')) > 255:
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

    def test_printable_value_escapes_bounds_and_keeps_non_ascii_visible(self) -> None:
        from adaptive_grok.change import printable_value

        self.assertEqual(printable_value('a\tb\nc\x1bд'), 'a\\tb\\nc\\x1bд')
        self.assertEqual(printable_value('рабочий \x00'), 'рабочий \\x00')
        self.assertNotIn('\x85', printable_value('c1 \x85 tail'))
        self.assertIn('\\x85', printable_value('c1 \x85 tail'))
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
            'route-id-missing': ({'route_id': None}, 'is not text'),
            'created-at-missing': ({'created_at': None}, 'is not text'),
        }
        for label, (mutation, expected) in cases.items():
            with self.subTest(case=label):
                with project_copy() as root:
                    route = route_for(root, 'Promote only after human approval', label)
                    route.update(mutation)
                    set_active_route(root, route)
                    with self.assertRaises(ValueError) as caught:
                        start_change(root, 'safe title')
                    self.assertIn(expected, str(caught.exception))
                    self.assertEqual(unsafe_package_entries(root), {}, label)
                    self.assertEqual(list((root / 'engineering/changes').iterdir()), [], label)

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
            (packages / 'over-link').symlink_to(Path('..') / '..' / 'outside')
            with self.subTest(change_id='symlink to outside'):
                with self.assertRaises(ValueError):
                    transition(root, 'over-link', 'scoped', 'the name is safe, the link is not')
            loop_a, loop_b = packages / 'loop-a', packages / 'loop-b'
            loop_a.symlink_to(loop_b.name)
            loop_b.symlink_to(loop_a.name)
            with self.subTest(change_id='symlink loop'):
                with self.assertRaises(ValueError) as caught:
                    transition(root, 'loop-a', 'scoped', 'resolve must not answer with a traceback')
                self.assertNotIn(str(packages.resolve()), str(caught.exception))
                self.assertNotIn('\n', str(caught.exception))
            self.assertEqual((outside / 'state.json').read_bytes(), before)
            self.assertTrue((packages / state['change_id'] / 'state.json').is_file())

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
        """The cheap structure assertion the issue asks for: one ``git ls-files -z`` scan."""
        proc = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=False)
        if proc.returncode != 0:
            self.skipTest('git inventory is unavailable')
        tracked = [os.fsdecode(item) for item in proc.stdout.split(b'\0') if item]
        self.assertGreater(len(tracked), 500, 'the tracked inventory looks truncated')
        self.assertEqual(unsafe_tracked_paths(tracked), {})

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
