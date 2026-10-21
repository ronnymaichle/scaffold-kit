#!/usr/bin/env python3
"""Agent guard (scaffold-kit).

A Claude Code PreToolUse hook for the Bash tool. It reads the hook's JSON on
stdin and enforces the repository rules an agent could break by mistake or
after reading a prompt injection, explaining each decision:

  deny   git writes by subagents (only the lead changes git state); skipping
         hooks (--no-verify, commit -n, core.hooksPath, LEFTHOOK=0); force
         pushes other than --force-with-lease; force-pushing or deleting
         main; pushing to main once the remote has it; the promote script
         run by a subagent
  ask    merging a pull request, creating or changing the remote repository,
         changing the git host through its API, promoting to production
         without --dry-run, and commands that discard uncommitted work across
         the tree (git reset --hard, git clean -f, git checkout or restore .)

Each deny and ask is appended to logs/agent-guard.log. The guard reads the
command text, so it is a seatbelt, not a security boundary: branch protection
and CI on the git host are, and in the strict profile the sandbox.

  agent_guard.py                      hook mode: the hook's JSON on stdin
  agent_guard.py --command CMD [--agent NAME] [--root DIR]
                                      print the decision for one command;
                                      exit 0 when allowed, 1 otherwise
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

__all__ = ["main", "decide"]

HOOKS = "Git hooks are never skipped (CONTRIBUTING.md): fix what the hook reports instead of bypassing it."
FORCE = "Plain force pushes are blocked: use --force-with-lease, which refuses to overwrite commits you have not seen."
MAIN_REWRITE = "main is never force-pushed or deleted."
MAIN_PR = "main changes only through a pull request (branch protection): push the feature branch and open a PR."
EVERY = "--all, --branches and --mirror push every branch, main included: push one branch at a time."
SUBAGENT_GIT = (
    "Only the lead changes git state (commits, pushes, branches, the index, discarding changes). "
    "Edit your slice's files directly and list what you need from git under Open in your report."
)
SUBAGENT_GH = (
    "Only the lead acts on the git host (pull requests, merges, releases, API calls). "
    "Read with gh pr view, gh pr diff or gh issue view, and list what you need under Open in your report."
)
SUBAGENT_DEPLOY = "Only the lead runs the promote script, after the user's approval."
DISCARD = "This discards uncommitted work across the working tree, which can include agents' unfinished slices."
MERGE = "Merging a pull request is the user's decision."
REPO = "Creating, changing or deleting the remote repository needs the user's approval."
API = "Changing the git host through its API (for example branch protection) needs the user's approval."
PROD = "Promoting to production needs the user's approval (Release workflow); run it with --dry-run first."
PARSE = "agent_guard could not read this command, so it is blocked; split it into plain commands."

_PROTECTED = {"main", "master"}
_SEPARATOR = set("();|&")
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
_PROMOTE = ("promote.sh", "promote.mjs", "promote.js", "promote.ts", "promote.py")
_PROMOTE_NAMES = {"deploy:env", "deploy-env", "deploy_env"}  # the package script, or a make target
_WHOLE_TREE = {".", "./", ":/", ":/.", ":/*", "*", ":(top)"}
_HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Commands that run their arguments as the real command, with their options that take a value.
_WRAPPERS = {
    "env": {"-u", "-C", "-S"}, "command": set(), "builtin": set(), "exec": {"-a"}, "nohup": set(),
    "time": set(), "noglob": set(), "nice": {"-n"}, "sudo": {"-u", "-g", "-C", "-h", "-p", "-U"},
    "timeout": {"-s", "-k"}, "stdbuf": {"-i", "-o", "-e"},
}
_SECRET = re.compile(r"(://)[^/\s:@]+:[^/\s@]+@|\b(?:ghp|gho|ghu|ghs|ghr|github_pat|glpat|xox[abprs])[-_][A-Za-z0-9_-]{16,}|\bsk-[A-Za-z0-9_-]{20,}")

# git subcommands a subagent may run: they only read the repository.
_GIT_READ = {
    "status", "diff", "log", "show", "blame", "annotate", "grep", "ls-files", "ls-tree", "ls-remote",
    "rev-parse", "rev-list", "describe", "shortlog", "cat-file", "merge-base", "name-rev", "for-each-ref",
    "show-ref", "whatchanged", "check-ignore", "check-attr", "count-objects", "var", "version", "help",
    "diff-tree", "diff-files", "diff-index", "range-diff", "cherry",
}
_GIT_GLOBAL_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env"}
_HOOKED = {"commit", "push", "merge", "rebase", "cherry-pick", "revert", "am"}
_COMMIT_VALUE_SHORT = set("mFCct")
_COMMIT_VALUE_LONG = {
    "--message", "--file", "--reuse-message", "--reedit-message", "--fixup", "--squash", "--author",
    "--date", "--template", "--cleanup", "--trailer", "--pathspec-from-file",
}
_BRANCH_WRITE = {
    "-d", "-D", "-m", "-M", "-c", "-C", "-f", "-u", "-t", "--force", "--delete", "--move", "--copy",
    "--set-upstream-to", "--unset-upstream", "--edit-description", "--track", "--no-track",
}
_BRANCH_LIST = {"--list", "-l", "--contains", "--no-contains", "--merged", "--no-merged", "--points-at"}
_TAG_WRITE = {"-d", "--delete", "-a", "--annotate", "-s", "--sign", "-m", "--message", "-f", "--force", "-F", "--file", "-u", "--local-user"}
_TAG_LIST = {"-l", "--list", "--contains", "--no-contains", "--merged", "--no-merged", "--points-at"}
_GH_READ = {
    ("pr", "view"), ("pr", "list"), ("pr", "diff"), ("pr", "checks"), ("pr", "status"),
    ("issue", "view"), ("issue", "list"), ("issue", "status"), ("run", "view"), ("run", "list"),
    ("run", "watch"), ("workflow", "view"), ("workflow", "list"), ("repo", "view"),
    ("release", "view"), ("release", "list"), ("auth", "status"),
}
_GH_ASK = {
    ("pr", "merge"): MERGE, ("repo", "create"): REPO, ("repo", "delete"): REPO, ("repo", "edit"): REPO,
    ("repo", "rename"): REPO, ("repo", "archive"): REPO, ("release", "delete"): REPO,
}


def decide(command, agent=None, root=None):
    """("allow" | "ask" | "deny", reason) for a shell command; agent names the subagent, None for the lead."""
    try:
        results = _analyze(command, agent, Path(root or "."), 0)
    except Exception:  # noqa: BLE001 - fail closed for the commands this guard covers
        if re.search(r"\b(git|gh)\b|deploy:env|promote\.", command):
            return "deny", PARSE
        return "allow", ""
    for wanted in ("deny", "ask"):
        reasons = [reason for decision, reason in results if decision == wanted]
        if reasons:
            return wanted, " ".join(dict.fromkeys(reasons))
    return "allow", ""


def _analyze(text, agent, root, depth):
    if depth > 4:
        raise ValueError("commands nested too deeply")
    text = _strip_heredocs(text.replace("\\\n", " "))
    results = []
    for inner in _substitutions(text):
        results += _analyze(inner, agent, root, depth + 1)
    for tokens in _segments(text):
        results += _segment(tokens, agent, root, depth)
    return results


def _strip_heredocs(text):
    """Drop here-document bodies: they are input data, not commands."""
    out, pending = [], []
    for line in text.split("\n"):
        if pending:
            tabs, word = pending[0]
            if (line.lstrip("\t") if tabs else line) == word:
                pending.pop(0)
            continue
        out.append(line)
        pending = [(m.group(1) == "-", m.group(3)) for m in _HEREDOC.finditer(line)]
    return "\n".join(out)


def _substitutions(text):
    """The commands inside $(...) and backticks, outside single quotes."""
    found, i, n, quote = [], 0, len(text), None
    while i < n:
        c = text[i]
        if quote == "'":
            quote = None if c == "'" else quote
            i += 1
        elif c == "\\":
            i += 2
        elif c == "'" and quote is None:
            quote = "'"
            i += 1
        elif c == '"':
            quote = None if quote == '"' else '"'
            i += 1
        elif c == "`":
            end = text.find("`", i + 1)
            end = n if end < 0 else end
            found.append(text[i + 1:end])
            i = end + 1
        elif text.startswith("$(", i):
            level, j = 1, i + 2
            while j < n and level:
                level += {"(": 1, ")": -1}.get(text[j], 0)
                j += 1
            found.append(text[i + 2:j - 1] if level == 0 else text[i + 2:])
            i = j
        else:
            i += 1
    return found


def _segments(text):
    """Simple commands as token lists, split at ; && || | & ( ) and line breaks, without redirections."""
    lexer = shlex.shlex(text.replace("\n", " ; "), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    segments, current = [], []
    for token in lexer:
        if token and set(token) <= _SEPARATOR:
            if current:
                segments.append(current)
            current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    return [_drop_redirections(s) for s in segments]


def _drop_redirections(tokens):
    out, skip = [], False
    for token in tokens:
        if skip:
            skip = False
        elif token and set(token) <= set("<>&") and ("<" in token or ">" in token):
            if out and out[-1].isdigit():
                out.pop()
            skip = True
        else:
            out.append(token)
    return out


def _strip_prefix(tokens):
    """(environment assignments, the command) without wrappers such as env, timeout or nohup."""
    env, i = {}, 0
    while i < len(tokens):
        token, base = tokens[i], os.path.basename(tokens[i])
        if _ASSIGNMENT.match(token):
            key, _, value = token.partition("=")
            env[key] = value
            i += 1
        elif base in _WRAPPERS:
            i += 1
            while i < len(tokens) and tokens[i].startswith("-"):
                i += 2 if tokens[i] in _WRAPPERS[base] else 1
            if base == "timeout" and i < len(tokens):
                i += 1  # the duration
        else:
            break
    return env, tokens[i:]


def _segment(tokens, agent, root, depth):
    env, tokens = _strip_prefix(tokens)
    if not tokens:
        return []
    program, args = os.path.basename(tokens[0]), tokens[1:]
    if program in _SHELLS:
        for index, arg in enumerate(args):
            if re.match(r"^-[a-z]*c[a-z]*$", arg) and index + 1 < len(args):
                return _analyze(args[index + 1], agent, root, depth + 1)
    if program == "eval":
        return _analyze(" ".join(args), agent, root, depth + 1)
    if any(t in _PROMOTE_NAMES or t.endswith(_PROMOTE) for t in tokens):
        if agent is not None:
            return [("deny", SUBAGENT_DEPLOY)]
        words = tokens + [f"{key}={value}" for key, value in env.items()]
        dry = "--dry-run" in words or any(w.upper() in ("DRY_RUN=1", "DRY_RUN=TRUE") for w in words)
        if not dry and any(w.rpartition("=")[2] in ("production", "prod") for w in words):
            return [("ask", PROD)]
        return []
    if program == "git":
        return _git(env, args, agent, root)
    if program == "gh":
        return _gh(args, agent)
    return []


def _git(env, args, agent, root):
    configs, i = [], 0
    while i < len(args) and args[i].startswith("-"):
        arg = args[i]
        if arg in _GIT_GLOBAL_VALUE and i + 1 < len(args):
            if arg == "-C":
                root = root / args[i + 1]
            elif arg in ("-c", "--config-env"):
                configs.append(args[i + 1])
            i += 2
            continue
        if arg.startswith("--config-env="):
            configs.append(arg.split("=", 1)[1])
        i += 1
    if i >= len(args):
        return []
    sub, rest = args[i], args[i + 1:]
    if agent is not None:
        return [] if _git_reads_only(sub, rest) else [("deny", SUBAGENT_GIT)]
    results = []
    skips = _hooks_skipped(env, configs) or "--no-verify" in rest
    if sub == "commit":
        skips = skips or _commit_skips_hooks(rest)
    if sub in _HOOKED and skips:
        results.append(("deny", HOOKS))
    if sub == "config" and any(a.lower() == "core.hookspath" for a in rest):
        if not set(rest) & {"--get", "--get-all", "--list", "-l"}:
            results.append(("deny", HOOKS))
    if sub == "push":
        results += _push(rest, root)
    if _discards(sub, rest):
        results.append(("ask", DISCARD))
    return results


def _hooks_skipped(env, configs):
    if env.get("LEFTHOOK", "").lower() in ("0", "false") or "LEFTHOOK_EXCLUDE" in env or env.get("HUSKY") == "0":
        return True
    if any(k.startswith("GIT_CONFIG") and "hookspath" in v.lower() for k, v in env.items()):
        return True
    return any(c.lower().startswith("core.hookspath") for c in configs)


def _commit_skips_hooks(args):
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            break
        if arg in _COMMIT_VALUE_LONG:
            i += 2
            continue
        if arg.startswith("-") and not arg.startswith("--"):
            for j, ch in enumerate(arg[1:], 1):
                if ch == "n":
                    return True
                if ch in _COMMIT_VALUE_SHORT:
                    if j == len(arg) - 1:
                        i += 1  # the value is the next token
                    break
                if ch in "Su":  # optional value, attached
                    break
        i += 1
    return False


def _push(args, root):
    force = lease = delete = dry = every = False
    positionals, i = [], 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            positionals += args[i + 1:]
            break
        if arg.startswith("--"):
            name = arg.split("=", 1)[0]
            force = force or name == "--force"
            lease = lease or name == "--force-with-lease"
            delete = delete or name == "--delete"
            dry = dry or name == "--dry-run"
            every = every or name in ("--all", "--branches", "--mirror")
            if name in ("--repo", "--receive-pack", "--exec", "--push-option") and "=" not in arg:
                i += 1
        elif arg.startswith("-") and len(arg) > 1:
            for j, ch in enumerate(arg[1:], 1):
                force = force or ch == "f"
                delete = delete or ch == "d"
                dry = dry or ch == "n"
                if ch == "o":
                    if j == len(arg) - 1:
                        i += 1
                    break
        else:
            positionals.append(arg)
        i += 1
    if dry:
        return []
    if every:
        return [("deny", EVERY)]
    remote = positionals[0] if positionals else None
    targets = []
    for spec in positionals[1:]:
        forced, spec = spec.startswith("+"), spec.lstrip("+")
        source, _, dest = spec.partition(":")
        dest = dest if ":" in spec else source
        if dest == "HEAD":
            dest = _git_output(root, "symbolic-ref", "--short", "-q", "HEAD") or dest
        targets.append((_branch(dest), forced, delete or (":" in spec and source == "")))
    if len(positionals) < 2:
        current = _git_output(root, "symbolic-ref", "--short", "-q", "HEAD")
        if current:
            targets.append((current, False, False))
    results = []
    for name, forced, deleting in targets:
        if name in _PROTECTED:
            if deleting or force or forced or lease:
                results.append(("deny", MAIN_REWRITE))
            elif _remote_has(root, remote, name):
                results.append(("deny", MAIN_PR))
        elif force or forced:
            results.append(("deny", FORCE))
    return results


def _branch(ref):
    return ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref


def _remote_has(root, remote, branch):
    """True when the remote already has the branch; a URL or path counts as yes, since it cannot be told."""
    remote = remote or "origin"
    if "/" in remote or ":" in remote:
        return True
    return _git_output(root, "rev-parse", "--verify", "-q", f"refs/remotes/{remote}/{branch}") is not None


def _git_output(root, *args):
    try:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _discards(sub, args):
    """True when a git command throws away uncommitted work across the tree."""
    flags = [a for a in args if a.startswith("-") and a != "--"]
    short = "".join(a[1:] for a in flags if not a.startswith("--"))
    paths = args[args.index("--") + 1:] if "--" in args else [a for a in args if not a.startswith("-")]
    whole = bool(set(paths) & _WHOLE_TREE)
    if sub == "reset":
        return "--hard" in args
    if sub == "clean":
        return ("--force" in flags or "f" in short) and not ("--dry-run" in flags or "n" in short)
    if sub == "checkout":
        return whole or "--force" in flags or "f" in short
    if sub == "restore":
        staged, worktree = "--staged" in flags or "S" in short, "--worktree" in flags or "W" in short
        return whole and (worktree or not staged)
    if sub == "switch":
        return bool({"--discard-changes", "--force", "-f"} & set(flags))
    if sub == "stash":
        return bool(args) and args[0] in ("clear", "drop")
    return False


def _git_reads_only(sub, args):
    """True when a subagent's git command only reads the repository."""
    first = args[0] if args else None
    positional = [a for a in args if not a.startswith("-")]
    if sub in _GIT_READ:
        return True
    if sub in ("stash", "notes"):
        return first in ("list", "show")
    if sub == "worktree":
        return first == "list"
    if sub == "submodule":
        return first in (None, "status")
    if sub == "reflog":
        return first in (None, "show") or first.startswith("-")
    if sub == "remote":
        return first in (None, "-v", "--verbose", "show", "get-url")
    if sub == "config":
        if set(args) & {"--unset", "--unset-all", "--add", "--replace-all", "--remove-section", "--rename-section", "--edit", "-e"}:
            return False
        return bool(set(args) & {"--get", "--get-all", "--get-regexp", "--list", "-l"}) or len(positional) <= 1
    if sub == "branch":
        if set(args) & _BRANCH_WRITE:
            return False
        return not positional or any(a.split("=", 1)[0] in _BRANCH_LIST for a in args)
    if sub == "tag":
        if set(args) & _TAG_WRITE:
            return False
        return not positional or any(a.split("=", 1)[0] in _TAG_LIST for a in args)
    return False


def _gh(args, agent):
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in ("-R", "--repo") else 1
    rest = args[i:]
    group = rest[0] if rest else None
    pair = (group, rest[1] if len(rest) > 1 else None)
    if agent is not None:
        return [] if pair in _GH_READ or group == "search" else [("deny", SUBAGENT_GH)]
    if pair in _GH_ASK:
        return [("ask", _GH_ASK[pair])]
    if group == "api":
        for j, arg in enumerate(rest):
            method = None
            if arg in ("-X", "--method") and j + 1 < len(rest):
                method = rest[j + 1]
            elif arg.startswith("--method="):
                method = arg.split("=", 1)[1]
            elif arg.startswith("-X") and len(arg) > 2:
                method = arg[2:]
            if method and method.upper() != "GET":
                return [("ask", API)]
    return []


def _redact(command):
    return _SECRET.sub(lambda m: (m.group(1) or "") + "***" + ("@" if m.group(1) else ""), command)[:500]


def _log(root, decision, reason, command, agent):
    entry = {
        "time": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decision": decision,
        "agent": agent or "lead",
        "command": _redact(command),
        "reason": reason,
    }
    try:
        path = Path(root) / "logs" / "agent-guard.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _hook(raw, root_arg=None):
    try:
        payload = json.loads(raw)
    except ValueError:
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str) or not command.strip():
        return 0
    # Claude Code sends agent_id only for commands a subagent or teammate runs.
    agent = (payload.get("agent_type") or "subagent") if payload.get("agent_id") else None
    root = Path(root_arg or os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".")
    decision, reason = decide(command, agent=agent, root=Path(payload.get("cwd") or root))
    if decision == "allow":
        return 0
    _log(root, decision, reason, command, agent)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason,
    }}))
    return 0


def main(argv=None):
    """Command-line entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--command", help="check one command instead of reading the hook's JSON on stdin")
    parser.add_argument("--agent", help="decide as for this subagent (for example implementer)")
    parser.add_argument("--root", help="project root for the git checks (default: current directory)")
    args = parser.parse_args(argv)
    if args.command is None:
        return _hook(sys.stdin.read(), args.root)
    decision, reason = decide(args.command, agent=args.agent, root=Path(args.root or ".").resolve())
    print(decision if decision == "allow" else f"{decision}: {reason}")
    return 0 if decision == "allow" else 1


if __name__ == "__main__":
    sys.exit(main())
