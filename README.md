# scaffold-kit

Rules, templates and tested check scripts for the `scaffold-project` Claude skill. The skill downloads a tagged release of this repository when it scaffolds or upgrades a project. Projects keep their own copies of what they use, so they never depend on this repository afterwards.

## Layout

| Path | What it is | Where it ends up in a project |
|---|---|---|
| `references/` | The full rules, one file per area | Project docs; the first lines of each file name the docs it becomes |
| `templates/` | Root `CLAUDE.md` with the workflows, folder doc, scaffold progress and launch checklists, ADR, `SECURITY.md`, GitHub templates and CI, lefthook, commitlint, quality config, editorconfig, gitattributes | Copied and filled in |
| `scripts/quality/` | Check scripts: Python 3.9+, standard library only | Copied unchanged to `scripts/quality/` |
| `tests/` | Unit tests for the scripts and the documented examples | Not copied |

| Reference | Becomes |
|---|---|
| `architecture.md` | `docs/ARCHITECTURE.md` |
| `backend.md` | `docs/DATABASE.md`; Auth, APIs and Caching in `docs/ARCHITECTURE.md` |
| `security.md` | `docs/security/THREAT-MODEL.md`, `docs/security/findings.md`, `SECURITY.md` |
| `privacy.md` | `docs/PRIVACY.md` |
| `hosting.md` | `docs/DEPLOYMENT.md`, `docs/SCALING.md`, `docs/OPERATIONS.md` |
| `git-workflow.md`, `folder-docs.md` | `CONTRIBUTING.md` |
| `design.md` | `docs/DESIGN.md` |
| `public-web.md` | `docs/SEO.md`, `docs/ANALYTICS.md` |
| `logging.md` | `docs/LOGGING.md` |
| `testing.md` | `docs/TESTING.md` |
| `upgrade.md` | Nothing; the procedure for existing repositories |

## Scripts

Run from the project root (or pass `--root <project>`). Each exits non-zero on problems.

| Command | Purpose |
|---|---|
| `python3 scripts/quality/folder_docs.py check` | Every folder has an up-to-date `CLAUDE.md`, and `docs/CODEMAP.md` is current |
| `python3 scripts/quality/folder_docs.py staged` | Pre-commit: added, removed or renamed files need their folder doc staged |
| `python3 scripts/quality/folder_docs.py init` | Create missing folder docs and append missing entries marked `TODO(describe)` |
| `python3 scripts/quality/folder_docs.py codemap` | Regenerate `docs/CODEMAP.md` |
| `python3 scripts/quality/debug_leftovers.py [--staged]` | No temporary debug markers, `debugger` or `breakpoint()` left in code |
| `python3 scripts/quality/design_tokens.py literals [--staged]` | No color literals or raw palette classes outside the theme files |
| `python3 scripts/quality/design_tokens.py contrast [--json]` | WCAG AA contrast for every token pair, light and dark |
| `python3 scripts/quality/palette.py theme --primary HEX [--highlight HEX] --out FILE` | Generate a full light and dark theme from a brand color |
| `python3 scripts/quality/palette.py preview A.css B.css --out FILE` | Compare theme proposals on one HTML page |

Configuration lives in `quality.config.json` at the project root (template in `templates/`). The defaults are in `scripts/quality/common.py`: the exclude lists and `design.contrastPairs` extend the defaults, every other key replaces its default.

## Versions

Releases are tagged `vMAJOR.MINOR.PATCH`, and the skill uses the newest `v2.*` tag. A breaking change to the layout or to a script's interface is a new major version and needs a skill update. Projects record the kit version in their root `CLAUDE.md`; upgrade mode (`references/upgrade.md`) moves them to a newer one. Changes are listed in `CHANGELOG.md`.

To release: update `VERSION` and `KIT_VERSION` in `scripts/quality/common.py` (a test keeps them equal), add a `CHANGELOG.md` entry, and tag the commit.

## Development

```bash
python3 -m unittest discover -s tests -v
```

CI runs the tests on Python 3.9 and 3.13.
