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


class OperationalIntentTests(unittest.TestCase):
    def test_weak_language_disclosure_survives_operational_route_without_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Package.swift').write_text('// not package metadata\n')
            (root / 'main.py').write_text('print("source")\n')
            route = self.route(root, 'Publish the package through a pull request')
            disclosed = route.to_dict()['repo']
            self.assertEqual(disclosed['detected_languages'], ['python', 'swift'])
            self.assertEqual(disclosed['languages'], [])
            self.assertEqual(disclosed['domains'], [])
            self.assertIn('language_scan', disclosed)
            self.assertEqual(route.intent, 'release')
            self.assertIsNone(route.write_agent)
            self.assertNotIn('apple', route.domains)
            self.assertNotIn('python', route.domains)
            self.assert_release_controls(root, 'Publish the package through a pull request')

    def route(self, root: Path, prompt: str):
        return build_route(root, prompt, 'operational-intent',
                           base_commit_override=None,
                           base_fingerprint_override='0' * 64)

    def assert_release_controls(self, root: Path, prompt: str) -> None:
        route = self.route(root, prompt)
        self.assertEqual(route.intent, 'release')
        self.assertEqual(route.risk, 'high')
        self.assertIsNone(route.write_agent)
        self.assertIn('release-readiness', route.workflow_skills)
        self.assertEqual(set(route.review_agents), {
            'code_reviewer', 'test_reviewer', 'security_reviewer', 'release_reviewer',
        })
        self.assertEqual(set(route.required_evidence), {
            'verification', 'code_review', 'test_review', 'security_review', 'release_review',
        })
        self.assertEqual(route.human_gates, [
            'scope_and_design_approval', 'production_action_approval',
        ])

    def test_artifact_history_does_not_negate_a_current_operation(self) -> None:
        # Global historical/past-state vetoes lose the requested publication.
        prompts = (
            'Publish the artifact built yesterday through a pull request',
            "Review yesterday's changes and publish v3 through PR",
            'Publish the artifact reviewed yesterday through a pull request',
            'Опубликуй пакет собранный вчера после ревью',
            'Publish the artifact that was reviewed through a pull request',
            'Deploy the build that has been reviewed through a pull request',
            'Опубликуй пакет который был проверен на ревью',
            'Опубликуй пакет, который был проверен на ревью',
        )
        with tempfile.TemporaryDirectory() as tmp:
            for prompt in prompts:
                with self.subTest(prompt=prompt):
                    self.assert_release_controls(Path(tmp), prompt)

    def test_object_and_destination_restrictions_do_not_negate_the_action(self) -> None:
        # Negation belongs to the command prefix, not arbitrary object words.
        prompts = (
            'Опубликуй пакет без README через PR',
            'Выпусти релиз без деплоя через pull request',
            'Publish the package with no need to restart; review the PR',
            'Опубликуй пакет без изменения версии после ревью',
            'Publish the artifact not to production but to staging after review',
            'Review this PR and publish the package',
        )
        with tempfile.TemporaryDirectory() as tmp:
            for prompt in prompts:
                with self.subTest(prompt=prompt):
                    self.assert_release_controls(Path(tmp), prompt)
            for prompt in (
                'No need to publish and release; review this PR',
                'Can you not deploy and publish; review this PR',
                'Нужно не опубликовать пакет и развернуть сборку; проверь код',
            ):
                with self.subTest(prompt=prompt):
                    route = self.route(Path(tmp), prompt)
                    self.assertEqual(route.intent, 'review')
                    self.assertNotIn('release-readiness', route.workflow_skills)

    def test_coordinated_plan_content_and_plural_nouns_remain_descriptive(self) -> None:
        # Splitting infinitives or excluding only singular nouns invents actions.
        cases = (
            ('Review the plan to deploy and publish the build', 'review'),
            ('Review the plans to deploy and publish the build', 'review'),
            ('Review the plan to deploy, then publish the build', 'review'),
            ('Create release plans', 'feature'),
            ('Prepare release checklists', 'feature'),
            ('Review the report; release plans are listed below', 'review'),
            ('Create release workflows', 'feature'),
            ('Prepare release policies', 'feature'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for prompt, expected in cases:
                with self.subTest(prompt=prompt):
                    route = self.route(Path(tmp), prompt)
                    self.assertEqual(route.intent, expected)
                    self.assertNotIn('release-readiness', route.workflow_skills)
            self.assert_release_controls(
                Path(tmp), 'Review the plan to deploy and publish; publish the build through PR',
            )

    def test_historical_prefix_scopes_coordinated_action_shaped_content(self) -> None:
        # These marker-only examples independently catch removal of history scope.
        prompts = (
            'Review the report; yesterday, publish the artifact',
            'Review the report; last week, deploy the build',
            'Проведи ревью отчета; вчера, опубликуй пакет',
            'Review the report; yesterday, deploy and publish the build',
            'Review the note; release v2 was published',
            'Review the note; publish was requested',
        )
        with tempfile.TemporaryDirectory() as tmp:
            for prompt in prompts:
                with self.subTest(prompt=prompt):
                    route = self.route(Path(tmp), prompt)
                    self.assertEqual(route.intent, 'review')
                    self.assertNotIn('release-readiness', route.workflow_skills)

    def test_dotted_versions_and_bounded_historical_subjects_remain_review(self) -> None:
        # Numeric dots and qualified subjects must not sever the past predicate.
        prompts = (
            'Review the note; release v2.1.1 was published yesterday',
            'Review the note; release v2.1.1 was published',
            'Review the note; release candidate v2 was published',
            'Review the note; publish the reviewed artifact was requested',
        )
        with tempfile.TemporaryDirectory() as tmp:
            for prompt in prompts:
                with self.subTest(prompt=prompt):
                    route = self.route(Path(tmp), prompt)
                    self.assertEqual(route.intent, 'review')
                    self.assertNotIn('release-readiness', route.workflow_skills)

    def test_russian_coordinated_plan_infinitives_remain_descriptive(self) -> None:
        # Russian plan context must survive both optional colon and coordination.
        prompts = (
            'Проведи ревью плана развернуть сборку и опубликовать пакет',
            'Проведи ревью плана: развернуть сборку и опубликовать пакет',
        )
        with tempfile.TemporaryDirectory() as tmp:
            for prompt in prompts:
                with self.subTest(prompt=prompt):
                    route = self.route(Path(tmp), prompt)
                    self.assertEqual(route.intent, 'review')
                    self.assertNotIn('release-readiness', route.workflow_skills)
            self.assert_release_controls(
                Path(tmp), 'Проведи ревью плана развернуть сборку и опубликовать пакет; опубликуй пакет',
            )

    def test_context_exclusion_preserves_raw_domain_and_risk_safety(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            route = self.route(Path(tmp), 'Review "publish SQL auth package in production"')
            self.assertEqual(route.intent, 'review')
            self.assertEqual(set(route.task_domains), {'data', 'security'})
            self.assertEqual(route.risk, 'high')
            self.assertIn('production_action_approval', route.human_gates)
            self.assertNotIn('release-readiness', route.workflow_skills)

    def test_affirmative_operation_survives_pr_review_and_fix_words(self) -> None:
        # A review-first or defect-first ladder loses the requested operation.
        prompts = (
            'Release the artifact through a pull request',
            'Please release v2.1.1 via PR after review',
            'Review this PR, then deploy the build',
            'Fix the bug and publish the package through a pull request',
            'Can you deploy this build after code review?',
            'We need to release v2.1.1 through a pull request',
            'I want you to publish the artifact after review',
            'Prepare the production release through PR',
            'Run the canary rollout after review',
            'Roll back the deployment after review',
            'Выпусти релиз через pull request после review',
            'Проведи ревью PR, затем опубликуй пакет',
            'Исправь баг и выкати релиз через PR',
            'Нужно развернуть сборку после code review',
            'Подготовь production release и canary rollout через PR',
            'Сделай релиз через pull request',
            'Откати сборку после ревью',
        )
        with tempfile.TemporaryDirectory() as tmp:
            for prompt in prompts:
                with self.subTest(prompt=prompt):
                    route = self.route(Path(tmp), prompt)
                    self.assertEqual(route.intent, 'release')
                    self.assertEqual(route.risk, 'high')
                    self.assertIsNone(route.write_agent)
                    self.assertIn('release-readiness', route.workflow_skills)
                    self.assertEqual(set(route.review_agents), {
                        'code_reviewer', 'test_reviewer', 'security_reviewer',
                        'release_reviewer',
                    })
                    self.assertEqual(set(route.required_evidence), {
                        'verification', 'code_review', 'test_review',
                        'security_review', 'release_review',
                    })
                    self.assertEqual(route.human_gates, [
                        'scope_and_design_approval', 'production_action_approval',
                    ])

    def test_incidental_and_descriptive_mentions_keep_ordinary_intent(self) -> None:
        # A raw release substring or a generic infinitive would escalate these.
        cases = (
            ('Review this release plan', 'review'),
            ('Review the plan to deploy later', 'review'),
            ('Review the release checklist before we publish', 'review'),
            ('Review the PR deployment report', 'review'),
            ('Проведи ревью плана релиза', 'review'),
            ('Проверь код для публикации релиза', 'review'),
            ('Fix the release installer', 'bugfix'),
            ('Fix the rollback path', 'bugfix'),
            ('Fix prerelease handling', 'bugfix'),
            ('Fix unpublished artifact handling', 'bugfix'),
            ('Update release notes documentation', 'docs'),
            ('Create a release plan', 'feature'),
            ('Prepare release notes', 'feature'),
            ('Создай план релиза', 'feature'),
            ('Сделай релизный checklist', 'feature'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for prompt, expected in cases:
                with self.subTest(prompt=prompt):
                    route = self.route(Path(tmp), prompt)
                    self.assertEqual(route.intent, expected)
                    self.assertNotIn('release-readiness', route.workflow_skills)
                    if 'deploy' not in prompt:
                        self.assertNotIn('production_action_approval', route.human_gates)

    def test_negated_operations_do_not_mask_code_or_review_tasks(self) -> None:
        cases = (
            ("Don't deploy, fix the code", 'bugfix'),
            ('Do not release or publish; fix the bug', 'bugfix'),
            ('Never deploy and publish; review this PR', 'review'),
            ('Please do not release this build; review the PR', 'review'),
            ('Do not deploy and then publish; fix the code', 'bugfix'),
            ('Не выкатывай релиз, исправь код', 'bugfix'),
            ('Не опубликуй пакет и не разверни сборку; проверь код', 'review'),
            ('Не нужно выпускать релиз; проверь код', 'review'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for prompt, expected in cases:
                with self.subTest(prompt=prompt):
                    self.assertEqual(self.route(Path(tmp), prompt).intent, expected)

    def test_negation_is_bounded_before_an_affirmative_operation(self) -> None:
        prompts = (
            'Do not deploy, but release the source through a pull request',
            "Don't publish; release the build via PR",
            'Не выкатывай в production, но опубликуй пакет через PR',
            'Не публикуй; затем выпусти релиз через pull request',
        )
        with tempfile.TemporaryDirectory() as tmp:
            for prompt in prompts:
                with self.subTest(prompt=prompt):
                    self.assertEqual(self.route(Path(tmp), prompt).intent, 'release')

    def test_quoted_and_historical_operations_are_context_only(self) -> None:
        prompts = (
            'Review the example "release the artifact through PR"',
            "Review the example 'deploy the build'",
            "Review the example 'don't deploy and publish the package'",
            'Review the example `publish the package`',
            'Review the example "deploy the build\nand publish the package"',
            'Review the incomplete example "deploy the build\nand publish the package',
            'Review the example “release the package”',
            'Проведи ревью примера «опубликуй пакет»',
            'Review the script:\n```\ndeploy the build\npublish the artifact\n```',
            'Review the report; yesterday, deploy the build was the old instruction',
            'Review the report; historically: release the build through PR',
            'Review the note; release v2 was published yesterday',
            'Review the note; on 2026-09-24: publish the artifact was requested',
            'Проведи ревью отчета; вчера, выпусти релиз было старой командой',
            'Проведи ревью отчета; ранее: опубликуй пакет',
        )
        with tempfile.TemporaryDirectory() as tmp:
            for prompt in prompts:
                with self.subTest(prompt=prompt):
                    self.assertEqual(self.route(Path(tmp), prompt).intent, 'review')
            for prompt in (
                'Review "do not release"; release the build via PR',
                'Yesterday we deployed v2; publish v3 through PR',
                'Ранее выпустили релиз; теперь опубликуй пакет через PR',
            ):
                with self.subTest(prompt=prompt):
                    self.assertEqual(self.route(Path(tmp), prompt).intent, 'release')

    def test_incident_priority_retains_explicit_operation_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for prompt in ('Production down; fix the incident and release the patch via PR',
                           'Авария: исправь баг и опубликуй пакет через PR'):
                with self.subTest(prompt=prompt):
                    route = self.route(root, prompt)
                    self.assertEqual(route.intent, 'incident')
                    self.assertEqual(route.write_agent, 'general_implementer')
                    self.assertIn('incident-response', route.workflow_skills)
                    self.assertIn('release-readiness', route.workflow_skills)
                    self.assertIn('production_action_approval', route.human_gates)
            for prompt, expected, owner in (
                ('Review this pull request', 'review', None),
                ('Check the PR', 'review', None),
                ('Fix the bug with a regression test', 'bugfix', 'general_implementer'),
                ('Hotfix the rollback path', 'incident', 'general_implementer'),
            ):
                with self.subTest(prompt=prompt):
                    route = self.route(root, prompt)
                    self.assertEqual(route.intent, expected)
                    self.assertEqual(route.write_agent, owner)
                    self.assertNotIn('release-readiness', route.workflow_skills)


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
