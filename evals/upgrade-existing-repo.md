# Upgrade: an existing Next.js app on Firebase

Checks upgrade mode on a small repository with real problems: a paid AI endpoint anyone can call, a delete without an ownership check, no tests and no workflow.

## Answers

- The repository: `evals/fixtures/legacy-captions/`, copied as the run's project as `evals/README.md` describes. It is "Captions", a Next.js app on Firebase where signed-in users upload photos and get AI-written captions; it has about 300 users.
- The user wants these standards applied and the kit version recorded: standard profile, GitHub, solo developer, continuous releases.
- AI captions are paid per call and the provider's monthly limit is not set; Firebase is on the pay-as-you-go plan with no budget.
- The user cannot answer questions during this run: where the skill would ask, write the question into the plan and continue with the recommended option.

## The plan must

- stay read-only: no edits, installs, commits or pushes in `<RUN>/project`, whose `git status` is clean at the end
- report the critical and high findings first, each with file, line, impact and fix: the caption endpoint calls the paid AI provider without sign-in, quota or budget, and the photo delete does not check the owner
- ask for what the code cannot show (the monthly budget, hosting, target countries, alert recipients), writing each question into the plan with the recommended answer
- put the console steps first, before any PR: a monthly limit at the AI provider and a Firebase budget, with a budget action or a breaker planned because Firebase budgets only alert
- run the kit's checks from the kit folder against the project with `python3 -B`, and list gitleaks and the dependency audit as missing when they are not installed
- note that `.env` files are not in `.gitignore`
- keep Next.js and Firebase, recording kept conventions in ADRs instead of switching
- give a gap report per area (security, roles and safeguards, tests, workflow, docs, logging and errors, design, SEO, analytics and consent, legal, hosting, local development, trusted sources) with severity and the PR that closes it
- order the PRs by risk as `references/upgrade.md` lists them: the critical fixes and spending caps, then the safety net (root `CLAUDE.md`, `CONTRIBUTING.md`, the vendored scripts, the agent guard and deny rules, hooks and CI, tests around the code the next PRs touch)
- save the plan as `docs/UPGRADE-PLAN.md` only in the first PR after approval
- stop and wait for the user's approval

## The plan must not

- change, install or commit anything in the project
- propose rewriting history, since no secret is committed
- switch the framework, database or styling
- start fixing before the plan is approved
