# Upgrade mode

For an existing repository: applying these standards to a project that was not scaffolded with the kit, moving a scaffolded project to a newer kit version, or moving a project up a profile. Only the approved plan (`docs/UPGRADE-PLAN.md`) is written from this file; every other change arrives through the Feature workflow.

## Rules

- Read-only until the user approves a plan: no edits, installs, migrations, deploys, commits or pushes during the inventory. If the working tree has uncommitted changes, say so and leave them alone.
- Never overwrite or regenerate existing files, rewrite history, or switch the stack, framework, database, ORM or styling approach as part of an upgrade. Each of those is a separate decision with its own ADR, made only when the user asks.
- Conventions that already work stay. Record each one in an ADR ("kept from the existing codebase") instead of replacing it.
- Changes arrive as small PRs through the Feature workflow, ordered by risk, each green before the next starts.

## Steps

1. Inventory, read-only: stack and versions, folder structure, package scripts, how tests run and what they cover, CI, git hooks, existing docs (`README.md`, `CLAUDE.md` files, `docs/`), dependencies, database and migrations, auth, input validation, logging and error handling, theming, SEO, analytics and consent, deployment, and the recorded kit version if any. Then ask in one round for what the code cannot show: the monthly budget for paid services, where the app runs and stores data, the target countries and expected users, and who receives security and budget alerts. When the user cannot answer now, write each question into the plan with the recommended answer.
2. Run the checks without installing anything into the project, with the kit's copies of the scripts: `python3 -B <kit>/scripts/quality/folder_docs.py --root <project> check`, `python3 -B <kit>/scripts/quality/debug_leftovers.py --root <project>`, and `design_tokens.py --root <project> literals` (plus `contrast` once the project has a theme file). `-B` keeps Python's bytecode cache out of the kit folder. Run gitleaks over the full history and the dependency audit when they are installed; otherwise list them as missing. Without a lockfile the audit cannot run: list it as not run, and the first dependency PR adds the lockfile. Do not start services or run the test suite if it needs a database or network access; ask first.
3. Review the code against the security defaults in the kit's `references/security.md`, with extra attention to injection (string-built SQL or shell commands), raw HTML rendering of user content (`{@html}`, `dangerouslySetInnerHTML`, `v-html`), missing authorization checks (every server entry point, including form actions, Server Actions and remote functions), paid providers without a budget or spending cap, committed secrets and `.env` files, and secrets reachable from client code.
4. Report critical and high findings at once, before anything else, each with file and line, impact and the fix. An exposed secret is rotated first and removed from the repository second; history is rewritten only with the user's explicit approval, because it changes every clone.
5. Gap report: for each area (security and supply chain, roles and safeguards, tests, workflow, docs, logging and errors, design, SEO, analytics and consent, legal documents, privacy (data export, deletion and retention), the agent setup, hosting, email and scaling, local development and promotion, trusted sources), what exists, what is missing for the chosen profile, its severity, and the PR that closes it. Ask which profile applies if it is not obvious.
6. After approval, the user first does the steps outside the repository that stop damage at once, from a checklist in the plan: a budget with alerts and, where offered, a hard cap on every paid provider that has none, because an uncapped bill can arrive before any fix lands, and locking down any rules or keys found exposed. Then the first PR saves the plan as `docs/UPGRADE-PLAN.md`, alone, so it merges quickly; later PRs tick it off. Recommended order:
   1. Critical and high security fixes, each with a regression test (the first fix PR adds the test runner when the project has none), and the budget actions or breakers that a provider's alerts cannot replace.
   2. A safety net: the root `CLAUDE.md` (merged with any existing one, never replacing what it says), `CONTRIBUTING.md`, `docs/SOURCES.md` with its WebFetch rules (merged into any existing `.claude/settings.json`), the agent guard hook and deny rules from the kit's `templates/claude/settings.json` (merged the same way), `docs/AGENT-TEAM.md` with `.claude/agents/`, `docs/security/THREAT-MODEL.md` with `docs/security/findings.md` and the root `SECURITY.md`, `quality.config.json`, the vendored `scripts/quality/`, hooks and CI that run what already passes, and tests around the code the next PRs touch.
   3. Repository workflow: branch protection, commit and PR conventions, PR and issue templates, `docs/ROADMAP.md` from the kit template with the features still planned, and `docs/AGENT-METRICS.md` from the kit template.
   4. Medium security findings and the remaining defaults (headers, validation, rate limits, CORS, webhooks, supply-chain settings, environment validation), then roles and permissions, quotas, metered provider modules with breakers, the security event catalog and admin alerts (`references/safeguards.md`).
   5. Logging, the error catalog and global error handling.
   6. Folder docs, adopted folder by folder with `folderDocs.include`, starting where work happens.
   7. Design tokens and the feedback system; SEO; analytics and consent; legal documents and terms acceptance; local development and the promote script; hosting, email, backups and scaling items; the launch checklist items that apply.
7. Record the kit version in the root `CLAUDE.md` when the safety-net PR merges.

## Moving to a newer kit version

- Compare the kit version recorded in the root `CLAUDE.md` with the new one and read the kit's `CHANGELOG.md` between them.
- Replace `scripts/quality/` with the new version (the folder is never edited in projects, so replacing it is safe) and run `check`; merge new configuration defaults into `quality.config.json` by hand.
- Propose rule and template changes as PRs against the project's docs, keeping project-specific decisions.

## Moving up a profile

The gap report lists what the new profile adds: the items the lean profile skipped, or the strict additions in each reference file. The PR order stays the same.
