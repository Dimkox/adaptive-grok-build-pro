from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok import repo


class RepoLanguageDisclosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix='repo-language-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'product'
        self.root.mkdir()

    def write(self, relative: str, text: str = 'source') -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def detected(self, profile) -> list[str]:
        self.assertIn('detected_languages', profile.to_dict())
        return profile.to_dict()['detected_languages']

    def scan(self, profile) -> dict:
        self.assertIn('language_scan', profile.to_dict())
        return profile.to_dict()['language_scan']

    def test_readable_swift_package_confirms_swift(self) -> None:
        self.write('Package.swift', 'import PackageDescription\nlet package = Package(name: "Demo")')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.kind, 'swift')
        self.assertEqual(profile.languages, ['swift'])
        self.assertEqual(self.detected(profile), ['swift'])
        self.assertIn('swift:Package.swift', profile.signals)
        self.assertIn('swift:profile=base-only', profile.signals)
        self.assertNotIn('apple', profile.domains)

    def test_first_party_swift_sources_confirm_without_manifest(self) -> None:
        self.write('Sources/App/Main.SWIFT', 'print("hi")')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, ['swift'])
        self.assertIn('swift:sources=1', profile.signals)

    def test_weak_swift_marker_does_not_mask_second_source_language(self) -> None:
        self.write('Package.swift', '// not package metadata')
        self.write('src/main.py', 'print("hi")')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(profile.kind, 'generic')
        self.assertEqual(self.detected(profile), ['python', 'swift'])
        self.assertIn('undetected-language:python=1', profile.signals)
        self.assertIn('swift:unconfirmed-package', profile.signals)

    def test_confirmed_swift_does_not_mask_other_sources(self) -> None:
        self.write('Main.swift', 'print("hi")')
        self.write('Main.kt', 'fun main() {}')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, ['swift'])
        self.assertEqual(self.detected(profile), ['kotlin', 'swift'])
        self.assertIn('undetected-language:kotlin=1', profile.signals)

    def test_legacy_manifests_and_node_scripts_remain_compatible(self) -> None:
        for relative in ('composer.json', 'pyproject.toml', 'go.mod', 'Cargo.toml'):
            self.write(relative, '{}')
        self.write('package.json', json.dumps({'scripts': {'test': 'node test', 'build': 'node build'}}))
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, ['php', 'javascript', 'typescript', 'python', 'go', 'rust'])
        self.assertEqual(profile.package_scripts, ['build', 'test'])
        self.assertEqual(profile.kind, 'polyglot')
        self.assertEqual(profile.domains, ['php', 'frontend'])
        self.assertTrue(set(profile.languages).issubset(self.detected(profile)))

    def test_php_source_and_bitrix_modules_stay_compatible(self) -> None:
        self.write('local/modules/acme.demo/lib/main.php', '<?php echo 1;')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.kind, 'bitrix')
        self.assertEqual(profile.languages, ['php'])
        self.assertIn('acme.demo', profile.bitrix_modules)
        self.assertIn('bitrix:custom-modules=1', profile.signals)

    def test_example_php_is_disclosed_without_promoting_repository_domain(self) -> None:
        self.write('examples/bitrix-module/local/modules/acme.demo/include.php', '<?php echo 1;')
        self.write('engineering/contracts/openapi/service.yaml', 'openapi: 3.0.0')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.kind, 'generic')
        self.assertEqual(profile.languages, [])
        self.assertEqual(profile.domains, ['api'])
        self.assertEqual(self.detected(profile), ['php'])
        self.assertIn('undetected-language:php=1', profile.signals)

    def test_legacy_first_party_php_source_locations_still_confirm(self) -> None:
        for relative in ('main.php', 'src/nested/main.php', 'app/main.php',
                         'local/main.php', 'public/main.php', 'www/main.php'):
            with self.subTest(relative=relative):
                source = self.write(relative, '<?php echo 1;')
                profile = repo.detect_repo(self.root)
                self.assertEqual(profile.languages, ['php'])
                self.assertEqual(profile.domains, ['php'])
                source.unlink()

    def test_contract_data_and_ai_markers_stay_compatible(self) -> None:
        self.write('engineering/contracts/openapi/nested/service.yaml', 'openapi: 3.0.0')
        self.write('engineering/contracts/asyncapi/service.json', '{}')
        (self.root / 'database/migrations').mkdir(parents=True)
        (self.root / 'prompts').mkdir()
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.domains, ['api', 'event', 'data', 'ai'])

    def test_symlinked_manifests_and_sources_never_confirm_language(self) -> None:
        outside = Path(self.tmp.name) / 'outside.swift'
        outside.write_text('import PackageDescription\nlet package = Package(name: "Outside")')
        for relative in ('Package.swift', 'composer.json', 'package.json', 'pyproject.toml', 'go.mod', 'Cargo.toml', 'Main.swift'):
            (self.root / relative).symlink_to(outside)
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.detected(profile), [])
        self.assertEqual(self.scan(profile)['skipped_symlinks'], 7)

    def test_symlinked_subtrees_and_contracts_are_not_followed(self) -> None:
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        (outside / 'main.swift').write_text('print("outside")')
        (outside / 'service.yaml').write_text('openapi: 3.0.0')
        (self.root / 'src').symlink_to(outside, target_is_directory=True)
        (self.root / 'engineering/contracts').mkdir(parents=True)
        (self.root / 'engineering/contracts/openapi').symlink_to(outside, target_is_directory=True)
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(profile.domains, [])
        self.assertEqual(self.scan(profile)['skipped_symlinks'], 2)

    def test_symlinked_root_is_incomplete_not_followed(self) -> None:
        self.write('Main.swift', 'print("hi")')
        link = Path(self.tmp.name) / 'root-link'
        link.symlink_to(self.root, target_is_directory=True)
        profile = repo.detect_repo(link)
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.scan(profile)['status'], 'incomplete')
        self.assertEqual(self.scan(profile)['unreadable'], 1)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'requires POSIX FIFO')
    def test_fifo_manifest_is_not_opened_or_accepted(self) -> None:
        os.mkfifo(self.root / 'Package.swift')
        os.mkfifo(self.root / 'package.json')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.scan(profile)['non_regular'], 2)

    def test_case_variant_package_is_disclosed_but_not_confirmed(self) -> None:
        self.write('package.SWIFT', 'import PackageDescription\nlet package = Package(name: "Case")')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.detected(profile), ['swift'])
        self.assertIn('manifest-case-variant:package.SWIFT', profile.signals)

    def test_case_conflict_is_disclosed_without_losing_canonical_legacy_language(self) -> None:
        self.write('package.json', '{}')
        self.write('PACKAGE.JSON', '{"scripts":{"other":"node other"}}')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, ['javascript', 'typescript'])
        self.assertIn('manifest-case-conflict:package.json', profile.signals)
        self.assertTrue(self.scan(profile)['unknown'])

    def test_vendor_generated_and_hidden_sources_are_excluded(self) -> None:
        for directory in ('vendor', 'NODE_MODULES', 'Pods', 'build', 'Generated', 'third_party', '.grok-stack', '.git'):
            self.write(f'{directory}/Main.swift', 'print("vendor")')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.detected(profile), [])
        self.assertEqual(self.scan(profile)['status'], 'complete')

    def test_unknown_extension_and_empty_repository_have_distinct_outcomes(self) -> None:
        empty = repo.detect_repo(self.root)
        self.assertEqual(empty.kind, 'generic')
        self.assertEqual(self.scan(empty)['status'], 'complete')
        self.assertFalse(self.scan(empty)['unknown'])
        self.write('main.zig', 'pub fn main() void {}')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.kind, 'generic')
        self.assertTrue(self.scan(profile)['unknown'])
        self.assertEqual(self.scan(profile)['unknown_extensions'], {'.zig': 1})
        self.assertIn('undetected-source-extension:.zig=1', profile.signals)

    def test_unreadable_file_discloses_extension_without_confirmation(self) -> None:
        self.write('Main.swift', 'print("hi")')
        original_open = os.open
        def denied_open(path, flags, *args, **kwargs):
            if path == 'Main.swift':
                raise PermissionError('fixture unreadable')
            return original_open(path, flags, *args, **kwargs)
        with patch.object(os, 'open', side_effect=denied_open):
            profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.detected(profile), ['swift'])
        self.assertEqual(self.scan(profile)['status'], 'incomplete')
        self.assertEqual(self.scan(profile)['unreadable'], 1)

    def test_unreadable_directory_makes_empty_verdict_incomplete(self) -> None:
        self.write('src/Main.swift', 'print("hi")')
        original_open = os.open
        def denied_open(path, flags, *args, **kwargs):
            if path == 'src':
                raise PermissionError('fixture unreadable')
            return original_open(path, flags, *args, **kwargs)
        with patch.object(os, 'open', side_effect=denied_open):
            profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.scan(profile)['status'], 'incomplete')
        self.assertTrue(self.scan(profile)['unknown'])
        self.assertIn('language-scan:unreadable=1', profile.signals)

    def test_file_budget_preserves_seen_languages_and_discloses_truncation(self) -> None:
        self.write('a.py', 'print(1)')
        self.write('b.swift', 'print(2)')
        self.write('c.go', 'package main')
        with patch.object(repo, 'SOURCE_SCAN_MAX_FILES', 2, create=True):
            profile = repo.detect_repo(self.root)
        self.assertEqual(self.detected(profile), ['python', 'swift'])
        self.assertEqual(self.scan(profile)['files'], 2)
        self.assertTrue(self.scan(profile)['truncated'])
        self.assertIn('files:2', self.scan(profile)['incomplete_reasons'])

    def test_byte_budget_caps_reads_and_retains_unread_language_signal(self) -> None:
        self.write('a.py', '1234')
        self.write('b.swift', '1234')
        with patch.object(repo, 'SOURCE_SCAN_MAX_BYTES', 4, create=True):
            profile = repo.detect_repo(self.root)
        self.assertEqual(self.detected(profile), ['python', 'swift'])
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.scan(profile)['bytes'], 4)
        self.assertIn('bytes:4', self.scan(profile)['incomplete_reasons'])

    def test_depth_budget_stops_before_deep_language(self) -> None:
        self.write('a/b/Main.swift', 'print(1)')
        with patch.object(repo, 'SOURCE_SCAN_MAX_DEPTH', 1, create=True):
            profile = repo.detect_repo(self.root)
        self.assertEqual(self.detected(profile), [])
        self.assertTrue(self.scan(profile)['truncated'])
        self.assertIn('depth:1', self.scan(profile)['incomplete_reasons'])

    def test_directory_budget_stops_pending_subtrees(self) -> None:
        self.write('a/Main.swift', 'print(1)')
        with patch.object(repo, 'SOURCE_SCAN_MAX_DIRS', 1, create=True):
            profile = repo.detect_repo(self.root)
        self.assertEqual(self.detected(profile), [])
        self.assertEqual(self.scan(profile)['directories'], 1)
        self.assertIn('directories:1', self.scan(profile)['incomplete_reasons'])

    def test_entry_budget_does_not_classify_arbitrary_partial_directory(self) -> None:
        for name in ('a.py', 'b.swift', 'c.go'):
            self.write(name)
        with patch.object(repo, 'SOURCE_SCAN_MAX_ENTRIES', 2, create=True):
            first = repo.detect_repo(self.root)
            second = repo.detect_repo(self.root)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(self.detected(first), [])
        self.assertLessEqual(self.scan(first)['entries'], 2)
        self.assertIn('entries:2', self.scan(first)['incomplete_reasons'])

    def test_per_directory_budget_discloses_truncation(self) -> None:
        for name in ('a.py', 'b.swift', 'c.go'):
            self.write(name)
        with patch.object(repo, 'SOURCE_SCAN_MAX_ENTRIES_PER_DIR', 2, create=True):
            profile = repo.detect_repo(self.root)
        self.assertEqual(self.detected(profile), [])
        self.assertIn('entries-per-directory:2', self.scan(profile)['incomplete_reasons'])

    def test_oversized_manifest_is_weak_signal_not_proof(self) -> None:
        self.write('Package.swift', 'import PackageDescription\nlet package = Package(name: "Large")')
        with patch.object(repo, 'MANIFEST_MAX_BYTES', 8, create=True):
            profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.detected(profile), ['swift'])
        self.assertEqual(self.scan(profile)['bytes'], 0)
        self.assertIn('manifest-bytes:8', self.scan(profile)['incomplete_reasons'])

    def test_invalid_json_and_nonmapping_scripts_do_not_crash(self) -> None:
        for contents in ('{broken', '{"scripts":[]}', 'null', '[]'):
            with self.subTest(contents=contents):
                self.write('package.json', contents)
                profile = repo.detect_repo(self.root)
                self.assertEqual(profile.languages, ['javascript', 'typescript'])
                self.assertEqual(profile.package_scripts, [])

    def test_non_contract_sources_in_contract_directory_do_not_add_api_domain(self) -> None:
        self.write('engineering/contracts/openapi/helper.py', 'print(1)')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.domains, [])
        self.assertEqual(self.detected(profile), ['python'])

    def test_exact_shared_budgets_are_complete(self) -> None:
        self.write('src/Main.swift', '1234')
        limits = {
            'SOURCE_SCAN_MAX_FILES': 1, 'SOURCE_SCAN_MAX_BYTES': 4,
            'SOURCE_SCAN_MAX_DEPTH': 1, 'SOURCE_SCAN_MAX_DIRS': 2,
            'SOURCE_SCAN_MAX_ENTRIES': 2, 'SOURCE_SCAN_MAX_ENTRIES_PER_DIR': 1,
        }
        with patch.multiple(repo, **limits):
            profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, ['swift'])
        self.assertEqual(self.scan(profile)['status'], 'complete')
        self.assertEqual(self.scan(profile)['incomplete_reasons'], [])

    def test_source_file_read_cap_retains_weak_extension(self) -> None:
        self.write('Main.swift', '1234')
        with patch.object(repo, 'SOURCE_MAX_FILE_BYTES', 3):
            profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.detected(profile), ['swift'])
        self.assertEqual(self.scan(profile)['bytes'], 0)
        self.assertIn('source-bytes:3', self.scan(profile)['incomplete_reasons'])

    def test_symlink_swap_before_file_open_cannot_read_outside_repository(self) -> None:
        source = self.write('Main.swift', '1234')
        outside = Path(self.tmp.name) / 'outside.swift'
        outside.write_text('print("outside")')
        original_open = os.open
        def swapped_open(path, flags, *args, **kwargs):
            if path == 'Main.swift':
                source.unlink()
                source.symlink_to(outside)
            return original_open(path, flags, *args, **kwargs)
        with patch.object(os, 'open', side_effect=swapped_open):
            profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.scan(profile)['bytes'], 0)
        self.assertEqual(self.scan(profile)['unreadable'], 1)

    def test_symlink_swap_before_directory_open_cannot_traverse_outside(self) -> None:
        self.write('src/Main.swift', '1234')
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        (outside / 'Main.swift').write_text('print("outside")')
        original_open = os.open
        def swapped_open(path, flags, *args, **kwargs):
            if path == 'src':
                (self.root / 'src').rename(self.root / 'moved')
                (self.root / 'src').symlink_to(outside, target_is_directory=True)
            return original_open(path, flags, *args, **kwargs)
        with patch.object(os, 'open', side_effect=swapped_open):
            profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.detected(profile), [])
        self.assertEqual(self.scan(profile)['unreadable'], 1)

    def test_source_changed_during_read_is_not_confirmed(self) -> None:
        source = self.write('Main.swift', '1234')
        original_read = os.read
        def changed_read(descriptor, count):
            data = original_read(descriptor, count)
            source.write_text('changed')
            return data
        with patch.object(os, 'read', side_effect=changed_read):
            profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, [])
        self.assertEqual(self.detected(profile), ['swift'])
        self.assertEqual(self.scan(profile)['unreadable'], 1)

    def test_root_manifest_survives_bounded_listing_overflow(self) -> None:
        self.write('pyproject.toml', '')
        self.write('a.swift', 'print(1)')
        self.write('b.kt', 'fun main() {}')
        with patch.object(repo, 'SOURCE_SCAN_MAX_ENTRIES_PER_DIR', 1):
            profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, ['python'])
        self.assertEqual(self.detected(profile), ['python'])
        self.assertTrue(self.scan(profile)['truncated'])

    def test_non_directory_bitrix_module_is_not_listed(self) -> None:
        self.write('local/modules/not.a.module', 'data')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.kind, 'bitrix')
        self.assertEqual(profile.bitrix_modules, [])

    def test_deeply_nested_node_json_is_bounded_and_does_not_crash(self) -> None:
        self.write('package.json', '{"scripts":' + '[' * 1100 + '0' + ']' * 1100 + '}')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, ['javascript', 'typescript'])
        self.assertEqual(profile.package_scripts, [])

    def test_invalid_unicode_node_json_does_not_crash(self) -> None:
        self.write('package.json').write_bytes(b'\xff\xff')
        profile = repo.detect_repo(self.root)
        self.assertEqual(profile.languages, ['javascript', 'typescript'])
        self.assertEqual(profile.package_scripts, [])

    def test_node_json_integer_conversion_limit_does_not_crash(self) -> None:
        self.write('package.json', '{"scripts":' + '1' * 5000 + '}')
        try:
            profile = repo.detect_repo(self.root)
        except ValueError as exc:
            self.fail(f'bounded package metadata must not crash classification: {exc}')
        self.assertEqual(profile.languages, ['javascript', 'typescript'])
        self.assertEqual(profile.package_scripts, [])


if __name__ == '__main__':
    unittest.main()
