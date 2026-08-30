from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from adaptive_trust_ci.migrations import (
    AppliedMigration,
    MigrationError,
    discover_migrations,
    plan_migrations,
)


class MigrationTests(unittest.TestCase):
    def test_production_promotion_migration_is_mirrored_and_checksum_locked(self) -> None:
        repository_root = Path(__file__).resolve().parents[2]
        deployment = repository_root / "trust-ci/sql/004_production_promotions.sql"
        packaged = repository_root / "trust-ci/src/adaptive_trust_ci/resources/004_production_promotions.sql"
        self.assertTrue(deployment.is_file())
        self.assertEqual(deployment.read_bytes(), packaged.read_bytes())
        migrations = discover_migrations(deployment.parent)
        self.assertEqual(migrations[-1].version, 4)
        self.assertEqual(migrations[-1].name, "production_promotions")
        self.assertEqual(migrations[-1].sha256, hashlib.sha256(deployment.read_bytes()).hexdigest())

    def test_historical_migration_bytes_are_unchanged(self) -> None:
        repository_root = Path(__file__).resolve().parents[2]
        expected = {
            "001_schema.sql": "c03e071c1a789c856b54be23c105fd224e1f569b1662b61d46354f2212f46532",
            "002_operational_indexes.sql": "f46128291b765a77568be448f5ef09d37300423afd327370ee2da79d5f33487c",
            "003_database_roles.sql": "1ba63d44639a6cb933a31b887717b021e35b6d056aa564a25f0aaba1683c888c",
        }
        for name, expected_sha256 in expected.items():
            with self.subTest(name=name):
                raw = (repository_root / "trust-ci/sql" / name).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected_sha256)

    def test_discovers_ordered_checksum_locked_migrations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '002_add_index.sql').write_text('SELECT 2;\n', encoding='utf-8')
            (root / '001_schema.sql').write_text('SELECT 1;\n', encoding='utf-8')
            migrations = discover_migrations(root)
        self.assertEqual([item.version for item in migrations], [1, 2])
        self.assertEqual([item.name for item in migrations], ['schema', 'add_index'])
        self.assertEqual(migrations[0].sha256, hashlib.sha256(b'SELECT 1;\n').hexdigest())

    def test_discovery_rejects_duplicate_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '001_schema.sql').write_text('SELECT 1;', encoding='utf-8')
            (root / '001_other.sql').write_text('SELECT 2;', encoding='utf-8')
            with self.assertRaisesRegex(MigrationError, 'duplicate migration version'):
                discover_migrations(root)

    def test_discovery_rejects_version_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '001_schema.sql').write_text('SELECT 1;', encoding='utf-8')
            (root / '003_gap.sql').write_text('SELECT 3;', encoding='utf-8')
            with self.assertRaisesRegex(MigrationError, 'contiguous'):
                discover_migrations(root)

    def test_plan_returns_only_pending_migrations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '001_schema.sql').write_text('SELECT 1;', encoding='utf-8')
            (root / '002_index.sql').write_text('SELECT 2;', encoding='utf-8')
            migrations = discover_migrations(root)
        applied = {
            1: AppliedMigration(
                version=1,
                name='schema',
                sha256=migrations[0].sha256,
            )
        }
        plan = plan_migrations(migrations, applied)
        self.assertEqual([item.version for item in plan.pending], [2])
        self.assertEqual([item.version for item in plan.applied], [1])

    def test_plan_rejects_historical_checksum_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '001_schema.sql').write_text('SELECT 1;', encoding='utf-8')
            migrations = discover_migrations(root)
        applied = {1: AppliedMigration(1, 'schema', 'f' * 64)}
        with self.assertRaisesRegex(MigrationError, 'checksum drift'):
            plan_migrations(migrations, applied)

    def test_plan_rejects_database_version_missing_from_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '001_schema.sql').write_text('SELECT 1;', encoding='utf-8')
            migrations = discover_migrations(root)
        applied = {
            1: AppliedMigration(1, 'schema', migrations[0].sha256),
            2: AppliedMigration(2, 'removed', 'e' * 64),
        }
        with self.assertRaisesRegex(MigrationError, 'missing from the deployed package'):
            plan_migrations(migrations, applied)


if __name__ == '__main__':
    unittest.main()
