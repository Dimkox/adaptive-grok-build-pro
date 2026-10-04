from __future__ import annotations

import unittest
from types import SimpleNamespace

from adaptive_grok.quality_gates import evaluate_quality_gate


def check(name: str, status: str = "pass", summary: str = "ok") -> SimpleNamespace:
    return SimpleNamespace(name=name, status=status, summary=summary)


BASE_PR_CHECKS = [
    check("git-diff-check"),
    check("docs-state-scope"),
    check("change-spec"),
    check("architecture-inputs"),
    check("architecture"),
    check("governance"),
    check("workflow-artifacts"),
    check("secret-scan"),
    check("contract-structure"),
    check("sql-safety"),
    check("source-stability"),
    check("ruff"),
    check("bandit"),
    check("python-unittest"),
    check("coverage"),
]


class QualityGateTests(unittest.TestCase):
    def test_completed_refusal_does_not_require_future_checks(self) -> None:
        from adaptive_grok.quality_gates import required_check_refused
        for mode in ('pr', 'release'):
            for status, summary, refused in (
                ('pass', 'ok', False), ('fail', 'actual refusal', True),
                ('skip', 'bandit not available', False), ('skip', 'unknown reason', True),
                ('unknown', 'ok', True), ('cancelled', 'interrupted', True),
            ):
                with self.subTest(mode=mode, status=status, summary=summary):
                    self.assertEqual(required_check_refused(check('bandit', status, summary), mode=mode), refused)
        self.assertFalse(required_check_refused(check('ruff', 'skip', 'not available'), mode='fast'))

    def test_exact_consumer_and_micro_skip_reasons_are_admitted(self) -> None:
        allowances = {
            'architecture-inputs': 'architecture authority inputs are absent; not executed',
            'bandit': 'bandit not available',
            'change-spec': '0 specs checked; exempt=True',
        }
        for mode in ('pr', 'release'):
            for name, reason in allowances.items():
                with self.subTest(mode=mode, name=name):
                    checks = [item for item in BASE_PR_CHECKS if item.name != name]
                    self.assertEqual(evaluate_quality_gate(mode=mode, checks=[*checks, check(name, 'skip', reason)]).status, 'pass')
                    for invalid in (reason + '; unknown', 'not executed'):
                        self.assertEqual(evaluate_quality_gate(mode=mode, checks=[*checks, check(name, 'skip', invalid)]).status, 'fail')
                    self.assertEqual(evaluate_quality_gate(mode=mode, checks=checks).status, 'fail')
                    other = 'secret-scan'
                    wrong = [item for item in BASE_PR_CHECKS if item.name != other]
                    self.assertEqual(evaluate_quality_gate(mode=mode, checks=[*wrong, check(other, 'skip', reason)]).status, 'fail')

    def test_discovery_status_matrix_requires_execution(self) -> None:
        for mode in ('pr', 'release'):
            for runner in ('python-unittest', 'pytest', 'python-focused-unittest'):
                for status in (None, 'skip', 'cancelled', 'unknown', 'pass', 'fail'):
                    with self.subTest(mode=mode, runner=runner, status=status):
                        checks = [item for item in BASE_PR_CHECKS if item.name not in {'python-unittest', 'coverage'}]
                        scope = None
                        if runner == 'python-focused-unittest':
                            scope = {'eligible': True, 'skipped_checks': ['python-unittest', 'coverage']}
                            checks.extend([check('python-unittest', 'skip'), check('coverage', 'skip')])
                        else:
                            checks.append(check('coverage'))
                        if status is not None:
                            checks.append(check(runner, status, 'architecture input preflight failed; not started' if status == 'skip' else 'result'))
                        decision = evaluate_quality_gate(mode=mode, checks=checks, docs_scope=scope)
                        # A failed executed run has complete admission evidence; the
                        # verifier's aggregate result still rejects the failing check.
                        self.assertEqual(decision.status, 'pass' if status in {'pass', 'fail'} else 'fail')
                        if status not in {'pass', 'fail'}:
                            self.assertIn('python-discovery', {item['path'] for item in decision.details})

    def test_scoped_full_discovery_skips_require_a_focused_result(self) -> None:
        checks = [item for item in BASE_PR_CHECKS if item.name not in {'python-unittest', 'coverage'}]
        checks.extend([check('python-unittest', 'skip'), check('coverage', 'skip')])
        scope = {'eligible': True, 'skipped_checks': ['python-unittest', 'coverage']}
        decision = evaluate_quality_gate(mode='pr', checks=checks, docs_scope=scope)
        self.assertEqual(decision.status, 'fail')
        self.assertIn('python-discovery', {item['path'] for item in decision.details})

    def test_focused_discovery_requires_scope_and_disclosed_replacements(self) -> None:
        checks = [item for item in BASE_PR_CHECKS if item.name not in {'python-unittest', 'coverage'}]
        checks.append(check('python-focused-unittest'))
        for scope in (None, {'eligible': False}, {'eligible': True, 'skipped_checks': ['coverage']}):
            with self.subTest(scope=scope):
                decision = evaluate_quality_gate(mode='pr', checks=checks, docs_scope=scope)
                self.assertEqual(decision.status, 'fail')
        # A declared omission must also have a result record; it is never silently absent.
        decision = evaluate_quality_gate(mode='pr', checks=checks, docs_scope={'eligible': True, 'skipped_checks': ['python-unittest', 'coverage']})
        self.assertEqual(decision.status, 'fail')

    def test_pytest_requires_coverage_record_and_retains_explicit_skip_allowance(self) -> None:
        checks = [item for item in BASE_PR_CHECKS if item.name not in {'python-unittest', 'coverage'}]
        checks.append(check('pytest'))
        missing = evaluate_quality_gate(mode='pr', checks=checks)
        self.assertEqual(missing.status, 'fail')
        self.assertIn('coverage', {item['path'] for item in missing.details})
        for coverage in (check('coverage'), check('coverage', 'skip', 'pytest runner owns tests; measure unittest trees only')):
            with self.subTest(status=coverage.status):
                decision = evaluate_quality_gate(mode='pr', checks=[*checks, coverage])
                self.assertEqual(decision.status, 'pass')

    def test_pr_fails_when_mandatory_check_is_missing(self) -> None:
        decision = evaluate_quality_gate(
            mode="pr",
            checks=[item for item in BASE_PR_CHECKS if item.name != "coverage"],
        )

        self.assertEqual(decision.status, "fail")
        self.assertIn("coverage", {item["path"] for item in decision.details})

    def test_pr_fails_when_mandatory_tool_is_skipped_without_allowance(self) -> None:
        checks = [*BASE_PR_CHECKS, check("factory-postgres-exit", "skip", "docker not available")]

        decision = evaluate_quality_gate(mode="pr", checks=checks)

        self.assertEqual(decision.status, "fail")
        self.assertIn(
            ("mandatory-check-skipped", "factory-postgres-exit"),
            {(item["code"], item["path"]) for item in decision.details},
        )

    def test_docs_state_profile_allows_declared_replaced_checks(self) -> None:
        checks = [
            item
            for item in BASE_PR_CHECKS
            if item.name not in {"python-unittest", "coverage"}
        ]
        checks.extend(
            [
                check(
                    "python-unittest",
                    "skip",
                    "focused documentation/state profile runs the admitted lockstep modules instead of full test discovery",
                ),
                check(
                    "coverage",
                    "skip",
                    "focused documentation/state profile does not measure full-suite coverage; the admitted inventory changes no executed product statement",
                ),
                check("python-focused-unittest"),
                check(
                    "factory-postgres-exit",
                    "skip",
                    "focused documentation/state profile changes no factory runtime path",
                ),
            ]
        )

        decision = evaluate_quality_gate(
            mode="pr",
            checks=checks,
            docs_scope={
                "eligible": True,
                "skipped_checks": ["python-unittest", "coverage", "factory-postgres-exit"],
            },
        )

        self.assertEqual(decision.status, "pass")

    def test_repository_sandbox_allows_declared_factory_exit_skip(self) -> None:
        checks = [
            *BASE_PR_CHECKS,
            check(
                "factory-postgres-exit",
                "skip",
                "repository-sandbox has no nested-container/database capability",
            ),
        ]

        decision = evaluate_quality_gate(mode="pr", checks=checks)

        self.assertEqual(decision.status, "pass")


if __name__ == "__main__":
    unittest.main()
