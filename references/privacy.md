# Privacy, consent and legal documents

Becomes `docs/PRIVACY.md`. Applies whenever the app serves people in the EU (GDPR and ePrivacy) and is good practice everywhere. Check the target country's regulator guidance (Spain: AEPD; France: CNIL). This is engineering guidance, not legal advice.

## Data protection

- `docs/PRIVACY.md` keeps a data inventory: which personal data is collected, why (purpose and legal basis), where it is stored, which providers process it, and how long it is kept.
- Collect the minimum. Store EU users' personal data in an EU region: the database, backups, uploaded files and logs. A service that only passes traffic through, such as an edge proxy or CDN that terminates TLS, may be outside the EU when it is listed as a processor with a data processing agreement and a transfer basis (an adequacy decision such as the EU-US Data Privacy Framework, or standard contractual clauses), and it never caches personal data. The plan names an EU-based alternative next to it, so the user chooses knowingly. Sign data processing agreements with every provider.
- Users can export their data and delete their account. Deletion cascades to their content, media, caches, search index and sitemap entries; backups age out according to the retention policy. Records the law requires someone to keep (for example clinical or invoicing records) are kept for that period with access restricted, deleted when it ends, and named in the privacy notice.
- Retention periods are defined for logs, the audit log, backups and deleted content.
- User-generated content is public and indexable only when its owner publishes it. Precise locations are personal data: offer approximate locations where that matters. Deleted public content returns 410 and leaves the sitemap.
- Any external service that processes personal data, including an AI service reading logs, is listed as a processor.
- In a business-to-business app where each customer organization (a clinic, a school, an employer) decides what personal data goes in, the customer is the controller and the app its processor: a data processing agreement with each customer lists the sub-processors, the app acts only on the customer's instructions, and the customer's data is returned or deleted when the contract ends.

## Legal documents and terms

- Public apps publish, each at a stable URL linked from the footer and the sign-up form: the terms of service, the privacy policy, the cookie policy, and any legal notices the target countries require (Spain, for example, requires a legal notice with the owner's details). Apps that take payments add pricing, cancellation and refund terms that follow consumer law in the target countries (in the EU, for example, the 14-day right of withdrawal and its exceptions for digital content).
- The terms cover at least: who may use the app and the minimum age, account rules, acceptable use and prohibited content, who owns user content and the licence the app needs to display it, suspension and termination, liability limits, the governing law, and how users are told about changes.
- Each document is versioned: its text lives in the repository with a version and an effective date, and earlier versions stay readable at their own URLs. Each change is marked material (it changes users' rights or obligations) or editorial (typos, clarifications).
- Accepting the terms is an explicit action at sign-up: an unticked checkbox, or a button that says what it does ("Create account and accept the terms"), next to links to the terms and the privacy policy. Marketing email needs its own unticked opt-in and is never bundled with the terms.
- The privacy policy is information, not a contract: users are shown it, not asked to agree to it, because consent is the legal basis only for the specific processing that asks for it.
- Acceptances are recorded on the server in an append-only table (user, document, version, accepted at), without IP addresses or user agents unless the target countries' law requires them. The table is in the data inventory, with its retention.
- Material changes are announced in advance by email and in the app, with the notice period the terms set (for example 30 days). After the effective date, signed-in users who have not accepted the current version see a screen that summarizes the changes and lets them accept, or export their data and delete the account. Editorial changes need no new acceptance.
- Minimum age: the terms set it from the target countries' rules (GDPR lets each EU country set the age of digital consent between 13 and 16, for example 14 in Spain; COPPA in the US covers children under 13), and sign-up asks users to confirm it, or asks for a birth date where the law or the audience requires one. An app meant for children needs verifiable parental consent and the strict profile.
- Apps that host user content state their content rules in the terms, put a report action on every piece of public content, follow a takedown process with response times, and publish a contact point. Check whether the EU Digital Services Act applies and which notice and statement-of-reasons duties it brings.
- Tests: sign-up fails without accepting the terms; a new material version shows the acceptance screen to existing users and records their acceptance; earlier versions stay reachable; the marketing opt-in stays off unless ticked.

## Cookie consent

- Categories: necessary (always on: session, CSRF, the consent record, preferences the user explicitly set such as theme and language), analytics, marketing. Add functional only if a feature needs third-party storage (for example embedded videos).
- With only necessary cookies and cookieless analytics, no banner is shown (the cookie policy still lists them). The banner appears automatically once any enabled analytics adapter or embed declares a non-necessary category, so adding or removing a provider adds or removes the banner (`docs/ANALYTICS.md`).
- First layer: short plain-language text with "Accept all", "Reject all" and "Customize" of equal visual weight, and a link to the cookie policy. No pre-selected options and no dark patterns.
- Customize panel: one toggle per category with a plain-language description and the providers in it, non-necessary toggles off by default, and "Save choices".
- Nothing non-necessary loads before consent (scripts, pixels, cookies, embeds); without JavaScript the default is reject. Third-party embeds show a click-to-load placeholder until their category is accepted.
- The choice is stored in a first-party cookie (categories, policy version, timestamp) that the server reads, so pages render without disallowed scripts. Where proof of consent is needed, choices are also recorded on the server without personal data.
- A persistent "Cookie settings" link (for example in the footer) reopens the panel; withdrawing is as easy as giving; on withdrawal, scripts stop and their cookies are deleted where possible.
- Ask again when categories, providers or the policy version change, and periodically as the regulator recommends.
- Google tools (GA4, Google Ads) receive the same consent state through Google Consent Mode v2. Serving Google ads in the EEA requires a Google-certified consent platform; use one instead of the built-in banner in that case.
- Build: a small banner in the design system (themed, translated, keyboard and screen-reader accessible) or a maintained open-source library (for example vanilla-cookieconsent); verify current options with a web search.
- Tests: e2e checks that before consent and after "Reject all" no non-necessary cookies are set and no analytics or marketing requests are made, that "Accept all" and per-category choices load only what was accepted, and that withdrawing consent stops tracking.

## Lean profile

Internal tools for known users skip the public terms and the acceptance flow unless the organization asks for them; the data inventory, retention and the privacy notice stay.

## Strict profile additions

- A lawyer reviews the terms, the privacy policy and the cookie policy before launch and after every material change.
- A data protection impact assessment (DPIA) when processing sensitive data or monitoring people at scale.
- Records of processing activities kept current.
- A breach response procedure: assess, contain, notify the supervisory authority within 72 hours when required, inform affected users.
