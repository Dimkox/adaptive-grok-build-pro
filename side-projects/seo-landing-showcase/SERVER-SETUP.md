# Server setup

## Current preview state

Страница предназначена для локального или review-просмотра. Она остаётся
`noindex, nofollow`; production origin, canonical URL и sitemap не назначены.

Локальный сервер:

```bash
python3 -m http.server 4173 --directory side-projects/seo-landing-showcase
```

## Production boundary

Публикация требует отдельного авторизованного изменения после получения
канонического HTTPS origin. Тогда необходимо согласованно добавить canonical,
Open Graph URL, sitemap и robots policy, проверить все абсолютные URL и снять
`noindex` только после review.

Для production-сервера включите TLS, Brotli с gzip fallback, повторную
валидацию HTML на каждом запросе и заголовки:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

`index.html` следует revalidate, а версионированные статические файлы можно
кэшировать как immutable. Этот документ не выполняет deployment и не меняет
внешнюю инфраструктуру.
