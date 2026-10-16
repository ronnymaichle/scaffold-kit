# Public web: SEO and analytics

Becomes `docs/SEO.md` (rendering, the route list, metadata, crawl rules, sitemap, structured data, URLs and language URLs, performance) and `docs/ANALYTICS.md` (the analytics module, adapters and event conventions). Cookie consent lives in `docs/PRIVACY.md`. An app without public pages keeps only the noindex rules.

## SEO

Applies to every route the public can reach without signing in.

- Rendering: public pages are server-rendered or prerendered, with the real content in the HTML. Signed-in app screens can stay client-heavy and are `noindex`.
- `docs/SEO.md` lists every route as indexable or `noindex`, with its title pattern, sitemap source and structured-data type. Private, account, admin, API and dev routes are `noindex` and protected by auth; robots.txt is not access control and never lists secret paths.
- One shared head component sets, for every indexable page: a unique `<title>` (~50-60 characters), a meta description (~150-160), an absolute canonical URL, `<html lang>`, Open Graph and Twitter card tags with a 1200x630 image (generated and cached per content page when the content is user-created), the favicon set and the web app manifest.
- `robots.txt` is served from a route. In production it allows public paths, disallows app, API and dev paths, applies the user's AI-crawler policy (allow, or block training crawlers such as GPTBot, ClaudeBot, Google-Extended and CCBot) and links the sitemap. Non-production environments send `X-Robots-Tag: noindex, nofollow` on every response and sit behind basic auth; they do not use `Disallow`, because it hides the noindex from crawlers.
- `sitemap.xml` is generated from the database for published content, with `lastmod`, split into a sitemap index beyond 50,000 URLs, and cached.
- Structured data: JSON-LD with matching schema.org types (Organization, WebSite, Place, Article, BreadcrumbList), validated with Google's Rich Results Test and serialized safely (escape `<`), since it often contains user content.
- URLs: stable, lowercase, readable slugs; one canonical host (www or not, and HTTP redirected to HTTPS at the proxy); one trailing-slash policy; 301 redirects when a URL changes; real 404 and 410 status codes.
- Languages: the locale in the URL path (`/es/`, `/en/`) and `hreflang` alternates, including `x-default`, on every indexable page and in the sitemap. Never redirect automatically by IP or browser language; offer a language switcher.
- Performance is a ranking factor: Core Web Vitals targets (LCP < 2.5s, INP < 200ms, CLS < 0.1); responsive AVIF or WebP images with explicit width and height, lazy-loaded below the fold; preloaded, subset fonts with `font-display: swap`; minimal JavaScript on public pages.
- Content structure: one `h1` per page, logical heading order, descriptive link text, alt text.
- Enforcement: e2e tests check that every indexable route has a title, description, canonical and Open Graph tags, that robots.txt and sitemap.xml are valid, and that non-production responses carry the noindex header. Lighthouse CI budgets (Phase 2) cover performance, SEO, accessibility and best practices.
- After launch: Google Search Console and Bing Webmaster Tools verified and the sitemap submitted; crawl errors are checked after changes to public routes (Release workflow).

## Analytics and marketing

Built in from Phase 1; the provider is optional.

- One analytics module (for example `$lib/analytics`) exposes `page()` and `track(event, props)`. Components and services call only this module, never a provider SDK.
- Provider adapters sit behind one interface: `noop` (the default) and, as chosen, `plausible`, `umami`, `posthog`, `ga4` and ad pixels (Meta, Google Ads, LinkedIn). Configuration picks the providers (`ANALYTICS_PROVIDERS` plus their keys), several can run at once, and adding, switching or removing one means changing configuration and one adapter file. With `noop`, nothing loads and no third-party request is made.
- Each adapter declares its consent category (none for cookieless analytics, otherwise `analytics` or `marketing`) and the domains it needs. The CSP and the consent banner (`docs/PRIVACY.md`) are built from the enabled adapters.
- The event catalog is typed in code (for example `$lib/analytics/events.ts`) and is the only list of events: `object_action` names in snake_case (`marker_viewed`, `marker_created`, `comment_posted`, `signup_completed`), each with its allowed properties, its consent category and a comment stating the question it answers. Uncatalogued events fail type checking. `docs/ANALYTICS.md` explains these conventions and links to the catalog instead of copying it.
- No personal data in events: no emails, names, free text, precise locations or raw user ids; use coarse values (city, category) or leave them out.
- Page views fire on client-side navigations as well as full page loads. UTM parameters and the referrer are captured on landing and attached to conversion events.
- Key conversions (signup, publish, purchase) are tracked on the server through the same module, so ad blockers do not drop them; UI interactions are tracked in the browser.
- Provider scripts load asynchronously, and only when enabled and consented. Cookieless providers can use an optional first-party proxy to reduce ad-blocker loss.
- Recommendation order: cookieless analytics (Plausible, Umami) for views, referrers and simple goals without a banner; PostHog (EU cloud or self-hosted) for funnels, retention and A/B tests; Google Analytics 4 when integrating with Google Ads, accepting the consent banner and Consent Mode.
- Tests: unit tests with a recording adapter assert that key flows emit the expected events and properties; e2e checks that `noop` makes no third-party analytics requests.

## Lean profile

Internal tools and prototypes: everything except sign-in sits behind auth, every response carries `X-Robots-Tag: noindex, nofollow` (robots.txt does not disallow, for the reason above), and there is no sitemap, structured data or analytics module until the app goes public, which is an upgrade-mode change.

## Strict profile additions

- Analytics is self-hosted or EU-hosted under a data processing agreement.
- No marketing pixels on signed-in pages or on pages that show sensitive data (health, finance, children's data).
