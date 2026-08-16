from __future__ import annotations

import json
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))


class StructureTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        for rel in (
            'AGENTS.md', 'README.md', '.grok/config.toml', '.grok/hooks.json',
            '.agents/skills/adaptive-delivery/SKILL.md', 'scripts/grok_route.py',
            'LICENSE',
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_agents_md_starts_with_self_learning(self) -> None:
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        headings = [line for line in text.splitlines() if line.startswith('## ')]
        self.assertTrue(headings, 'AGENTS.md has no ## headings')
        self.assertEqual(headings[0], '## Agent self-learning')
        entrypoint = text.find('## Mandatory entrypoint')
        self.assertGreaterEqual(entrypoint, 0, 'missing ## Mandatory entrypoint')
        prefix = text[:entrypoint]
        self.assertIn('engineering/decisions.md', prefix)
        self.assertIn('engineering/mistakes.md', prefix)
        self.assertIn('log it in', prefix)
        self.assertIn('record it in', prefix)
        self.assertIn('worth the effort', prefix)
        self.assertIn('no more than 3 sentences', prefix)
        self.assertIn('root cause (not the symptom)', prefix)

    def test_readme_is_free_mit_commercial_product(self) -> None:
        text = (ROOT / 'README.md').read_text(encoding='utf-8')
        license_text = (ROOT / 'LICENSE').read_text(encoding='utf-8')
        self.assertIn('MIT', text)
        self.assertIn('MIT License', license_text)
        lowered = text.lower()
        self.assertIn('commercial', lowered)
        self.assertIn('free', lowered)
        self.assertIn('public', lowered)
        self.assertNotIn('enterprise-style', lowered)
        self.assertIn('no eula', lowered)
        self.assertIn('no paid tier', lowered)

    def test_grok_config_is_valid_toml(self) -> None:
        data = tomllib.loads((ROOT / '.grok/config.toml').read_text(encoding='utf-8'))
        self.assertEqual(data['sandbox_mode'], 'workspace-write')
        self.assertTrue(data['features']['hooks'])

    def test_hooks_are_valid_and_cover_lifecycle(self) -> None:
        data = json.loads((ROOT / '.grok/hooks.json').read_text(encoding='utf-8'))
        expected = {
            'SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse',
            'PreCompact', 'SubagentStart', 'SubagentStop', 'Stop', 'SessionEnd',
        }
        self.assertTrue(expected.issubset(data['hooks']))
        for entries in data['hooks'].values():
            for entry in entries:
                for hook in entry.get('hooks', []):
                    self.assertIn('commandWindows', hook)

    def test_adaptive_hooks_are_path_qualified(self) -> None:
        data = json.loads((ROOT / '.grok/hooks/adaptive.json').read_text(encoding='utf-8'))
        for entries in data['hooks'].values():
            for entry in entries:
                for hook in entry.get('hooks', []):
                    command = hook.get('command', '')
                    self.assertTrue(
                        command.startswith('python3 .grok/hooks/'),
                        command,
                    )
                    self.assertIn('||', command, command)

    def test_workspace_root_has_dispatch_shims_not_lib(self) -> None:
        self.assertFalse((ROOT / '_lib.py').exists())
        for name in (
            'user_prompt_submit.py', 'pre_tool_use.py', 'post_tool_use.py',
            'pre_compact.py', 'session_start.py', 'session_end.py', 'stop_gate.py',
            'subagent_start.py', 'subagent_stop.py',
        ):
            path = ROOT / name
            self.assertTrue(path.is_file(), name)
            text = path.read_text(encoding='utf-8')
            self.assertIn('.grok', text)
            self.assertNotIn('STACK =', text)
            self.assertNotIn('parents[1]', text)

    def test_agents_have_required_contract(self) -> None:
        agents = list((ROOT / '.grok/agents').glob('*.toml'))
        self.assertGreaterEqual(len(agents), 20)
        names = set()
        for path in agents:
            data = tomllib.loads(path.read_text(encoding='utf-8'))
            self.assertTrue(data.get('name'), path)
            self.assertTrue(data.get('description'), path)
            self.assertTrue(data.get('developer_instructions'), path)
            self.assertIn(data.get('sandbox_mode'), {'read-only', 'workspace-write'})
            self.assertNotIn(data['name'], names)
            names.add(data['name'])
        self.assertIn('bitrix_implementer', names)
        self.assertIn('bitrix_reviewer', names)

    def test_skills_have_frontmatter(self) -> None:
        skills = list((ROOT / '.agents/skills').glob('*/SKILL.md'))
        self.assertGreaterEqual(len(skills), 15)
        for path in skills:
            text = path.read_text(encoding='utf-8')
            self.assertTrue(text.startswith('---\n'), path)
            self.assertIn('\nname:', text[:500])
            self.assertIn('\ndescription:', text[:1200])

    def test_quality_profiles_are_valid(self) -> None:
        profiles = list((ROOT / '.grok-stack/config/quality-profiles').glob('*.json'))
        self.assertGreaterEqual(len(profiles), 9)
        for path in profiles:
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(data['schema_version'], 1)
            self.assertEqual(data['name'], path.stem)
            self.assertIsInstance(data['required_checks'], list)

    def test_product_tree_has_no_packaging_markers(self) -> None:
        for name in ('pyproject.toml', 'requirements.txt', 'setup.py'):
            self.assertFalse((ROOT / name).exists(), name)

    def test_version_is_2_0_8_and_github_actions_are_absent(self) -> None:
        self.assertEqual((ROOT / 'VERSION').read_text(encoding='utf-8').strip(), '2.0.8')
        workflows = ROOT / '.github/workflows'
        self.assertEqual(list(workflows.glob('*.yml')) if workflows.is_dir() else [], [])
        self.assertFalse((ROOT / '.github/dependabot.yml').exists())
        self.assertFalse((ROOT / '.grok-stack/templates/ci/github-actions.yml').exists())

    def test_changelog_2_0_6_does_not_claim_stale_latest(self) -> None:
        text = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
        marker = '## 2.0.6'
        start = text.find(marker)
        self.assertGreaterEqual(start, 0, 'missing 2.0.6 section')
        nxt = text.find('\n## ', start + len(marker))
        section = text[start:] if nxt == -1 else text[start:nxt]
        self.assertNotIn('until a human last mile', section)
        self.assertNotIn('2.0.5 remains', section)

    def test_package_version_matches_version_file(self) -> None:
        from adaptive_grok import __version__

        self.assertEqual(__version__, (ROOT / 'VERSION').read_text(encoding='utf-8').strip())


if __name__ == '__main__':
    unittest.main()
