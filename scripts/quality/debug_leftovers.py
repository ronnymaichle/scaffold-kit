#!/usr/bin/env python3
"""Debug leftovers check (scaffold-kit).

Fails when code contains temporary investigation lines (tagged with the marker
built in _MARKER: the word DEBUG, a hyphen and TEMP), or debugger statements: `debugger` in JS/TS/Svelte/Vue/Astro scripts,
breakpoint() and pdb/ipdb/pudb .set_trace() in Python. Markdown and text files
are ignored, so docs can mention the marker. Words inside comments and strings
do not count, except the marker, which is meant to sit in a comment.

  debug_leftovers.py [--staged]

Configuration: the "debug" section of quality.config.json.
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

__all__ = ["main"]

_MARKER = "DEBUG" + "-TEMP"
_TEXT_EXTS = {".md", ".mdx", ".markdown", ".txt", ".rst"}
_JS_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"}
_MARKUP_EXTS = {".svelte", ".vue", ".astro", ".html", ".htm"}
_DEBUGGER = re.compile(r"(?<![\w$.])debugger(?![\w$])")


def _line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def _js_findings(code, offset_text, base=0):
    cleaned = common.strip_js_comments_and_strings(code)
    return [(_line_of(offset_text, base + m.start()), "debugger statement") for m in _DEBUGGER.finditer(cleaned)]


def _python_findings(text):
    findings = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return findings
    for i, tok in enumerate(tokens):
        if tok.type != tokenize.NAME:
            continue
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if tok.string == "breakpoint" and nxt and nxt.string == "(":
            prev = tokens[i - 1] if i else None
            if not (prev and prev.string in (".", "def")):
                findings.append((tok.start[0], "breakpoint() call"))
        if tok.string == "set_trace" and i >= 2 and tokens[i - 1].string == ".":
            if tokens[i - 2].string in ("pdb", "ipdb", "pudb"):
                findings.append((tok.start[0], f"{tokens[i - 2].string}.set_trace() call"))
    return findings


def _find_leftovers(path, text):
    """Return [(line, description)] for one file's text."""
    ext = Path(path).suffix.lower()
    if ext in _TEXT_EXTS:
        return []
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        if _MARKER in line:
            findings.append((number, f"{_MARKER} line"))
    if ext in _JS_EXTS:
        findings += _js_findings(text, text)
    elif ext in _MARKUP_EXTS:
        for _attrs, body, start in common.extract_script_blocks(text):
            findings += _js_findings(body, text, start)
    elif ext == ".py":
        findings += _python_findings(text)
    return sorted(set(findings))


def main(argv=None):
    """Command-line entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=".", help="project root (default: current directory)")
    parser.add_argument("--config", help="config file (default: <root>/quality.config.json)")
    parser.add_argument("--staged", action="store_true", help="check staged content only")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    cfg = common.load_config(root, args.config)
    exclude = cfg["debug"]["exclude"]
    if args.staged:
        changes = common.git_staged_changes(root)
        if changes is None:
            return common.report(["--staged needs a git repository"])
        paths = [path for status, path, _old in changes if status in "AMRC"]
    else:
        paths = common.list_project_files(root)
    errors = []
    for rel in paths:
        if common.is_excluded(rel, exclude):
            continue
        text = common.read_staged_text(root, rel) if args.staged else common.read_text(root / rel)
        if text is None:
            continue
        for line, what in _find_leftovers(rel, text):
            errors.append(f"{rel}:{line}: {what}; remove it before committing")
    return common.report(errors, ok="no debug leftovers")


if __name__ == "__main__":
    sys.exit(main())
