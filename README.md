# scaffold-kit

Rules, templates and tested check scripts for the `scaffold-project` Claude skill, plus the skill's own source. The skill downloads a tagged release of this repository when it scaffolds or upgrades a project. Projects keep their own copies of what they use, so they never depend on this repository afterwards.

## Layout

| Path | What it is | Where it ends up in a project |
|---|---|---|
| `references/` | The full rules, one file per area | Project docs; the first lines of each file name the docs it becomes |
| `templates/` | Root `CLAUDE.md` with the workflows, the plan-step draft page, folder doc, scaffold progress and launch checklists, roadmap, agent metrics, ADR, `SECURITY.md`, GitHub templates and CI, lefthook, commitlint, quality config, editorconfig, gitattributes, Claude Code settings, agent definitions and the stack-conventions skill (`claude/`, copied to `.claude/`) | Copied and filled in |
| `scripts/quality/` | Check scripts: Python 3.9+, standard library only | Copied unchanged to `scripts/quality/` |
| `tests/` | Unit tests for the scripts, the documented examples and the skill files | Not copied |
| `evals/` | Repeatable dry runs of the skill's planning step: sample ideas with complete answers, the checklist each plan must meet, and an upgrade fixture | Not copied |
| `skill/scaffold-project/SKILL.md` | Source of the scaffold-project skill | Not copied; saved in the user's claude.ai account, which syncs it to Claude Code |
| `skill/scaffold-kit-maintainer/SKILL.md` | Source of the scaffold-kit-maintainer skill, for changing this repository | Not copied; saved in the user's claude.ai account, which syncs it to Claude Code |

| Reference | Becomes |
|---|---|
| `architecture.md` | `docs/ARCHITECTURE.md` |
| `backend.md` | `docs/DATABASE.md`; Auth, APIs and Caching in `docs/ARCHITECTURE.md` |
| `security.md` | `docs/security/THREAT-MODEL.md`, `docs/security/findings.md`, `SECURITY.md` |
| `safeguards.md` | `docs/security/SAFEGUARDS.md` |
| `privacy.md` | `docs/PRIVACY.md` |
| `hosting.md` | `docs/DEPLOYMENT.md`, `docs/SCALING.md`, `docs/OPERATIONS.md` |
| `git-workflow.md`, `folder-docs.md` | `CONTRIBUTING.md` |
| `design.md` | `docs/DESIGN.md` |
| `public-web.md` | `docs/SEO.md`, `docs/ANALYTICS.md` |
| `logging.md` | `docs/LOGGING.md` |
| `testing.md` | `docs/TESTING.md` |
| `sources.md` | `docs/SOURCES.md` |
| `agents.md` | `docs/AGENT-TEAM.md`; `.claude/agents/`, `.claude/skills/stack-conventions/` and `.claude/settings.json` from `templates/claude/` |
| `upgrade.md` | Nothing; the procedure for existing repositories |

## Scripts

Run from the project root (or pass `--root <project>`). Each exits non-zero on problems.

| Command | Purpose |
|---|---|
| `python3 scripts/quality/folder_docs.py check` | Every folder has an up-to-date `CLAUDE.md`, and `docs/CODEMAP.md` is current |
| `python3 scripts/quality/folder_docs.py staged` | Pre-commit: added, removed or renamed files need their folder doc staged |
| `python3 scripts/quality/folder_docs.py init` | Create missing folder docs, append missing entries marked `TODO(describe)`, and write each file's `Depends on:` line from its imports |
| `python3 scripts/quality/folder_docs.py codemap` | Regenerate `docs/CODEMAP.md` |
| `python3 scripts/quality/folder_docs.py deps FILE...` | What each file imports and what imports it, tests included |
| `python3 scripts/quality/debug_leftovers.py [--staged]` | No temporary debug markers, `debugger` or `breakpoint()` left in code |
| `python3 scripts/quality/design_tokens.py literals [--staged]` | No color literals or raw palette classes outside the theme files |
| `python3 scripts/quality/design_tokens.py contrast [--json]` | WCAG AA contrast for every token pair, light and dark |
| `python3 scripts/quality/palette.py theme --primary HEX [--highlight HEX] --out FILE` | Generate a full light and dark theme from a brand color |
| `python3 scripts/quality/palette.py preview A.css B.css --out FILE` | Compare theme proposals on one HTML page |
| `python3 scripts/quality/sources.py check` | Claude Code's WebFetch allow rules match the https links in `docs/SOURCES.md`, with no wildcards and no hosts where anyone can publish; warns when the list's review date is old |
| `python3 scripts/quality/sources.py sync` | Rewrite the WebFetch allow rules in `.claude/settings.json` from `docs/SOURCES.md`, keeping every other setting |
| `python3 scripts/quality/sources.py domains` | Print the pre-approved domains |
| `python3 scripts/quality/agent_guard.py` | Claude Code PreToolUse hook (the hook's JSON on stdin): denies git writes by subagents, skipped hooks, plain force pushes and changes to `main` outside a PR; asks before merges, remote repository changes, production promotes and discarding uncommitted work; for every agent, keeps the browser CLI on the local app and denies shell reads of deny-listed key files, Keychain reads and opening web addresses in the developer's browser; asks before `osascript`, installs outside the project and project scripts that changed since the user approved them; logs to `logs/agent-guard.log`. As a PostToolUse and PostToolUseFailure hook it records approvals in `~/.claude/script-approvals/` |
| `python3 scripts/quality/agent_guard.py --command CMD [--agent NAME]` | What the guard decides for one command |

Configuration lives in `quality.config.json` at the project root (template in `templates/`). The defaults are in `scripts/quality/common.py`: the exclude lists, `sources.neverPreapprove` and `design.contrastPairs` extend the defaults, every other key replaces its default.

## Versions

Releases are tagged `vMAJOR.MINOR.PATCH`, and the skill uses the newest `v2.*` tag. A breaking change to the layout or to a script's interface is a new major version and needs a skill update. Projects record the kit version in their root `CLAUDE.md`; upgrade mode (`references/upgrade.md`) moves them to a newer one. Changes are listed in `CHANGELOG.md`.

Every change and release follows the scaffold-kit-maintainer skill (`skill/scaffold-kit-maintainer/SKILL.md`): which file a change belongs in, tests, version bumps, tagging, and publishing a changed skill.

## Development

```bash
python3 -B -m unittest discover -s tests -v
```

CI runs the tests on Python 3.9 and 3.13.
