#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

ROOT = Path("/home/pall/grok-projects/adaptive-grok-build-pro")
PROJECT = ROOT / "side-projects" / "seo-landings" / "winston-wolfe-pulp-fiction-v2"
HERO = "82065b0b1cb4"
METHOD = "ec74513ab552"
WIDTHS = (320, 640, 768, 1024, 1280, 1920)
SIZES_HERO = "(min-width: 1200px) 1200px, 100vw"
SIZES_METHOD = "(min-width: 900px) 42vw, 100vw"


def sha256_csp(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return "sha256-" + base64.b64encode(digest).decode("ascii")


def srcset(family: str, digest: str, ext: str) -> str:
    return ", ".join(f"images/{family}.{digest}-{width}.{ext} {width}w" for width in WIDTHS)


def picture(family: str, digest: str, sizes: str, alt: str, width: int, height: int, *, lcp: bool) -> str:
    extra = ' fetchpriority="high" decoding="async"' if lcp else ' loading="lazy" decoding="async"'
    return (
        f'<picture>'
        f'<source type="image/avif" srcset="{srcset(family, digest, "avif")}" sizes="{sizes}">'
        f'<source type="image/webp" srcset="{srcset(family, digest, "webp")}" sizes="{sizes}">'
        f'<img src="images/{family}.{digest}-1280.jpg" '
        f'srcset="{srcset(family, digest, "jpg")}" sizes="{sizes}" '
        f'alt="{alt}" width="{width}" height="{height}"{extra}>'
        f"</picture>"
    )


CSS = """*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#0b0a08;color:#f3ead8;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI","Roboto","Oxygen","Ubuntu","Cantarell","Helvetica Neue",Arial,sans-serif;line-height:1.55}img{max-width:100%;height:auto;display:block}a{color:#d4a643}a:hover{color:#f3ead8}.skip-link{position:absolute;inset-inline-start:max(16px,env(safe-area-inset-left));top:max(8px,env(safe-area-inset-top));transform:translateY(-200%);background:#d4a643;color:#0b0a08;padding:.5rem .8rem;z-index:20}.skip-link:focus{transform:none}.site-header{position:sticky;top:0;z-index:10;background:#0b0a08f2;border-bottom:1px solid #2a241c;padding-top:max(.7rem,env(safe-area-inset-top));padding-bottom:.7rem}.shell{width:100%;max-width:1200px;margin:0 auto;padding-inline:max(15px,env(safe-area-inset-left)) max(15px,env(safe-area-inset-right))}.header-inner{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:.8rem}.brand{display:flex;align-items:baseline;gap:.6rem;text-decoration:none;color:#f3ead8;letter-spacing:.18em;text-transform:uppercase;font-size:.82rem}.brand b{color:#d4a643;font-weight:700}nav{display:flex;flex-wrap:wrap;gap:.9rem}nav a{color:#b7aea0;text-decoration:none;font-size:.92rem}nav a:hover{color:#f3ead8}.hero{padding:1.2rem 0 2.4rem}.hero-grid{display:grid;gap:1.4rem}@media(min-width:900px){.hero-grid{grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);align-items:center}.hero-copy{order:-1}}.eyebrow{margin:0 0 .6rem;color:#d4a643;letter-spacing:.16em;text-transform:uppercase;font-size:.72rem}h1{margin:0 0 .8rem;font-size:clamp(2rem,6vw,3.6rem);line-height:1.08;letter-spacing:-.02em}.lead{margin:0 0 1.2rem;color:#b7aea0;font-size:1.05rem;max-width:38rem}.hero-actions{display:flex;flex-wrap:wrap;gap:.7rem;margin-bottom:1rem}.button{display:inline-block;padding:.75rem 1.1rem;text-decoration:none;border-radius:2px}.button-primary{background:#d4a643;color:#0b0a08;font-weight:700}.button-primary:hover{background:#f3ead8}.button-secondary{border:1px solid #d4a643;color:#d4a643}.chips{display:flex;flex-wrap:wrap;gap:.4rem;padding:0;margin:0;list-style:none}.chips li{border:1px solid #3a3228;color:#b7aea0;padding:.25rem .55rem;font-size:.8rem}.frame{background:#161310;border:1px solid #2a241c}.frame picture,.method-visual picture{aspect-ratio:16/9}.method-visual picture{aspect-ratio:4/3}.section{padding:2.4rem 0;border-top:1px solid #2a241c}h2{margin:0 0 1rem;font-size:1.7rem}.prose{color:#d8d0c4;max-width:42rem}.card-grid{display:grid;gap:1rem}@media(min-width:700px){.card-grid{grid-template-columns:1fr 1fr}.method-layout{grid-template-columns:1.1fr .9fr;align-items:center}}.card{background:#161310;border:1px solid #2a241c;padding:1rem 1.1rem}.card h3{margin:0 0 .4rem;color:#d4a643;font-size:1rem}.card p{margin:0;color:#d8d0c4}.disclaimer{background:#8b1e2d14;border:1px solid #8b1e2d66;padding:1.2rem 1.3rem}.disclaimer h2{color:#f3ead8}details{border-bottom:1px solid #2a241c;padding:.8rem 0}summary{cursor:pointer;font-weight:650;color:#f3ead8}summary:focus-visible,a:focus-visible,.button:focus-visible,.skip-link:focus-visible{outline:2px solid #d4a643;outline-offset:3px}footer{padding:1.4rem 0 max(1.6rem,env(safe-area-inset-bottom));border-top:1px solid #2a241c;color:#9a9184;font-size:.92rem}footer p{margin:.3rem 0}@media (prefers-reduced-motion: reduce){html{scroll-behavior:auto}*{animation:none!important;transition:none!important}}"""

FAQ = [
    (
        "Кто такой Винстон Вульф?",
        "В русской Википедии — Уинстон Вульф, «Чистильщик». Вымышленный cleaner Марселласа Уоллеса. Он появляется в главе «Ситуация с Бонни»: после случайного выстрела Винсента Веги в Марвина Джулс везёт машину к Джимми Диммику, а Марселлас посылает мистера Вульфа.",
    ),
    (
        "Кто сыграл Волка?",
        "Харви Кейтель. По русской Википедии роль была специально написана для него. На этой странице нет портрета актёра и нет кадров из фильма.",
    ),
    (
        "Что за фильм?",
        "Pulp Fiction / «Криминальное чтиво», США, 1994, 154 минуты, режиссёр Квентин Тарантино, прокат Miramax. Золотая пальмовая ветвь Канн-1994; «Оскар», BAFTA и «Золотой глобус» за оригинальный сценарий. IMDb tt0110912.",
    ),
    (
        "Это реальная услуга?",
        "Нет. Это неофициальная фан-страница о персонаже. Здесь нет телефона, адреса, цен, записи и заявок.",
    ),
]

LD = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "Movie",
            "@id": "https://www.wikidata.org/wiki/Q104123",
            "name": "Pulp Fiction",
            "alternateName": "Криминальное чтиво",
            "dateCreated": "1994",
            "duration": "PT154M",
            "director": {"@type": "Person", "name": "Quentin Tarantino"},
            "sameAs": [
                "https://www.wikidata.org/wiki/Q104123",
                "https://www.imdb.com/title/tt0110912/",
            ],
        },
        {
            "@type": "Person",
            "name": "Winston Wolfe",
            "alternateName": ["Винстон Вульф", "The Wolf", "Волк"],
            "description": "Вымышленный чистильщик Марселласа Уоллеса в главе «Ситуация с Бонни» фильма «Криминальное чтиво» (1994).",
        },
        {
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": a},
                }
                for q, a in FAQ
            ],
        },
    ],
}

JSONLD = json.dumps(LD, ensure_ascii=False, separators=(",", ":")).replace("<", r"\u003c")
STYLE_HASH = sha256_csp(CSS)
JSON_HASH = sha256_csp(JSONLD)
CSP = (
    "default-src 'self'; "
    f"script-src '{JSON_HASH}'; "
    f"style-src '{STYLE_HASH}'; "
    "img-src 'self'; font-src 'self'; connect-src 'self'; object-src 'none'; "
    "base-uri 'self'; form-action 'none'; frame-src 'none'; frame-ancestors 'none'"
)

HERO_PIC = picture(
    "hero",
    HERO,
    SIZES_HERO,
    "Ночной чёрный седан, серебристый кейс и чашка кофе на капоте",
    1280,
    720,
    lcp=True,
)
METHOD_PIC = picture(
    "method",
    METHOD,
    SIZES_METHOD,
    "Чёрные перчатки, термос кофе и сложенное бельё на верстаке",
    1280,
    960,
    lcp=False,
)

FAQ_HTML = "".join(
    f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in FAQ
)

HTML = f"""<!doctype html>
<html lang="ru-RU" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="description" content="Неофициальная фан-страница о Винстоне Вульфе — чистильщике из фильма «Криминальное чтиво» (1994). Не услуга и не бизнес.">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<title>Винстон Вульф — Волк из «Криминального чтива»</title>
<meta property="og:type" content="website">
<meta property="og:locale" content="ru_RU">
<meta property="og:title" content="Винстон Вульф — Волк из «Криминального чтива»">
<meta property="og:description" content="Неофициальная фан-страница о персонаже Уинстоне Вульфе из фильма 1994 года. Не услуга.">
<meta property="og:image" content="images/hero.{HERO}-1280.jpg">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="720">
<meta property="og:image:alt" content="Ночной чёрный седан, кейс и чашка кофе">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Винстон Вульф — Волк из «Криминального чтива»">
<meta name="twitter:description" content="Неофициальная фан-страница о персонаже Уинстоне Вульфе из фильма 1994 года. Не услуга.">
<meta name="twitter:image" content="images/hero.{HERO}-1280.jpg">
<link rel="icon" href="favicon.png" type="image/png" sizes="96x96">
<style>{CSS}</style>
</head>
<body>
<a class="skip-link" href="#content">Перейти к содержанию</a>
<header class="site-header">
<div class="shell header-inner">
<a class="brand" href="#top"><b>THE WOLF</b> <span>Вульф</span></a>
<nav aria-label="Разделы страницы">
<a href="#character">Персонаж</a>
<a href="#method">Метод</a>
<a href="#facts">Факты</a>
<a href="#about">О странице</a>
</nav>
</div>
</header>
<main id="content">
<section class="hero" id="top" aria-labelledby="hero-title">
<div class="shell hero-grid">
<div class="frame">{HERO_PIC}</div>
<div class="hero-copy">
<p class="eyebrow">Pulp Fiction · глава «Ситуация с Бонни» · 1994</p>
<h1 id="hero-title">Уинстон Вульф, чистильщик из «Криминального чтива»</h1>
<p class="lead">Американский фильм Квентина Тарантино, 154 минуты, прокат Miramax. Золотая пальмовая ветвь Канн-1994. Волк — не главный герой: он приезжает на одну сцену и закрывает бардак, который устроили Джулс и Винсент.</p>
<div class="hero-actions">
<a class="button button-primary" href="#character">Ситуация с Бонни</a>
<a class="button button-secondary" href="#facts">Факты фильма</a>
</div>
<ul class="chips" aria-label="Границы страницы">
<li>Не услуга</li>
<li>Без заявок</li>
<li>Только факты фильма</li>
</ul>
</div>
</div>
</section>
<section class="section" id="character" aria-labelledby="character-title">
<div class="shell">
<h2 id="character-title">Ситуация с Бонни</h2>
<div class="prose">
<p>В хронологии фильма глава идёт сразу после квартиры Бретта. Винсент Вега случайно стреляет в голову Марвину. Джулс Уиннфилд ведёт машину в гараж к Джимми Диммику — его играет сам Тарантино. С ночного дежурства должна вернуться жена Джимми, медсестра Бонни: если она увидит труп, Джимми обещает развод.</p>
<p>Марселлас Уоллес посылает мистера Вульфа. Под его руководством Джулс и Винсент приводят салон и себя в порядок и везут машину с трупом в багажнике на автосвалку Монстра Джо. Вульф уезжает с Ракель, дочерью Монстра Джо. Джулс и Винсент идут завтракать — и попадают в ограбление забегаловки, которым фильм открывается и закрывается.</p>
<p>Роль сыграл Харви Кейтель; по русской Википедии её написали специально для него. На странице нет портрета актёра и нет студийных кадров — только исходные натюрморты.</p>
</div>
</div>
</section>
<section class="section" id="method" aria-labelledby="method-title">
<div class="shell">
<h2 id="method-title">Метод — не оферта</h2>
<p class="prose">Ниже не прайс и не регламент фирмы. Это разбор того, как персонаж выглядит в фильме.</p>
<div class="card-grid method-layout">
<div class="card-grid">
<article class="card"><h3>Вызов</h3><p>Его не ищут Джулс и Винсент. Его присылает Марселлас, когда локальная дружба с Джимми уже не спасает.</p></article>
<article class="card"><h3>Порядок</h3><p>Салон, одежда, маршрут на свалку Монстра Джо. Волк не «вдохновляет» — он раздаёт шаги, пока Бонни не пришла с смены.</p></article>
<article class="card"><h3>Кофе у Джимми</h3><p>Бытовая пауза в чужой кухне. В фильме это не бренд и не меню, а тон сцены: хаос уже чужой дом.</p></article>
<article class="card"><h3>Уход</h3><p>Он не остаётся на завтрак с Джулсом и Винсентом. Уезжает с Ракель. На этом его экранное время кончается.</p></article>
</div>
<div class="frame method-visual">{METHOD_PIC}</div>
</div>
</div>
</section>
<section class="section" id="about" aria-labelledby="about-title">
<div class="shell">
<div class="disclaimer">
<h2 id="about-title">Это не услуга</h2>
<p>Страница неофициальная и не связана с правообладателями, съёмочной группой и актёрами. Товарные знаки принадлежат их владельцам. Здесь нет телефона, адреса, мессенджеров, цен, SLA и записи. Ничего нельзя заказать.</p>
</div>
</div>
</section>
<section class="section" id="facts" aria-labelledby="facts-title">
<div class="shell">
<h2 id="facts-title">Факты</h2>
{FAQ_HTML}
</div>
</section>
</main>
<footer>
<div class="shell">
<p>Локальный side-project репозитория adaptive-grok-build-pro. Индексация выключена, пока нет канонического HTTPS-домена.</p>
<p>Справки: <a href="https://ru.wikipedia.org/wiki/%D0%9A%D1%80%D0%B8%D0%BC%D0%B8%D0%BD%D0%B0%D0%BB%D1%8C%D0%BD%D0%BE%D0%B5_%D1%87%D1%82%D0%B8%D0%B2%D0%BE">русская Википедия о фильме</a>, <a href="https://www.imdb.com/title/tt0110912/">IMDb tt0110912</a>.</p>
</div>
</footer>
<script type="application/ld+json">{JSONLD}</script>
</body>
</html>
"""

PROJECT.mkdir(parents=True, exist_ok=True)
(PROJECT / "index.html").write_text(HTML, encoding="utf-8")
print("wrote", PROJECT / "index.html")
print("style", STYLE_HASH)
print("jsonld", JSON_HASH)
