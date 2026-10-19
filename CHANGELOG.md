# Changelog

## 2.5.0 (2026-10-19)

- Linked files in the folder docs: `folder_docs.py` reads each file's imports and writes its `Depends on:` line, listing the project files it imports by path from the project root (for Go, the package folders). `init` writes and refreshes the lines, and `check`, and so the pre-commit hook, fails when one no longer matches the code, so which files are connected can be trusted without opening them. Test files and glob entries get none; `folderDocs.dependsCheck: false` turns the check off.
- Imports resolve through relative paths, `tsconfig.json` or `jsconfig.json` paths (following relative `extends`), Node subpath imports in `package.json` (`#lib/*`), the new `folderDocs.aliases` setting (default `$lib` to `src/lib`), Python packages at the root, in `src/` or next to the file, and the module path in `go.mod`. Packages from outside the project are left out.
- New command `folder_docs.py deps FILE...`: what each file imports and what imports it, tests included, read from the code each time. The root `CLAUDE.md` template (Commands, Finding code, Feature step 4) and the `implementer`, `reviewer` and `debugger` agents use it before changing what a file exports.
- `references/folder-docs.md` documents the line, the command and what the check verifies, and its example carries a generated line; the vendored `scripts/quality/CLAUDE.md` has its own lines. New tests in `tests/test_folder_docs_depends.py`.
- Projects: in upgrade mode, replace `scripts/quality/`, run `python3 scripts/quality/folder_docs.py init` (it also rewrites handwritten Depends on lines into the checked format), review and commit the folder docs, and add `folderDocs.aliases` for any import alias defined outside `tsconfig.json` and `package.json` (for example Vite's `resolve.alias`); update the root `CLAUDE.md` lines and `.claude/agents/` (`implementer`, `reviewer`, `debugger`).

## 2.4.0 (2026-10-19)

- Draft before code: the plan step ends with a draft the user approves before any code exists, on one page from the new template `templates/plan-preview.html` (a pinned Mermaid build, and switches for the color proposals, light and dark, and phone and desktop width). It shows the system and main-flow diagrams, the data model and example payloads for the main actions (`references/architecture.md`), and, for apps with screens, the color proposals, the look and rough mockups of the main screens (`references/design.md`). The lean profile drafts the system diagram, the data model and the main screen only. Colors are now chosen at this step instead of in checkpoint C.
- Architecture (`architecture.md`): composition over inheritance; shared code is extracted on its third repetition; a Diagrams section keeps the system and main-flow diagrams as Mermaid in `docs/ARCHITECTURE.md`, updated by every change that alters them; Planned actions hold each approved payload until the feature that builds the action turns it into its schema, DTO and tests and deletes the entry.
- Design (`design.md`): a Look decided with the colors (font, density, corners, motion) and recorded in `docs/DESIGN.md`; Screen mockups, kept in `docs/mockups/` until each screen is built; Component composition: three levels enforced by the boundary lint rule, content passed in rather than flags, shared behaviour in one place; the interface font is self-hosted.
- Templates: the skill's steps 3 and 4, the scaffold progress checklist, the root `CLAUDE.md` summary lines and Feature steps 4 and 9, and the `designer` agent follow the above. A new test keeps the preview template's scripts pinned to exact versions.
- Projects: in upgrade mode, add the Diagrams section to `docs/ARCHITECTURE.md` (the system and main flow as they are today), the composition principle and the third-repetition rule, a Look section in `docs/DESIGN.md` that records the current look, and the Component composition section with the boundary lint rule for the component levels; update the root `CLAUDE.md` lines and Feature steps 4 and 9, and `.claude/agents/designer.md`. Planned actions and `docs/mockups/` start empty and fill as new actions and screens are planned.

## 2.3.0 (2026-10-18)

- Stack expertise: new skill template `templates/claude/skills/stack-conventions/SKILL.md`, written at scaffold time from the official docs for the exact versions in the lockfile. It records the conventional and the currently recommended way per topic, the project's choice where they differ, and the traps (old APIs that still look plausible), each with its source and date. The `implementer`, `reviewer`, `debugger`, `designer` and `architect` preload it; it is refreshed on major upgrades and in the quarterly `chore(agents)` review.
- New `designer` agent (Opus, high, no edit tools): proposes layout, components, states, feedback and accessibility for new screens at planning time, and reviews every change to the project's UI paths at Feature step 8, in parallel with the `reviewer` and within the same single review round.
- New `architect` agent (Opus, xhigh, no edit tools, can fetch the trusted sources): consulted only for a new architecture pattern, a framework or major-version migration, a core dependency, or a choice where the conventional and recommended ways differ. It returns options with sources and dates and drafts the ADR; routine features do not use it.
- `references/agents.md` gains the Stack expertise and UI work sections; the lean profile keeps the designer for new screens only and drops the architect. The root `CLAUDE.md` template's Agents line and Feature steps 2, 4 and 8 name the new agents. Tests check that the advisory agents cannot edit, that coding agents preload the skill, and the skill template's structure.
- Projects: in upgrade mode, copy `designer.md` and (standard and strict) `architect.md` into `.claude/agents/`, add the `skills` preload to the existing `implementer`, `reviewer` and `debugger`, write `.claude/skills/stack-conventions/SKILL.md` from the official docs for the installed versions and add those pages to `docs/SOURCES.md` (then `sources.py sync`), list the UI paths in `docs/AGENT-TEAM.md`, and update the root `CLAUDE.md` lines.

## 2.2.0 (2026-10-18)

- Agent team: new reference `references/agents.md`, which becomes `docs/AGENT-TEAM.md`. The main session leads on Opus at `xhigh` effort, writes the plan to `.claude/plan.md` and delegates slices to specialist agents: `implementer` (Opus, high), `test-runner` (Haiku, low, in the background), `reviewer` (Opus, xhigh, fresh context, no edit tools), `debugger` (Opus, high) and, on the strict profile, `security-auditor` (Opus, max). Agents report only to the lead, in one shared format with the evidence for their status.
- Loop limits: two attempts per failure before an agent stops as `blocked`, a `maxTurns` limit on every agent, one review round that re-checks only its own findings, test results reused for an unchanged commit, and one owner per slice and per file.
- Agent teams stay off in project settings and are enabled per session only for parallel review, competing-hypothesis debugging and multi-layer features with separate files.
- New templates in `templates/claude/`: `settings.json` pins the lead's model and sets its effort through `modelSettings` (a top-level `effortLevel` is ignored by Opus 5.5 and later), and `agents/` holds the five agent definitions. New test `tests/test_agent_templates.py` checks their frontmatter, the read-only roles, the report format, the roster table and the lead settings.
- The root `CLAUDE.md` template gains an Agents line, and Feature steps 7 and 8 and Hotfix step 1 name the agents. The scaffold progress checklist copies `.claude/` in checkpoint A and ignores `.claude/plan.md`. `references/sources.md` lists the Claude Code documentation for keeping models and effort levels current.
- Projects: in upgrade mode, write `docs/AGENT-TEAM.md`, copy `templates/claude/agents/` to `.claude/agents/` (keeping the roles the profile needs), merge `model` and `modelSettings` from `templates/claude/settings.json` into `.claude/settings.json`, add `.claude/plan.md` to `.gitignore`, add the Claude Code rows to `docs/SOURCES.md` and run `sources.py sync`, and update the root `CLAUDE.md` lines.

## 2.1.2 (2026-10-16)

- The scaffold-kit-maintainer skill's source moved from `.claude/skills/scaffold-kit-maintainer/` to `skill/scaffold-kit-maintainer/`, next to the scaffold-project source. The repository no longer has a `.claude/skills/` folder, so Claude Code loads only the copy saved in claude.ai; the root `CLAUDE.md` names the source file to read when that copy is not available.
- Projects: nothing to adopt; no rules, templates or scripts changed.

## 2.1.1 (2026-10-16)

- The scaffold-kit-maintainer skill and the README no longer describe a second copy of the scaffold-project skill in `~/.claude/skills/`. The copy saved in claude.ai syncs to Claude Code automatically, so step 8 publishes a changed skill only there.
- Projects: nothing to adopt; no rules, templates or scripts changed.

## 2.1.0 (2026-10-16)

- Trusted sources: new reference `references/sources.md`, which becomes `docs/SOURCES.md`. It lists the official and curated sources for versions, support windows, advisories, malicious packages, platform limits, security practice, SEO, privacy law and email, in order of trust, filtered to each project's stack and countries. It also says when Claude consults them (scaffold, every new dependency, releases, hotfixes, an optional weekly agent) and treats fetched pages as data, never instructions. The skill and the Feature, Hotfix and Release workflows now check these sources instead of relying on memory.
- New check script `scripts/quality/sources.py` (`check`, `sync`, `domains`): keeps Claude Code's WebFetch allow rules in `.claude/settings.json` in step with the sources file. It never pre-approves wildcards or hosts where anyone can publish, flags http links, and warns when the list's review date is older than `sources.reviewDays`. New `sources` section in `quality.config.json`; the hook template runs the check.
- Legal documents (`privacy.md`): terms of service and what they cover, versioned legal documents, explicit acceptance at sign-up recorded per version, re-acceptance after material changes, minimum age, and duties for apps that host user content. The privacy policy is shown, not agreed to.
- Local development and promotion: development never uses a hosted project; everything a hosted project needs lives in the repository; one idempotent promote script (`deploy:env`, with `--dry-run`) takes it to staging and production. Commands are listed for Postgres, Supabase and Firebase. A data-store family rule says which moves are scriptable (within Postgres-compatible stores, or local and hosted Firebase) and which are a data-layer rewrite (across families).
- Security: CORS policy, incoming and outgoing webhooks, bot protection with a challenge on public forms, an edge proxy with DDoS protection and a WAF with the origin locked to it, the client IP read only from the trusted proxy's header, and a new supply-chain section (frozen installs, minimum release age and update cooldowns, install scripts only for trusted packages, incident response). A lean section lets VPN-only internal tools skip the WAF and the bot challenge.
- Email (`hosting.md`): a local mail catcher, a staging allowlist, SPF, DKIM and DMARC, separate transactional and marketing streams, one-click unsubscribe, bounce and complaint handling.
- Templates: new lines in the root `CLAUDE.md`, the scaffold progress and launch checklists, and the PR template for all of the above.
- Projects: in upgrade mode, replace `scripts/quality/`; add the `sources` section to `quality.config.json`; write `docs/SOURCES.md` and run `sources.py sync`; add the `trusted-sources` hook job; then adopt the new rules as PRs: legal documents and terms acceptance, the promote script, email authentication, edge protection, CORS, webhooks and supply-chain settings.

## 2.0.1 (2026-10-16)

- The scaffold-project skill's source now lives in the kit (`skill/scaffold-project/SKILL.md`), so it is versioned and edited together with the rules it uses.
- New scaffold-kit-maintainer skill (`.claude/skills/scaffold-kit-maintainer/`) and a root `CLAUDE.md`: which file each kind of change belongs in, testing, version bumps, releases and publishing a changed skill.
- New tests keep both skills valid and in sync with the kit: frontmatter, the major version the skill fetches, the skill's size, and the reference mapping tables.
- Projects: nothing to adopt; no rules, templates or scripts changed.

## 2.0.0 (2026-10-13)

First release of the kit. Version 1 of the `scaffold-project` skill was a single file; version 2 is a short skill plus this kit.

- Check scripts with tests (Python 3.9+, standard library only): folder docs and code map, debug leftovers, design literals and contrast, and a palette generator with a side-by-side preview.
- Reference rules per area, each naming the project docs it becomes.
- Templates: the root `CLAUDE.md` with the Feature, Hotfix and Release workflows, the scaffold progress and launch checklists, ADR, `SECURITY.md`, GitHub PR and issue templates, project CI, lefthook, commitlint and the quality config.
- New compared with skill v1: lean, standard and strict profiles; Phase 1 in four resumable checkpoints; upgrade mode for existing repositories; a testing guide; shadcn-compatible token names; error and analytics event catalogs kept only in code; logging rules in `docs/LOGGING.md` instead of `docs/ERRORS.md`; session rules per auth approach.
