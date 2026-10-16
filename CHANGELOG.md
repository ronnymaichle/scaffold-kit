# Changelog

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
