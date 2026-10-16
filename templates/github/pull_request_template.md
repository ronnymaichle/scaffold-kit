## What and why

<!-- The change and the reason for it. Link the issue: Refs #12 -->

## How it was tested

<!-- Tests added or changed; manual checks. -->

## Security and privacy

<!-- Inputs, access rules, personal data touched; threat-model risks and how they are handled; trusted sources checked, with dates (docs/SOURCES.md). "None" if nothing applies. -->

## Scalability

<!-- New state and where it lives, new queries and their indexes, pagination, jobs, cache entries with TTL and invalidation. -->

## Database changes

<!-- Migrations: backward compatible (expand, migrate, contract)? Rollback plan. -->

## SEO

<!-- Public routes only: indexability, metadata, sitemap, structured data. -->

## Analytics

<!-- Events added or changed in the catalog. -->

## Screenshots

<!-- UI changes: light and dark mode, mobile and desktop. -->

## Checklist

- [ ] Tests written first; `check` and `check:security` pass (and `test:e2e` when a flow or public route changed)
- [ ] Folder docs and the code map updated
- [ ] New error codes and analytics events are in their catalogs
- [ ] Every user action has feedback (toast, inline error, banner or dialog)
- [ ] No temporary debug lines, no secrets
- [ ] New dependencies checked in the trusted sources: advisories, malicious-package reports, health and the exact name
- [ ] Design checks pass in both themes
- [ ] Affected docs updated (database, privacy, threat model, SEO, operations)
