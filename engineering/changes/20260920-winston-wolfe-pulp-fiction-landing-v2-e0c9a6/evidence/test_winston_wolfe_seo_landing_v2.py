from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tests"))
from test_seo_landing_side_project import external_runtime_urls  # noqa: E402

PROJECT = ROOT / "side-projects" / "seo-landings" / "winston-wolfe-pulp-fiction-v2"
WIDTHS = (320, 640, 768, 1024, 1280, 1920)
FORMATS = ("avif", "webp", "jpg")
GRAPH_ALLOWED = {"Movie", "Person", "FAQPage"}
FORBIDDEN_SCHEMA = {
    "LocalBusiness",
    "Organization",
    "WebSite",
    "WebPage",
    "BreadcrumbList",
    "Review",
    "AggregateRating",
    "Offer",
    "Service",
    "VideoObject",
}


def local_asset_urls(html: str, css: str) -> list[str]:
    candidates: list[str] = []
    candidates.extend(re.findall(r'<(?:img|source|script)\b[^>]*\b(?:src|poster)="([^"]+)"', html, re.I))
    candidates.extend(re.findall(r'<link\b[^>]*\bhref="([^"]+)"', html, re.I))
    for srcset in re.findall(r'\b(?:srcset|imagesrcset)="([^"]+)"', html, re.I):
        for item in srcset.split(","):
            url = item.strip().split()[0]
            if url:
                candidates.append(url)
    for match in re.findall(r'url\(\s*["\']?([^"\')]+)["\']?\s*\)', css, re.I):
        candidates.append(match)
    local: list[str] = []
    for raw in candidates:
        parsed = urlsplit(raw)
        if parsed.scheme in {"http", "https", "data", "mailto", "tel"} or raw.startswith("//") or raw.startswith("#"):
            continue
        local.append(raw.split("?")[0])
    return local


def inline_css(html: str) -> str:
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.I | re.S))


def json_ld_blocks(html: str) -> list[object]:
    blocks = re.findall(
        r'<script\b[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    )
    return [json.loads(block) for block in blocks]


def collect_types(node: object) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        value = node.get("@type")
        if isinstance(value, str):
            found.add(value)
        elif isinstance(value, list):
            found.update(str(item) for item in value)
        for child in node.values():
            found.update(collect_types(child))
    elif isinstance(node, list):
        for child in node:
            found.update(collect_types(child))
    return found


class WinstonWolfeLandingV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.html_path = PROJECT / "index.html"
        self.assertTrue(self.html_path.is_file(), self.html_path)
        self.html = self.html_path.read_text(encoding="utf-8")
        self.css = inline_css(self.html)

    def test_project_tree_and_local_assets_exist(self) -> None:
        self.assertTrue((PROJECT / "robots.txt").is_file())
        self.assertTrue((PROJECT / "favicon.png").is_file())
        self.assertTrue((PROJECT / "ASSETS.md").is_file())
        self.assertTrue((PROJECT / "SERVER-SETUP.md").is_file())
        self.assertFalse((PROJECT / "sitemap.xml").exists())
        self.assertFalse((PROJECT / "script.js").exists())
        self.assertFalse((PROJECT / "styles.css").exists())
        for family in ("hero", "method"):
            matches = list((PROJECT / "images").glob(f"{family}.[0-9a-f]*-320.jpg"))
            self.assertEqual(len(matches), 1, family)
            digest = re.search(r"\.([0-9a-f]{8,})-320\.jpg$", matches[0].name)
            self.assertIsNotNone(digest)
            token = digest.group(1)
            for width in WIDTHS:
                for ext in FORMATS:
                    path = PROJECT / "images" / f"{family}.{token}-{width}.{ext}"
                    self.assertTrue(path.is_file(), path)
        for relative in local_asset_urls(self.html, self.css):
            target = (PROJECT / relative).resolve()
            self.assertTrue(str(target).startswith(str(PROJECT.resolve())), relative)
            self.assertTrue(target.is_file(), relative)

    def test_language_landmarks_noindex_and_no_form(self) -> None:
        self.assertRegex(self.html, r"<html\b[^>]*\blang=\"ru-RU\"")
        self.assertRegex(self.html, r"<html\b[^>]*\bdir=\"ltr\"")
        self.assertLess(self.html.find("<meta charset=\"utf-8\">"), self.html.find("<title>"))
        self.assertEqual(len(re.findall(r"<h1(?:\s|>)", self.html, re.I)), 1)
        self.assertRegex(self.html, r'<meta\s+name="robots"\s+content="noindex, nofollow"')
        self.assertNotRegex(self.html, r'<link[^>]+rel="canonical"')
        self.assertNotRegex(self.html, r'property="og:url"')
        self.assertRegex(self.html, r'property="og:locale"\s+content="ru_RU"')
        self.assertNotRegex(self.html, r"<form(?:\s|>)")
        self.assertNotRegex(self.html, r"mailto:|tel:")
        self.assertNotRegex(self.html, r"<(iframe|svg|video)\b")
        self.assertRegex(self.html, r"<header\b")
        self.assertRegex(self.html, r"<nav\b")
        self.assertRegex(self.html, r"<main\b")
        self.assertRegex(self.html, r"<footer\b")
        self.assertIn("не услуга", self.html.casefold())
        robots = (PROJECT / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Disallow: /", robots)
        self.assertNotRegex(robots, r"(?i)sitemap:")
        lcp = re.search(r"<img\b[^>]*fetchpriority=\"high\"[^>]*>", self.html, re.I)
        self.assertIsNotNone(lcp)
        self.assertNotRegex(lcp.group(0), r'loading=["\']lazy["\']')

    def test_no_external_runtime_urls_or_likeness_claims(self) -> None:
        self.assertEqual(external_runtime_urls(self.html, self.css), [])
        self.assertIn("system-ui", self.css)
        self.assertIn(":focus-visible", self.css)
        self.assertIn("prefers-reduced-motion: reduce", self.css)
        self.assertNotRegex(self.html, r"(?:Lighthouse\s*100|PageSpeed|WCAG(?:\s+2\.1)?\s+compliant)")
        assets = (PROJECT / "ASSETS.md").read_text(encoding="utf-8").casefold()
        self.assertRegex(assets, r"no actor likeness|без сходства с акт")
        self.assertNotIn("harvey keitel", assets)
        for block in json_ld_blocks(self.html):
            types = collect_types(block)
            self.assertFalse(types & FORBIDDEN_SCHEMA, types)
            graph = block.get("@graph") if isinstance(block, dict) else None
            if graph:
                top = {item.get("@type") for item in graph if isinstance(item, dict)}
                self.assertTrue(top <= GRAPH_ALLOWED, top)


if __name__ == "__main__":
    unittest.main()
