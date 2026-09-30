import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

from adaptive_factory.contracts import ContractError
from adaptive_factory.settings import FactorySettings, SettingsError
from factory.tests.test_qualification import qualification_evidence

TASK = '00000000-0000-0000-0000-000000000001'


class QualificationFileTests(unittest.TestCase):
    def reader(self, root):
        from adaptive_factory.qualification import FileQualificationEvidenceReader
        return FileQualificationEvidenceReader(root)

    def bundle(self):
        evidence = qualification_evidence()
        return dict(schema_version=1, repository_id='owner/project', task_id=TASK,
                    evidence={key: ([item.to_dict() for item in value] if isinstance(value, list)
                                    else value.to_dict() if hasattr(value, 'to_dict') else value)
                              for key, value in evidence.items()})

    def test_private_file_evidence_is_typed_bound_and_missing_is_honest(self):
        from adaptive_factory.qualification import qualify
        task = SimpleNamespace(repository_id='owner/project', task_id=TASK)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); reader = self.reader(root)
            self.assertEqual(reader(task), {})
            path = root / (TASK + '.json')
            path.write_text(json.dumps(self.bundle())); path.chmod(0o600)
            self.assertEqual(qualify(task.repository_id, TASK, reader(task)).to_dict()['core_status'], 'ready_for_human')
            with self.assertRaises(ContractError): reader(SimpleNamespace(repository_id='other/project', task_id=TASK))
            path.chmod(0o644)
            with self.assertRaises(SettingsError): reader(task)

    def test_duplicate_keys_traversal_and_symlink_fail_closed(self):
        task = SimpleNamespace(repository_id='owner/project', task_id=TASK)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); reader = self.reader(root); path = root / (TASK + '.json')
            path.write_text('{"schema_version":1,"schema_version":1}'); path.chmod(0o600)
            with self.assertRaises(ContractError): reader(task)
            with self.assertRaises(ContractError): reader(SimpleNamespace(repository_id='owner/project', task_id='../escape'))
            path.unlink(); path.symlink_to(root / 'missing')
            with self.assertRaises(SettingsError): reader(task)

    def test_environment_enablement_is_explicit_and_server_wires_the_reader(self):
        environment = dict(FACTORY_DATABASE_URL='postgresql://runtime', FACTORY_ACTORS_FILE='/run/actors.json')
        with patch.dict(os.environ, environment, clear=True):
            self.assertIsNone(FactorySettings.from_environment().v15_evidence_root)
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {**environment, 'FACTORY_V15_EVIDENCE_ROOT': directory}, clear=True):
                settings = FactorySettings.from_environment()
            self.assertEqual(settings.v15_evidence_root, Path(directory))
            from adaptive_factory.server import build_app
            with patch('adaptive_factory.server.PostgresFactoryStore'), patch('adaptive_factory.server._runtime_readiness'), patch('adaptive_factory.server.load_actors', return_value={}), patch('adaptive_factory.server.Authenticator'), patch('adaptive_factory.server.create_app') as create:
                build_app(settings)
            self.assertIsNotNone(create.call_args.kwargs['qualification_service'])

    def test_cli_qualification_uses_authenticated_existing_transport(self):
        from adaptive_factory.cli import main
        response = Mock(is_success=True); response.json.return_value={'core_status':'not_evaluated'}
        with patch('adaptive_factory.cli.read_token_file', return_value='test-token'), patch('adaptive_factory.cli.httpx.Client') as client:
            client.return_value.__enter__.return_value.get.return_value = response
            self.assertEqual(main(['--token-file','/run/token', 'qualification', TASK]), 0)
            call = client.return_value.__enter__.return_value.get.call_args
            self.assertEqual(call.args[0], '/v1.5/tasks/'+TASK+'/qualification')
            self.assertEqual(call.kwargs['headers']['Authorization'], 'Bearer test-token')
