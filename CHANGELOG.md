# Changelog

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
