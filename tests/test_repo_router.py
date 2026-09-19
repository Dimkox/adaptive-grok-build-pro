from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.repo import detect_repo
from adaptive_grok.router import (
    build_route,
    can_reuse_active_route,
    is_development_prompt,
    should_reuse_active_route,
)
from tests._support import project_copy


class RepoDetectionTests(unittest.TestCase):
    def test_detects_bitrix(self) -> None:
        with project_copy() as root:
            (root / 'bitrix').mkdir()
            (root / 'local/modules/acme.demo').mkdir(parents=True)
            profile = detect_repo(root)
            self.assertEqual(profile.kind, 'bitrix')
            self.assertIn('bitrix', profile.domains)
            self.assertIn('acme.demo', profile.bitrix_modules)

    def test_detects_polyglot(self) -> None:
        with project_copy() as root:
            (root / 'composer.json').write_text('{}')
            (root / 'package.json').write_text('{"scripts":{"test":"vitest"}}')
            profile = detect_repo(root)
            self.assertEqual(profile.kind, 'polyglot')
            self.assertIn('php', profile.languages)
            self.assertIn('typescript', profile.languages)


class RouterTests(unittest.TestCase):
    @staticmethod
    def _control_contract(route):
        return {
            "schema_version": route.schema_version,
            "intent": route.intent,
            "domains": route.domains,
            "task_domains": route.task_domains,
            "risk": route.risk,
            "complexity": route.complexity,
            "primary_skill": route.primary_skill,
            "workflow_skills": route.workflow_skills,
            "analysis_agents": route.analysis_agents,
            "write_agent": route.write_agent,
            "review_agents": route.review_agents,
            "allowed_agents": route.allowed_agents,
            "quality_profiles": route.quality_profiles,
            "required_evidence": route.required_evidence,
            "human_gates": route.human_gates,
            "delivery_expected": route.delivery_expected,
            "status": route.status,
        }

    def test_release_intent_is_not_masked_by_pull_request_delivery_wording(self) -> None:
        prompts = (
            "Prepare the production release and canary rollout",
            "Prepare the release and review the rollout",
            "Prepare the production release and canary rollout; include its pull request in the report",
            "Prepare the production release and canary rollout; mention PR #42 among merged pull requests",
        )
        with project_copy() as root:
            routes = [build_route(root, prompt, f"release-{index}") for index, prompt in enumerate(prompts)]

        expected = {
            "schema_version": 1,
            "intent": "release",
            "domains": ["generic"],
            "task_domains": [],
            "risk": "high",
            "complexity": "high-risk",
            "primary_skill": "adaptive-delivery",
            "workflow_skills": ["adaptive-delivery", "release-readiness"],
            "analysis_agents": ["repo_explorer", "architect", "docs_researcher"],
            "write_agent": None,
            "review_agents": ["security_reviewer", "release_reviewer"],
            "allowed_agents": ["repo_explorer", "architect", "docs_researcher", "security_reviewer", "release_reviewer"],
            "quality_profiles": ["base"],
            "required_evidence": ["verification", "security_review", "release_review"],
            "human_gates": ["scope_and_design_approval", "production_action_approval"],
            "delivery_expected": True,
            "status": "routed",
        }
        for route in routes:
            with self.subTest(prompt=route.task):
                self.assertEqual(self._control_contract(route), expected)
        self.assertEqual(self._control_contract(routes[0]), self._control_contract(routes[1]))
        self.assertEqual(self._control_contract(routes[0]), self._control_contract(routes[2]))

    def test_explicit_review_of_pull_request_remains_review_route(self) -> None:
        with project_copy() as root:
            route = build_route(root, "Review this pull request for security vulnerabilities", "explicit-review")
        self.assertEqual(
            self._control_contract(route),
            {
                "schema_version": 1,
                "intent": "review",
                "domains": ["security"],
                "task_domains": ["security"],
                "risk": "high",
                "complexity": "high-risk",
                "primary_skill": "adaptive-delivery",
                "workflow_skills": ["adaptive-delivery", "verification-evidence", "security-sensitive-change"],
                "analysis_agents": ["repo_explorer", "architect", "docs_researcher"],
                "write_agent": None,
                "review_agents": ["code_reviewer", "test_reviewer", "security_reviewer", "release_reviewer"],
                "allowed_agents": ["repo_explorer", "architect", "docs_researcher", "code_reviewer", "test_reviewer", "security_reviewer", "release_reviewer"],
                "quality_profiles": ["base"],
                "required_evidence": ["verification", "code_review", "test_review", "security_review", "release_review"],
                "human_gates": ["scope_and_design_approval"],
                "delivery_expected": True,
                "status": "routed",
            },
        )

    def test_bare_pull_request_or_pr_wording_does_not_create_review_intent(self) -> None:
        prompts = (
            "Implement a cache refresh option and mention the pull request in the report",
            "Implement a cache refresh option and include PR #42 in the report",
        )
        with project_copy() as root:
            routes = [build_route(root, prompt, f"delivery-word-{index}") for index, prompt in enumerate(prompts)]
        for route in routes:
            with self.subTest(prompt=route.task):
                self.assertEqual(route.intent, "feature")
                self.assertIsNotNone(route.write_agent)

    def test_release_installer_bugfix_with_pull_request_stays_bugfix(self) -> None:
        with project_copy() as root:
            route = build_route(root, "Fix the release installer bug and mention the pull request in the report", "release-bugfix")
        self.assertEqual(
            self._control_contract(route),
            {
                "schema_version": 1,
                "intent": "bugfix",
                "domains": ["generic"],
                "task_domains": [],
                "risk": "low",
                "complexity": "micro",
                "primary_skill": "adaptive-delivery",
                "workflow_skills": ["adaptive-delivery", "bugfix-workflow"],
                "analysis_agents": ["repo_explorer"],
                "write_agent": "general_implementer",
                "review_agents": ["code_reviewer", "test_reviewer"],
                "allowed_agents": ["repo_explorer", "code_reviewer", "test_reviewer", "general_implementer"],
                "quality_profiles": ["base"],
                "required_evidence": ["verification", "code_review", "test_review"],
                "human_gates": [],
                "delivery_expected": True,
                "status": "routed",
            },
        )

    def test_bitrix_bug_routes_specialists(self) -> None:
        with project_copy() as root:
            (root / 'bitrix').mkdir()
            route = build_route(root, 'Исправить баг в D7 обработчике события Битрикс и добавить PHPUnit тест', 's1')
            self.assertEqual(route.intent, 'bugfix')
            self.assertEqual(route.write_agent, 'bitrix_implementer')
            self.assertIn('bitrix_architect', route.analysis_agents)
            self.assertIn('bitrix_reviewer', route.review_agents)
            self.assertIn('bitrix', route.quality_profiles)

    def test_frontend_focus_wins_inside_bitrix_repo(self) -> None:
        with project_copy() as root:
            (root / 'bitrix').mkdir()
            (root / 'package.json').write_text('{"scripts":{"test":"echo ok"}}')
            route = build_route(root, 'Сделай React интерфейс фильтра каталога и Cypress тест', 's2')
            self.assertEqual(route.write_agent, 'frontend_implementer')
            self.assertIn('bitrix_reviewer', route.review_agents)
            self.assertIn('frontend', route.task_domains)

    def test_explicit_bitrix_frontend_stays_bitrix_owned(self) -> None:
        with project_copy() as root:
            (root / 'bitrix').mkdir()
            route = build_route(root, 'Переделай шаблон компонента Битрикс и его JavaScript', 's3')
            self.assertEqual(route.write_agent, 'bitrix_implementer')

    def test_event_integration_route(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Добавить REST API и событие OrderChanged через RabbitMQ для интеграции с 1С', 's4')
            self.assertEqual(route.write_agent, 'integration_implementer')
            self.assertIn('integration_architect', route.analysis_agents)
            self.assertIn('security_reviewer', route.review_agents)
            self.assertIn('contracts', route.quality_profiles)

    def test_data_migration_route(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Сделать SQL миграцию и backfill индекса Elasticsearch', 's5')
            self.assertEqual(route.write_agent, 'data_implementer')
            self.assertIn('data_reviewer', route.review_agents)
            self.assertEqual(route.risk, 'medium')

    def test_ai_security_route(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Добавить RAG по персональным данным с vector store и защитой prompt injection', 's6')
            self.assertEqual(route.write_agent, 'ai_implementer')
            self.assertEqual(route.risk, 'high')
            self.assertIn('security_reviewer', route.review_agents)

    def test_review_has_no_write_owner(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Проведи code review текущего PR', 's7')
            self.assertIsNone(route.write_agent)
            self.assertIn('code_reviewer', route.review_agents)

    def test_release_has_no_write_owner_and_human_gate(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Подготовь production release и canary rollout', 's8')
            self.assertIsNone(route.write_agent)
            self.assertIn('release_reviewer', route.review_agents)
            self.assertIn('production_action_approval', route.human_gates)

    def test_docs_can_have_write_owner_without_test_reviewer(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Обнови README и документацию запуска', 's9')
            self.assertEqual(route.write_agent, 'general_implementer')
            self.assertIn('code_reviewer', route.review_agents)
            self.assertNotIn('test_reviewer', route.review_agents)
            self.assertTrue(route.delivery_expected)
            self.assertIn('verification', route.required_evidence)
            self.assertIn('code_review', route.required_evidence)

    def test_micro_bug(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправь баг в одной функции PHP', 's10')
            self.assertEqual(route.complexity, 'micro')

    def test_short_followup_is_not_new_development_prompt(self) -> None:
        with project_copy() as root:
            self.assertFalse(is_development_prompt('делай', detect_repo(root)))

    def test_repair_yourself_is_bugfix_with_generic_write_owner(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'repair yourself', 's-repair')
            self.assertEqual(route.intent, 'bugfix')
            self.assertEqual(route.write_agent, 'general_implementer')
            self.assertTrue(is_development_prompt('repair yourself', detect_repo(root)))

    def test_reuse_active_route_only_for_followups(self) -> None:
        self.assertFalse(should_reuse_active_route('repair yourself'))
        self.assertFalse(should_reuse_active_route('please inspect hook policy matching'))
        self.assertTrue(should_reuse_active_route('делай'))
        self.assertTrue(should_reuse_active_route('continue'))

    def test_can_reuse_requires_same_session_and_open_status(self) -> None:
        self.assertFalse(can_reuse_active_route('делай', None, 'session-1'))
        existing = {'session_id': 'session-1', 'status': 'routed'}
        self.assertTrue(can_reuse_active_route('делай', existing, 'session-1'))
        self.assertFalse(can_reuse_active_route('делай', existing, 'session-2'))
        ready = {'session_id': 'session-1', 'status': 'ready'}
        self.assertFalse(can_reuse_active_route('делай', ready, 'session-1'))
        self.assertTrue(should_reuse_active_route('делай'))

    def test_bug_with_regression_test_keeps_bugfix_intent(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправь ошибку Битрикс D7 и добавь регрессионный PHPUnit тест', 'x')
            self.assertEqual(route.intent, 'bugfix')
            self.assertEqual(route.write_agent, 'bitrix_implementer')

    def test_clickhouse_event_migration_uses_data_implementer(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Добавь миграцию ClickHouse для аналитических событий и безопасный backfill', 'x')
            self.assertEqual(route.write_agent, 'data_implementer')
            self.assertIn('data_reviewer', route.review_agents)

    def test_prompt_injection_and_tenant_isolation_are_high_risk(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Добавь RAG с tenant isolation и защитой от prompt injection', 'x')
            self.assertEqual(route.risk, 'high')
            self.assertIn('security_reviewer', route.review_agents)
            self.assertIn('scope_and_design_approval', route.human_gates)

    def test_produkt_is_not_a_production_risk_signal(self) -> None:
        with project_copy() as root:
            route = build_route(
                root,
                'веди это как коммерческий продукт но фришный и под мит лицензией',
                's-product',
            )
            self.assertNotEqual(route.risk, 'high')
            self.assertNotIn('production_action_approval', route.human_gates)

    def test_prod_outage_phrase_is_still_high_risk(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'прод упал почини срочно', 's-prod')
            self.assertEqual(route.risk, 'high')
            self.assertIn('production_action_approval', route.human_gates)

    def test_primary_test_request_uses_test_intent(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Добавь регрессионные PHPUnit тесты для сервиса заказов', 'x')
            self.assertEqual(route.intent, 'test')

    def test_generic_feature_uses_widened_analysis_floor(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Добавить функцию', 's-floor')
            self.assertEqual(
                route.analysis_agents,
                ['repo_explorer', 'task_analyst', 'architect', 'docs_researcher'],
            )
            self.assertEqual(route.write_agent, 'general_implementer')
            self.assertNotIn(route.write_agent, route.analysis_agents)
            self.assertLessEqual(len(route.analysis_agents), 10)
            for name in ('bitrix_architect', 'data_architect', 'ai_architect', 'integration_architect'):
                self.assertNotIn(name, route.analysis_agents)

    def test_micro_bug_skips_standard_analysis_floor(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Исправь баг в одной функции PHP', 's-micro')
            self.assertEqual(route.complexity, 'micro')
            self.assertNotIn('docs_researcher', route.analysis_agents)
            self.assertNotIn('architect', route.analysis_agents)

    def test_analysis_cap_truncates_and_does_not_pad(self) -> None:
        with project_copy() as root:
            path = root / '.grok-stack/config/routing.json'
            data = json.loads(path.read_text(encoding='utf-8'))
            data['max_parallel_analysis'] = 2
            path.write_text(json.dumps(data), encoding='utf-8')
            route = build_route(
                root,
                'Добавить REST API и событие OrderChanged через RabbitMQ для интеграции с 1С и SQL миграцию',
                's-cap',
            )
            self.assertEqual(route.analysis_agents, ['repo_explorer', 'task_analyst'])
        with project_copy() as root:
            route = build_route(root, 'Добавить функцию', 's-cap-default')
            self.assertEqual(len(route.analysis_agents), 4)
            self.assertNotEqual(len(route.analysis_agents), 10)

    def test_missing_or_invalid_routing_json_uses_defaults(self) -> None:
        with project_copy() as root:
            (root / '.grok-stack/config/routing.json').unlink()
            route = build_route(root, 'Добавить функцию', 's-missing')
            self.assertEqual(
                route.analysis_agents,
                ['repo_explorer', 'task_analyst', 'architect', 'docs_researcher'],
            )
        with project_copy() as root:
            (root / '.grok-stack/config/routing.json').write_text('{', encoding='utf-8')
            route = build_route(root, 'Добавить функцию', 's-invalid')
            self.assertEqual(
                route.analysis_agents,
                ['repo_explorer', 'task_analyst', 'architect', 'docs_researcher'],
            )


if __name__ == '__main__':
    unittest.main()
