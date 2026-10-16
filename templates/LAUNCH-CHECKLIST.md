# Launch checklist (Phase 2)

Everything here is finished before real users arrive. Each item is its own `chore` or `ci` PR through the Feature workflow, done between features; every feature report states the progress. Items that do not apply to the profile are deleted when this file is created; tick the rest as their PRs merge.

## Infrastructure and delivery

- [ ] Servers provisioned and hardened (`docs/security/THREAT-MODEL.md`, Servers and deployment); staging per the agreed plan (`docs/DEPLOYMENT.md`)
- [ ] Deploy pipelines: staging on merge to `main` (if staging is used), production on `v*` tags with manual approval; first tag `v0.1.0`
- [ ] Release automation (release-please or git-cliff)
- [ ] Encrypted, off-server daily database backups with a tested restore; the production database reachable only from the app's network
- [ ] Promote script run against staging, then production; hosted projects hold only what the repository defines
- [ ] Edge proxy with DDoS protection and a web application firewall in front of the app; the origin reachable only through it; the client IP taken from its header
- [ ] Email: SPF, DKIM and DMARC published and verified; bounce and complaint webhooks suppress addresses; staging cannot email real users
- [ ] Usage alerts for every free tier in use, and a written plan for exceeding each limit

## Monitoring and operations

- [ ] Error tracker (GlitchTip or Sentry) with releases, environments and PII scrubbing
- [ ] External uptime monitoring and the alerts in `docs/OPERATIONS.md`, each with a runbook entry
- [ ] `docs/OPERATIONS.md` completed: where logs live, how to query them, dashboards; read-only access for agents if wanted
- [ ] The weekly trusted-sources agent (`docs/SOURCES.md`), if wanted

## Quality and security gates

- [ ] Lighthouse CI budgets for performance, SEO, accessibility and best practices
- [ ] Trivy image scan and hadolint in CI
- [ ] Renovate or Dependabot, security updates first, with a cooldown for other updates
- [ ] Bot challenge on sign-up, password reset and other public forms
- [ ] OWASP ZAP baseline against staging or a pre-production deploy
- [ ] k6 load-test baseline recorded in `docs/SCALING.md`; two app instances behind the proxy to prove statelessness

## Privacy, analytics and search

- [ ] Analytics provider adapter, if one was chosen; if it needs consent, the consent banner and, for Google tools, Consent Mode v2
- [ ] Account deletion and data export; privacy policy, cookie policy and the legal notices the target countries require
- [ ] Terms of service with the minimum age, versioned and accepted at sign-up; the re-acceptance screen for material changes
- [ ] Apps that host user content: a report action, the takedown process and a contact point
- [ ] Google Search Console and Bing Webmaster Tools verified, sitemap submitted

## Strict profile

- [ ] Data protection impact assessment, if required; records of processing activities
- [ ] Incident response plan with contacts and breach-notification steps
- [ ] MFA required for admin and staff accounts; append-only audit log in place
- [ ] Infrastructure as code; point-in-time recovery with a restore drill; recovery time and recovery point objectives written down
- [ ] SBOM per release; blocking dependency and container scans
- [ ] External penetration test, findings fixed or accepted in `docs/security/findings.md`
- [ ] Manual keyboard and screen-reader pass on key flows; accessibility statement where required
