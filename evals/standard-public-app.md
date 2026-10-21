# Standard: a community garden product

Checks the full plan and draft for a public product: tenancy planned from the start, safeguards on a small budget, a public landing page, a second language within a year, and the standard agent team. This is the idea of the first dry run (kit 2.5.0).

## Answers

- The idea: "Huerto", a web app for a neighbourhood community garden association in Valencia. Members reserve a plot for a season, log tasks (watering, weeding, harvest) on a shared task board, and see which plots are free. Admins approve new members, open seasons and assign plots. Later it will be offered to other garden associations, so treat it as a product. Core entities: association, member, plot, season, reservation, task. Users are adults (18+), mostly on phones. Personal data: name, email, optional phone. Members see each other's first names on the task board; nothing else is shown to others and nothing is public. No payments.
- Stack: knows TypeScript and Tailwind; no preferred framework; wants a recommendation.
- Data and auth: free tiers or self-hosting matter; Postgres is fine; sign-in with an email magic link; roles member and admin.
- Hosting: one cheap EU VPS with Docker Compose; no staging for now; transactional email through a cheap EU provider.
- Users: about 40 at launch, about 300 in 12 months (a few associations); no real-time or offline needs.
- Budget: at most 10 euros a month; fine with light server administration.
- Git: GitHub, solo developer, continuous releases.
- Visual identity: no logo; mood "earthy, calm, friendly, like a well-kept allotment"; wants color recommendations.
- Public pages and SEO: one public landing page that should appear in search in Spain; block AI training crawlers.
- Analytics: later.
- Interface languages: Spanish now, English within a year.

## The plan must

- choose the standard profile and say why: a product for several associations, with a public landing page
- make the app multi-tenant from the first migration (`association` as the tenant, a tenant filter in every repository, cross-tenant tests), with Row Level Security as a second layer on Postgres
- keep personal data in the EU (database, backups, logs) and choose an EU email provider
- sign in with an email magic link, with rate limits per IP and per recipient on the emails it sends
- define the roles `anonymous`, `member` and `admin` with their permissions, and a safeguards table whose budgets fit 10 euros a month
- make only the landing page indexable, for Spain, block AI training crawlers, and send noindex everywhere else
- plan i18n from the start, since English follows within a year
- leave analytics for later with the `noop` adapter, and show no cookie banner until a non-necessary adapter is on
- host on one EU VPS with Docker Compose, encrypted off-server backups with a tested restore, and the promote script; no staging for now
- build the draft: a top-down system diagram, the main-flow sequence diagram, the data model, example payloads for the main actions, two or three color proposals for an earthy, calm look, and phone-first mockups of the main screens
- list the features in build order in the roadmap, starting with sign-up and sign-in, each small enough for one PR
- list the standard agent roster and the agent guardrails, with the sandbox off by default
- say what waits for Phase 2 (the launch checklist)

## The plan must not

- propose payments, marketing pixels or an analytics provider now
- store personal data outside the EU
- propose staging now, against the user's answer
- ask the user any question
