# Scaffold progress

Phase 1 in four checkpoints. Each checkpoint ends with `check` passing and one commit on `main`; these are the only commits without a PR. Tick items as they are done. After an interruption or a compacted conversation, resume at the first unchecked item. The last checkpoint's commit deletes this file.

- Kit: scaffold-kit {{KIT_VERSION}} (fetch the same tag again if the local copy is gone)
- Profile: {{PROFILE}}
- Confirmed plan: {{PLAN_SUMMARY}}
- Approved draft: {{APPROVED_DRAFT: the draft folder, the chosen theme with the palette.py command that regenerates it, and the look}}

Items that do not apply to the profile are deleted when this file is created. Each doc is written from its kit reference and holds only what applies to this stack and profile, with scaffold-time tables replaced by the decision and its reason.

## Checkpoint A: foundation

- [ ] Root `CLAUDE.md` from the kit template, with every `{{...}}` placeholder filled
- [ ] `docs/SOURCES.md` from the kit reference, filtered to the stack, platforms, target countries and data, with today's review date; the WebFetch rules written with `python3 scripts/quality/sources.py sync` once the scripts are copied
- [ ] Git initialized on `main`; the project created with the framework's official CLI and official integrations added through it (no hand-written boilerplate that a CLI generates)
- [ ] `scripts/quality/` copied from the kit unchanged; `quality.config.json` from the template, with the theme file path and any extra excludes set
- [ ] Tooling: formatter; linter with the ecosystem's security rules and a ban on `console.*` outside the logger; strict type checking; module-boundary lint rule; test runners; commitlint; git hooks from `templates/lefthook.yml`, each command checked against the installed tool's `--help`; package manager hardening (frozen installs, a minimum release age, install scripts only for trusted packages)
- [ ] Structure (only the folders the first features need), environment validation at startup, liveness and readiness endpoints, graceful shutdown, security headers, same-origin CORS, and the client IP read only from the trusted proxy's header
- [ ] `.claude/settings.json` and `.claude/agents/` from the kit's `templates/claude/`, keeping the agents the profile needs (`docs/AGENT-TEAM.md`); `.claude/skills/stack-conventions/SKILL.md` written from the official docs for the installed versions, each entry with its source and date, and those pages added to `docs/SOURCES.md`
- [ ] `.gitignore` (including `.env`, `logs/`, `.claude/plan.md`), `.gitattributes`, `.editorconfig`, `.env.example` with placeholders
- [ ] For apps with screens: `docs/mockups/` from the approved draft, with only its screens and the approved theme left, and that theme's CSS file next to it
- [ ] Docs: `CONTRIBUTING.md` (git workflow and folder docs), `docs/ARCHITECTURE.md` (the approved diagrams, and the payloads under Planned actions), `docs/ROADMAP.md` from the template (the confirmed plan's features in build order), `docs/TESTING.md`, `docs/AGENT-TEAM.md`, `docs/security/THREAT-MODEL.md`, `docs/security/findings.md`; ADRs `0001-stack` and `0002-branching`
- [ ] Folder docs created with `folder_docs.py init`, every `TODO(describe)` replaced, code map generated
- [ ] `check` passes; commit `chore(scaffold): foundation`

## Checkpoint B: data, auth and errors

- [ ] Database in docker-compose with production's version and extensions, or the platform's local stack; ORM and the first migration, from the approved data model; `migrate`, `db:reset` and `db:seed` with realistic fake data; a separate test database; no hosted project used for development
- [ ] Mail module with a local mail catcher (for example Mailpit) in docker-compose
- [ ] Public apps: versioned legal documents and the append-only terms-acceptance table; the acceptance step itself is built with sign-up
- [ ] DTO pattern and type checks spanning database, server and UI; schema-drift check in `check`
- [ ] Auth library or platform installed and configured; sign-up and sign-in are built afterwards as the first feature, through the Feature workflow
- [ ] Roles and permissions: the permission catalog with `anonymous`, `user`, `admin` and any roles the plan adds; `can()` and the `guard()` helper for every entry point; the role assignments table; the first-admin command; the permission matrix and route coverage tests
- [ ] Safeguards: the rate limiter and quota modules, the security event catalog with its thresholds, the audit log table, the alert module (email and the admin alert inbox), feature breakers with read-only mode, a metered module for each paid provider in the plan with the lint rule that keeps its SDK inside it, and the safeguards table with the budgets from the plan
- [ ] Logger with redaction, `logs/dev.log` in development, error catalog, `AppError` and global error handling
- [ ] Docs: `docs/DATABASE.md`, `docs/LOGGING.md`, `docs/PRIVACY.md` (data protection and the first data inventory), `docs/security/SAFEGUARDS.md`, the Auth (with roles and permissions), APIs and Caching sections of `docs/ARCHITECTURE.md`; ADR `0003-data-and-auth`
- [ ] Folder docs and code map updated; `check` passes; commit `chore(scaffold): data, auth and errors`

## Checkpoint C: interface and public web

- [ ] Theme file written from the theme approved with the draft, with the look's radius; the look's font self-hosted and its density set as the base components' default size; contrast check green
- [ ] Tokens wired into the styling framework; light, dark and system themes with the switcher; component base; root toaster, banner slot, flash messages and the `notify` module; dev design page (not in the lean profile)
- [ ] Shared head component, robots.txt and sitemap.xml routes, noindex outside production
- [ ] Analytics module with the `noop` adapter and the event catalog; consent state, necessary only, with the banner hidden until a non-necessary adapter is enabled (not in the lean profile)
- [ ] i18n, if two or more languages are planned
- [ ] Docs: `docs/DESIGN.md` (source colors, rationale, the look, contrast table), `docs/SEO.md`, `docs/ANALYTICS.md`, the cookie consent section of `docs/PRIVACY.md`; ADR `0004-design-system`
- [ ] Folder docs and code map updated; `check` passes; commit `chore(scaffold): interface and public web`

## Checkpoint D: delivery, docs and verification

- [ ] Multi-stage Dockerfile running as non-root, `.dockerignore`, docker-compose for local services
- [ ] Scripts: `check` (format check, lint, type check including framework checks, schema drift, unit and integration tests, folder docs and code map, debug leftovers, design literals and contrast, trusted sources), `check:security` (dependency audit, gitleaks, Semgrep), `test:e2e` (with axe, SEO metadata and consent checks), `migrate`, `db:reset`, `db:seed`, `docs:codemap`, and the promote script `deploy:env` with `--dry-run`
- [ ] CI on every PR from `templates/github/workflows/ci.yml`: `check`, `check:security`, `test:e2e`, image build, PR title lint
- [ ] Docs: `docs/DEPLOYMENT.md`, `docs/SCALING.md`, `docs/OPERATIONS.md`, `docs/LAUNCH-CHECKLIST.md`; ADR `0005-hosting`; root `SECURITY.md`, PR and issue templates, `README.md` (what it is, quick start, commands, links to the docs)
- [ ] Verify:
  - [ ] `check`, `check:security` and the e2e smoke test pass
  - [ ] docker-compose starts; migrations apply to an empty database and the seed runs
  - [ ] `deploy:env staging --dry-run` lists every promote step and changes nothing
  - [ ] a test email lands in the local mail catcher
  - [ ] liveness and readiness respond
  - [ ] robots.txt and sitemap.xml are served, and the noindex header appears outside production
  - [ ] with the `noop` adapter there are no third-party requests and no non-necessary cookies
  - [ ] the dev design page renders in both themes, with every feedback variant
  - [ ] a test error appears in the logs with requestId and commit, and as an error toast showing the same ref
  - [ ] a test security event past its threshold blocks the actor, reaches the admin alert inbox and the local mail catcher, and appears in the audit log
  - [ ] a tripped breaker returns `FEATURE_DISABLED` to a user, still lets an admin through, and stays tripped until an admin resets it
  - [ ] every rule from the kit references that applies to this profile is in its mapped file
  - [ ] no `{{` placeholders and no `TODO(describe)` markers remain
- [ ] Every critical and high finding resolved; this file deleted; commit `chore(scaffold): delivery, docs and verification`
- [ ] With the user's approval: create the remote repository, push, and apply branch protection (or hand over the exact settings)
- [ ] Report: structure, commands, scan results, contrast report, launch checklist, and the first ready feature in `docs/ROADMAP.md`
