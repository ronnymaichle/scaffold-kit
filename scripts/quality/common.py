"""Shared helpers for the scaffold-kit quality scripts.

Standard library only, Python 3.9+. Vendored into projects as scripts/quality/;
change behaviour through quality.config.json, not by editing these files.
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
from pathlib import Path

__all__ = [
    "KIT_VERSION",
    "load_config",
    "list_project_files",
    "glob_match",
    "any_glob_match",
    "is_excluded",
    "strip_js_comments_and_strings",
    "extract_script_blocks",
    "git_staged_changes",
    "read_staged_text",
    "read_text",
    "report",
]

KIT_VERSION = "2.1.1"

_DEFAULTS = {
    "folderDocs": {
        "docFile": "CLAUDE.md",
        # Names without a slash match a folder at any depth; "/name" matches only at
        # the project root; other entries with a slash are path globs.
        "exclude": [
            "node_modules", "__pycache__", "venv", "vendor", "playwright-report",
            "test-results", "/build", "/dist", "/out", "/coverage", "/logs", "/tmp",
            "/target", "/docs", "/static", "/public",
        ],
        "excludeHidden": True,
        # Empty means every folder is enforced; otherwise only these folders and their subfolders.
        "include": [],
        "extensions": [
            ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".svelte", ".vue",
            ".astro", ".py", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".swift",
            ".sql", ".css", ".scss", ".sass", ".less", ".html", ".sh", ".json", ".yaml",
            ".yml", ".toml",
        ],
        "ignoreFiles": [
            "*.lock", "*.lockb", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
            "go.sum", "*.min.js", "*.min.css", "*.map", "*.gen.*", "*.generated.*",
        ],
        "symbolCheck": True,
        "symbolCheckSkip": [
            "*.test.*", "*.spec.*", "test_*.py", "*_test.py", "conftest.py", "*_test.go",
        ],
        "codemapFile": "docs/CODEMAP.md",
    },
    "design": {
        # Files that define the theme tokens; literals are allowed only there.
        "themeFiles": ["src/lib/theme/theme.css", "src/app.css"],
        "allowLiteralsIn": [],
        "extensions": [
            ".svelte", ".tsx", ".jsx", ".vue", ".astro", ".html", ".css", ".scss", ".sass",
            ".less",
        ],
        "exclude": ["node_modules", "/build", "/dist", "/coverage", "/docs"],
        # Pairs checked in addition to the defaults in design_tokens.py, as
        # {"fg": "sidebar-foreground", "bg": "sidebar", "min": 4.5, "required": true};
        # a pair with the same fg and bg as a default replaces it.
        "contrastPairs": [],
        "darkSelectors": [
            r"\.dark\b",
            r"\[data-theme=['\"]?dark['\"]?\]",
            r"\[data-mode=['\"]?dark['\"]?\]",
        ],
    },
    "debug": {
        "exclude": ["node_modules", "/build", "/dist", "/coverage"],
    },
    "sources": {
        "file": "docs/SOURCES.md",
        # Claude Code project settings that receive the WebFetch allow rules;
        # null turns the rules off and checks only the sources file.
        "settingsFile": ".claude/settings.json",
        # Hosts where anyone can publish (code hosts, registries, blogs, forums,
        # community threads, social media). They may be linked but are never
        # pre-approved, because a page there can carry instructions written by an
        # attacker.
        "neverPreapprove": [
            "github.com", "*.github.com", "*.github.io", "*.githubusercontent.com",
            "gitlab.com", "bitbucket.org", "npmjs.com", "*.npmjs.com", "pypi.org",
            "crates.io", "pkg.go.dev", "medium.com", "*.medium.com", "substack.com",
            "*.substack.com", "dev.to", "reddit.com", "*.reddit.com",
            "stackoverflow.com", "*.stackexchange.com", "news.ycombinator.com",
            "support.google.com", "techcommunity.microsoft.com", "x.com",
            "twitter.com", "youtube.com", "*.youtube.com", "linkedin.com",
            "*.linkedin.com", "pastebin.com",
        ],
        "reviewDays": 180,
    },
}

# Lists that extend the defaults instead of replacing them.
_EXTEND_KEYS = {
    ("folderDocs", "exclude"),
    ("folderDocs", "ignoreFiles"),
    ("folderDocs", "symbolCheckSkip"),
    ("design", "exclude"),
    ("debug", "exclude"),
    ("sources", "neverPreapprove"),
}

_GLOB_CACHE: dict = {}


def load_config(root, path=None):
    """Return the built-in defaults merged with quality.config.json (if present).

    Lists named in _EXTEND_KEYS are appended to the defaults; every other key
    replaces the default value. Raises SystemExit(2) on invalid JSON.
    """
    root = Path(root)
    cfg = copy.deepcopy(_DEFAULTS)
    cfg_path = Path(path) if path else root / "quality.config.json"
    if not cfg_path.is_file():
        return cfg
    try:
        user = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: cannot read {cfg_path}: {exc}") from exc
    if not isinstance(user, dict):
        raise SystemExit(f"error: {cfg_path} must contain a JSON object")
    for section, values in user.items():
        if not isinstance(values, dict):
            cfg[section] = values
            continue
        target = cfg.setdefault(section, {})
        for key, value in values.items():
            if (section, key) in _EXTEND_KEYS and isinstance(value, list):
                target[key] = list(target.get(key, [])) + [v for v in value if v not in target.get(key, [])]
            else:
                target[key] = value
    return cfg


def _run_git(root, args):
    try:
        proc = subprocess.run(
            ["git", "-C", str(root)] + list(args),
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def list_project_files(root):
    """Return project files as sorted POSIX paths relative to root.

    Inside a git work tree this is tracked plus untracked-but-not-ignored files,
    so .gitignore is respected. Outside git it walks the file system, skipping
    hidden folders and common dependency and build folders.
    """
    root = Path(root)
    out = _run_git(root, ["rev-parse", "--is-inside-work-tree"])
    if out is not None and out.strip() == b"true":
        listing = _run_git(root, ["ls-files", "-z", "--cached", "--others", "--exclude-standard"])
        if listing is not None:
            files = set()
            for raw in listing.split(b"\0"):
                if not raw:
                    continue
                rel = raw.decode("utf-8", "surrogateescape")
                if (root / rel).is_file():
                    files.add(rel)
            return sorted(files)
    skip = {"node_modules", "__pycache__", "venv", "dist", "build", "target", "vendor"}
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in skip]
        for name in filenames:
            full = Path(dirpath) / name
            files.append(full.relative_to(root).as_posix())
    return sorted(files)


def _glob_to_regex(pattern):
    out = []
    i, n = 0, len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                i += 2
                if i < n and pattern[i] == "/":
                    i += 1
                    out.append("(?:.*/)?")
                else:
                    out.append(".*")
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "{":
            end = pattern.find("}", i)
            if end == -1:
                out.append(re.escape(c))
            else:
                alternatives = pattern[i + 1:end].split(",")
                out.append("(?:" + "|".join(re.escape(a) for a in alternatives) + ")")
                i = end + 1
                continue
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def glob_match(path, pattern):
    """Match a POSIX path against a glob supporting **, *, ? and {a,b}.

    A pattern without a slash is matched against the last path segment, like
    .gitignore. A pattern ending in /** also matches the folder itself.
    """
    path = str(path).strip("/")
    pattern = str(pattern).strip()
    if not pattern:
        return False
    if "/" not in pattern.strip("/"):
        target = path.rsplit("/", 1)[-1]
        pattern = pattern.strip("/")
    else:
        target = path
        pattern = pattern.strip("/")
        if pattern.endswith("/**") and target == pattern[:-3]:
            return True
    regex = _GLOB_CACHE.get(pattern)
    if regex is None:
        regex = _glob_to_regex(pattern)
        _GLOB_CACHE[pattern] = regex
    return bool(regex.match(target))


def any_glob_match(path, patterns):
    """True when path matches at least one glob in patterns."""
    return any(glob_match(path, p) for p in patterns or [])


def _full_match(path, pattern):
    regex = _GLOB_CACHE.get(("full", pattern))
    if regex is None:
        regex = _glob_to_regex(pattern)
        _GLOB_CACHE[("full", pattern)] = regex
    return bool(regex.match(path))


def is_excluded(path, entries, hidden=True):
    """True when path, or a folder above it, is excluded.

    Entry forms: "name" matches any path segment (any depth), "/name" matches
    from the project root only, "a/b" or "a/**" is a glob on the path. With
    hidden=True any segment starting with "." is excluded too.
    """
    path = str(path).strip("/")
    if not path:
        return False
    parts = path.split("/")
    if hidden and any(part.startswith(".") for part in parts):
        return True
    prefixes = ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]
    for entry in entries or []:
        entry = str(entry).strip()
        if not entry:
            continue
        pattern = entry.strip("/")
        if entry.startswith("/") or "/" in pattern:
            if any(_full_match(prefix, pattern) for prefix in prefixes):
                return True
        elif any(_full_match(part, pattern) for part in parts):
            return True
    return False


def _blank(text):
    return "".join("\n" if ch == "\n" else " " for ch in text)


def strip_js_comments_and_strings(text, keep_strings=False):
    """Blank out comments (and string contents unless keep_strings) in JS/TS code.

    Lengths and line breaks are preserved, so offsets and line numbers still
    match the original. Quote characters are kept; template literal
    expressions (${...}) stay as code. Regex literals are not recognised.
    """
    res = []
    i, n = 0, len(text)
    depth = 0
    template_stack = []
    in_template = False
    while i < n:
        c = text[i]
        if in_template:
            if c == "\\":
                chunk = text[i:i + 2]
                res.append(chunk if keep_strings else _blank(chunk))
                i += 2
                continue
            if c == "`":
                res.append(c)
                in_template = False
                i += 1
                continue
            if c == "$" and i + 1 < n and text[i + 1] == "{":
                res.append("${")
                template_stack.append(depth)
                depth += 1
                in_template = False
                i += 2
                continue
            res.append(c if keep_strings or c == "\n" else " ")
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            end = text.find("\n", i)
            end = n if end == -1 else end
            res.append(_blank(text[i:end]))
            i = end
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            end = n if end == -1 else end + 2
            res.append(_blank(text[i:end]))
            i = end
            continue
        if c in "'\"":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            j = min(j, n)
            body = text[i + 1:j]
            res.append(c + (body if keep_strings else _blank(body)))
            if j < n and text[j] == c:
                res.append(c)
                j += 1
            i = j
            continue
        if c == "`":
            res.append(c)
            in_template = True
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if template_stack and template_stack[-1] == depth:
                template_stack.pop()
                res.append(c)
                in_template = True
                i += 1
                continue
        res.append(c)
        i += 1
    return "".join(res)


_SCRIPT_BLOCK = re.compile(r"<script\b([^>]*)>(.*?)</script\s*>", re.S | re.I)
_ASTRO_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---", re.S)


def extract_script_blocks(text):
    """Return (attributes, body, start_offset) for each <script> block.

    Astro frontmatter (--- ... ---) is returned as a block with attributes
    "frontmatter". Offsets point into the original text.
    """
    blocks = []
    fm = _ASTRO_FRONTMATTER.match(text)
    if fm:
        blocks.append(("frontmatter", fm.group(1), fm.start(1)))
    for m in _SCRIPT_BLOCK.finditer(text):
        blocks.append((m.group(1), m.group(2), m.start(2)))
    return blocks


def git_staged_changes(root):
    """Return staged changes under root as (status, path, old_path) tuples.

    status is A, C, D, M, R, T or U; old_path is set for renames and copies.
    Paths are POSIX and relative to root. Returns None outside a git work tree.
    """
    out = _run_git(root, ["diff", "--cached", "--relative", "--name-status", "-z", "-M"])
    if out is None:
        return None
    parts = [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0")]
    changes = []
    i = 0
    while i < len(parts):
        status = parts[i]
        if not status:
            i += 1
            continue
        letter = status[0]
        if letter in "RC":
            old, new = parts[i + 1], parts[i + 2]
            changes.append((letter, new, old))
            i += 3
        else:
            changes.append((letter, parts[i + 1], None))
            i += 2
    return changes


def read_staged_text(root, path):
    """Return the staged (index) content of path as text, or None if unavailable or binary."""
    out = _run_git(root, ["show", ":./" + str(path)])
    if out is None or b"\0" in out[:8000]:
        return None
    return out.decode("utf-8", "replace")


def read_text(path, limit=2_000_000):
    """Return a file's text, or None when it is missing, too large or binary."""
    try:
        path = Path(path)
        if path.stat().st_size > limit:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8000]:
        return None
    return data.decode("utf-8", "replace")


def report(errors, warnings=(), ok="ok"):
    """Print warnings and errors one per line; return 1 if there are errors, else 0."""
    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}")
    if errors:
        print(f"{len(errors)} problem(s) found")
        return 1
    print(ok)
    return 0
