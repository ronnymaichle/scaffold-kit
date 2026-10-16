#!/usr/bin/env python3
"""Trusted sources check (scaffold-kit).

docs/SOURCES.md lists the sources the project trusts for current facts. The
host of every https:// link in it, except hosts where anyone can publish, may be
fetched by Claude without a prompt. This script keeps the WebFetch allow rules
in Claude Code's project settings in step with that list.

  sources.py check     fail when an allow rule names a domain that is not a
                       trusted source, is a wildcard or is never pre-approved;
                       when a trusted domain has no rule; or when the sources
                       file links over http://. Warns when its "Last reviewed:"
                       date is missing or older than reviewDays
  sources.py sync      rewrite the WebFetch allow rules from the sources file,
                       keeping every other setting
  sources.py domains   print the pre-approved domains, one per line

Configuration: the "sources" section of quality.config.json.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

__all__ = ["main", "linked_domains", "preapproved", "review_warning"]

_LINK = re.compile(r"\b(https?)://([A-Za-z0-9.-]+)([^\s)>\]|`'\"]*)")
_RULE = re.compile(r"^WebFetch\(domain:(.*)\)$")
_REVIEWED = re.compile(r"^Last reviewed:\s*(\d{4}-\d{2}-\d{2})\b", re.M)


def linked_domains(text):
    """Return (sorted https hosts, [(line, url)] for http links) found in text."""
    hosts, http = set(), []
    for number, line in enumerate(text.splitlines(), 1):
        for m in _LINK.finditer(line):
            scheme, host = m.group(1), m.group(2).lower().rstrip(".")
            if scheme == "http":
                http.append((number, m.group(0)))
            elif host:
                hosts.add(host)
    return sorted(hosts), http


def preapproved(hosts, never):
    """The hosts that get a WebFetch allow rule: all except never-pre-approved ones."""
    return sorted(h for h in hosts if not common.any_glob_match(h, never))


def review_warning(text, today, max_days):
    """A warning when the "Last reviewed:" date is missing or older than max_days, else None."""
    m = _REVIEWED.search(text)
    if not m:
        return 'no "Last reviewed: YYYY-MM-DD" line; add one when the list is reviewed'
    try:
        reviewed = datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return f"invalid review date {m.group(1)}"
    age = (today - reviewed).days
    if age > max_days:
        return f"sources last reviewed {age} days ago; check each source still exists and add new ones"
    return None


def _load_settings(path):
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"error: {path} must contain a JSON object")
    return data


def _allow_list(data):
    allow = (data.get("permissions") or {}).get("allow") or []
    return [rule for rule in allow if isinstance(rule, str)]


def _check(cfg, root, text, rel):
    errors, warnings = [], []
    hosts, http = linked_domains(text)
    for line, url in http:
        errors.append(f"{rel}:{line}: {url} uses http; link trusted sources over https")
    wanted = preapproved(hosts, cfg["neverPreapprove"])
    warning = review_warning(text, datetime.date.today(), int(cfg["reviewDays"]))
    if warning:
        warnings.append(f"{rel}: {warning}")
    if not cfg["settingsFile"]:
        return errors, warnings
    settings_rel = cfg["settingsFile"]
    data = _load_settings(root / settings_rel)
    if data is None:
        errors.append(f"{settings_rel}: missing; run `python3 scripts/quality/sources.py sync`")
        return errors, warnings
    allowed = set()
    for rule in _allow_list(data):
        if rule == "WebFetch":
            errors.append(f"{settings_rel}: bare WebFetch allows every domain; allow trusted domains only")
            continue
        m = _RULE.match(rule)
        if not m:
            continue
        domain = m.group(1).strip().lower().rstrip(".")
        if "*" in domain:
            errors.append(f"{settings_rel}: {rule} uses a wildcard; allow exact trusted domains only")
        elif common.any_glob_match(domain, cfg["neverPreapprove"]):
            errors.append(f"{settings_rel}: {rule}: anyone can publish on {domain}, so it is never pre-approved")
        elif domain not in wanted:
            errors.append(f"{settings_rel}: {rule}: {domain} is not linked in {rel}; add it there as a trusted source or remove the rule")
        allowed.add(domain)
    for domain in wanted:
        if domain not in allowed:
            errors.append(f"{settings_rel}: no rule for {domain}; run `python3 scripts/quality/sources.py sync`")
    return errors, warnings


def _sync(cfg, root, text):
    if not cfg["settingsFile"]:
        return common.report(['"sources.settingsFile" is null; nothing to sync'])
    path = root / cfg["settingsFile"]
    data = _load_settings(path) or {}
    hosts, _http = linked_domains(text)
    rules = [f"WebFetch(domain:{d})" for d in preapproved(hosts, cfg["neverPreapprove"])]
    permissions = data.setdefault("permissions", {})
    kept = [r for r in permissions.get("allow") or [] if not (r == "WebFetch" or _RULE.match(str(r)))]
    permissions["allow"] = kept + rules
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return common.report([], ok=f"{len(rules)} WebFetch rule(s) written to {cfg['settingsFile']}")


def main(argv=None):
    """Command-line entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["check", "sync", "domains"])
    parser.add_argument("--root", default=".", help="project root (default: current directory)")
    parser.add_argument("--config", help="config file (default: <root>/quality.config.json)")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    cfg = common.load_config(root, args.config)["sources"]
    rel = cfg["file"]
    text = common.read_text(root / rel)
    if text is None:
        return common.report([f"{rel}: missing; write it from the kit's references/sources.md"])
    try:
        if args.command == "domains":
            for domain in preapproved(linked_domains(text)[0], cfg["neverPreapprove"]):
                print(domain)
            return 0
        if args.command == "sync":
            return _sync(cfg, root, text)
        errors, warnings = _check(cfg, root, text, rel)
    except SystemExit as exc:
        print(exc)
        return 2
    return common.report(errors, warnings, ok="trusted sources and WebFetch rules match")


if __name__ == "__main__":
    sys.exit(main())
