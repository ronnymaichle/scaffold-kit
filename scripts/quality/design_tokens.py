#!/usr/bin/env python3
"""Design token checks (scaffold-kit).

  literals [--staged]   fail on color literals (hex, rgb(), hsl(), oklch(), named
                        colors) and raw Tailwind palette classes outside the theme
                        files; components must use semantic tokens
  contrast [--json]     check WCAG 2 AA contrast for every foreground/background
                        token pair, in the light and the dark theme

A line containing "design-check-ignore" is skipped; add the reason next to it.
Configuration: the "design" section of quality.config.json.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import colors  # noqa: E402
import common  # noqa: E402

__all__ = [
    "main",
    "DEFAULT_PAIRS",
    "parse_theme_text",
    "parse_theme_files",
    "resolve_value",
    "evaluate_contrast",
]

_IGNORE = "design-check-ignore"
_CSS_EXTS = {".css", ".scss", ".sass", ".less"}
_JS_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}

_TW_COLORS = (
    "slate|gray|zinc|neutral|stone|mauve|olive|mist|taupe|red|orange|amber|yellow|lime|"
    "green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose"
)
_TW_PREFIX = (
    r"(?:bg|text|border(?:-[xytrblse])?|ring(?:-offset)?|outline|fill|stroke|from|via|to|"
    r"decoration|divide|placeholder|caret|accent|shadow|inset-shadow|inset-ring|"
    r"drop-shadow|text-shadow)"
)
_TW_RE = re.compile(
    r"(?<![\w-])" + _TW_PREFIX + r"-(?:(?:" + _TW_COLORS + r")-(?:50|[1-9]00|950)|black|white)(?![\w-])"
)
_HEX_RE = re.compile(r"(?<![\w&#/-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")
_FUNC_RE = re.compile(r"(?<![\w.-])(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(", re.I)
_ATTR_BEFORE = re.compile(
    r"(?:href|to|id|for|name|action|xlink:href|aria-[\w-]+|data-[\w-]+)\s*=\s*[\"'{]?\s*$", re.I
)
_URL_BEFORE = re.compile(r"url\(\s*[\"']?\s*$", re.I)
_COLOR_PROPS = (
    r"(?:color|background(?:-color)?|border(?:-(?:top|right|bottom|left|block|inline)"
    r"(?:-(?:start|end))?)?(?:-color)?|outline(?:-color)?|fill|stroke|box-shadow|"
    r"text-shadow|caret-color|accent-color|column-rule(?:-color)?|"
    r"text-decoration(?:-color)?|stop-color|flood-color|lighting-color|backgroundColor|"
    r"borderColor|outlineColor|caretColor|accentColor|textDecorationColor|stopColor|"
    r"floodColor|boxShadow|textShadow)"
)
_DECL_RE = re.compile(r"(?<![\w-])" + _COLOR_PROPS + r"\s*:\s*([^;{}\n]+)")
_ATTR_COLOR_RE = re.compile(
    r"(?<![\w-])(?:fill|stroke|stop-color|flood-color|color|bgcolor)\s*=\s*[\"']([^\"']*)[\"']", re.I
)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_STYLE_BLOCK = re.compile(r"(<style\b[^>]*>)(.*?)</style\s*>", re.S | re.I)
_DEFAULT_DARK = [
    r"\.dark\b",
    r"\[data-theme=['\"]?dark['\"]?\]",
    r"\[data-mode=['\"]?dark['\"]?\]",
]
_ALLOWED_WORDS = {
    "transparent", "currentcolor", "inherit", "initial", "unset", "none", "revert",
    "revert-layer", "auto",
}

# (foreground token, background token, minimum ratio, required)
DEFAULT_PAIRS = [
    ("foreground", "background", 4.5, True),
    ("card-foreground", "card", 4.5, False),
    ("popover-foreground", "popover", 4.5, False),
    ("primary-foreground", "primary", 4.5, True),
    ("secondary-foreground", "secondary", 4.5, False),
    ("muted-foreground", "background", 4.5, True),
    ("muted-foreground", "card", 4.5, False),
    ("muted-foreground", "muted", 4.5, False),
    ("accent-foreground", "accent", 4.5, False),
    ("highlight-foreground", "highlight", 4.5, False),
    ("ring", "background", 3.0, True),
    ("ring", "card", 3.0, False),
    ("input", "background", 3.0, True),
    ("input", "card", 3.0, False),
]
for _role in ("destructive", "success", "warning", "info"):
    DEFAULT_PAIRS += [
        (f"{_role}-foreground", _role, 4.5, False),
        (f"{_role}-text", "background", 4.5, False),
        (f"{_role}-text", "card", 4.5, False),
        (f"{_role}-text", f"{_role}-subtle", 4.5, False),
        ("foreground", f"{_role}-subtle", 4.5, False),
    ]


def _blank(text):
    return "".join("\n" if ch == "\n" else " " for ch in text)


def _line_of(text, offset):
    return text.count("\n", 0, offset) + 1


# ---------------------------------------------------------------- CSS parsing


def _walk(text, i, preludes, out):
    """Recursive CSS block walker; records (preludes, [(decl_text, start)])."""
    n = len(text)
    chunk_start = i
    decls = []
    while i < n:
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if c == "(":
            depth, j = 1, i + 1
            while j < n and depth:
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                j += 1
            i = j
            continue
        if c == ";":
            decls.append((text[chunk_start:i], chunk_start))
            chunk_start = i + 1
            i += 1
            continue
        if c == "{":
            prelude = " ".join(text[chunk_start:i].split())
            i = _walk(text, i + 1, preludes + [prelude], out)
            chunk_start = i
            continue
        if c == "}":
            if text[chunk_start:i].strip():
                decls.append((text[chunk_start:i], chunk_start))
            out.append((preludes, decls))
            return i + 1
        i += 1
    if text[chunk_start:i].strip():
        decls.append((text[chunk_start:i], chunk_start))
    out.append((preludes, decls))
    return n


def _css_blocks(text):
    cleaned = re.sub(r"/\*.*?\*/", lambda m: _blank(m.group(0)), text, flags=re.S)
    out = []
    _walk(cleaned, 0, [], out)
    return cleaned, out


def _scope(preludes, dark_res):
    joined = " ".join(preludes)
    if re.search(r"prefers-color-scheme\s*:\s*dark", joined) or any(r.search(joined) for r in dark_res):
        return "dark"
    for prelude in preludes:
        p = prelude.strip()
        if p.startswith("@theme") or ":root" in p or re.match(r"(?:html|:host)\b", p):
            return "base"
        if re.search(r"\.light\b|\[data-theme=['\"]?light['\"]?\]", p):
            return "base"
    return None


def parse_theme_text(text, dark_selectors=None, into=None):
    """Read custom properties from theme CSS text.

    Returns {"base": {...}, "dark": {...}} with names lacking the leading "--";
    pass a previous result as into to accumulate several files.
    """
    dark_res = [re.compile(p) for p in (dark_selectors or _DEFAULT_DARK)]
    result = into if into is not None else {"base": {}, "dark": {}}
    _, blocks = _css_blocks(text)
    for preludes, decls in blocks:
        scope = _scope(preludes, dark_res)
        if scope is None:
            continue
        target = result["dark"] if scope == "dark" else result["base"]
        for decl, _start in decls:
            decl = decl.strip()
            if not decl.startswith("--") or ":" not in decl:
                continue
            name, value = decl.split(":", 1)
            value = re.sub(r"!important\s*$", "", value.strip()).strip()
            target[name.strip()[2:]] = value
    return result


def parse_theme_files(paths, dark_selectors=None):
    """Read custom properties from theme CSS files.

    Returns {"light": {name: value}, "dark": {name: value}}; names have no
    leading "--". Dark values fall back to light ones when not overridden.
    """
    acc = {"base": {}, "dark": {}}
    for path in paths:
        text = common.read_text(path)
        if text is not None:
            parse_theme_text(text, dark_selectors, acc)
    merged_dark = dict(acc["base"])
    merged_dark.update(acc["dark"])
    return {"light": dict(acc["base"]), "dark": merged_dark}


def resolve_value(value, env, depth=0):
    """Substitute var() references from env (names without "--"); None if unresolvable."""
    if value is None or depth > 25:
        return None
    out, i = [], 0
    while True:
        k = value.find("var(", i)
        if k == -1:
            out.append(value[i:])
            break
        out.append(value[i:k])
        j, level = k + 4, 1
        while j < len(value) and level:
            if value[j] == "(":
                level += 1
            elif value[j] == ")":
                level -= 1
            j += 1
        inner = value[k + 4:j - 1]
        name, _, fallback = inner.partition(",")
        name = name.strip()
        if name.startswith("--") and name[2:] in env:
            replacement = resolve_value(env[name[2:]], env, depth + 1)
        elif fallback.strip():
            replacement = resolve_value(fallback.strip(), env, depth + 1)
        else:
            replacement = None
        if replacement is None:
            return None
        out.append(replacement)
        i = j
    return "".join(out).strip()


def _color(env, name):
    raw = env.get(name)
    if raw is None:
        return None, f"--{name} is not defined"
    resolved = resolve_value(raw, env)
    if resolved is None:
        return None, f"--{name} references an undefined variable"
    parsed = colors.parse_color(resolved)
    if parsed is None:
        return None, f"--{name} is not a color this check can evaluate ({resolved})"
    return parsed, None


def evaluate_contrast(themes, pairs=None):
    """Check token pairs in each theme.

    themes is the dict from parse_theme_files. Each result is a dict with
    theme, fg, bg, min, ratio (or None), status ("pass", "fail", "skip",
    "missing") and note.
    """
    pairs = pairs or DEFAULT_PAIRS
    results = []
    for theme_name in ("light", "dark"):
        env = themes.get(theme_name) or {}
        if not env:
            continue
        canvas = (1.0, 1.0, 1.0) if theme_name == "light" else (0.0, 0.0, 0.0)
        page, _ = _color(env, "background")
        page_rgb = colors.composite(page, canvas) if page else canvas
        for fg_name, bg_name, minimum, required in pairs:
            fg, fg_note = _color(env, fg_name)
            bg, bg_note = _color(env, bg_name)
            entry = {"theme": theme_name, "fg": fg_name, "bg": bg_name, "min": minimum, "ratio": None}
            if fg is None or bg is None:
                entry["status"] = "missing" if required else "skip"
                entry["note"] = fg_note or bg_note
                results.append(entry)
                continue
            bg_rgb = colors.composite(bg, page_rgb)
            fg_rgb = colors.composite(fg, bg_rgb)
            ratio = colors.contrast_ratio(fg_rgb, bg_rgb)
            entry["ratio"] = round(ratio, 2)
            entry["status"] = "pass" if ratio + 1e-9 >= minimum else "fail"
            entry["note"] = ""
            results.append(entry)
    return results


def _pairs_from_config(cfg):
    """Default pairs plus the configured ones; a configured pair with the same
    fg and bg replaces the default (to change its minimum or make it optional)."""
    pairs = {(fg, bg): (fg, bg, minimum, required) for fg, bg, minimum, required in DEFAULT_PAIRS}
    for item in cfg["design"].get("contrastPairs") or []:
        try:
            fg, bg = item["fg"], item["bg"]
            minimum = float(item.get("min", 4.5))
        except (KeyError, TypeError, ValueError) as exc:
            raise SystemExit(f"error: invalid design.contrastPairs entry {item!r}: {exc}") from exc
        pairs[(fg, bg)] = (fg, bg, minimum, bool(item.get("required", False)))
    return list(pairs.values())


def _theme_paths(root, cfg):
    return [root / p for p in cfg["design"]["themeFiles"] if (root / p).is_file()]


# ------------------------------------------------------------ literal scanning


def _words(value):
    return [w for w in re.split(r"[\s,()'\"/]+", value.lower()) if w]


def _scan_value(value, base, text, findings):
    """Literals inside a CSS value starting at offset base."""
    for m in _HEX_RE.finditer(value):
        findings.append((base + m.start(), m.group(0)))
    for m in _FUNC_RE.finditer(value):
        findings.append((base + m.start(), m.group(0) + "...)"))


def _scan_css(css, offset, text, findings, check_named=True):
    _, blocks = _css_blocks(css)
    for _preludes, decls in blocks:
        for decl, start in decls:
            stripped = decl.strip()
            if stripped.startswith("@apply"):
                for m in _TW_RE.finditer(decl):
                    findings.append((offset + start + m.start(), m.group(0)))
                continue
            if ":" not in decl or stripped.startswith("--"):
                continue
            prop, value = decl.split(":", 1)
            value_start = offset + start + len(prop) + 1
            _scan_value(value, value_start, text, findings)
            if check_named and re.fullmatch(_COLOR_PROPS, prop.strip(), re.I):
                for word in _words(value):
                    if word in colors.NAMED_COLORS and word not in _ALLOWED_WORDS:
                        findings.append((value_start + value.lower().find(word), word))


def _scan_markup(code, text, findings):
    """Literals in markup, scripts and JSX (code has comments blanked)."""
    for m in _HEX_RE.finditer(code):
        before = code[max(0, m.start() - 40):m.start()]
        if _ATTR_BEFORE.search(before) or _URL_BEFORE.search(before):
            continue
        findings.append((m.start(), m.group(0)))
    for m in _FUNC_RE.finditer(code):
        findings.append((m.start(), m.group(0) + "...)"))
    for m in _TW_RE.finditer(code):
        findings.append((m.start(), m.group(0)))
    for regex in (_DECL_RE, _ATTR_COLOR_RE):
        for m in regex.finditer(code):
            value = m.group(1)
            for word in _words(value):
                if word in colors.NAMED_COLORS and word not in _ALLOWED_WORDS:
                    findings.append((m.start(1) + value.lower().find(word), word))


def _find_literals(path, text):
    ext = Path(path).suffix.lower()
    findings = []
    if ext in _CSS_EXTS:
        _scan_css(text, 0, text, findings)
    else:
        code = _HTML_COMMENT.sub(lambda m: _blank(m.group(0)), text)
        if ext in _JS_EXTS:
            code = common.strip_js_comments_and_strings(code, keep_strings=True)
        else:
            for _attrs, body, start in common.extract_script_blocks(code):
                stripped = common.strip_js_comments_and_strings(body, keep_strings=True)
                code = code[:start] + stripped + code[start + len(body):]
        for m in _STYLE_BLOCK.finditer(code):
            css_start = m.start(2)
            _scan_css(m.group(2), css_start, text, findings)
            code = code[:css_start] + _blank(m.group(2)) + code[m.end(2):]
        _scan_markup(code, text, findings)
    lines = text.splitlines()
    seen, result = set(), []
    for offset, literal in sorted(findings):
        line = _line_of(text, offset)
        if line - 1 < len(lines) and _IGNORE in lines[line - 1]:
            continue
        key = (line, literal.lower())
        if key in seen:
            continue
        seen.add(key)
        result.append((line, literal))
    return result


def _literals(root, cfg, staged):
    design = cfg["design"]
    allowed = list(design["themeFiles"]) + list(design.get("allowLiteralsIn") or [])
    exts = set(design["extensions"])
    errors = []
    if staged:
        changes = common.git_staged_changes(root)
        if changes is None:
            return common.report(["--staged needs a git repository"])
        candidates = [(path, None) for status, path, _old in changes if status in "AMRC"]
    else:
        candidates = [(path, None) for path in common.list_project_files(root)]
    checked = 0
    for rel, _ in candidates:
        if Path(rel).suffix.lower() not in exts:
            continue
        if common.is_excluded(rel, design["exclude"]) or common.any_glob_match(rel, allowed):
            continue
        text = common.read_staged_text(root, rel) if staged else common.read_text(root / rel)
        if text is None:
            continue
        checked += 1
        for line, literal in _find_literals(rel, text):
            errors.append(f"{rel}:{line}: color literal `{literal}`; use a theme token (docs/DESIGN.md)")
    return common.report(errors, ok=f"no color literals outside theme files ({checked} files checked)")


def _contrast(root, cfg, as_json):
    paths = _theme_paths(root, cfg)
    if not paths:
        return common.report(
            ["no theme file found; set design.themeFiles in quality.config.json"]
        )
    themes = parse_theme_files(paths, cfg["design"]["darkSelectors"])
    results = evaluate_contrast(themes, _pairs_from_config(cfg))
    if as_json:
        print(json.dumps({"files": [str(p.relative_to(root)) for p in paths], "results": results}, indent=2))
    else:
        current = None
        for r in results:
            if r["theme"] != current:
                current = r["theme"]
                print(f"{current} theme ({', '.join(str(p.relative_to(root)) for p in paths)})")
            if r["status"] in ("pass", "fail"):
                print(f"  {r['status']:4}  {r['ratio']:5.2f}  {r['fg']} on {r['bg']} (min {r['min']})")
            elif r["status"] == "missing":
                print(f"  MISS         {r['fg']} on {r['bg']}: {r['note']}")
    errors = [
        f"{r['theme']}: {r['fg']} on {r['bg']} is {r['ratio']}:1, needs {r['min']}:1"
        for r in results if r["status"] == "fail"
    ]
    errors += [
        f"{r['theme']}: required pair {r['fg']} on {r['bg']}: {r['note']}"
        for r in results if r["status"] == "missing"
    ]
    checked = sum(1 for r in results if r["status"] in ("pass", "fail"))
    if checked == 0:
        errors.append("no token pairs could be evaluated")
    if as_json:
        return 1 if errors else 0
    return common.report(errors, ok=f"all {checked} token pairs meet WCAG AA")


def main(argv=None):
    """Command-line entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=".", help="project root (default: current directory)")
    parser.add_argument("--config", help="config file (default: <root>/quality.config.json)")
    sub = parser.add_subparsers(dest="command", required=True)
    lit = sub.add_parser("literals", help="find color literals outside theme files")
    lit.add_argument("--staged", action="store_true", help="check staged files only")
    con = sub.add_parser("contrast", help="check token contrast in light and dark themes")
    con.add_argument("--json", action="store_true", help="print machine-readable results")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    cfg = common.load_config(root, args.config)
    if args.command == "literals":
        return _literals(root, cfg, args.staged)
    return _contrast(root, cfg, args.json)


if __name__ == "__main__":
    sys.exit(main())
