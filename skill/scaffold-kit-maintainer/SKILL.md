---
name: scaffold-kit-maintainer
description: "Change the scaffold-project skill or its scaffold-kit repository (ronnymaichle/scaffold-kit): add or change a rule, template, check script, profile or workflow, fix a bug, review the rules, or release a new kit version. Knows which file each kind of change belongs in and keeps tests, versions and the changelog consistent. Use whenever the user wants to update, fix, extend or review the scaffolding rules or either skill, even if they only describe a rule they want new projects to follow. Not for changing one project that was scaffolded with the kit; that project's own docs hold its rules."
---

# Maintaining scaffold-project and scaffold-kit

## How the pieces fit

- **The kit**, `https://github.com/ronnymaichle/scaffold-kit`: the full rules (`references/`), templates (`templates/`), check scripts (`scripts/quality/`) and their tests (`tests/`). Each release is an annotated tag `vMAJOR.MINOR.PATCH`.
- **The scaffold-project skill**: the short process (inputs, profiles, checkpoints, upgrade mode). Its source is `skill/scaffold-project/SKILL.md` in the kit. The copy Claude actually uses is saved in the user's claude.ai account, which syncs it to Claude Code automatically; there is no separate local copy to keep in step. At scaffold time it fetches the newest `v2.*` tag, so kit releases reach new projects without touching the skill.
- **This skill**: its source is `skill/scaffold-kit-maintainer/SKILL.md` in the kit, next to the scaffold-project source. The copy Claude uses is saved in the user's claude.ai account, which syncs it to Claude Code automatically; the repository has no `.claude/skills/` folder, so only that copy is loaded.
- **Existing projects** keep their own copies of the docs and scripts and record their kit version in their root `CLAUDE.md`. A kit change never edits them; they adopt it through the skill's upgrade mode.

## Where a change goes

| The user wants to change | Edit | Also check |
|---|---|---|
| A rule projects follow (security, data, testing, design, SEO, logging and so on) | The reference for that area in `references/` | Its summary line in `templates/CLAUDE.md`, if it has one |
| Lean or strict variations | The "Lean profile" or "Strict profile additions" section of that reference | The profile table in the skill, if what a profile means changes |
| The Feature, Hotfix or Release workflow, or the root rules summary | `templates/CLAUDE.md` | It must stay under 200 lines (a test checks) |
| The agent roster, a role's model, effort, tools or turn limit, or how agents hand off work | `references/agents.md` and the matching file in `templates/claude/` | `tests/test_agent_templates.py` keeps the roster table and the templates in step |
| What Phase 1 builds, or in which checkpoint | `templates/SCAFFOLD-PROGRESS.md` | Skill step 4, only if the checkpoints themselves change |
| Launch items | `templates/LAUNCH-CHECKLIST.md` | |
| PR and issue templates, project CI, hooks, commitlint, editor and git configs | The file in `templates/` | `references/git-workflow.md`, if the rule behind it changes |
| A check script, or a new check | `scripts/quality/`, with tests in `tests/` written first | `scripts/quality/CLAUDE.md`, the commands table in `README.md`, and the reference that documents the check |
| The scripts' configuration defaults | `_DEFAULTS` in `scripts/quality/common.py` | `templates/quality.config.json` for new keys, and the configuration note in `README.md` |
| The process: inputs asked, profiles, checkpoints, upgrade mode, the kit URL | `skill/scaffold-project/SKILL.md` | Publishing the skill (workflow step 8) |
| Which project doc a reference becomes | The reference's first lines | The mapping tables in the skill and in `README.md` (a test compares them) |

Rules that keep the kit coherent:

- One rule, one home. Before adding a rule, search for its topic (`grep -rni "<keyword>" references templates skill`) so it lands in the one file that owns it and does not contradict another; other files link to it.
- References become project docs, so their rules are written for the project ("Every list endpoint is paginated"), not for the skill. Choices made only while scaffolding sit in sections marked "(scaffold-time)".
- A rule that can be checked mechanically gets a check or a test.
- Match the existing style: plain, short sentences in the present tense; "for example" rather than "e.g."; the reason stated when a rule is not obvious; no all-caps emphasis.
- The scaffold-project skill stays short (a test caps it at 16,000 characters) so it survives compaction; detail belongs in the kit.

## Workflow

1. **Repository:** work in the user's clone (usually `~/Development/GitHub/scaffold-kit`), or clone it with `gh repo clone ronnymaichle/scaffold-kit`. Start from a clean, current `main`: `git status`, `git switch main`, `git pull --ff-only`.
2. **Plan:** restate the change, pick the files from the table above, and show the user the exact edits and the version bump (step 6). Wait for approval unless it is a typo fix.
3. **Branch:** `git switch -c <type>/<short-description>`, using the Conventional Commit types (`feat`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`).
4. **Edit**, writing tests before changing a script.
5. **Test:** `python3 -B -m unittest discover -s tests` must pass (Python 3.9 or newer; `-B` keeps `__pycache__` out of the tree). The tests also check the versions, the skills' frontmatter, the mapping tables and the documented examples. Never edit a test just to make it pass.
6. **Version:** pick the bump, update `VERSION` and `KIT_VERSION` in `scripts/quality/common.py` (a test keeps them equal), and add a `CHANGELOG.md` entry at the top: version, date, what changed, and what existing projects should do.
   - Patch (`2.0.x`): fixes and clarifications that do not change what a project gets: typos, wording, a script bug fix with the same interface, tests, maintenance files.
   - Minor (`2.x.0`): new or changed rules, templates, checks or defaults that stay compatible. New scaffolds get them; existing projects adopt them through upgrade mode.
   - Major (`x.0.0`): anything that breaks what the skill or projects rely on: renaming or moving kit files the skill reads, changing a script's command line or configuration keys, removing a template. A major release also changes the tag pattern in `skill/scaffold-project/SKILL.md` (`'v2.*'` and `^v2\.`) and needs the saved skill updated (step 8). Until then the saved skill keeps using the newest 2.x, so a major release never breaks it.
7. **Release:** commit, push the branch and open a PR with a Conventional Commit title (`gh pr create`). After the user approves, squash-merge it (`gh pr merge --squash --delete-branch`), update `main` (`git switch main && git pull --ff-only`), tag the merge commit (`git tag -a vX.Y.Z -m "scaffold-kit X.Y.Z"`), push the tag (`git push origin vX.Y.Z`) and confirm it with `git ls-remote --tags origin`. If `git push` asks for credentials, offer `gh auth setup-git`; it changes the global git config, so ask first. Never put a token in a remote URL.
8. **Publish the skills**, only when a skill file changed:
   - claude.ai: the user opens a chat on claude.ai, attaches the changed `SKILL.md` and asks Claude to update their skill of that name from it, then saves the card Claude shows.
   The claude.ai copy syncs to Claude Code automatically, so nothing is copied into `~/.claude/skills/`. Changes to the kit alone need nothing here: the skill picks up the new tag on its own.
9. **Report:** what changed, the new version, whether a saved skill needs updating, and what existing projects gain by running upgrade mode.

## Trying a process change

For changes to how the skill behaves (questions, profiles, the plan, checkpoints), offer a dry run before releasing. In an empty scratch folder, have a fresh Claude session follow `skill/scaffold-project/SKILL.md` for a sample idea, with this repository as the local copy of the kit, and stop at the plan. Then compare its plan with the previous version's.

## Never

- Move, delete or recreate a published tag, or force-push `main`; fix forward with a new version.
- Edit a project scaffolded with the kit from here; projects change through their own workflow.
