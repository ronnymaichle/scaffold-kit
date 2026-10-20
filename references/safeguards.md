# Safeguards: limits, spending caps, breakers and responses

Becomes `docs/security/SAFEGUARDS.md`: every limit, quota, spending cap, circuit breaker and security event the app has, with the automatic response and who is notified. Keep what applies to the stack, the clients and the profile. Roles and permissions are in `docs/ARCHITECTURE.md` (Auth); the threat model is in `docs/security/THREAT-MODEL.md`.

The goal: no person, bug or leaked key can read data they should not see or run up a large bill, and when something gets past one safeguard, the next one stops the damage on its own and tells the people who can fix it.

## Everything is enforced on the server

- Every permission check, limit, quota and breaker runs on the server or in the database's rules, never only in the client. Any web page or iOS or Android app can be modified, or replaced by a script that calls the API directly, so a check in the client helps the user but protects nothing.
- Every server entry point runs its checks through one `guard()` helper per framework (session, permission, rate limit, breaker), so each check is one line and a missing one shows in review. Several entry points do not look like endpoints but are (Framework entry points, below).
- A request a safeguard stops has no effect: the check runs before the work, and the work runs in a transaction, so nothing is half-written. The response is a catalogued error (`RATE_LIMITED`, `QUOTA_EXCEEDED`, `FEATURE_DISABLED`, `FORBIDDEN`) that does not reveal which rule or threshold was hit.

## Layers

Each layer catches what the one before it misses:

1. Limits per request: rate, size and time.
2. Quotas per user and per tenant.
3. A circuit breaker per feature: a budget counted across everyone, background jobs included.
4. The provider's own spending cap or budget action. Only this layer catches a leaked key used outside the app.

## The safeguards table

`docs/security/SAFEGUARDS.md` keeps one table with a row for every entry point and every costly or sensitive action. Each feature that adds one adds its row in the same PR. For example:

| Action or route | Permission | Rate limit | Quota | Breaker budget | Events |
|---|---|---|---|---|---|
| `POST /api/v1/markers` | `marker.create` (verified `user`) | 30 per minute per user | 500 markers per user | none | `RATE_LIMITED` |
| Photo caption (AI) | `caption.generate` (verified `user`) | 10 per minute per user | 200 per day per user | 3 EUR per hour, 20 EUR per day | `QUOTA_EXCEEDED`, `BREAKER_TRIPPED` |
| Data export | `account.export` | 2 per hour per user | 5 per month per user | 200 exports per day | `EXPORT_REQUESTED` |

## Budgets (scaffold-time)

The plan lists each feature that costs money per use (AI, SMS, email, maps, image processing, storage and egress), its provider, and how it is billed. From the user's monthly budget it proposes each provider's budget, the starting quotas and the breaker budgets. Until real use is known they start low; they are reviewed after launch.

## Limits

- Rate limits work at two levels: the edge proxy's rate rules per IP for sign-in and sign-up (`docs/security/THREAT-MODEL.md`), and the app's limiter on every entry point: per client IP for anonymous requests (the address from the trusted proxy's header), per user or API token once signed in, and per tenant in multi-tenant apps.
- Costly and sensitive actions get their own, tighter limits: sign-in, sign-up and password reset (with backoff), anything that sends email or SMS, uploads, search, exports, and calls to paid APIs.
- Anything that sends to an address the caller chooses (invites, share by email, SMS codes) is also limited per recipient, so the app cannot be used to flood one person. SMS goes only to the countries the app serves, because SMS pumping fraud sends codes to premium-rate numbers at the app's expense.
- A rejected request gets 429 with `Retry-After` and the catalogued `RATE_LIMITED` error, and is logged as a security event.
- Every request has size limits (body, upload, page size), and every external call and database query has a timeout (for example Postgres `statement_timeout`), so one slow dependency cannot tie up every instance.
- Limiter counters live in the shared store behind the rate-limiter module (`docs/SCALING.md`), so limits hold across instances.

## Quotas

- Anything that costs money or storage has a quota per user and, in multi-tenant apps, per tenant: emails and SMS sent, AI calls or tokens, storage used, exports. Quotas reset daily or monthly; a plan or a role may raise them.
- The service checks the quota before the costly call and records the use in the same place: reserve, call, then confirm or release. A failure between the steps never gives free use.
- Costly features need a verified account (a verified email, and a payment method where the feature is paid), because unverified sign-ups are the cheapest way to multiply free quotas. `anonymous` gets no costly feature unless the plan gives it its own small budget and breaker.
- Users see their remaining quota where they use the feature, and a clear message when it runs out (`QUOTA_EXCEEDED`).

## Spending caps

Check each provider's current options in the trusted sources before relying on them (`docs/SOURCES.md`), and record them in the hosting ADR.

- Every paid or metered provider (hosting, database platform, object storage and egress, email, SMS, maps, AI APIs) has a monthly budget with alerts at 50%, 80% and 100%, sent to the admins' alert channels.
- Where the provider offers a hard cap or an automatic pause, it is on (for example Vercel's Spend Management pauses production at the set amount, and AI providers have spend limits per workspace or project). Where budgets only alert (for example Google Cloud and most Firebase services), the budget's notification triggers a small function that trips the matching breakers, or, as the last resort, disables billing; what that does to the app is written next to it.
- Autoscaling and serverless functions have a maximum instance count, a concurrency limit and a timeout, so a traffic flood or a loop cannot grow the bill without bound.
- API keys that must ship to a client (maps, Firebase configuration) are restricted to the app's domains, bundle id or package name and signing certificate, limited to the APIs they need, and given quotas in the provider's console. Secret keys never ship to a client.

## Feature circuit breakers

The last safeguard inside the app, for what limits and quotas miss: the same attack spread over many accounts or IP addresses, a bug or a job that loops, retries piling up after an outage, or a webhook storm. Each of these can run up a bill while every single caller stays under its limit.

- Every paid provider is called through one metered module (for example `$lib/server/paid/ai.ts`), which checks the feature's breaker before each call and records the call's usage and cost after it. A lint rule bans importing the provider's SDK anywhere else, so nothing bypasses the meter.
- Each costly feature has a budget per hour and per day, in money or units, counted across all users and background jobs. Admins are notified at 50% and 80%; at 100% the breaker trips. Once there is enough history, it also trips when an hour's use is far above normal (for example five times the same hour a week earlier), which stops a fast attack long before the daily budget is spent.
- A tripped breaker stays tripped until an admin with the `features.manage` permission resets it and writes down why. It never resets itself, because whatever tripped it is still there until someone has looked. Trips and resets go into the audit log.
- A breaker covers one feature, one route, or the whole app in read-only mode (sign-in and reading still work; every write and costly action returns `FEATURE_DISABLED`). Admins can trip any of them by hand.
- While a breaker is tripped, admins can still use the feature to test a fix. Everyone else gets `FEATURE_DISABLED` with a "temporarily unavailable" message; their data stays as it was and nothing is charged. Clients read feature states from the server when they start and whenever they get `FEATURE_DISABLED`, so web, iOS and Android hide what is off.
- Breakers fail closed: when the usage counter or the breaker state cannot be read, costly calls are refused.
- The same mechanism guards data: a route that returns far more records in an hour than normal (exports, lists, search) trips and stays off until an admin has reviewed it.
- Breaker states live in the database or the shared store, never in instance memory, so every instance sees a trip at once. Budgets and thresholds live in one configuration file in the repository.

## Data-leak safeguards

These add to the rules that already prevent leaks: deny by default and ownership checks (`docs/security/THREAT-MODEL.md`), DTOs only, tenant filters and Row Level Security (`docs/DATABASE.md`), `Cache-Control: private, no-store` on personalized responses (`docs/ARCHITECTURE.md`), and redacted logs (`docs/LOGGING.md`).

- Reads are limited like writes: list, search and detail endpoints have per-user rate limits and a maximum page size, so scraping is slow, and a user reading far more distinct records than normal raises `BULK_READ_SUSPECTED`.
- Exports and bulk downloads need their own permission and a fresh password or passkey check, count against a quota, run as a background job that delivers to the requester's verified email or account, go into the audit log, and notify admins above a size set in the configuration.
- Sign-in, sign-up and password reset never reveal whether an account exists: the same message and the same timing either way.
- A request for another user's or tenant's record gets the same 404 as a missing one, and is logged as `AUTHZ_DENIED`.
- Admins see only what support needs; opening a user's private data goes into the audit log with a reason.
- Nothing shipped to a client is secret: no keys, tokens or internal URLs in web bundles or mobile binaries.

## Security events and responses

Security events are catalogued like errors: one typed file in code (for example `$lib/server/security/events.ts`) lists each event with its severity, threshold, automatic response and who is notified, and unknown events fail type checking. Thresholds live in the same configuration file as the budgets.

| Severity | Examples | Automatic response | Who is notified |
|---|---|---|---|
| low | one failed sign-in, one denied request, one rate-limit hit | logged | nobody |
| medium | repeated failed sign-ins or rate-limit hits, failed bot challenges | slowed down, then blocked for a short time that grows with each repeat; a bot challenge where the client has one | admins, in a daily digest |
| high | repeated requests for other users' or tenants' records, bulk reads, a costly feature's quota used up, a role change, a burst of invalid webhook signatures | the actor (user, token or IP) blocked for a time that grows with each repeat, and signed out everywhere | admins, at once |
| critical | spending past a budget, a breaker trip, a mass export, signs of a taken-over account (for example an admin signing in from a new country and then changing roles) | the breaker trips or the app goes read-only; a taken-over account is locked until an admin reviews it | admins, at once, on every channel |

- Blocks expire on their own and grow with each repeat (for example 15 minutes, 1 hour, 24 hours). Only critical events, and signs that an account was taken over, lock an account until an admin reviews it; locking on high events would let an attacker lock real users out on purpose.
- Admins lift blocks and locks in the admin area, and every lift goes into the audit log.
- Every event is logged (`docs/LOGGING.md`) and written to the audit log (`docs/security/THREAT-MODEL.md`).

## Notifications

- Security alerts go to everyone holding the `security.alerts.receive` permission, so any role can be given it; the first admin has it.
- Channels: email through the mail module and an alert inbox in the admin area, plus a chat channel (for example Telegram or Slack) or push notifications when the plan adds one. Critical alerts go to every channel; when a delivery fails, the next channel is tried.
- Alerts are grouped (one per event type and actor in a time window) and rate-limited, so an attack cannot flood the admins or use up the email quota; the digest lists what was grouped.
- Users are told about events on their own account: a sign-in from a new device, a changed password or email, a role change, a block or lock, and an export.
- Each event with an automatic response and each breaker has a runbook entry in `docs/OPERATIONS.md`: what it means, how to check, and how to reset safely. Infrastructure alerts (uptime, disk, backups, certificates) are there too.

## Framework entry points

Each of these is a public HTTP endpoint, reachable without the page that normally calls it, so each runs its own checks:

- SvelteKit: `load` in `+page.server.ts` and `+layout.server.ts`, form actions, `+server.ts`, and remote functions (`query`, `form`, `command`). `hooks.server.ts` sets the session and applies rate limits and route breakers; each `load` and action still checks its permission itself, because a layout's `load` does not protect its child pages (they run in parallel, and a page's data can be requested on its own). Universal `+page.ts` and `+layout.ts` also run in the browser, so they hold no secrets and make no access decisions.
- Next.js (App Router): Route Handlers (`route.ts`), every Server Action (a `'use server'` function is a public POST endpoint, even when no button shows it), and Server Components that read data. Middleware (`proxy.ts` from Next.js 16) does only coarse checks such as redirects and rate limits and is never the only access check, because middleware has been bypassed before (CVE-2025-29927). Server modules start with `import 'server-only'`; variables prefixed `NEXT_PUBLIC_` are public; only DTOs are passed to Client Components, because their props are written into the page; personalized data is never cached for everyone.
- APIs (Hono, Elysia, FastAPI, Go and others): every route goes through the guard.
- Platforms: callable functions (Firebase Functions, Supabase Edge Functions) check the caller themselves, and direct database access from clients is governed by tested security rules or Row Level Security (`docs/ARCHITECTURE.md`).
- Background jobs and incoming webhooks call paid providers through the metered modules too, so they count toward the breakers.
- The route coverage test (`docs/TESTING.md`) fails when an entry point has no entry in the route access list.

## Website costs

- The host's spending controls are on: a hard limit or pause where offered, alerts otherwise (Spending caps).
- Image optimization (Next.js `next/image`, or a host's or CDN's image service) accepts only the app's own sources (in Next.js, `images.remotePatterns`) and a fixed set of sizes, so nobody can use it as a free image service at the app's expense.
- Middleware or proxy code never runs for static files (in Next.js, its `matcher`), because on serverless hosts every run is billed.
- Public pages are cached at the edge (`docs/ARCHITECTURE.md`, Caching), so bots and traffic spikes hit the cache, not billed functions. Pages rebuilt in the background (ISR) have a revalidation time that fits how often they change, and on-demand revalidation requires auth.
- Public forms (contact, newsletter, sign-up) have a honeypot, a bot challenge, rate limits and a per-recipient limit (`docs/security/THREAT-MODEL.md`), because each submission can send a paid email.
- Large media is served from object storage through a CDN, private files through short-lived signed URLs, so heavy downloads never run through billed functions.
- A site without accounts has only `anonymous`, plus `admin` if it has a CMS; breakers still guard anything that costs money, such as forms, search and AI.

## Clients: web, iOS and Android

The rules above apply to every client, because they run on the server. On top of them:

- App attestation as an extra signal, never a replacement for auth or limits: Firebase App Check, Apple App Attest, Google Play Integrity, and on the web a bot challenge (for example Cloudflare Turnstile). Once it is rolled out to every supported app version, costly endpoints reject requests without a valid attestation.
- No secrets in app bundles or binaries; the public keys that must ship are restricted as in Spending caps.
- Mobile apps keep tokens in the iOS Keychain or in storage encrypted with an Android Keystore key, never in plain preferences; the web keeps sessions in httpOnly cookies (`docs/ARCHITECTURE.md`, Auth).
- The API is versioned (`/api/v1`), and the server holds a minimum supported app version. Raising it makes older builds show an update screen, which stops a build that is being abused or leaks data.
- Clients read feature states from the server, so a tripped breaker hides the feature in every app at once.

## Tests

- Each rate limit and quota: the last allowed request passes; the next is rejected with the catalogued error and logs the event.
- Each breaker: a call under the budget passes; the call that reaches the budget trips the breaker, notifies admins and returns `FEATURE_DISABLED`; the feature stays off for everyone but admins until an admin resets it; costly calls are refused when the counter cannot be read.
- Each security event: one occurrence below the threshold changes nothing; reaching it triggers the response and the notification, grouped as configured; a block expires after its time.
- The lint rule that keeps provider SDKs inside the metered modules runs in `check`.
- The permission matrix and route coverage tests are in `docs/TESTING.md`.

## Lean profile

Everything except the notification channels: limits, quotas, spending caps, breakers, the event catalog and the client rules all apply. Alerts go by email only, for high and critical events, with no digest and no alert inbox.

## Strict profile additions

- Every admin action asks for a fresh password or passkey check, and the admin area is reachable only through an access proxy or an IP allowlist.
- Lifting a lock after a suspected account takeover, and resetting a breaker after a critical event, need a second admin's approval.
- Budgets, quotas and thresholds are reviewed every quarter against real use.
