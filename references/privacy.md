# Privacy and cookie consent

Becomes `docs/PRIVACY.md`. Applies whenever the app serves people in the EU (GDPR and ePrivacy) and is good practice everywhere. Check the target country's regulator guidance (Spain: AEPD; France: CNIL). This is engineering guidance, not legal advice.

## Data protection

- `docs/PRIVACY.md` keeps a data inventory: which personal data is collected, why (purpose and legal basis), where it is stored, which providers process it, and how long it is kept.
- Collect the minimum. Host EU users' data in an EU region and sign data processing agreements with providers.
- Users can export their data and delete their account. Deletion cascades to their content, media, caches, search index and sitemap entries; backups age out according to the retention policy.
- Retention periods are defined for logs, backups and deleted content.
- User-generated content is public and indexable only when its owner publishes it. Precise locations are personal data: offer approximate locations where that matters. Deleted public content returns 410 and leaves the sitemap.
- Any external service that processes personal data, including an AI service reading logs, is listed as a processor.
- Publish a privacy policy, a cookie policy and any legally required notices for the target countries (Spain, for example, requires a legal notice with the owner's details).

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

## Strict profile additions

- A data protection impact assessment (DPIA) when processing sensitive data or monitoring people at scale.
- Records of processing activities kept current.
- A breach response procedure: assess, contain, notify the supervisory authority within 72 hours when required, inform affected users.
