# Repository workflow

Becomes the workflow part of `CONTRIBUTING.md`; the documentation rules from `folder-docs.md` complete it. Written for people and AI alike. On GitLab or Gitea/Forgejo, use the same model with that host's merge requests, protected branches and CI.

## Branching model

Default for continuously deployed web apps, solo or small team: GitHub Flow with release tags.

- `main` is always deployable and protected; merges deploy to staging automatically when staging exists.
- Production deploys only from SemVer tags (`vX.Y.Z`), with manual approval in CI.
- All work happens on short-lived branches from `main`, merged within a few days: one feature or fix per branch, one PR, squash-merged, so each feature is one commit on `main`.
- No long-lived `develop` branch; unfinished work that must merge goes behind a feature flag.

Alternative: Git Flow (`develop` plus `release/*` branches) only for scheduled releases or several supported versions at once (app-store mobile apps, on-premise software). Recommend against it for continuously deployed web apps.

## Branch names

`<type>/<issue-id>-<short-description>` (the issue id is optional), lowercase kebab-case, ASCII, at most ~50 characters.

| Prefix | Use for | Example |
|---|---|---|
| `feat/` | New feature | `feat/12-marker-comments` |
| `fix/` | Bug fix through the normal flow | `fix/upload-mime-check` |
| `hotfix/` | Urgent production fix (Hotfix workflow) | `hotfix/session-cookie-expiry` |
| `security/` | Security fix or hardening | `security/rate-limit-login` |
| `perf/` | Performance or scaling work | `perf/marker-bbox-index` |
| `refactor/` | Behaviour-preserving restructuring | `refactor/split-marker-service` |
| `ui/` | Visual or theme changes | `ui/dark-mode-surfaces` |
| `seo/` | Metadata, sitemap, structured data, crawl rules | `seo/marker-page-metadata` |
| `test/`, `docs/`, `chore/`, `ci/` | Tests, documentation, tooling, pipeline | `chore/update-base-image` |

## Commits

- Conventional Commits with the standard types only: `feat`, `fix`, `perf`, `refactor`, `test`, `docs`, `build`, `ci`, `chore`, `revert`, and `style` for code formatting only (never for visual changes). The area goes in the scope: `fix(security): ...`, `feat(seo): ...`, `feat(theme): ...`, `feat(analytics): ...`, `feat(db): ...`, `fix(i18n): ...`, `fix(markers): ...`.
- Format: `type(scope): imperative summary`, at most 72 characters; the body explains why; footers such as `Refs #12` and `BREAKING CHANGE: ...`.
- commitlint with the conventional config enforces this in the commit-msg hook and on PR titles in CI.
- Small logical commits are fine on a branch; the squash merge turns the PR title into the single commit on `main`.
- Never commit secrets, generated files or temporary debug lines (`docs/LOGGING.md`).
- Hooks are never skipped (`--no-verify`); a failing hook is fixed, not bypassed.

## Pull requests

- Title in Conventional Commit format. The body follows the PR template: what and why; how it was tested; security and privacy notes; scalability notes; SEO notes for public routes; analytics events added or changed; database changes and migrations (backward compatible, rollback plan); screenshots in light and dark mode, mobile and desktop, for UI changes; the checklist.
- Required CI checks: `check`, `check:security`, `test:e2e`, image build and PR title lint; Lighthouse CI and the image scan once added in Phase 2.
- Claude reviews its own diff before opening the PR (Feature workflow, step 8). Merging is the user's decision unless they say otherwise. The branch is deleted after merge.

## Branch protection

Applied through the host's CLI only with the user's approval; otherwise hand over the exact settings.

- `main`: PR required, required checks passing, branch up to date before merging, squash merge only, no force pushes, no deletion, conversations resolved; signed commits recommended.
- Tags `v*` protected.
- With more than one person: at least one approving review and CODEOWNERS.

## Versioning and changelog

- SemVer: `feat` -> minor; `fix`, `perf` and `revert` -> patch; a breaking change -> major; other types do not trigger a release. Stay on 0.x until launch.
- The changelog and tags are generated from the commits: release-please on GitHub, git-cliff on any host. `CHANGELOG.md` is never edited by hand.
- Environments and promotion of the built image: `docs/DEPLOYMENT.md`.

## Repository files

`.gitignore`, `.gitattributes`, `.editorconfig`, this `CONTRIBUTING.md`, the root `SECURITY.md` (how to report a vulnerability), the PR template, issue templates (bug, feature), `CODEOWNERS` when more than one person works on the code, the commitlint config, the Renovate or Dependabot config, and the release automation config.

## Lean profile

Same model and conventions. Release automation is optional: tags can be created by hand, with git-cliff generating the changelog.

## Strict profile additions

- Signed commits and tags required.
- Branch protection enforces the approving review that `docs/security/THREAT-MODEL.md` requires for sensitive changes; CODEOWNERS routes those paths to their reviewers.
- No administrator bypass of branch protection.
- Lockfile changes are reviewed like code; new dependencies need explicit approval in the PR.
