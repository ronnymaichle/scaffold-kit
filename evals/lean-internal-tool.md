# Lean: an internal equipment-loan tool

Checks that a small internal tool gets the lean profile's reductions without losing the defaults that are never relaxed, and that the plan stays short.

## Answers

- The idea: "Préstamos", an internal web tool for a six-person video production company in Madrid. Staff record which camera, lens or light each person has borrowed, since when and when it is due back, and see what is available. Core entities: item, person, loan. All users are adult employees. Personal data: names and work emails; nothing is shown outside the company, and nothing is public. No payments and no paid services.
- Stack: knows a little Python, no preference; wants a recommendation.
- Data and auth: free tiers or self-hosting matter; any database is fine; sign-in with the company's Google Workspace accounts only. Roles: staff and one admin.
- Hosting: the company already has a small VPS; Docker Compose is fine; no staging. The app sends no email to users.
- Users: 6 now, perhaps 8 in a year; no real-time or offline needs.
- Budget: at most 5 euros a month; little server administration.
- Git: GitHub, solo developer, continuous releases.
- Visual identity: the company's orange `#E4572E`, no logo; plain and quick to use.
- Public pages and SEO: none; nothing may appear in search engines.
- Analytics: none.
- Interface languages: Spanish only.

## The plan must

- choose the lean profile and say why: an internal tool for a handful of known users
- keep the security defaults, tests first, folder docs, the error catalog and the three workflows
- restrict sign-in to the company's Google Workspace domain and put every page behind sign-in
- send `X-Robots-Tag: noindex, nofollow` on every response, with no sitemap or SEO work
- leave out staging, load tests, the analytics module and i18n
- limit end-to-end tests to sign-in and the main task
- keep the safeguards (rate limits, quotas, breakers, the security event catalog), sending high and critical alerts to the admin by email, the only email the app sends
- include off-server backups with a tested restore
- list the lean agent roster (the lead with the `test-runner`, the `reviewer`, and the `designer` at planning time only) and the agent guardrails
- list the features in build order in the roadmap, starting with sign-in, each small enough for one PR
- generate one theme from `#E4572E` and recommend one look
- stay short: one or two lines per item

## The plan must not

- propose staging, load tests, an analytics provider, marketing pixels or a cookie banner
- turn on the agent sandbox by default or propose agent teams
- ask the user any question
- replace `#E4572E` with an invented brand color
