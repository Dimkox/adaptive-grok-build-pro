from pathlib import Path
import hashlib
import json
import subprocess

base = 'c46f14f6a39ca8dc778f8a179ab4f61cdfe13599'
frozen = 'f31406e970d67f7cd59694da5de88915adb0fa68'
whole = ['factory/src/adaptive_factory/' + name for name in (
    'landing_contracts.py', 'landing_provider.py', 'landing_service.py', 'landing_artifact_retention.py',
)]
whole += ['factory/contracts/jsonschema/landing-provider-evidence.v2.schema.json']
whole += ['factory/tests/' + name for name in (
    'test_landing_contracts.py', 'test_semantic_bridge.py', 'test_semantic_contracts.py',
)]
whole += ['tests/test_architecture_model.py', 'tests/test_architecture_fitness.py']
shared = 'factory/src/adaptive_factory/landing_runtime.py'
model_path = 'architecture/system.yaml'
extra = 'factory/tests/test_landing_runtime.py'
expected = set(whole + [shared, model_path, extra])
changed = set(subprocess.check_output(['git', 'diff', '--name-only', base], text=True).splitlines())
changed.update(subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], text=True).splitlines())
product = {p for p in changed if p.startswith(('factory/', 'architecture/', 'schemas/', '.grok-stack/', 'tests/', 'delivery/'))
           and p != 'factory/README.md'}
assert product == expected, (product - expected, expected - product)
for path in whole:
    assert Path(path).read_bytes() == subprocess.check_output(['git', 'show', frozen + ':' + path]), path
old_runtime = subprocess.check_output(['git', 'show', base + ':' + shared], text=True)
assert old_runtime.count('LandingProviderEvidenceV1') == 3
assert Path(shared).read_text() == old_runtime.replace('LandingProviderEvidenceV1', 'LandingProviderEvidence')
model = json.loads(subprocess.check_output(['git', 'show', base + ':' + model_path]))
reference = json.loads(subprocess.check_output(['git', 'show', frozen + ':' + model_path]))
identity = 'CONTRACT-FACTORY-LANDING-PROVIDER-EVIDENCE-V2'
contract = next(item for item in reference['contracts'] if item['id'] == identity)
index = next(i for i, item in enumerate(model['contracts']) if item['id'] == 'CONTRACT-FACTORY-LANDING-PROVIDER-EVIDENCE-V1')
model['contracts'].insert(index + 1, contract)
node = next(item for item in model['nodes'] if item['id'] == 'NODE-FACTORY-LANDING-DOGFOOD')
node['public_contracts'] = sorted([*node['public_contracts'], identity])
node['repository_paths'] = sorted([*node['repository_paths'], contract['path']])
assert json.loads(Path(model_path).read_text()) == model
# Preserve every preexisting runtime test body; the additive reader proof is
# the only test-method delta, accompanied by its local import additions.
old_test = subprocess.check_output(['git', 'show', base + ':' + extra], text=True)
new_test = Path(extra).read_text()
marker = '    def test_offline_fixture_reaches_artifact_and_retains_full_sealed_metadata(self):\n'
assert old_test[old_test.index(marker):] == new_test[new_test.index(marker):]
rows = {}
for path in sorted(expected):
    data = Path(path).read_bytes()
    selection = ('whole_frozen' if path in whole else 'union_only' if path == shared
                 else 'three_v2_registration_entries' if path == model_path else 'independent_reader_test_strengthening')
    rows[path] = {'selection': selection, 'sha256': hashlib.sha256(data).hexdigest(),
                  'git_blob': subprocess.check_output(['git', 'hash-object', path], text=True).strip()}
unchanged = ('factory/contracts/jsonschema/landing-provider-evidence.v1.schema.json', 'factory/uv.lock',
             'factory/contracts/openapi/landing-dogfood.v1.json', 'architecture/rules.yaml')
for path in unchanged:
    assert Path(path).read_bytes() == subprocess.check_output(['git', 'show', base + ':' + path]), path
manifest = {'route_id': '00652f60f78c', 'base_sha': base, 'frozen_source_sha': frozen,
            'head_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'paths': rows, 'unchanged': list(unchanged), 'root_owned_documentation_exclusion': ['factory/README.md']}
Path('/tmp/agbp-sweep/split-c-source-sha256.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
r = subprocess.run(['/home/pall/.local/bin/ruff', 'check', *[p for p in sorted(expected) if p.endswith('.py')]], capture_output=True, text=True)
Path('/tmp/agbp-sweep/split-c-ruff.out').write_text(r.stdout + r.stderr)
print('exact_paths', len(expected), 'ruff_exit', r.returncode, r.stdout + r.stderr)
r = subprocess.run(['git', 'diff', '--check'], capture_output=True, text=True)
print('diff_check_exit', r.returncode, r.stdout + r.stderr)
print('observed_head', manifest['head_sha'])
