# scaffold-kit

Source of the scaffold-project skill (`skill/scaffold-project/SKILL.md`) and of the kit it downloads: rules in `references/`, templates in `templates/`, check scripts in `scripts/quality/` with their tests in `tests/`.

For any change to the rules, templates, scripts or skills, follow the scaffold-kit-maintainer skill. Claude Code loads the copy saved in claude.ai; its source is `skill/scaffold-kit-maintainer/SKILL.md`, which is read directly when that skill is not available. It says which file a change belongs in, how to test it, and how to version and release it.

- `python3 -B -m unittest discover -s tests` passes before every commit.
- Published tags are never moved or deleted; fix forward with a new version.
