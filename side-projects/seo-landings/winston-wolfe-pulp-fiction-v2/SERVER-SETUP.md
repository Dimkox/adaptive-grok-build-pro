# Server setup — Winston Wolfe landing v2

This tree is a **local, non-indexable** fan page. It is not a production host.

## Local preview

From the repository root:

```bash
python3 -m http.server 4174 --bind 127.0.0.1 --directory side-projects/seo-landings/winston-wolfe-pulp-fiction-v2
```

Open `http://127.0.0.1:4174/`.

## Indexing boundary

- HTML: `noindex, nofollow`.
- No canonical, no `og:url`, no `sitemap.xml`.
- `robots.txt` disallows `/` and has no `Sitemap:` line.
- First-party asset URLs are **relative** until a later change supplies a real HTTPS origin.

Enabling indexing requires a separate change with a verified canonical host, absolute URLs, and a re-check of JSON-LD `@id`s.

## Future host (not deployed by this change)

Copy the Apache/Nginx header, cache, MIME, HTTPS-redirect, CSP, and HSTS instructions from `.agents/skills/seo-landing/references/server-config.md`. Until a named host with `ngx_brotli` exists, treat compression as **gzip-only**. Do not claim Brotli. Do not enable HSTS preload.

Meta CSP is already on the page for local `http.server`. `frame-ancestors` is ignored in meta CSP; put it on the response header when a host exists.

## MIME types to verify on a future host

| Resource | Content-Type |
| --- | --- |
| HTML | `text/html; charset=utf-8` |
| PNG / AVIF / WebP / JPEG | matching image types |
| `robots.txt` | `text/plain; charset=utf-8` |

## Dependencies

Zero third-party runtime requests on first load. Wikipedia and IMDb appear only as ordinary `<a href>` navigation.
