## What and why

Roadmap: <!-- the feature's row in docs/ROADMAP.md, for example R7, or "none" -->

<!-- The change and the reason for it. Link the issue: Refs #12 -->

## How it was tested

<!-- Tests added or changed; manual checks. -->

## Security and privacy

<!-- Inputs, access rules, personal data touched; new entry points, permissions, limits, quotas and breakers (docs/security/SAFEGUARDS.md); threat-model risks and how they are handled; trusted sources checked, with dates (docs/SOURCES.md). "None" if nothing applies. -->

## Scalability

<!-- New state and where it lives, new queries and their indexes, pagination, jobs, cache entries with TTL and invalidation. -->

## Database changes

<!-- Migrations: backward compatible (expand, migrate, contract)? Rollback plan. -->

## SEO

<!-- Public routes only: indexability, metadata, sitemap, structured data. -->

## Analytics

<!-- Events added or changed in the catalog. -->

## Screenshots

<!-- UI changes: light and dark mode, mobile and desktop, from the designer's review and showing seeded data only; attach them with `gh pr create --attach` or drag them in. -->

## Checklist

- [ ] Within the PR size limit in `CONTRIBUTING.md`, or a part of a split the user approved
- [ ] Tests written first; `check` and `check:security` pass (and `test:e2e` when a flow or public route changed)
- [ ] Changed screens, flows and public routes checked in the running app (browser check, `docs/TESTING.md`)
- [ ] Folder docs and the code map updated
- [ ] New error codes and analytics events are in their catalogs
- [ ] Every user action has feedback (toast, inline error, banner or dialog)
- [ ] No temporary debug lines, no secrets
- [ ] New dependencies checked in the trusted sources: advisories, malicious-package reports, health and the exact name
- [ ] Design checks pass in both themes
- [ ] Affected docs updated (database, privacy, threat model, SEO, operations)
