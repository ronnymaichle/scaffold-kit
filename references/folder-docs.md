# Folder docs and the code map

Becomes the documentation part of `CONTRIBUTING.md`; the finding-code rule also goes into the root `CLAUDE.md`. The scripts in `scripts/quality/` enforce the format below, so keep to it exactly.

## Why

Claude and people find the right file and function, and what it is connected to, from short indexes instead of reading whole files. Claude Code also loads a folder's `CLAUDE.md` automatically when it works in that folder.

## Finding code

Navigate top-down: `docs/CODEMAP.md` (one line per folder), then the folder's `CLAUDE.md` (every file, its exported symbols and what it depends on), then open only the file needed and, within it, only the relevant function. If an index entry turns out to be wrong or missing, fix it in the same change.

Before changing a file, `python3 scripts/quality/folder_docs.py deps <file>` lists what it imports and what imports it, tests included, so the files a change can break are known without opening them. It reads the code each time, so it is never out of date.

## Which folders

- Every folder with source, test or config files (the extensions in `folderDocs.extensions`) has a `CLAUDE.md`, and so does each of its parent folders, to list its subfolders.
- Files at the project root are described in the root `CLAUDE.md` instead.
- Skipped: hidden folders and the folders in `folderDocs.exclude` (dependencies, build output, coverage, logs, `docs/`, `static/`, `public/`). Lockfiles, minified, source-map and generated files are skipped by name (`folderDocs.ignoreFiles`).
- `scripts/quality/` is vendored from the kit with its own `CLAUDE.md`; never edit that folder by hand.

## Format

```markdown
# src/lib/server/services

Purpose: Business logic per domain; called by routes, calls repositories.

## Files

### markers.ts
Marker business logic: viewport queries and the create and update rules.
- `getMarkersInBbox(db, bbox, limit)` -> `MarkerDTO[]`: published markers inside a bounding box, newest first, at most 500
- `createMarker(db, user, input)` -> `MarkerDTO`: validates input, checks the user's quota, inserts; throws `MARKER_QUOTA_EXCEEDED`; emits `marker_created`
- Also exports: `MarkerInput`, `MAX_MARKERS_PER_USER`
Depends on: `src/lib/schemas/marker.ts`, `src/lib/server/repositories/markers.ts`

### *.test.ts
Unit tests for the services in this folder, one file per service.

## Subfolders

- `uploads/`: presigned upload URLs and media records

## Conventions
- No database access here; call repositories.

## Gotchas
- `createMarker` rounds coordinates to 5 decimals before saving.
```

Rules the check relies on:

- The title is the folder path; the `Purpose:` line is one sentence, and the code map is built from it.
- `## Files` has one `### <file name>` entry per file, or one `### <glob>` entry for a group of similar files (tests, migrations, generated route files). Each entry starts with a one-line description.
- Each exported symbol other code uses gets a bullet starting with its backticked name or signature: `` - `name(params)` -> `ReturnType`: what it does; side effects ``. Side effects are database writes, jobs enqueued, events emitted and errors thrown. Types and constants that need no explanation share one `- Also exports:` bullet.
- Components list their props in one bullet: `` - Props: `marker: MarkerDTO`, `onClose: () => void` ``. Callback props cover events.
- A file that imports other project files ends with a `Depends on:` line: those files in backticks, by path from the project root (for Go, the package folders, ending in `/`). `init` writes and refreshes it from the code and the check compares it with the imports, so it is never edited by hand. Test files (`folderDocs.symbolCheckSkip`) and glob entries get none. Imports resolve through relative paths, `tsconfig.json` or `jsconfig.json` paths, `folderDocs.aliases` (default `$lib` to `src/lib`), Python packages at the root, in `src/` or next to the file, and the module path in `go.mod`; packages from outside the project are left out.
- Routes describe the URL, what `load` returns, and each action with who may call it, for example: `` - `load` -> `{ marker: MarkerDTO }`: public; 404 when unpublished unless the viewer owns it `` and `` - `actions` -> `comment` (signed-in users), `delete` (owner only) ``.
- `## Subfolders` has one bullet per subfolder, starting with its backticked name: `` - `uploads/`: purpose ``.
- Optional sections, only when they say something useful: `## Conventions`, `## Security and privacy` (trust boundaries, authorization checks, personal data touched), `## State and scaling` (tables, queries and their indexes, cache entries with TTL and invalidation, jobs), `## Errors, logs and analytics` (error codes thrown, log module name, events emitted), `## Gotchas` (non-obvious behaviour, invariants, known limitations).
- Not listed: private helpers and line numbers, which change too often and would make the index wrong.
- Plain, precise wording for an AI reader: real names, no marketing prose. A folder doc that grows past ~150 lines usually means the folder should be split.

## Commands

| Command | What it does |
|---|---|
| `python3 scripts/quality/folder_docs.py check` | Part of `check`: verifies every folder doc and the code map |
| `python3 scripts/quality/folder_docs.py staged` | Pre-commit hook: checks the folders touched by the staged changes |
| `python3 scripts/quality/folder_docs.py init` | Creates missing folder docs, appends missing entries, bullets and subfolders marked `TODO(describe)`, and writes or refreshes every `Depends on:` line; never removes or rewrites other text |
| `python3 scripts/quality/folder_docs.py codemap` | Regenerates `docs/CODEMAP.md` (the `docs:codemap` script); never edit that file by hand |
| `python3 scripts/quality/folder_docs.py deps <file>...` | Prints what each file imports and what imports it (for a Go file, what imports its package) |

After `init`, replace every `TODO(describe)` with a real description; the check fails while any remain, and it lists stale entries for removal by hand.

## What the check verifies

- Every folder that needs a doc has one, with a `Purpose:` line and no `TODO(describe)` left.
- Every file is listed (directly or through a glob entry) and every listed file exists and has a description.
- Every file's `Depends on:` line lists exactly the project files it imports, and a file without such imports has none (`folderDocs.dependsCheck: false` turns this off).
- Every exported symbol is listed, and every listed symbol is still exported. Exports are read from the code: JavaScript and TypeScript (ES modules and CommonJS) with comments and strings ignored, Svelte module-script exports and component props, Python's `__all__` or public top-level names, Go's exported names (methods as `Type.Method`). Test files are skipped (`folderDocs.symbolCheckSkip`), and a file with `export * from` skips the stale-symbol part because its re-exports cannot be resolved.
- Every subfolder is listed and every listed subfolder exists.
- `docs/CODEMAP.md` matches the folder docs.
- In the pre-commit hook, adding, removing or renaming a file fails unless its folder's `CLAUDE.md` is staged in the same commit; changing a file without its folder doc staged prints a reminder to check that the doc still describes it.

The check cannot tell whether a description is still accurate; that is part of the self-review before each commit (Feature workflow, step 9).

## Progressive adoption

In an existing codebase, `folderDocs.include` in `quality.config.json` limits enforcement to the listed folders and their subfolders, so docs can be added folder by folder, starting where work happens. Remove the setting once every folder is covered.
