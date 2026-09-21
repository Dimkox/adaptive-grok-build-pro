from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.change import start_change
from adaptive_grok.repo import detect_repo
from adaptive_grok.router import (
    build_route,
    can_reuse_active_route,
    is_development_prompt,
    should_reuse_active_route,
)
from adaptive_grok.state import set_active_route
from adaptive_grok.workflow_artifacts import load_runtime_authority
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
    def test_security_aliases_keep_high_risk_route_obligations(self) -> None:
        # These prompts contain no second domain/risk signal that could mask a miss.
        families = (
            ('auth', ('auth', 'authn', 'authz', 'authentication', 'authenticate',
                      'authenticated', 'authenticating', 'reauthentication',
                      'unauthenticated', 'authorization', 'authorize', 'authorized',
                      'authorizing', 'unauthorized', 'authorisation', 'authorise',
                      'authorised', 'authorising', 'unauthorised')),
            ('роль', ('роль', 'ролью')),
        )
        expected = {
            'task_domains': ['security'],
            'domains': ['security'],
            'risk': 'high',
            'complexity': 'high-risk',
            'write_agent': 'general_implementer',
            'workflow_skills': ['adaptive-delivery', 'bugfix-workflow',
                                'security-sensitive-change'],
            'review_agents': ['code_reviewer', 'test_reviewer',
                              'security_reviewer', 'release_reviewer'],
            'required_evidence': ['verification', 'code_review', 'test_review',
                                  'security_review', 'release_review'],
            'human_gates': ['scope_and_design_approval'],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(detect_repo(root).domains, [])
            for canonical, words in families:
                for word in words:
                    for prompt in (f'Fix {word}', f'Fix /{word.upper()}/'):
                        with self.subTest(prompt=prompt):
                            route = build_route(
                                root, prompt, 'security-alias',
                                base_commit_override=None,
                                base_fingerprint_override='0' * 64,
                            )
                            self.assertEqual(
                                {key: getattr(route, key) for key in expected}, expected,
                            )
                            self.assertEqual(route.matched_keywords, {
                                'security': [canonical],
                            })

    def test_security_aliases_are_development_signals_without_intent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = detect_repo(Path(tmp))
            for prompt in ('authentication observations', 'authorization observations',
                           'authorisation observations', 'AUTHN observations',
                           'authz observations', 'authenticated observations',
                           'unauthorised observations', 'Наблюдения с ролью'):
                with self.subTest(prompt=prompt):
                    self.assertTrue(is_development_prompt(prompt, repo))

    def test_security_alias_boundaries_do_not_route_unrelated_words(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = detect_repo(root)
            for word in ('author', 'authority', 'authoritative', 'authorship', 'authentic',
                         'xauthn', 'authz_name', 'xauthentication', 'authorizationx',
                         'authorisation_name', 'ролью_имя', 'xролью', 'гастролью'):
                with self.subTest(word=word):
                    route = build_route(
                        root, f'Fix {word}', 'security-alias-boundary',
                        base_commit_override=None,
                        base_fingerprint_override='0' * 64,
                    )
                    self.assertEqual(route.task_domains, [])
                    self.assertEqual(route.domains, ['generic'])
                    self.assertEqual(route.risk, 'low')
                    self.assertEqual(route.complexity, 'micro')
                    self.assertEqual(route.write_agent, 'general_implementer')
                    self.assertEqual(route.workflow_skills,
                                     ['adaptive-delivery', 'bugfix-workflow'])
                    self.assertEqual(route.review_agents, ['code_reviewer', 'test_reviewer'])
                    self.assertEqual(route.required_evidence,
                                     ['verification', 'code_review', 'test_review'])
                    self.assertEqual(route.human_gates, [])
                    self.assertEqual(route.matched_keywords, {})
                    self.assertFalse(is_development_prompt(f'{word} observations', repo))

    def test_issue_155_guard_task_does_not_select_frontend(self) -> None:
        historical = ROOT / 'engineering/changes/20260920-fix-issue-155-guards-inside-the-semantic-bind-re-c4e47e/route.json'
        task = json.loads(historical.read_text(encoding='utf-8'))['task']
        with project_copy() as root:
            route = build_route(root, task, 'issue-155')
            self.assertEqual(set(route.task_domains), {'data', 'integration'})
            self.assertEqual(route.write_agent, 'integration_implementer')
            self.assertNotIn('frontend', route.quality_profiles)
            self.assertNotIn('frontend-change', route.workflow_skills)
            self.assertEqual(route.to_dict().get('matched_keywords'), {
                'data': ['postgres'], 'integration': ['integration'],
            })

    def test_embedded_short_keywords_leave_generic_work_generic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for word in ('distinguish', 'build', 'fluid', 'guide', 'capillary', 'sqlstate',
                         'ad7', 'd7x', 'x1c', '1система', 'fragment', 'restful',
                         'ui_name', 'éui', 'uiя', 'sql2', 'api_'):
                with self.subTest(word=word):
                    route = build_route(root, f'Fix {word} handling', 'boundary')
                    self.assertEqual(route.task_domains, [])
                    self.assertEqual(route.write_agent, 'general_implementer')

    def test_standalone_short_terms_keep_specialist_owners_and_checks(self) -> None:
        cases = (
            ('UI', 'frontend', 'frontend_implementer', 'frontend', None),
            ('API', 'api', 'integration_implementer', 'contracts', None),
            ('REST', 'api', 'integration_implementer', 'contracts', None),
            ('SQL', 'data', 'data_implementer', 'data', 'data_review'),
            ('D7', 'bitrix', 'bitrix_implementer', 'bitrix', 'bitrix_review'),
            ('1C', 'integration', 'integration_implementer', 'integration', 'security_review'),
            ('1С', 'integration', 'integration_implementer', 'integration', 'security_review'),
            ('RAG', 'ai', 'ai_implementer', 'ai', 'security_review'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for term, domain, owner, profile, evidence in cases:
                for prompt in (f'Fix {term}', f'Fix ({term}) handling', f'Fix /{term}/ handling'):
                    with self.subTest(prompt=prompt):
                        route = build_route(root, prompt, 'standalone')
                        self.assertEqual(route.task_domains, [domain])
                        self.assertEqual(route.write_agent, owner)
                        self.assertIn(profile, route.quality_profiles)
                        self.assertIn('code_review', route.required_evidence)
                        self.assertIn('test_review', route.required_evidence)
                        if evidence:
                            self.assertIn(evidence, route.required_evidence)

    def test_domain_match_evidence_preserves_phrases_stems_and_punctuation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            route = build_route(Path(tmp), 'Fix UI/API D7/SQL React UI component, Cypress flow, '
                                'миграцию и интеграцию, external system', 'evidence')
            self.assertEqual(route.to_dict().get('matched_keywords'), {
                'api': ['api'],
                'bitrix': ['d7'],
                'data': ['sql', 'миграц'],
                'frontend': ['cypress', 'react', 'ui'],
                'integration': ['external system', 'интеграц'],
            })
            self.assertEqual(route.task_domains, ['frontend', 'integration', 'data', 'api', 'bitrix'])
            self.assertEqual(route.write_agent, 'bitrix_implementer')

    def test_technical_prompt_detection_uses_short_word_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = detect_repo(Path(tmp))
            for prompt in ('Please distinguish these', 'A capillary observation',
                           'The fluid guide', 'A sqlstate observation', 'An éui observation'):
                with self.subTest(prompt=prompt):
                    self.assertFalse(is_development_prompt(prompt, repo))
            for prompt in ('UI/API observations', 'D7/SQL observations', '1C/1С observations',
                           'AI observations', 'миграционные наблюдения'):
                with self.subTest(prompt=prompt):
                    self.assertTrue(is_development_prompt(prompt, repo))

    def test_keyword_evidence_survives_persistence_and_excludes_repo_domains(self) -> None:
        with project_copy() as root:
            (root / 'bitrix').mkdir()
            generic = build_route(root, 'Fix distinguish handling', 'repo-fallback')
            self.assertEqual(generic.task_domains, [])
            self.assertEqual(generic.write_agent, 'bitrix_implementer')
            self.assertIn('bitrix_review', generic.required_evidence)
            route = build_route(root, 'Fix SQL handling', 'persist')
            expected = {'data': ['sql']}
            self.assertEqual(route.to_dict().get('matched_keywords'), expected)
            self.assertIn('bitrix', route.domains)
            self.assertIn('bitrix_review', route.required_evidence)
            self.assertEqual(build_route(root, route.task, 'again').to_dict().get('matched_keywords'), expected)
            set_active_route(root, route.to_dict())
            self.assertEqual(load_runtime_authority(root, 'route')['matched_keywords'], expected)
            archived = root / f'.grok-stack/runtime/routes/{route.route_id}.json'
            self.assertEqual(json.loads(archived.read_text())['matched_keywords'], expected)
            change = start_change(root)
            copied = root / 'engineering/changes' / change['change_id'] / 'route.json'
            self.assertEqual(json.loads(copied.read_text())['matched_keywords'], expected)

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
