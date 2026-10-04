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
