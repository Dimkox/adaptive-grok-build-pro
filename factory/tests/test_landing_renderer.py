from contextlib import contextmanager
from dataclasses import FrozenInstanceError, replace
import inspect
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from adaptive_factory.landing_contracts import StaticLandingSpecV1
from adaptive_factory.landing_renderer import (
    DeterministicLandingRenderer,
    ExactGitLandingWorkspace,
    LandingRenderError,
    source_surface_facts,
)


WRITE_PATHS = frozenset({"index.html", "content.css"})


SOURCE_INDEX = """<!doctype html>
<html lang="en-US" dir="ltr">
<head>
  <meta charset="utf-8">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <link rel="canonical" href="https://therealaidarkfactory.online/">
  <link rel="alternate" hreflang="en" href="https://therealaidarkfactory.online/">
  <link rel="alternate" hreflang="zh-Hans" href="https://therealaidarkfactory.online/zh-cn/">
  <link rel="alternate" hreflang="ko-KR" href="https://therealaidarkfactory.online/ko/">
  <link rel="alternate" hreflang="nl-NL" href="https://therealaidarkfactory.online/nl/">
  <link rel="alternate" hreflang="lv-LV" href="https://therealaidarkfactory.online/lv/">
  <link rel="alternate" hreflang="km-KH" href="https://therealaidarkfactory.online/km/">
  <link rel="alternate" hreflang="x-default" href="https://therealaidarkfactory.online/">
  <style>body { color: #fff; background: #07090d; }</style>
</head>
<body>
  <header><a href="/roadmap.html">Roadmap</a></header>
  <main id="content"><h1>Original</h1></main>
  <footer><a href="/privacy.html">Privacy</a><a href="/terms.html">Terms</a></footer>
  <script type="application/ld+json">{"@context":"https://schema.org","@type":"WebSite"}</script>
</body>
</html>
"""


def _git(repository, *arguments, extra_environment=None):
    git = shutil.which("git")
    if git is None:
        raise AssertionError("git is required by the focused workspace test")
    environment = {
        "HOME": str(repository.parent),
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "TZ": "UTC",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        **(extra_environment or {}),
    }
    completed = subprocess.run(
        (git, *arguments),
        cwd=repository,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        raise AssertionError("sealed target fixture Git command failed")
    return completed.stdout.decode("ascii").strip()


@contextmanager
def sealed_target():
    with tempfile.TemporaryDirectory(prefix="sealed-landing-target-") as directory:
        repository = Path(directory) / "target"
        repository.mkdir(mode=0o700)
        _git(repository, "init", "--initial-branch=main")
        files = {
            ".gitattributes": "* text=auto eol=lf\n",
            ".htaccess": "Header always set Content-Security-Policy \"default-src 'self'; script-src 'self' 'sha256-fixture'; style-src 'self' 'sha256-fixture'\"\n",
            "content.css": ":root { color-scheme: dark; }\nbody { margin: 0; }\n",
            "index.html": SOURCE_INDEX,
            "robots.txt": "User-agent: *\nAllow: /\nSitemap: https://therealaidarkfactory.online/sitemap.xml\n",
            "sitemap.xml": "<urlset><url><loc>https://therealaidarkfactory.online/</loc></url></urlset>\n",
            "privacy.html": "<!doctype html><title>Privacy</title>\n",
            "cookies.html": "<!doctype html><title>Cookies</title>\n",
            "california-privacy.html": "<!doctype html><title>California privacy</title>\n",
            "terms.html": "<!doctype html><title>Terms</title>\n",
            "roadmap.html": "<!doctype html><title>Roadmap</title>\n",
            "favicon.png": b"\x89PNG\r\n\x1a\nfixture-icon\n",
            "og-image-automatic.jpg": b"\xff\xd8\xff\xe0fixture-og-image\xff\xd9",
            "zh-cn/index.html": "<!doctype html><html lang=\"zh-Hans\"></html>\n",
            "ko/index.html": "<!doctype html><html lang=\"ko-KR\"></html>\n",
            "nl/index.html": "<!doctype html><html lang=\"nl-NL\"></html>\n",
            "lv/index.html": "<!doctype html><html lang=\"lv-LV\"></html>\n",
            "km/index.html": "<!doctype html><html lang=\"km-KH\"></html>\n",
            "google4175cca555a80a32.html": "google-site-verification: fixture\n",
            "yandex_15bd00519dc47ca1.html": "Verification: fixture\n",
        }
        previous = os.umask(0o077)
        try:
            for name, value in files.items():
                path = repository / name
                path.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(value, bytes):
                    path.write_bytes(value)
                else:
                    path.write_text(value, encoding="utf-8")
        finally:
            os.umask(previous)
        _git(repository, "add", "--", ".")
        commit_environment = {
            "GIT_AUTHOR_NAME": "Sealed Target Fixture",
            "GIT_AUTHOR_EMAIL": "fixture@invalid.local",
            "GIT_COMMITTER_NAME": "Sealed Target Fixture",
            "GIT_COMMITTER_EMAIL": "fixture@invalid.local",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
        }
        _git(repository, "commit", "--no-gpg-sign", "-m", "sealed target", extra_environment=commit_environment)
        sha = _git(repository, "rev-parse", "HEAD")
        tree = _git(repository, "rev-parse", "HEAD^{tree}")
        with patch.multiple(
            "adaptive_factory.landing_renderer",
            TARGET_BASE_SHA=sha,
            TARGET_BASE_TREE=tree,
        ):
            yield repository, sha, tree


def landing_spec() -> StaticLandingSpecV1:
    return StaticLandingSpecV1.from_facts(
        {
            "schema_version": 1,
            "input_digest": "1" * 64,
            "site_id": "therealaidarkfactory.online",
            "canonical_origin": "https://therealaidarkfactory.online/",
            "locale": "en",
            "direction": "ltr",
            "title": 'Trust & "proof"',
            "description": "A bounded, independently evaluated candidate.",
            "robots_policy": "preserve_source",
            "sections": [
                {
                    "kind": "hero",
                    "heading": "Build & verify",
                    "body": "Input 'quoted' & bounded.",
                    "items": ["Alpha & beta", "Gamma"],
                    "cta_label": "Read & verify",
                    "cta_path": "/roadmap.html",
                },
                {
                    "kind": "workflow",
                    "heading": "One controlled loop",
                    "body": "Render, inspect, and stop.",
                    "items": [],
                    "cta_label": "",
                    "cta_path": "",
                },
            ],
            "assets": [],
            "source_claim_refs": ["source:fixture-1"],
        }
    )


def inventory(snapshot, name):
    return {
        member.path: (member.mode, member.object_id)
        for member in getattr(snapshot, name)
    }


class FailingRenderer:
    def render(self, *_args, **_kwargs):
        raise LandingRenderError("fixture_renderer_failure")


class LandingRendererTests(unittest.TestCase):
    def test_exact_target_workspace_is_private_detached_independent_and_two_file_bounded(self):
        with sealed_target() as (target, target_sha, target_tree):
            source_before = (
                target.joinpath(".git/HEAD").read_bytes(),
                target.stat().st_mtime_ns,
            )
            observed = []
            with tempfile.TemporaryDirectory() as scratch:
                broker = ExactGitLandingWorkspace(
                    target,
                    scratch_root=Path(scratch),
                    workspace_observer=observed.append,
                )
                first = broker.build_candidate(
                    landing_spec(), DeterministicLandingRenderer(), ordinal=1
                )
                second = broker.build_candidate(
                    landing_spec(), DeterministicLandingRenderer(), ordinal=1
                )
            source_after = (
                target.joinpath(".git/HEAD").read_bytes(),
                target.stat().st_mtime_ns,
            )

        self.assertEqual((first.source_sha, first.source_tree), (target_sha, target_tree))
        self.assertEqual((first.candidate_sha, first.candidate_tree), (second.candidate_sha, second.candidate_tree))
        self.assertEqual(first.changed_paths, ("content.css", "index.html"))
        self.assertEqual(len(observed), 2)
        self.assertEqual(len(set(observed)), 2)
        self.assertTrue(all(not path.exists() for path in observed))
        self.assertEqual(first.workspace_mode, 0o700)
        self.assertEqual(first.clone_strategy, "no-local-no-hardlinks")
        self.assertTrue(first.head_detached)
        self.assertTrue(first.object_storage_independent)
        self.assertEqual(source_before, source_after)

        source = inventory(first, "source_members")
        candidate = inventory(first, "candidate_members")
        self.assertEqual(set(source), set(candidate))
        self.assertGreaterEqual(len(source), 18)
        self.assertEqual(
            {path for path in source if source[path] != candidate[path]},
            WRITE_PATHS,
        )
        for protected in (
            ".htaccess",
            "robots.txt",
            "sitemap.xml",
            "privacy.html",
            "cookies.html",
            "california-privacy.html",
            "terms.html",
            "zh-cn/index.html",
            "ko/index.html",
            "nl/index.html",
            "lv/index.html",
            "km/index.html",
            "google4175cca555a80a32.html",
            "yandex_15bd00519dc47ca1.html",
        ):
            with self.subTest(protected=protected):
                self.assertEqual(candidate[protected], source[protected])

    def test_renderer_escapes_spec_and_preserves_source_indexing_jsonld_and_csp_facts(self):
        with sealed_target() as (target, _sha, _tree), tempfile.TemporaryDirectory() as scratch:
            snapshot = ExactGitLandingWorkspace(
                target, scratch_root=Path(scratch)
            ).build_candidate(landing_spec(), DeterministicLandingRenderer(), ordinal=1)

        source_html = snapshot.source_index_html.decode("utf-8")
        candidate_html = snapshot.index_html.decode("utf-8")
        candidate_css = snapshot.content_css.decode("utf-8")
        self.assertEqual(
            source_surface_facts(source_html), source_surface_facts(candidate_html)
        )
        self.assertIn("Trust &amp; &quot;proof&quot;", candidate_html)
        self.assertIn("Build &amp; verify", candidate_html)
        self.assertIn("Input &#x27;quoted&#x27; &amp; bounded.", candidate_html)
        self.assertNotIn("Trust & \"proof\"", candidate_html)
        self.assertEqual(candidate_html.count("<script"), 1)
        self.assertIn('<script type="application/ld+json">', candidate_html)
        for forbidden in ("<form", "google-analytics", "gtag(", "javascript:"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, candidate_html.lower())
        self.assertNotIn("@import", candidate_css.lower())
        self.assertNotIn("url(http", candidate_css.lower())
        self.assertTrue(snapshot.content_css.startswith(snapshot.source_content_css))
        with self.assertRaises(FrozenInstanceError):
            snapshot.candidate_sha = "0" * 40

    def test_renderer_revalidates_forged_cta_before_emission(self):
        spec = landing_spec()
        forged = replace(
            spec,
            sections=(
                replace(spec.sections[0], cta_path="/\\attacker.example/collect"),
                *spec.sections[1:],
            ),
        )
        with self.assertRaisesRegex(LandingRenderError, "cta_path"):
            DeterministicLandingRenderer().render(
                SOURCE_INDEX.encode(),
                b":root { color-scheme: dark; }\n",
                forged,
                repair_codes=(),
            )

    def test_wrong_repository_identity_fails_before_workspace_creation(self):
        observed = []
        with sealed_target(), tempfile.TemporaryDirectory() as scratch:
            broker = ExactGitLandingWorkspace(
                Path(__file__).resolve().parents[2],
                scratch_root=Path(scratch),
                workspace_observer=observed.append,
            )
            with self.assertRaisesRegex(LandingRenderError, "source_identity"):
                broker.build_candidate(
                    landing_spec(), DeterministicLandingRenderer(), ordinal=1
                )
        self.assertEqual(observed, [])

    def test_workspace_cleanup_is_unconditional_when_renderer_fails(self):
        observed = []
        with sealed_target() as (target, _sha, _tree), tempfile.TemporaryDirectory() as scratch:
            broker = ExactGitLandingWorkspace(
                target,
                scratch_root=Path(scratch),
                workspace_observer=observed.append,
            )
            with self.assertRaisesRegex(LandingRenderError, "fixture_renderer_failure"):
                broker.build_candidate(landing_spec(), FailingRenderer(), ordinal=1)
        self.assertEqual(len(observed), 1)
        self.assertFalse(observed[0].exists())

    def test_workspace_api_has_no_ref_network_or_arbitrary_path_controls(self):
        parameters = inspect.signature(ExactGitLandingWorkspace.build_candidate).parameters
        self.assertEqual(
            tuple(parameters),
            ("self", "spec", "renderer", "ordinal", "repair_codes"),
        )
        self.assertNotIn("branch", parameters)
        self.assertNotIn("remote", parameters)
        self.assertNotIn("allowed_paths", parameters)


if __name__ == "__main__":
    unittest.main()
