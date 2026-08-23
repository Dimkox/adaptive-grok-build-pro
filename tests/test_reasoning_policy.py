from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_EFFORTS = frozenset({'low', 'medium', 'high', 'xhigh'})


def agent_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding='utf-8')
    parts = text.split('---', 2)
    if len(parts) != 3:
        raise AssertionError(f'agent definition has no YAML frontmatter: {path}')
    values: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        values[key.strip()] = value.strip()
    return values


class ReasoningPolicyTests(unittest.TestCase):
    def test_project_default_reasoning_is_low(self) -> None:
        config = (ROOT / '.grok/config.toml').read_text(encoding='utf-8')
        self.assertRegex(config, r'(?m)^default_reasoning_effort\s*=\s*"low"\s*$')

    def test_every_project_agent_has_explicit_policy_effort(self) -> None:
        routing = json.loads((ROOT / '.grok-stack/config/routing.json').read_text(encoding='utf-8'))
        reasoning = routing['reasoning']
        self.assertEqual(reasoning['default'], 'low')
        high_effort_agents = set(reasoning['high_effort_agents'])

        seen: set[str] = set()
        for path in sorted((ROOT / '.grok/agents').glob('*.md')):
            data = agent_frontmatter(path)
            name = data.get('name')
            effort = data.get('effort')
            self.assertTrue(name, path.as_posix())
            self.assertIn(effort, ALLOWED_EFFORTS, path.as_posix())
            expected = 'high' if name in high_effort_agents else reasoning['default']
            self.assertEqual(effort, expected, path.as_posix())
            seen.add(str(name))

        self.assertEqual(
            high_effort_agents,
            {
                'task_analyst',
                'architect',
                'bitrix_architect',
                'integration_architect',
                'data_architect',
                'ai_architect',
                'security_reviewer',
                'release_reviewer',
            },
        )
        self.assertTrue(high_effort_agents <= seen)

    def test_legacy_toml_files_do_not_define_a_conflicting_effort(self) -> None:
        for path in sorted((ROOT / '.grok/agents').glob('*.toml')):
            text = path.read_text(encoding='utf-8')
            match = re.search(r'(?m)^effort\s*=\s*"([^"]+)"\s*$', text)
            if match:
                md = agent_frontmatter(path.with_suffix('.md'))
                self.assertEqual(match.group(1), md['effort'], path.as_posix())


if __name__ == '__main__':
    unittest.main()
