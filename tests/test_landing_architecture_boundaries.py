"""Every landing source has an explicit owner and direct-I/O boundary."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from tests import test_architecture_fitness as fixture

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "factory/src/adaptive_factory/"
OFFLINE = frozenset(PREFIX + name for name in (
    "landing_artifact.py", "landing_artifact_retention.py", "landing_contracts.py",
    "landing_coordinator.py", "landing_evaluation.py", "landing_intake.py",
    "landing_normalizer.py", "landing_provider.py", "landing_renderer.py",
    "landing_runtime.py", "landing_service.py", "landing_http.py", "landing_backup.py",
    "landing_media.py", "landing_sse.py", "landing_publication_cli.py",
    "landing_host_config.py", "resources/landing_pdf_worker.py",
))
GROUPS = {
    "offline": OFFLINE,
    "sqlite": frozenset({PREFIX + "landing_sqlite_store.py"}),
    "host": frozenset({PREFIX + "landing_host.py", PREFIX + "landing_server.py"}),
    "live": frozenset({PREFIX + "landing_live_executors.py"}),
}
OWNERS = {
    "offline": "NODE-FACTORY-LANDING-DOGFOOD",
    "sqlite": "NODE-FACTORY-LANDING-SQLITE",
    "host": "NODE-FACTORY-LOCAL-API",
    "live": "NODE-FACTORY-LANDING-LIVE-EXECUTORS",
}
RULES = {
    "offline": "FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY",
    "sqlite": "FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY",
    "host": "FIT-FACTORY-LANDING-HOST-BOUNDARY",
    "live": "FIT-FACTORY-LANDING-LIVE-BOUNDARY",
}


def classified_inventory(inventory, groups):
    seen = set()
    for files in groups.values():
        if seen.intersection(files):
            raise ValueError("overlapping landing I/O classes")
        seen.update(files)
    if seen != set(inventory):
        raise ValueError("landing I/O classification is incomplete")


class LandingArchitectureBoundaryTests(unittest.TestCase):
    def test_every_actual_landing_source_has_exact_owner_and_boundary(self):
        inventory = {str(path.relative_to(ROOT)) for path in (ROOT / PREFIX).rglob("landing*.py")}
        classified_inventory(inventory, GROUPS)
        snapshot = fixture.ARCHITECTURE.load_architecture(ROOT)
        for group, paths in GROUPS.items():
            for path in paths:
                with self.subTest(group=group, path=path):
                    owners = {node["id"] for node in snapshot.system["nodes"] if path in node["repository_paths"]}
                    rules = {rule["id"] for rule in snapshot.rules["path_boundaries"] if path in rule["source_prefixes"]}
                    self.assertEqual(owners, {OWNERS[group]})
                    self.assertEqual(rules, {RULES[group]})

    def test_inventory_rejects_new_even_empty_sources_and_overlapping_classes(self):
        inventory = set().union(*GROUPS.values())
        classified_inventory(inventory, GROUPS)
        for name in ("landing_unclassified.py", "resources/landing_other_worker.py"):
            with self.subTest(path=name), self.assertRaisesRegex(ValueError, "incomplete"):
                classified_inventory(inventory | {PREFIX + name}, GROUPS)
        groups = {**GROUPS, "accidental-live": {PREFIX + "landing_backup.py"}}
        with self.assertRaisesRegex(ValueError, "overlapping"):
            classified_inventory(inventory, groups)

    def test_actual_offline_rule_rejects_each_direct_client_in_every_source(self):
        actual = fixture.ARCHITECTURE.load_architecture(ROOT)
        offline_rule = next(rule for rule in actual.rules["path_boundaries"] if rule["id"] == RULES["offline"])
        rules = fixture._rules()
        rules["path_boundaries"] = [copy.deepcopy(offline_rule)]
        repo = fixture.GitArchitectureRepo(self)
        repo.model(fixture._system(), rules)
        repo.write_text(PREFIX + "__init__.py", "")
        base = repo.commit("offline rule")
        clients = ("httpx", "socket", "urllib.request", "psycopg", "adaptive_trust_ci")
        # Distinct AST nodes and findings prove every client is refused at every
        # source path, without making network requests or importing the clients.
        for path in OFFLINE | GROUPS["sqlite"]:
            repo.write_text(path, "".join(f"import {client}\n" for client in clients))
        head = repo.commit("inject direct clients")
        diff = fixture.FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
        report = fixture.FIT.evaluate_fitness(repo.root, fixture.FIT.load_architecture(repo.root), diff,
                                              diff.changed_paths, pre_risk="green")
        result = next(item for item in report.results if item.category == "module_boundary")
        self.assertEqual(result.status, "fail")
        for path in OFFLINE | GROUPS["sqlite"]:
            for client in clients:
                with self.subTest(path=path, client=client):
                    self.assertIn(f"{RULES['offline']}: {path} imports forbidden {client}", result.findings)

    def test_uri_exception_is_declared_only_for_staged_delivery(self):
        snapshot = fixture.ARCHITECTURE.load_architecture(ROOT)
        allowed = {rule["id"]: rule["allowed_dependency_modules"]
                   for rule in snapshot.rules["path_boundaries"] if rule.get("allowed_dependency_modules")}
        self.assertEqual(allowed, {"FIT-STAGED-DELIVERY-SOURCE-BOUNDARY": ["urllib.parse"]})
