import os
import unittest

from adaptive_factory.admin import (
    provision_artifact_attestor_login,
    provision_runtime_login,
)
from adaptive_factory.migrations import PostgresMigrator
from adaptive_factory.store import (
    PostgresArtifactAttestationStore,
    PostgresFactoryStore,
    StoreError,
)


DATABASE_URL = os.environ.get("FACTORY_TEST_DATABASE_URL")


@unittest.skipUnless(
    DATABASE_URL, "FACTORY_TEST_DATABASE_URL must name a disposable database"
)
class RuntimeCapabilityPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        PostgresMigrator(DATABASE_URL).apply()
        cls.login = f"factory_slice04_runtime_{os.getpid()}"
        cls.attestor_login = f"factory_slice04_attestor_{os.getpid()}"
        cls.password = "local-" + "slice04-runtime-password"
        cls.attestor_password = "local-" + "slice04-attestor-password"
        with psycopg.connect(DATABASE_URL) as connection:
            for login in (cls.attestor_login, cls.login):
                connection.execute(
                    sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(login))
                )
        provision_runtime_login(DATABASE_URL, cls.login, cls.password)
        provision_artifact_attestor_login(
            DATABASE_URL,
            cls.attestor_login,
            cls.attestor_password,
            runtime_login=cls.login,
        )
        cls.runtime_url = make_conninfo(
            **{
                **conninfo_to_dict(DATABASE_URL),
                "user": cls.login,
                "password": cls.password,
            }
        )
        cls.attestor_url = make_conninfo(
            **{
                **conninfo_to_dict(DATABASE_URL),
                "user": cls.attestor_login,
                "password": cls.attestor_password,
            }
        )

    @classmethod
    def tearDownClass(cls):
        import psycopg
        from psycopg import sql

        with psycopg.connect(DATABASE_URL) as connection:
            for login in (cls.attestor_login, cls.login):
                connection.execute(
                    sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(login))
                )

    def test_runtime_store_requires_exact_capability_login_before_set_role(self):
        with self.assertRaisesRegex(StoreError, "runtime login is not least privilege"):
            with PostgresFactoryStore(DATABASE_URL)._connect():
                pass

        with (
            PostgresFactoryStore(self.runtime_url)._connect() as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(
                "SELECT session_user,current_user,current_setting('search_path')"
            )
            self.assertEqual(
                cursor.fetchone(),
                (self.login, "factory_runtime", "pg_catalog, factory"),
            )

        self.assertEqual(
            PostgresFactoryStore(self.runtime_url).readiness()["session_user"],
            self.login,
        )
        self.assertEqual(
            PostgresArtifactAttestationStore(self.attestor_url).readiness(),
            {
                "session_user": self.attestor_login,
                "database_role": "factory_artifact_attestor",
            },
        )

    def test_runtime_store_rejects_swapped_dual_and_direct_authority(self):
        import psycopg
        from psycopg import sql

        with self.assertRaisesRegex(StoreError, "excess role membership"):
            PostgresFactoryStore(self.attestor_url).readiness()
        with self.assertRaisesRegex(StoreError, "excess role membership"):
            PostgresArtifactAttestationStore(self.runtime_url).readiness()
        with self.assertRaisesRegex(StoreError, "login is not least privilege"):
            PostgresArtifactAttestationStore(DATABASE_URL).readiness()

        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                sql.SQL("GRANT factory_artifact_attestor TO {}").format(
                    sql.Identifier(self.login)
                )
            )
        try:
            with self.assertRaisesRegex(StoreError, "excess role membership"):
                PostgresFactoryStore(self.runtime_url).readiness()
        finally:
            with psycopg.connect(DATABASE_URL) as connection:
                connection.execute(
                    sql.SQL("REVOKE factory_artifact_attestor FROM {}").format(
                        sql.Identifier(self.login)
                    )
                )

        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                sql.SQL("GRANT SELECT (task_id) ON factory.tasks TO {}").format(
                    sql.Identifier(self.login)
                )
            )
        try:
            with self.assertRaisesRegex(StoreError, "direct database authority"):
                PostgresFactoryStore(self.runtime_url).readiness()
        finally:
            with psycopg.connect(DATABASE_URL) as connection:
                connection.execute(
                    sql.SQL("REVOKE SELECT (task_id) ON factory.tasks FROM {}").format(
                        sql.Identifier(self.login)
                    )
                )

        schema = f"slice04_owned_{os.getpid()}"
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                sql.SQL("CREATE SCHEMA {} AUTHORIZATION {}").format(
                    sql.Identifier(schema), sql.Identifier(self.login)
                )
            )
        try:
            with self.assertRaisesRegex(StoreError, "direct database authority"):
                PostgresFactoryStore(self.runtime_url).readiness()
        finally:
            with psycopg.connect(DATABASE_URL) as connection:
                connection.execute(
                    sql.SQL("DROP SCHEMA {}").format(sql.Identifier(schema))
                )

        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                sql.SQL("ALTER ROLE {} SET application_name='unsafe'").format(
                    sql.Identifier(self.login)
                )
            )
        try:
            with self.assertRaisesRegex(StoreError, "not least privilege"):
                PostgresFactoryStore(self.runtime_url).readiness()
        finally:
            with psycopg.connect(DATABASE_URL) as connection:
                connection.execute(
                    sql.SQL("ALTER ROLE {} RESET ALL").format(
                        sql.Identifier(self.login)
                    )
                )


if __name__ == "__main__":
    unittest.main()
