# Docs/SEO research: existing landing preservation boundary

Route: `9f67efd2575c`
Repository head inspected: `ad6d23cc30c11e5ea51c388213f5ebdfe306fb56`
Repository tree: `878fd39838d43131b05dfa5e553be11260237342`
Observed: 2026-09-04 UTC

## Ruling

The public site cannot currently be bound to any accessible repository or
Desktop Codex source by content hash. The existing site is therefore an
**unknown live source that must be preserved**, not a target that a generated
directory may overwrite. Local generation and validation may proceed, but a
live materialization must stop until an authorized read-only snapshot and
compare-and-swap deployment precondition exist.

The user-provided Google SERP screenshot shows that the domain is indexed and
includes at least these search results:

- homepage title: `AI Dark Factory | Automatic Software Delivery`;
- roadmap title: `AI Dark Factory Roadmap | Capability Delivery`.

The anti-bot response seen by this automated audit is therefore an automation
observability gap, not evidence that Google has not indexed the site. Preserve
the exact indexed homepage and roadmap URLs, titles, descriptions, canonicals,
and redirect shapes when they are captured from the live source; do not infer
the roadmap slug from its title.

## Public behavior observed without bypass

Only ordinary unauthenticated `curl` HEAD/GET requests were made. No challenge
was solved, no browser identity or crawler was impersonated, and no external
write was attempted.

| Request | Observation |
| --- | --- |
| `http://therealaidarkfactory.online/` | `301` to the apex HTTPS root. |
| `http://therealaidarkfactory.online/preserve-me?x=1` | `301` to `https://therealaidarkfactory.online/preserve-me?x=1`; path and query were preserved. |
| `https://therealaidarkfactory.online/` | `200 text/html`, `server: openresty/1.31.1.1`, private/no-store caching, and a JavaScript anti-bot interstitial titled `One moment, please...`; the origin landing was not exposed. |
| `https://www.therealaidarkfactory.online/` | Also returned a `200` interstitial. A single canonical-host redirect is not observable at the edge. |
| `/robots.txt` and `/sitemap.xml` | Both returned the same class of `200 text/html` interstitial rather than an observable robots document or XML sitemap. Their origin contents cannot be declared missing, but their public machine-readable behavior failed this audit. |

The interstitial includes headless/browser checks and per-request values, so
its changing length or hash is not a source fingerprint. The observed HTTPS
edge response did not expose HSTS, CSP, `X-Content-Type-Options`, frame,
referrer, or permissions-policy headers. That finding is limited to the
challenge surface; it does not establish what headers the hidden origin sends.

DNS observations tie the current delivery path to Namecheap hosting without
proving the hidden document-root layout: the authoritative nameservers are
`dns1.namecheaphosting.com` and `dns2.namecheaphosting.com`, the apex A record
resolved to `162.0.215.194`, and `www` is a CNAME to the apex. Plain HTTP
identified LiteSpeed while the challenged HTTPS surface identified OpenResty,
so deployment must account for distinct hosting and edge layers and must not
assume that changing document-root files alone changes public behavior.

An internet search made during the audit did not return the target domain, but
that one query is not an indexing test and does not override the supplied SERP
evidence. Search Console and origin logs were neither available nor accessed.

## Accessible local-source findings

- `/home/pall/Desktop` contained no accessible files in the bounded search.
- A targeted safe-text search of Codex session/state references found the
  user's statement and the target URL, but no source directory, artifact hash,
  deployment manifest, or live-to-local provenance record. Secrets, auth data,
  shell snapshots, and credential files were excluded.
- Local project trees contain copies of the tracked SEO showcase. They are Git
  replicas, not independent evidence of the live site's source.
- The current showcase tree is
  `264b1e2ab7de3775d89a7f9dbd1730a131d74d07`, introduced for `index.html` by
  commit `abed410c5219a593403c8385e4a86b1d3c953a18`.
- Its current key SHA-256 values are:
  - `index.html`: `5ef1bb8037df7fe537d832d8e5c52924887b0ac18c486ec8efe9a9c2217f949e`;
  - `styles.css`: `8b15910433fc62294fb6b8376cf876b70bbe47d9f661be12b9f8b7ee54497065`.

The showcase is explicitly local/review-only: Russian content, `noindex,
nofollow`, no canonical, no `og:url`, no JSON-LD, no sitemap, no robots file,
and no external assets, forms, analytics, fonts, or runtime JavaScript. Its CTA
is inert. It is a useful static-layout/test fixture, but it is not evidence of
the public content and must not be copied to production unchanged.

Historical local evidence dated 2026-09-01 reports three Lighthouse 13.4.1
runs with median Performance 100, Accessibility 100, Best Practices 96, SEO
60, LCP 901.6 ms, CLS 0, and TBT 0. The SEO loss was expected from `noindex`;
the Best Practices loss was an undeclared favicon request. Those are historical
localhost lab measurements, not current-domain results, field Core Web Vitals,
or WCAG certification.

## Minimum production SEO and delivery contract

### Canonical and URL preservation

1. Adopt the apex only if the authorized live snapshot confirms it as the
   intended canonical host. Every alternate host, including `www`, must make
   one permanent `301` or `308` hop to that host while preserving path and
   query. HTTP-to-HTTPS already demonstrates the required preservation shape.
2. Every indexable page must have one absolute self-canonical. For the root it
   is `https://therealaidarkfactory.online/`; the roadmap keeps its captured
   indexed URL and self-canonical rather than being canonicalized to the root.
3. Canonical, `og:url`, sitemap `<loc>`, navigation, redirects, and post-deploy
   response URL must agree. Preserve existing URL/trailing-slash behavior or
   provide an explicit one-hop redirect map; do not normalize unknown URLs by
   guesswork.
4. Preserve the indexed titles and descriptions unless the closed landing spec
   explicitly approves replacements and records the old-to-new metadata diff.

### Robots, sitemap, and crawlability

1. Intended public pages must not retain the showcase's `noindex, nofollow`.
   Use `index, follow, max-image-preview:large, max-snippet:-1,
   max-video-preview:-1` once production readiness is approved.
2. `/robots.txt` must return `200 text/plain`, be readable without JavaScript,
   allow the public landing and its render-critical assets, and include
   `Sitemap: https://therealaidarkfactory.online/sitemap.xml`.
3. `/sitemap.xml` must return `200` with an XML MIME type and UTF-8 XML. Include
   only canonical, indexable, successful URLs, including the preserved
   homepage and roadmap. Values must be absolute and XML-escaped. Omit
   `<lastmod>` when a significant-change timestamp cannot be verified.
4. The site shell, robots file, sitemap, CSS, images, and other public static
   resources must be usable by ordinary GET/HEAD clients without a JavaScript
   challenge. The origin owner must change the WAF rule deliberately; this
   audit must not spoof Googlebot or solve the challenge. A claimed User-Agent
   alone is not an authentication signal.
5. Each public page must be reachable through crawlable HTML links and return
   its actual content with `200`, not a soft-404, interstitial, client-side
   redirect, or login. Validate a representative unknown path as a real 404.

### Structured data

- Add one valid JSON-LD `WebSite` entity on the homepage only after the site
  name and canonical URL are verified; its URL must equal the HTML canonical.
- Add `Organization` only if legal identity, public name, logo ownership, and
  contact facts are verified. Do not infer them from the domain or SERP title.
- Do not add self-serving ratings, `LocalBusiness`, `FAQPage`, breadcrumbs, or
  video schema without matching visible, complete, verified content. Schema
  must describe the page, not manufacture eligibility for a rich result.
- Parse the final JSON-LD, validate required properties, and ensure every local
  referenced asset exists in the immutable artifact.

### Performance, static delivery, and headers

- Keep the landing framework-free with no third-party dependency on first
  load. Target LCP below 2.5 s, INP below 100 ms, and CLS below 0.1. Before a
  release claim, run Lighthouse 13.4.1 three times against the real candidate
  origin and require median Performance, Accessibility, Best Practices, and
  SEO scores of at least 90. Report these as lab results, not field data.
- Give content-addressed CSS/images/fonts immutable caching. Keep HTML,
  `/robots.txt`, and `/sitemap.xml` revalidatable/non-immutable so corrections
  can propagate. Send exact MIME types and compression without transforming
  the attested bytes.
- Require at least `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`, and a restrictive
  `Permissions-Policy`. Stage CSP in report-only mode before enforcement.
  Enable HSTS only after all required hostnames are HTTPS-clean; do not request
  preload or `includeSubDomains` without separate operational approval.
- Re-run the existing 320/768/1280/1920 browser contract, keyboard/focus and
  reduced-motion checks, plus manual landmarks, heading order, alt text,
  contrast, zoom, and assistive-technology checks appropriate to changed UI.

## Non-overwriting preservation and sync strategy

1. **Snapshot before mutation.** Under separately authorized read access, the
   hosting owner exports the current document root, route/server configuration,
   redirects, response headers, CDN/WAF behavior, and an inventory containing
   path, size, MIME type, and SHA-256. Also capture the exact indexed homepage
   and roadmap URLs/metadata. Store the snapshot privately; do not ingest
   secrets or customer data into the repository.
2. **Fail closed on unknown provenance.** If that snapshot cannot be obtained,
   L5 may produce and attest a local immutable artifact but may not materialize
   it at the live domain. Public visibility does not grant overwrite authority.
3. **Stage by digest.** Build into a new content-addressed release directory or
   object prefix keyed by the attested artifact SHA. Never upload directly into
   the active document root and never use `rsync --delete` against an unknown
   tree.
4. **Allowlist owned paths.** A versioned manifest names only files owned by
   this release. Unknown files are retained. Treat `.well-known/`, server
   configuration, redirects, `robots.txt`, and `sitemap.xml` as protected:
   replace them only when their observed hash equals the snapshot's expected
   hash and the candidate explicitly owns them.
5. **Compare and swap.** Immediately before activation, repeat the inventory
   and abort on drift. Activate only the exact attested directory with an
   atomic release-pointer/vhost switch (or an equivalently atomic hosting
   primitive), after the route's human gate and exact external-write grant.
   On the observed Namecheap-hosted path, first prove which reversible primitive
   is actually available. If the plan only offers in-place FTP/file-manager
   overwrite, it does not satisfy this requirement; retain the local artifact
   until a versioned-directory plus atomic mapping/rename procedure is proven.
6. **Preserve rollback.** Keep the prior release and routing snapshot intact.
   Rollback changes only the pointer to the prior known-good release; it does
   not reconstruct or delete live files. Define health checks for homepage,
   roadmap, robots, sitemap, headers, canonical host, and representative 404.
7. **Verify, then retain evidence.** After activation, capture response hashes,
   redirect chains, canonical/metadata/schema, robots/sitemap, WAF-visible
   content, and three Lighthouse runs. Any mismatch triggers pointer rollback.

This strategy does not authorize deployment. The present task performed no
push, production mutation, form submission, WAF change, DNS change, or other
external write.
