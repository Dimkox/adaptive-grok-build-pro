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
