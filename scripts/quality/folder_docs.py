#!/usr/bin/env python3
"""Folder docs and code map (scaffold-kit).

Every folder with source, test or config files has a CLAUDE.md listing each
file, its exported symbols (and component props) and each subfolder, so Claude
can find code from short indexes instead of reading whole files.

  check             verify every folder doc and the code map; exit 1 on problems
  staged            pre-commit: files added, removed or renamed need their folder
                    doc staged too; then check the touched folders
  init              create missing folder docs and append missing entries, marked
                    TODO(describe), and write each file's Depends on line; never
                    removes or rewrites other text
  codemap [--check] write docs/CODEMAP.md, or only verify it is current
  deps FILE...      print what each file imports and what imports it

Format rules the check relies on (see references/folder-docs.md in the kit):
  "Purpose: ..." line; "## Files" with one "### <file name or glob>" per file;
  symbol bullets start with a backticked name ("- `createMarker(db, input)` -> ...");
  "- Props: `a: T`, `b`" and "- Also exports: `X`, `Y`" bullets list several names;
  "Depends on: `src/lib/db.ts`, `internal/store/`" lists the project files a file
  imports (Go: package folders), by path from the project root; init writes it;
  "## Subfolders" bullets start with a backticked folder name ("- `uploads/`: ...").
Configuration: the "folderDocs" section of quality.config.json.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

__all__ = ["main"]

_TODO = "TODO" + "(describe)"
_H2 = re.compile(r"^##\s+(.+?)\s*$")
_H3 = re.compile(r"^###\s+(.+?)\s*$")
_BULLET = re.compile(r"^\s*[-*]\s+(.*)$")
_TICKS = re.compile(r"`([^`]+)`")
_IDENT = re.compile(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*")
_GLOB_CHARS = set("*?[{")
_JS_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"}
_OPTIONAL_SECTIONS = (
    "<!-- Optional sections, add when they say something useful: ## Conventions, "
    "## Security and privacy, ## State and scaling, ## Errors, logs and analytics, ## Gotchas -->"
)


class _Entry:
    def __init__(self, name, line):
        self.name = name
        self.line = line
        self.end = line
        self.has_description = False
        self.symbols = set()
        self.props = set()
        self.depends = None  # items of the first Depends on line, in written order
        self.depends_lines = []


class _Doc:
    def __init__(self):
        self.purpose = None
        self.files = {}
        self.subfolders = set()
        self.todo_lines = []
        self.lines = []
        self.sections = {}  # lowercase heading -> (start_line, end_line)


def _leading_ident(text):
    m = _IDENT.match(text.strip())
    return m.group(0) if m else None


def _parse_doc(text):
    doc = _Doc()
    doc.lines = text.splitlines()
    section, entry, fenced = None, None, False
    for idx, line in enumerate(doc.lines):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if _TODO in line:
            doc.todo_lines.append(idx + 1)
        if line.lstrip().startswith("<!--"):
            continue
        if doc.purpose is None and line.startswith("Purpose:"):
            doc.purpose = line[len("Purpose:"):].strip()
            continue
        m = _H2.match(line)
        if m:
            section = m.group(1).strip().lower()
            doc.sections[section] = [idx, idx]
            entry = None
            continue
        if section is not None and line.strip():
            doc.sections[section][1] = idx
        if section == "files":
            m = _H3.match(line)
            if m:
                name = m.group(1).strip().strip("`").strip()
                entry = _Entry(name, idx)
                doc.files[name] = entry
                continue
            if entry is None or not line.strip():
                continue
            entry.end = idx
            b = _BULLET.match(line)
            body = (b.group(1) if b else line).strip()
            if body.lower().startswith("depends on:"):
                entry.depends_lines.append(idx)
                if entry.depends is None:
                    rest = body[len("depends on:"):]
                    entry.depends = _TICKS.findall(rest) or [t.strip() for t in rest.split(",") if t.strip()]
                continue
            if not b:
                entry.has_description = True
                continue
            lower = body.lower()
            if lower.startswith("props:"):
                for tick in _TICKS.findall(body):
                    ident = _leading_ident(tick)
                    if ident:
                        entry.props.add(ident)
            elif lower.startswith("also exports:"):
                for tick in _TICKS.findall(body):
                    ident = _leading_ident(tick)
                    if ident:
                        entry.symbols.add(ident)
            elif body.startswith("`"):
                first = _TICKS.match(body)
                ident = _leading_ident(first.group(1)) if first else None
                if ident:
                    entry.symbols.add(ident)
        elif section == "subfolders":
            b = _BULLET.match(line)
            if b:
                tick = _TICKS.search(b.group(1))
                name = tick.group(1) if tick else b.group(1).split(":")[0]
                name = name.strip().strip("/")
                if name:
                    doc.subfolders.add(name)
    return doc


# ------------------------------------------------------------ symbol extraction

_JS_DECL = [
    re.compile(r"\bexport\s+(?:declare\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)"),
    re.compile(r"\bexport\s+(?:declare\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"\bexport\s+(?:declare\s+)?(?:const\s+)?enum\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"\bexport\s+(?:declare\s+)?(?:type|interface|namespace|module)\s+([A-Za-z_$][\w$]*)"),
]
_JS_VAR = re.compile(r"\bexport\s+(?:declare\s+)?(?:const|let|var|using)\s+([A-Za-z_$][\w$]*)")
_JS_DESTRUCT = re.compile(r"\bexport\s+(?:const|let|var)\s+[{\[]([^}\]]*)[}\]]")
_JS_LIST = re.compile(r"\bexport\s+(?:type\s+)?\{([^}]*)\}")
_JS_STAR = re.compile(r"\bexport\s*\*\s*(?:as\s+([A-Za-z_$][\w$]*)\s*)?from\b")
_JS_DEFAULT = re.compile(r"\bexport\s+default\b\s*(?:async\s+)?(function|class)?\s*\*?\s*([A-Za-z_$][\w$]*)?")
_CJS_PROP = re.compile(r"(?<![\w$.])(?:module\.)?exports\.([A-Za-z_$][\w$]*)\s*=(?![=>])")
_CJS_ASSIGN = re.compile(r"(?<![\w$.])module\.exports\s*=(?![=>])\s*")
_KEY_PREFIX = re.compile(r"^(?:(?:async|get|set|static)\s+)*\*?\s*")


def _cjs_exports(code):
    """CommonJS exports: names from exports.x = ... and module.exports = { ... }."""
    names = set(_CJS_PROP.findall(code))
    wildcard = False
    for m in _CJS_ASSIGN.finditer(code):
        if not code.startswith("{", m.end()):
            wildcard = True  # module.exports = someFunction or another module
            continue
        close_at = _matching_brace(code, m.end())
        if close_at == -1:
            wildcard = True
            continue
        for item in _split_top_level(code[m.end() + 1:close_at]):
            item = _KEY_PREFIX.sub("", item.strip())
            if not item:
                continue
            ident = None if item.startswith("...") else _leading_ident(item)
            if ident:
                names.add(ident)
            else:
                wildcard = True  # spread or computed key
    return names, wildcard


def _js_exports(code):
    """Exported names from JS/TS code whose comments and strings are blanked."""
    names, wildcard = _cjs_exports(code)
    for regex in _JS_DECL:
        names.update(regex.findall(code))
    for name in _JS_VAR.findall(code):
        if name != "enum":
            names.add(name)
    for body in _JS_DESTRUCT.findall(code):
        for part in body.split(","):
            part = part.split("=")[0].strip()
            if ":" in part:
                part = part.split(":")[1].strip()
            ident = _leading_ident(part.lstrip("."))
            if ident and not part.startswith("..."):
                names.add(ident)
    for body in _JS_LIST.findall(code):
        for item in body.split(","):
            item = item.strip()
            if not item:
                continue
            item = re.sub(r"^type\s+", "", item)
            name = item.split(" as ")[-1].strip()
            ident = _leading_ident(name)
            if ident:
                names.add(ident)
    for alias in _JS_STAR.findall(code):
        if alias:
            names.add(alias)
        else:
            wildcard = True
    for kind, name in _JS_DEFAULT.findall(code):
        if not (kind and name):
            names.add("default")
    return names, wildcard


def _split_top_level(text):
    """Split on commas outside brackets and generic type arguments.

    "<" opens type arguments only right after a name (Map<K, V>); ">" closes
    them unless it belongs to an arrow (=>), so comparisons and arrow-function
    defaults do not swallow the items after them.
    """
    parts, current = [], []
    depth = angle = 0
    prev = ""
    for ch in text:
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth = max(0, depth - 1)
        elif ch == "<" and (prev.isalnum() or prev in "_$"):
            angle += 1
        elif ch == ">" and angle and prev != "=":
            angle -= 1
        if ch == "," and depth == 0 and angle == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
        prev = ch
    parts.append("".join(current))
    return parts


def _matching_brace(code, start):
    depth = 0
    for i in range(start, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _svelte_props(code):
    """Props from Svelte 5 $props() destructuring or Svelte 4 `export let`; None if unknowable."""
    props = set()
    found_props_call = False
    for m in re.finditer(r"\blet\s*\{", code):
        open_at = code.index("{", m.start())
        close_at = _matching_brace(code, open_at)
        if close_at == -1:
            continue
        rest = code[close_at + 1:close_at + 200]
        if not re.match(r"\s*(?::\s*[^=;]+)?=\s*\$props\s*\(", rest):
            continue
        found_props_call = True
        for item in _split_top_level(code[open_at + 1:close_at]):
            item = item.strip()
            if not item or item.startswith("..."):
                continue
            ident = _leading_ident(item)
            if ident:
                props.add(ident)
    if not found_props_call and re.search(r"\$props\s*\(", code):
        return None
    props.update(re.findall(r"\bexport\s+let\s+([A-Za-z_$][\w$]*)", code))
    return props


def _svelte_exports(text):
    symbols, props, wildcard = set(), set(), False
    instance_seen = False
    for attrs, body, _start in common.extract_script_blocks(text):
        code = common.strip_js_comments_and_strings(body)
        is_module = re.search(r"\bcontext\s*=\s*['\"]module['\"]", attrs) or re.search(
            r"(?<![\w-])module(?![\w-])", attrs
        )
        if is_module:
            names, wild = _js_exports(code)
            symbols |= names
            wildcard = wildcard or wild
        else:
            instance_seen = True
            found = _svelte_props(code)
            if found is None:
                props = None
            elif props is not None:
                props |= found
    if not instance_seen and props is not None and not props:
        props = set()
    return symbols, props, wildcard


def _python_exports(text):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            try:
                return {str(v) for v in ast.literal_eval(node.value)}
            except (ValueError, TypeError):
                break
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return {n for n in names if not n.startswith("_")}


def _go_exports(text):
    code = common.strip_js_comments_and_strings(text)
    names = set()
    func = re.compile(
        r"^func\s+(?:\(\s*(?:[A-Za-z_]\w*\s+)?\*?\s*([A-Za-z_]\w*)(?:\[[^\]]*\])?\s*\)\s*)?([A-Z]\w*)", re.M
    )
    for recv, name in func.findall(code):
        names.add(f"{recv}.{name}" if recv else name)
    names.update(re.findall(r"^(?:type|var|const)\s+([A-Z]\w*)", code, re.M))
    for block in re.findall(r"^(?:type|var|const)\s*\((.*?)^\)", code, re.M | re.S):
        for line in block.splitlines():
            m = re.match(r"\s*([A-Z]\w*)\b", line)
            if m:
                names.add(m.group(1))
    return names


def _symbols_for(path):
    """Return (symbols, props, wildcard); None for a kind that is not checked."""
    text = common.read_text(path)
    if text is None:
        return None, None, False
    ext = path.suffix.lower()
    if ext in _JS_EXTS:
        names, wildcard = _js_exports(common.strip_js_comments_and_strings(text))
        return names, None, wildcard
    if ext == ".svelte":
        return _svelte_exports(text)
    if ext == ".py":
        return _python_exports(text), None, False
    if ext == ".go":
        return _go_exports(text), None, False
    return None, None, False


# ------------------------------------------------------------ import extraction

_IMPORT_FROM = re.compile(r"(?<![\w$.])(?:import|export)\b[^'\";]*?\bfrom\s*(['\"])([^'\"\n]+)\1")
_IMPORT_BARE = re.compile(r"(?<![\w$.])import\s*(['\"])([^'\"\n]+)\1")
_IMPORT_CALL = re.compile(r"(?<![\w$.])(?:import|require)\s*\(\s*(['\"])([^'\"\n]+)\1\s*\)")
_SCRIPT_EXTS = {".svelte", ".vue", ".astro"}
_IMPORT_EXTS = _JS_EXTS | _SCRIPT_EXTS | {".py", ".go"}
_RESOLVE_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs", ".svelte", ".vue", ".json")
_EXT_SWAPS = {".js": (".ts", ".tsx"), ".jsx": (".tsx",), ".mjs": (".mts",), ".cjs": (".cts",)}


def _js_import_specs(text):
    """Specifiers of imports, re-exports, require() and import() calls in JS/TS code.

    Statements are found in a copy with comments and strings blanked, so code
    quoted in strings is ignored; each specifier is read back at the same
    offsets from a copy that keeps the strings.
    """
    blank = common.strip_js_comments_and_strings(text)
    kept = common.strip_js_comments_and_strings(text, keep_strings=True)
    specs = []
    for regex in (_IMPORT_FROM, _IMPORT_BARE, _IMPORT_CALL):
        for m in regex.finditer(blank):
            spec = kept[m.start(2):m.end(2)].strip()
            if spec:
                specs.append(spec)
    return specs


def _python_imports(text):
    """(level, module, names) for every import statement in Python code."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(0, alias.name, ()) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            found.append((node.level or 0, node.module, tuple(a.name for a in node.names if a.name != "*")))
    return found


def _go_imports(text):
    code = common.strip_js_comments_and_strings(text, keep_strings=True)
    paths = []
    for block in re.findall(r"^import\s*\((.*?)\)", code, re.M | re.S):
        paths += re.findall(r"\"([^\"\n]+)\"", block)
    paths += re.findall(r"^import\s+(?:[\w.]+\s+)?\"([^\"\n]+)\"", code, re.M)
    return paths


def _read_jsonc(path):
    """JSON that may have comments and trailing commas, as tsconfig.json does; None if unreadable."""
    text = common.read_text(path)
    if text is None:
        return None
    code = common.strip_js_comments_and_strings(text, keep_strings=True)
    try:
        return json.loads(re.sub(r",(\s*[}\]])", r"\1", code))
    except ValueError:
        return None


def _root_relative(path, root):
    rel = os.path.relpath(os.path.normpath(str(path)), str(root)).replace(os.sep, "/")
    return None if rel == ".." or rel.startswith("../") else rel


def _ts_settings(path, root, depth=0):
    """(baseUrl, paths) of a tsconfig file and the relative files it extends, as root-relative paths."""
    data = _read_jsonc(path)
    if not isinstance(data, dict):
        return None, {}
    base_url, paths = None, {}
    extends = data.get("extends")
    for parent in extends if isinstance(extends, list) else [extends]:
        if isinstance(parent, str) and parent.startswith(".") and depth < 5:
            target = path.parent / parent
            if target.suffix != ".json":
                target = target.with_name(target.name + ".json")
            parent_base, parent_paths = _ts_settings(target, root, depth + 1)
            base_url = parent_base if parent_base is not None else base_url
            paths = parent_paths or paths
    options = data.get("compilerOptions")
    if not isinstance(options, dict):
        return base_url, paths
    if isinstance(options.get("baseUrl"), str):
        base_url = _root_relative(path.parent / options["baseUrl"], root)
    if isinstance(options.get("paths"), dict):
        anchor = root / base_url if base_url is not None else path.parent
        paths = {}
        for pattern, targets in options["paths"].items():
            if isinstance(targets, list):
                rels = (_root_relative(anchor / t, root) for t in targets if isinstance(t, str))
                paths[pattern] = [r for r in rels if r is not None]
    return base_url, paths


def _condition_target(value):
    """The path a package.json "imports" entry points to, preferring runtime conditions over types."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return next((t for t in map(_condition_target, value) if t), None)
    if isinstance(value, dict):
        for key in ("import", "node", "default", "require", "types"):
            if key in value:
                return _condition_target(value[key])
        return next((t for t in map(_condition_target, value.values()) if t), None)
    return None


def _subpath_imports(root):
    """Node subpath imports ("#lib/*": "./src/lib/*") from package.json, as root-relative targets."""
    package = _read_jsonc(root / "package.json")
    entries = package.get("imports") if isinstance(package, dict) else None
    found = {}
    for key, value in (entries or {}).items() if isinstance(entries, dict) else ():
        target = _condition_target(value)
        rel = _root_relative(root / target, root) if key.startswith("#") and target else None
        if rel:
            found[key] = [rel]
    return found


def _prefix_length(alias):
    return -len(alias[0].split("*")[0])


class _Imports:
    """Resolves the imports of source files to the project files they name."""

    def __init__(self, project):
        self.root = project.root
        self.files = project.sources
        self.dirs = {str(PurePosixPath(f).parent) for f in self.files}
        self.base_url, ts_paths = None, {}
        for name in ("tsconfig.json", "jsconfig.json"):
            if (self.root / name).is_file():
                self.base_url, ts_paths = _ts_settings(self.root / name, self.root)
                break
        configured = []
        for alias, target in (project.cfg.get("aliases") or {}).items():
            alias, target = alias.rstrip("/"), str(target).strip("/")
            configured += [(alias, [target or "."]), (alias + "/*", [f"{target}/*" if target else "*"])]
        known = list(ts_paths.items()) + list(_subpath_imports(self.root).items())
        self.aliases = sorted(known, key=_prefix_length) + sorted(configured, key=_prefix_length)
        m = re.search(r"^module\s+(\S+)", common.read_text(self.root / "go.mod") or "", re.M)
        self.go_module = m.group(1) if m else None
        self._cache = {}

    def of(self, rel):
        """Sorted project files (Go: package folders ending in /) that the file rel imports."""
        if rel not in self._cache:
            self._cache[rel] = sorted(self._targets(rel) - {rel})
        return self._cache[rel]

    def _targets(self, rel):
        text = common.read_text(self.root / rel)
        if text is None:
            return set()
        ext = PurePosixPath(rel).suffix.lower()
        folder = str(PurePosixPath(rel).parent)
        folder = "" if folder == "." else folder
        if ext == ".py":
            return {t for imp in _python_imports(text) for t in self._python(folder, *imp)}
        if ext == ".go":
            return {t for t in map(self._go, _go_imports(text)) if t}
        if ext in _JS_EXTS:
            specs = _js_import_specs(text)
        elif ext in _SCRIPT_EXTS:
            specs = [s for _attrs, body, _start in common.extract_script_blocks(text) for s in _js_import_specs(body)]
        else:
            return set()
        return {t for t in (self._js(folder, spec) for spec in specs) if t}

    def _js(self, folder, spec):
        spec = spec.split("?")[0]
        if spec in (".", "..") or spec.startswith(("./", "../")):
            bases = [posixpath.join(folder, spec)]
        else:
            bases = self._alias_bases(spec)
        for base in bases:
            hit = self._js_file(posixpath.normpath(base))
            if hit:
                return hit
        return None

    def _alias_bases(self, spec):
        bases = []
        for pattern, targets in self.aliases:
            prefix, star, suffix = pattern.partition("*")
            if star and spec.startswith(prefix) and spec.endswith(suffix) and len(spec) >= len(prefix) + len(suffix):
                middle = spec[len(prefix):len(spec) - len(suffix)]
                bases += [t.replace("*", middle, 1) for t in targets]
            elif not star and spec == pattern:
                bases += targets
        if not bases and self.base_url is not None:
            bases.append(posixpath.join(self.base_url, spec))
        return bases

    def _js_file(self, base):
        if base in self.files:
            return base
        stem, ext = posixpath.splitext(base)
        for swap in _EXT_SWAPS.get(ext, ()):
            if stem + swap in self.files:
                return stem + swap
        candidates = [base + e for e in _RESOLVE_EXTS] + [posixpath.join(base, "index" + e) for e in _RESOLVE_EXTS]
        for candidate in candidates:
            candidate = posixpath.normpath(candidate)
            if candidate in self.files:
                return candidate
        return None

    def _python(self, folder, level, module, names):
        """Files a Python import names: the submodules of `from x import y`, otherwise the module.

        Absolute imports are looked up from the project root, then `src/`, then the
        file's own folder (a script's folder is first on sys.path).
        """
        path = module.replace(".", "/") if module else ""
        if level:
            parts = folder.split("/") if folder else []
            if level - 1 > len(parts):
                return []
            package = "/".join(parts[:len(parts) - level + 1])
            bases = [posixpath.join(package, path) if package else path]
        elif path:
            bases = [path, posixpath.join("src", path)] + ([posixpath.join(folder, path)] if folder else [])
        else:
            return []
        for base in bases:
            found = [s for s in (self._py_module(posixpath.join(base, n) if base else n) for n in names) if s]
            if len(found) < len(names) or not names:
                own = self._py_module(base) if base else None
                if own:
                    found.append(own)
            if found:
                return found
        return []

    def _py_module(self, base):
        for candidate in (base + ".py", base + "/__init__.py"):
            if candidate in self.files:
                return candidate
        return None

    def _go(self, path):
        if not self.go_module or not path.startswith(self.go_module + "/"):
            return None
        folder = path[len(self.go_module) + 1:]
        return folder + "/" if folder in self.dirs else None


# ------------------------------------------------------------- project model


class _Project:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg["folderDocs"]
        self.doc_name = self.cfg["docFile"]
        exts = set(self.cfg["extensions"])
        self.files = {}  # folder -> [file names]
        self.sources = set()  # every documentable file, including those at the root
        self.all_dirs = set()
        self._imports = None
        for rel in common.list_project_files(root):
            p = PurePosixPath(rel)
            documentable = (
                p.name != self.doc_name
                and p.suffix.lower() in exts
                and not common.any_glob_match(p.name, self.cfg["ignoreFiles"])
            )
            if len(p.parts) < 2:
                if documentable:
                    self.sources.add(p.as_posix())
                continue
            folder = str(p.parent)
            if common.is_excluded(folder, self.cfg["exclude"], self.cfg.get("excludeHidden", True)):
                continue
            parts = folder.split("/")
            for i in range(1, len(parts) + 1):
                self.all_dirs.add("/".join(parts[:i]))
            if not documentable:
                continue
            self.sources.add(p.as_posix())
            self.files.setdefault(folder, []).append(p.name)
        needed = set()
        for folder in self.files:
            parts = folder.split("/")
            for i in range(1, len(parts) + 1):
                needed.add("/".join(parts[:i]))
        include = self.cfg.get("include") or []
        if include:
            needed = {f for f in needed if self._included(f, include)}
        self.needed = needed

    @staticmethod
    def _included(folder, include):
        for entry in include:
            entry = entry.strip("/")
            if folder == entry or folder.startswith(entry + "/") or common.glob_match(folder, entry):
                return True
        return False

    def children(self, folder):
        prefix = folder + "/"
        return sorted(
            f[len(prefix):] for f in self.needed if f.startswith(prefix) and "/" not in f[len(prefix):]
        )

    def doc_path(self, folder):
        return self.root / folder / self.doc_name

    def symbol_checked(self, name):
        return self.cfg.get("symbolCheck", True) and not common.any_glob_match(name, self.cfg["symbolCheckSkip"])

    def depends_checked(self, name):
        return (
            self.cfg.get("dependsCheck", True)
            and not _is_glob(name)
            and PurePosixPath(name).suffix.lower() in _IMPORT_EXTS
            and not common.any_glob_match(name, self.cfg["symbolCheckSkip"])
        )

    @property
    def imports(self):
        if self._imports is None:
            self._imports = _Imports(self)
        return self._imports


def _is_glob(name):
    return any(ch in _GLOB_CHARS for ch in name)


def _depends_line(targets):
    return "Depends on: " + ", ".join(f"`{t}`" for t in targets)


def _depends_errors(project, folder, name, entry, doc_rel):
    if not project.depends_checked(name):
        return []
    expected = project.imports.of(f"{folder}/{name}")
    if expected and (entry.depends != expected or len(entry.depends_lines) != 1):
        items = ", ".join(f"`{t}`" for t in expected)
        return [f"{doc_rel}: {name}: Depends on should be {items} (run folder_docs.py init)"]
    if not expected and entry.depends_lines:
        return [f"{doc_rel}: {name}: imports no project files, so it needs no Depends on line (run folder_docs.py init)"]
    return []


def _check_folder(project, folder):
    errors, warnings = [], []
    doc_rel = f"{folder}/{project.doc_name}"
    path = project.doc_path(folder)
    if not path.is_file():
        return [f"{folder}/: missing {project.doc_name} (run folder_docs.py init)"], warnings
    doc = _parse_doc(common.read_text(path) or "")
    if not doc.purpose:
        errors.append(f"{doc_rel}: missing 'Purpose:' line")
    if doc.todo_lines:
        lines = ", ".join(str(n) for n in doc.todo_lines[:10])
        errors.append(f"{doc_rel}: {len(doc.todo_lines)} {_TODO} placeholder(s) to replace (lines {lines})")
    actual = sorted(project.files.get(folder, []))
    globs = [name for name in doc.files if _is_glob(name)]
    for name in actual:
        if name not in doc.files and not any(common.glob_match(name, g) for g in globs):
            errors.append(f"{doc_rel}: {name} is not listed under ## Files")
    for name, entry in doc.files.items():
        if _is_glob(name):
            if not any(common.glob_match(a, name) for a in actual):
                warnings.append(f"{doc_rel}: pattern '{name}' matches no files")
            if not entry.has_description:
                errors.append(f"{doc_rel}: entry '{name}' has no description")
            continue
        file_path = project.root / folder / name
        if not file_path.exists():
            errors.append(f"{doc_rel}: lists {name}, which does not exist")
            continue
        if not entry.has_description:
            errors.append(f"{doc_rel}: entry '{name}' has no description")
        if name not in actual:
            continue
        errors += _depends_errors(project, folder, name, entry, doc_rel)
        if not project.symbol_checked(name):
            continue
        symbols, props, wildcard = _symbols_for(file_path)
        if symbols is not None:
            for missing in sorted(symbols - entry.symbols):
                errors.append(f"{doc_rel}: {name} exports `{missing}`, which is not listed")
            if not wildcard:
                for stale in sorted(entry.symbols - symbols):
                    errors.append(f"{doc_rel}: {name} lists `{stale}`, which it does not export")
        if props is not None:
            for missing in sorted(props - entry.props):
                errors.append(f"{doc_rel}: {name} has prop `{missing}`, which is not listed under Props")
            for stale in sorted(entry.props - props):
                errors.append(f"{doc_rel}: {name} lists prop `{stale}`, which it does not have")
    for child in project.children(folder):
        if child not in doc.subfolders:
            errors.append(f"{doc_rel}: subfolder {child}/ is not listed under ## Subfolders")
    for listed in sorted(doc.subfolders):
        if f"{folder}/{listed}" not in project.all_dirs and not (project.root / folder / listed).is_dir():
            errors.append(f"{doc_rel}: lists subfolder {listed}/, which does not exist")
    return errors, warnings


# ------------------------------------------------------------------- codemap


def _codemap_text(project):
    target = project.root / project.cfg["codemapFile"]
    lines = [
        "# Code map",
        "",
        "Generated by `python3 scripts/quality/folder_docs.py codemap`; do not edit by hand.",
        "Find code top-down: pick a folder here, read its CLAUDE.md, then open only the file you need.",
        "",
    ]
    documented = sorted(f for f in project.needed if project.doc_path(f).is_file())
    for folder in documented:
        doc = _parse_doc(common.read_text(project.doc_path(folder)) or "")
        depth = sum(1 for other in documented if folder.startswith(other + "/"))
        link = os.path.relpath(project.doc_path(folder), target.parent).replace(os.sep, "/")
        purpose = doc.purpose or "(no purpose line)"
        lines.append(f"{'  ' * depth}- [`{folder}/`]({link}): {purpose}")
    return "\n".join(lines) + "\n"


def _codemap_errors(project):
    if not project.cfg.get("codemapFile"):
        return []
    path = project.root / project.cfg["codemapFile"]
    expected = _codemap_text(project)
    current = common.read_text(path) if path.is_file() else None
    if current != expected:
        return [f"{project.cfg['codemapFile']} is out of date (run folder_docs.py codemap)"]
    return []


# ---------------------------------------------------------------------- init


def _entry_lines(project, folder, name, existing=None):
    path = project.root / folder / name
    lines = []
    if existing is None:
        lines += [f"### {name}", f"{_TODO}: what this file is responsible for."]
    if _is_glob(name) or not project.symbol_checked(name):
        return lines
    symbols, props, _wild = _symbols_for(path)
    have = existing.symbols if existing else set()
    have_props = existing.props if existing else set()
    for symbol in sorted((symbols or set()) - have):
        lines.append(f"- `{symbol}` {_TODO}: inputs -> output, what it does, side effects")
    missing_props = sorted((props or set()) - have_props)
    if missing_props:
        listed = ", ".join(f"`{p}`" for p in missing_props)
        lines.append(f"- Props: {listed} {_TODO}: types and meaning")
    return lines


def _wanted_depends(project, folder, name):
    """The Depends on line a file needs, "" when it needs none, None when the file is not checked."""
    if not project.depends_checked(name):
        return None
    targets = project.imports.of(f"{folder}/{name}")
    return _depends_line(targets) if targets else ""


def _new_entry_lines(project, folder, name):
    wanted = _wanted_depends(project, folder, name)
    return _entry_lines(project, folder, name) + ([wanted] if wanted else [])


def _init_folder(project, folder):
    path = project.doc_path(folder)
    actual = sorted(project.files.get(folder, []))
    children = project.children(folder)
    if not path.is_file():
        lines = [f"# {folder}", "", f"Purpose: {_TODO} one sentence on what this folder is responsible for.", ""]
        if actual:
            lines += ["## Files", ""]
            for name in actual:
                lines += _new_entry_lines(project, folder, name) + [""]
        if children:
            lines += ["## Subfolders", ""]
            lines += [f"- `{child}/`: {_TODO} purpose" for child in children]
            lines.append("")
        lines.append(_OPTIONAL_SECTIONS)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return "created"
    text = common.read_text(path) or ""
    doc = _parse_doc(text)
    lines = list(doc.lines)
    # (line index, kind, lines): "after" inserts after that line; "set" replaces it, or deletes it when empty
    edits = []
    globs = [n for n in doc.files if _is_glob(n)]
    for name, entry in doc.files.items():
        if name not in actual:
            continue
        extra = _entry_lines(project, folder, name, existing=entry)
        wanted = _wanted_depends(project, folder, name)
        if not entry.depends_lines:
            block = extra + ([wanted] if wanted else [])
            if block:
                edits.append((entry.end, "after", block))
            continue
        first = entry.depends_lines[0]
        if extra:
            edits.append((first - 1, "after", extra))  # new bullets go before the Depends on line
        if wanted is None:
            continue
        if lines[first] != wanted:
            edits.append((first, "set", [wanted] if wanted else []))
        edits += [(dup, "set", []) for dup in entry.depends_lines[1:]]
    new_entries = []
    for name in actual:
        if name not in doc.files and not any(common.glob_match(name, g) for g in globs):
            new_entries += [""] + _new_entry_lines(project, folder, name)
    if new_entries:
        if "files" in doc.sections:
            edits.append((doc.sections["files"][1], "after", new_entries))
        else:
            edits.append((len(lines) - 1, "after", ["", "## Files"] + new_entries))
    missing_children = [c for c in children if c not in doc.subfolders]
    if missing_children:
        bullets = [f"- `{child}/`: {_TODO} purpose" for child in missing_children]
        if "subfolders" in doc.sections:
            edits.append((doc.sections["subfolders"][1], "after", bullets))
        else:
            edits.append((len(lines) - 1, "after", ["", "## Subfolders", ""] + bullets))
    if not edits:
        return None
    # Bottom-up, so earlier indexes stay valid; at the same index, insert after a line before replacing it.
    for index, kind, block in sorted(edits, key=lambda e: (e[0], e[1] == "after"), reverse=True):
        if kind == "after":
            lines[index + 1:index + 1] = block
        else:
            lines[index:index + 1] = block
    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    return "updated"


# ---------------------------------------------------------------------- main


def _cmd_check(project, folders=None, with_codemap=True):
    errors, warnings = [], []
    for folder in sorted(folders if folders is not None else project.needed):
        if folder not in project.needed:
            continue
        e, w = _check_folder(project, folder)
        errors += e
        warnings += w
    if with_codemap:
        errors += _codemap_errors(project)
    return errors, warnings


def _cmd_staged(project):
    changes = common.git_staged_changes(project.root)
    if changes is None:
        return ["staged mode needs a git repository"], [], set()
    staged = set()
    for status, path, old in changes:
        staged.add(path)
        if old:
            staged.add(old)
    staged_now = {path for status, path, _old in changes if status != "D"}
    errors, warnings, touched = [], [], set()
    doc_name = project.doc_name

    def folder_of(rel):
        parent = str(PurePosixPath(rel).parent)
        return "" if parent == "." else parent

    def documentable(rel):
        p = PurePosixPath(rel)
        folder = folder_of(rel)
        return (
            folder in project.needed or (folder and not common.is_excluded(folder, project.cfg["exclude"]))
        ) and p.suffix.lower() in set(project.cfg["extensions"]) and not common.any_glob_match(
            p.name, project.cfg["ignoreFiles"]
        )

    for status, path, old in changes:
        for rel, kind in ((path, status), (old, "D") if old else (None, None)):
            if not rel:
                continue
            folder = folder_of(rel)
            name = PurePosixPath(rel).name
            if not folder:
                continue
            if name == doc_name:
                parent = folder_of(folder)
                if kind in ("A", "D") and parent and parent in project.needed:
                    if f"{parent}/{doc_name}" not in staged:
                        errors.append(f"{rel} was {'added' if kind == 'A' else 'removed'}; stage {parent}/{doc_name} with the subfolder list updated")
                touched.add(folder)
                continue
            if not documentable(rel) or (folder not in project.needed and kind != "D"):
                continue
            touched.add(folder)
            doc_rel = f"{folder}/{doc_name}"
            if kind in ("A", "C", "R", "D") and doc_rel not in staged_now and doc_rel not in staged:
                verb = {"A": "added", "C": "added", "R": "renamed", "D": "removed"}[kind]
                errors.append(f"{rel} was {verb}; update and stage {doc_rel}")
            elif kind == "M" and doc_rel not in staged:
                warnings.append(f"{rel} changed; check that {doc_rel} still describes it")
    return errors, warnings, touched


def _project_rel(root, arg):
    path = Path(arg)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(root).as_posix()
        except ValueError:
            return arg
    return posixpath.normpath(arg.replace(os.sep, "/"))


def _cmd_deps(project, paths):
    """Print what each file imports and which project files import it (Go: its package)."""
    graph = {
        rel: project.imports.of(rel)
        for rel in sorted(project.sources)
        if PurePosixPath(rel).suffix.lower() in _IMPORT_EXTS
    }
    blocks, errors = [], []
    for arg in paths:
        rel = _project_rel(project.root, arg)
        if rel not in project.sources:
            errors.append(f"{arg}: not a source file of this project")
            continue
        package = f"{PurePosixPath(rel).parent.as_posix()}/" if rel.endswith(".go") else None
        importers = sorted(f for f, deps in graph.items() if f != rel and (rel in deps or package in deps))
        targets = graph.get(rel, [])
        block = [rel]
        block += (["  imports:"] + [f"    {t}" for t in targets]) if targets else ["  imports: none"]
        block += (["  imported by:"] + [f"    {f}" for f in importers]) if importers else ["  imported by: none"]
        blocks.append("\n".join(block))
    if blocks:
        print("\n\n".join(blocks))
    return common.report(errors) if errors else 0


def main(argv=None):
    """Command-line entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=".", help="project root (default: current directory)")
    parser.add_argument("--config", help="config file (default: <root>/quality.config.json)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="verify all folder docs and the code map")
    sub.add_parser("staged", help="pre-commit check of staged changes")
    sub.add_parser("init", help="create or extend folder docs with TODO(describe) entries and Depends on lines")
    cm = sub.add_parser("codemap", help="write the code map")
    cm.add_argument("--check", action="store_true", help="only verify that the code map is current")
    dp = sub.add_parser("deps", help="print what files import and what imports them")
    dp.add_argument("files", nargs="+", help="paths from the project root")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    project = _Project(root, common.load_config(root, args.config))

    if args.command == "check":
        errors, warnings = _cmd_check(project)
        return common.report(errors, warnings, ok=f"folder docs ok ({len(project.needed)} folders)")
    if args.command == "staged":
        errors, warnings, touched = _cmd_staged(project)
        more, more_warnings = _cmd_check(project, touched, with_codemap=bool(touched))
        return common.report(errors + more, warnings + more_warnings, ok="staged folder docs ok")
    if args.command == "init":
        changed = []
        for folder in sorted(project.needed):
            result = _init_folder(project, folder)
            if result:
                changed.append(f"{result} {folder}/{project.doc_name}")
        for line in changed:
            print(line)
        errors, _warnings = _cmd_check(project, with_codemap=False)
        stale = [e for e in errors if "does not exist" in e or "does not export" in e or "does not have" in e]
        for line in stale:
            print(f"remove by hand: {line}")
        print(f"{len(changed)} doc(s) created or extended; replace every {_TODO}, then run codemap")
        return 0
    if args.command == "codemap":
        if args.check:
            return common.report(_codemap_errors(project), ok="code map is current")
        target = root / project.cfg["codemapFile"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_codemap_text(project), encoding="utf-8")
        print(f"wrote {project.cfg['codemapFile']}")
        return 0
    if args.command == "deps":
        return _cmd_deps(project, args.files)
    return 2


if __name__ == "__main__":
    sys.exit(main())
