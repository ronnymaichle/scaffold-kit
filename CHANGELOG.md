# Changelog

## 2.0.0 (2026-10-13)

First release of the kit. Version 1 of the `scaffold-project` skill was a single file; version 2 is a short skill plus this kit.

- Check scripts with tests (Python 3.9+, standard library only): folder docs and code map, debug leftovers, design literals and contrast, and a palette generator with a side-by-side preview.
- Reference rules per area, each naming the project docs it becomes.
- Templates: the root `CLAUDE.md` with the Feature, Hotfix and Release workflows, the scaffold progress and launch checklists, ADR, `SECURITY.md`, GitHub PR and issue templates, project CI, lefthook, commitlint and the quality config.
- New compared with skill v1: lean, standard and strict profiles; Phase 1 in four resumable checkpoints; upgrade mode for existing repositories; a testing guide; shadcn-compatible token names; error and analytics event catalogs kept only in code; logging rules in `docs/LOGGING.md` instead of `docs/ERRORS.md`; session rules per auth approach.
