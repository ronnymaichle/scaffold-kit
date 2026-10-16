# scripts/quality

Purpose: Quality checks vendored from scaffold-kit (folder docs and code map, debug leftovers, design tokens and contrast, palette generation, trusted sources); Python 3.9+, standard library only.

Do not edit these files in a project: change behaviour through `quality.config.json` at the project root, and send improvements to the kit so every project gets them. Upgrade by replacing the whole folder with the kit's newer copy.

## Files

### common.py
Shared helpers: configuration, project file listing, glob matching, JS comment stripping and git access.
- `KIT_VERSION` -> `str`: kit version these scripts belong to
- `load_config(root, path=None)` -> `dict`: built-in defaults merged with quality.config.json; exclude lists extend the defaults, other keys replace them; exits with code 2 on invalid JSON
- `list_project_files(root)` -> `list[str]`: tracked plus untracked-but-not-ignored files inside git, otherwise a filesystem walk
- `glob_match(path, pattern)` -> `bool`: glob with `**`, `*`, `?` and `{a,b}`; a pattern without a slash matches the last path segment
- `any_glob_match(path, patterns)` -> `bool`: true when any pattern matches
- `is_excluded(path, entries, hidden=True)` -> `bool`: "name" excludes a folder at any depth, "/name" only at the root, "a/b" is a path glob
- `strip_js_comments_and_strings(text, keep_strings=False)` -> `str`: blanks comments (and string contents) keeping offsets and line breaks
- `extract_script_blocks(text)` -> `list[tuple]`: (attributes, body, offset) for each `<script>` block and Astro frontmatter
- `git_staged_changes(root)` -> `list[tuple] | None`: (status, path, old_path) for staged changes, None outside git
- `read_staged_text(root, path)` -> `str | None`: staged content of a file
- `read_text(path, limit=2_000_000)` -> `str | None`: file text, None when missing, binary or too large
- `report(errors, warnings=(), ok="ok")` -> `int`: prints the findings and returns the exit code

### colors.py
Color parsing (hex, rgb, hsl, oklch, oklab, named), sRGB and OKLCH conversion, gamut mapping and WCAG contrast.
- `NAMED_COLORS` -> `dict[str, str]`: the 148 CSS named colors as hex
- `parse_color(value)` -> `tuple | None`: (r, g, b, alpha) in 0..1; None for var(), color-mix() and keywords
- `srgb_to_oklch(r, g, b)` -> `tuple`: (L, C, H)
- `oklch_to_srgb(L, C, H)` -> `tuple`: gamma-encoded sRGB, not clamped
- `in_gamut(rgb, eps=1e-5)` -> `bool`: all channels within 0..1
- `gamut_map(L, C, H)` -> `tuple`: same lightness and hue with chroma reduced to fit sRGB
- `to_hex(rgb)` -> `str`: #rrggbb
- `format_oklch(L, C, H, alpha=None)` -> `str`: CSS oklch() text
- `composite(fg, bg)` -> `tuple`: an (r, g, b, a) color blended over an opaque background
- `relative_luminance(rgb)` -> `float`: WCAG 2 relative luminance
- `contrast_ratio(a, b)` -> `float`: WCAG 2 contrast ratio, 1 to 21

### folder_docs.py
Checks that every folder doc lists its files, exported symbols, component props and subfolders; creates skeleton docs; writes the code map.
- `main(argv=None)` -> `int`: commands `check`, `staged`, `init`, `codemap [--check]`; exit 0 when clean, 1 when problems are found, 2 on usage errors

### debug_leftovers.py
Finds DEBUG-TEMP lines, `debugger` statements and Python breakpoints in code (not in Markdown).
- `main(argv=None)` -> `int`: `[--staged]`; exit 1 when anything is found

### design_tokens.py
Flags color literals and raw Tailwind palette classes outside the theme files, and checks WCAG AA contrast of token pairs in the light and dark theme.
- `main(argv=None)` -> `int`: commands `literals [--staged]` and `contrast [--json]`
- `DEFAULT_PAIRS` -> `list[tuple]`: (foreground token, background token, minimum ratio, required) checked when the config has no pairs
- `parse_theme_text(text, dark_selectors=None, into=None)` -> `dict`: custom properties by scope, {"base": {...}, "dark": {...}}
- `parse_theme_files(paths, dark_selectors=None)` -> `dict`: {"light": {...}, "dark": {...}} with dark falling back to light
- `resolve_value(value, env, depth=0)` -> `str | None`: substitutes var() references, honouring fallbacks
- `evaluate_contrast(themes, pairs=None)` -> `list[dict]`: one result per theme and pair with ratio and status pass, fail, skip or missing

### palette.py
Generates OKLCH scales and complete light and dark token themes that pass the contrast pairs, and HTML previews comparing proposals.
- `main(argv=None)` -> `int`: commands `scale`, `theme --primary HEX [--highlight HEX] [--out FILE] [--no-tailwind]`, `preview FILE... [--out FILE]`
- `build_scale(hue, peak, brand=None, lightness=None)` -> `list[tuple]`: (step, (L, C, H)) for steps 50 to 950
- `build_theme(primary, highlight=None, tailwind=True)` -> `tuple[str, list[str]]`: theme CSS and notes; raises RuntimeError if a pair would fail
- `build_preview(paths, title="Theme proposals")` -> `str`: standalone HTML page

### sources.py
Keeps Claude Code's WebFetch allow rules in `.claude/settings.json` in step with the https links in `docs/SOURCES.md`, never pre-approving wildcards or hosts where anyone can publish.
- `main(argv=None)` -> `int`: commands `check`, `sync` and `domains`; exit 1 when problems are found, 2 on unreadable settings
- `linked_domains(text)` -> `tuple[list, list]`: sorted https hosts, and (line, url) for every http link
- `preapproved(hosts, never)` -> `list[str]`: the hosts that get an allow rule
- `review_warning(text, today, max_days)` -> `str | None`: a warning when the "Last reviewed:" date is missing or too old

## Conventions
- Each script runs on its own (`python3 scripts/quality/<script>.py --help`) and imports only these modules and the standard library.
- Output is one finding per line, `path:line: message`, so hooks and CI logs stay readable.

## Gotchas
- Export detection for JS and TS is pattern-based; `export * from` disables the stale-symbol check for that file, and regex literals are not parsed.
- Svelte props are read from `$props()` destructuring (Svelte 5) or `export let` (Svelte 4); `let props = $props()` cannot be checked.
