"""Read-only B source-layout characterization against the genuine predecessor."""
import ast
import json
import subprocess

from adaptive_factory.landing_artifact import DEPLOY_MEMBERS, LandingArtifactError, deploy_members_for_source
from adaptive_factory.landing_renderer import source_surface_facts
from factory.tests.test_landing_renderer import SOURCE_INDEX

base = 'fb582c91cd80c042d26b7467679d27a295a2396b'
old_tree = ast.parse(subprocess.check_output(
    ['git', 'show', base + ':factory/src/adaptive_factory/landing_artifact.py'], text=True,
))
assignment = next(node for node in old_tree.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == 'DEPLOY_MEMBERS'
                          for target in node.targets))
old_members = tuple(sorted(ast.literal_eval(assignment.value.args[0].args[0])))
identities = (
    ('699010380f4f90a0193a9c22090c35e6aded7d2c', 'f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4', old_members),
    ('176efcaab931c2482781ff163c621b10aa05dee9', 'f2bdcecc6dbe9ecc82007610d398ca12bd75e07f',
     tuple(path for path in old_members if path != 'index.css')),
    ('fde60e040167c10975b00d11f578c4da6763069a', '21817e70e079b772e1f3114a80dfc0320d1ada91',
     tuple(sorted((*old_members, 'analytics.js', 'analytics.css')))),
)
for sha, tree, expected in identities:
    assert deploy_members_for_source(sha, tree) == expected
    assert not {'ASSETS.md', 'SERVER-SETUP.md'}.intersection(expected)
    print(json.dumps({'source_sha': sha, 'member_count': len(expected), 'status': 'pass'}))
for sha, tree in ((identities[0][0], identities[2][1]), (identities[2][0], identities[0][1]),
                  ('0' * 40, '1' * 40)):
    try:
        deploy_members_for_source(sha, tree)
    except LandingArtifactError as exc:
        assert str(exc) == 'source_identity'
    else:
        raise AssertionError('unknown or crossed source epoch was accepted')
assert len(DEPLOY_MEMBERS) == 22
facts = source_surface_facts(SOURCE_INDEX)
assert facts.analytics_script_sha256 and facts.analytics_settings_sha256
print(json.dumps({'unknown_and_crossed_epochs': 'rejected', 'approved_analytics': 'accepted', 'status': 'pass'}))
