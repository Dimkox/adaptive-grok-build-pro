import unittest
from pathlib import Path
from adaptive_factory import api, landing_host_config

class DedicatedHostSeamTests(unittest.TestCase):
    def test_completed_config_loader_exists(self):
        self.assertTrue(callable(getattr(landing_host_config, "load_host_config", None)))

    def test_landing_only_composition_omits_task_routes(self):
        app = api.create_app(None, object(), execution_enabled=False, landing_service=object(), landing_only=True)
        paths = {route.path for route in app.routes}
        self.assertIn("/v1/landing-inputs", paths)
        self.assertNotIn("/v1/tasks", paths)

    def test_dedicated_host_imports(self):
        from adaptive_factory import landing_host
        self.assertTrue(callable(landing_host.main))

if __name__ == "__main__":
    unittest.main()
