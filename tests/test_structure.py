from __future__ import annotations

import json
import re
import sys
import tomllib
import unittest
from itertools import combinations
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
        self.assertTrue((ROOT / 'decisions.md').is_file(), 'decisions.md')
        self.assertTrue((ROOT / 'mistakes.md').is_file(), 'mistakes.md')
        decisions_head = (ROOT / 'decisions.md').read_text(encoding='utf-8')[:400]
        mistakes_head = (ROOT / 'mistakes.md').read_text(encoding='utf-8')[:400]
        self.assertIn('Patterns that paid for themselves', decisions_head)
        self.assertIn('Root causes, not symptoms', mistakes_head)
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        headings = [line for line in text.splitlines() if line.startswith('## ')]
        self.assertTrue(headings, 'AGENTS.md has no ## headings')
        self.assertEqual(headings[0], '## Agent self-learning')
        entrypoint = text.find('## Mandatory entrypoint')
        self.assertGreaterEqual(entrypoint, 0, 'missing ## Mandatory entrypoint')
        prefix = text[:entrypoint]
        self.assertIn('log it in decisions.md', prefix)
        self.assertIn('record it in mistakes.md', prefix)
        self.assertNotIn('engineering/decisions.md', prefix)
        self.assertNotIn('engineering/mistakes.md', prefix)
        self.assertIn('worth the effort', prefix)
        self.assertIn('no more than 3 sentences', prefix)
        self.assertIn('root cause (not the symptom)', prefix)

    def test_engineering_self_learning_stubs_are_pointers(self) -> None:
        for rel, dest in (
            ('engineering/decisions.md', '/decisions.md'),
            ('engineering/mistakes.md', '/mistakes.md'),
        ):
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)
            text = path.read_text(encoding='utf-8')
            lines = text.splitlines()
            self.assertLessEqual(len(lines), 5, rel)
            self.assertIn('Canonical log is /', text)
            self.assertIn(f'Canonical log is {dest}', text)
            self.assertIn('Do not append here', text)
            self.assertFalse(
                any(line.startswith('## 20') for line in lines),
                rel,
            )

    def test_readme_names_root_self_learning_logs(self) -> None:
        text = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn('decisions.md', text)
        self.assertIn('mistakes.md', text)
        self.assertTrue(
            'self-learning' in text or 'Agent self-learning' in text,
            'README must name self-learning or Agent self-learning',
        )

    def test_readme_names_onboarding_docs_and_current_version(self) -> None:
        text = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn('QUICKSTART.md', text)
        self.assertIn('CHANGELOG.md', text)
        self.assertIn('2.0.10', text)

    def test_agents_md_requires_readme_refresh_before_push(self) -> None:
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('## README before push', text)
        self.assertIn('git push', text)
        self.assertIn('grok_deploy', text)
        self.assertIn('complete', text)

    def test_decisions_md_records_readme_before_push(self) -> None:
        text = (ROOT / 'decisions.md').read_text(encoding='utf-8')
        self.assertIn('README is the push-time product map', text)

    def test_agents_md_splits_large_tasks(self) -> None:
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('## Split large tasks', text)
        self.assertIn('shared memory', text.lower())
        self.assertIn('decisions.md', text)

    def test_decisions_md_records_split_large_tasks(self) -> None:
        text = (ROOT / 'decisions.md').read_text(encoding='utf-8')
        self.assertIn('Split one large task', text)

    def test_agents_md_releases_when_green(self) -> None:
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('## Release when green', text)
        self.assertIn('gh release create', text)
        headings = [line for line in text.splitlines() if line.startswith('## ')]
        self.assertIn('## Release when green', headings)

    def test_decisions_md_records_green_verify_means_release(self) -> None:
        text = (ROOT / 'decisions.md').read_text(encoding='utf-8')
        self.assertIn('Green verify means a new release', text)

    def test_readme_stack_graph_is_complete(self) -> None:
        text = (ROOT / 'README.md').read_text(encoding='utf-8')
        fence = '```mermaid'
        start = text.find(fence)
        self.assertGreaterEqual(start, 0, 'missing mermaid fence')
        body_start = start + len(fence)
        end = text.find('```', body_start)
        self.assertGreater(end, body_start, 'unclosed mermaid fence')
        mermaid = text[body_start:end]
        required = (
            'Route', 'Skills', 'Agents', 'Hooks', 'Policy',
            'Verify', 'Packages', 'Contract', 'Decisions', 'Mistakes',
        )
        for node_id in required:
            self.assertIn(node_id, mermaid, node_id)

        nodes: set[str] = set()
        edges: set[frozenset[str]] = set()
        for raw in mermaid.splitlines():
            line = re.sub(r'\[[^\]]*\]', '', raw).strip()
            if not line or line.startswith('graph '):
                continue
            match = re.fullmatch(r'(\w+)\s+---\s+(\w+)', line)
            if match is None:
                decl = re.fullmatch(r'(\w+)', line)
                if decl is not None:
                    nodes.add(decl.group(1))
                continue
            left, right = match.group(1), match.group(2)
            nodes.add(left)
            nodes.add(right)
            edges.add(frozenset((left, right)))

        self.assertEqual(nodes, set(required))
        self.assertEqual(len(edges), 45, f'expected 45 unique undirected edges, got {len(edges)}')
        expected = {frozenset(pair) for pair in combinations(required, 2)}
        self.assertEqual(len(expected), 45)
        self.assertEqual(edges, expected)

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

    def test_version_is_2_0_10_and_github_actions_are_absent(self) -> None:
        self.assertEqual((ROOT / 'VERSION').read_text(encoding='utf-8').strip(), '2.0.10')
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
