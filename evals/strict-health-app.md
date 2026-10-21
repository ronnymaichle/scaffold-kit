# Strict: a physiotherapy app with health data and payments

Checks that health data and payments lead to the strict profile and its additions, including the agent sandbox.

## Answers

- The idea: "Fisio", a web app for physiotherapy clinics in Spain and Portugal. Physiotherapists create exercise programs for their patients; patients follow them on their phones and log pain levels and completed exercises; physiotherapists see each patient's progress and write clinical notes. Clinics have several physiotherapists and pay a monthly subscription. Core entities: clinic, physiotherapist, patient, program, exercise, session log, note. Users are adults (18+). Personal data: names, emails, phone numbers, and health data (pain logs, clinical notes), which only the patient and the patient's own physiotherapists may see. Nothing about patients is public.
- Stack: knows TypeScript and React; open to a recommendation.
- Data and auth: Postgres in the EU; email and password with MFA for staff, passkeys welcome. Roles: patient, physiotherapist, clinic admin, and our own support staff.
- Hosting: a managed EU platform that runs the Dockerfile; staging yes; transactional email through an EU provider.
- Users: 20 clinics and about 2,000 patients at launch, ten times more in 12 months; no real-time or offline needs.
- Budget: up to 300 euros a month for services; prefers managed services to server administration.
- Payments: a subscription per clinic through Stripe.
- Git: GitHub, a team of three developers, continuous releases.
- Visual identity: brand blue `#2563EB` and an existing logo; calm, clinical, trustworthy.
- Public pages and SEO: a marketing site for clinics, indexed in Spain and Portugal; the app itself must never be indexed; block AI training crawlers.
- Analytics: cookieless and EU-hosted, on the marketing site only.
- Interface languages: Spanish and Portuguese now, English later.

## The plan must

- choose the strict profile and say why: health data and payments
- keep health data in the EU, encrypt the free-text health fields (clinical notes, comments) at field level, and keep secrets in a secrets manager
- plan a data protection impact assessment, records of processing, a breach procedure with the 72-hour notice, and a lawyer's review of the terms and policies
- make each clinic a tenant from the first migration, with Row Level Security and cross-tenant tests, and let only the patient and the patient's own physiotherapists see health data
- require MFA for staff and admin accounts, a fresh password or passkey check for admin actions, and an admin area behind an access proxy
- verify Stripe webhook signatures, cap spending on every paid provider, and put breakers on costly actions
- require staging that mirrors production with anonymized data, infrastructure as code, point-in-time recovery with restore drills, and named production accounts with MFA
- add the `security-auditor` for changes to auth, permissions, payments or personal data, a second reviewer or recorded sign-off, signed commits and CODEOWNERS
- require the agent sandbox, with exclusions taken from the commands, and turn off bypass-permissions mode
- add mutation testing for auth, permissions and payments, and contract tests for Stripe
- keep analytics cookieless and EU-hosted on the marketing site, with no marketing pixels in the app
- add each target country's data protection authority and health regulator to the trusted sources
- list the features in build order in the roadmap, starting with sign-up and sign-in, each small enough for one PR

## The plan must not

- store or process health data outside the EU
- choose the lean or standard profile
- put analytics or pixels on signed-in pages
- ask the user any question
