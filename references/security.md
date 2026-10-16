# Security

Becomes `docs/security/THREAT-MODEL.md` (threat model, defaults in force, scanning and severity policy), `docs/security/findings.md` (open and accepted risks) and the root `SECURITY.md` (from `templates/SECURITY.md`). Keep what applies to the chosen stack and profile.

Security comes right after correctness. When two options are otherwise comparable, take the more secure one and say so.

## Threat model

`docs/security/THREAT-MODEL.md` lists the assets (accounts, personal data, media, secrets), the actors (visitors, users, admins, attackers, third parties), the trust boundaries (browser to server, server to database, storage, external APIs, workers) and the main threats with their controls. Every feature's threat-model step (Feature workflow, step 3) updates it when something new crosses a boundary.

## Application defaults

- Input: validate every external input at the boundary with a schema; reject unknown fields; enforce length and size limits.
- Authorization: deny by default; check ownership on the server on every read and write of a user-owned resource (prevents IDOR); never trust ids, roles or prices from the client.
- Authentication and sessions: follow `docs/ARCHITECTURE.md` (Auth); rate limits on login, signup and password reset.
- Database: parameterized queries or a query builder only; a least-privilege database user, never a superuser; never on a public port.
- Output: framework escaping; never render user content as raw HTML (`{@html}`, `dangerouslySetInnerHTML`, `v-html`); sanitize rich text on the server with a maintained sanitizer.
- Headers: strict Content-Security-Policy, HSTS, X-Content-Type-Options, Referrer-Policy, frame-ancestors; CSRF protection on every state-changing request.
- Uploads: size limits, type checked by magic bytes, random file names, private object storage (never local disk), short-lived signed URLs, EXIF and GPS metadata stripped.
- Outbound requests: never fetch user-supplied URLs without an allowlist (SSRF).
- Configuration: environment variables validated with a schema at startup so the app fails fast on missing or invalid values; secrets only in server-only modules (SvelteKit `$env/static/private`); `.env` gitignored, `.env.example` committed with placeholders.
- Health endpoints: the public liveness endpoint returns only a status; readiness details, version and commit are available only on the internal network or behind auth.
- Logs: no secrets or personal data (`docs/LOGGING.md`).

## Servers and deployment

- Host firewall allows only 80, 443 and SSH. SSH accepts keys only (no root login, no passwords), ideally restricted to known IPs or a VPN (Tailscale, WireGuard); fail2ban or equivalent; automatic security updates.
- Only the reverse proxy publishes ports. Databases, object storage and workers stay on internal Docker networks or bind to 127.0.0.1, because ports Docker publishes bypass host firewall rules such as ufw.
- Deploys run as a non-root user; that user's Docker access is root-equivalent, so its key is protected like a root key.
- CI deploy credentials are environment-scoped secrets with approval required for production: dedicated deploy keys or least-privilege platform tokens, rotated, never in the repo.
- Containers: pinned base images, non-root user, minimal image.
- Backups are encrypted and stored off the server.

## Scanning

Layered, because no single tool or review catches everything. Verify each tool's current support for the stack (for example the lockfile format) with a web search during setup.

| Layer | Tool (pick what supports the stack) | When | Phase |
|---|---|---|---|
| Secrets in code | gitleaks | pre-commit (staged) and CI (full history) | 1 |
| Dependency vulnerabilities | the ecosystem audit (`bun audit`, `npm audit`, `pip-audit`, `govulncheck`) plus OSV-Scanner or Trivy | `check:security`, CI, weekly scheduled run | 1 |
| Static analysis | Semgrep (community and framework rules) and security lint rules | `check:security` and CI | 1 |
| Security tests | authorization negative tests, validation tests, rate-limit tests; RLS or security-rule tests when a platform is used | every `check` | 1 |
| AI review | Claude reviews every diff (Feature workflow, step 8); Claude Code's `/security-review` when available | every feature | 1 |
| Dependency updates | Renovate or Dependabot, security updates first | automatic PRs | 2 |
| Container and config | Trivy (image, Dockerfile, compose), hadolint | CI on every image build | 2 |
| Dynamic scan | OWASP ZAP baseline | before launch and significant releases (every release in the strict profile) | 2 |

## Severity policy

- Critical and high: fixed before committing; never merged.
- Medium: fixed in the same feature unless the user explicitly defers it; deferred items go to `docs/security/findings.md` with reason and date.
- Low and informational: reported as recommendations.
- False positives are suppressed only with an inline justification, never by disabling a rule globally.
- An exposed secret is rotated first; cleaning git history comes after.

## Audits

On request ("run a security audit") or before launch: run every layer, review the codebase against the OWASP Top 10, write a dated report in `docs/security/`, and propose fixes ordered by severity.

## Strict profile additions

- A second reviewer, or the user's explicit sign-off recorded in the PR, for changes to auth, permissions, payments or personal data.
- An append-only audit log of security-relevant actions (logins, permission changes, exports, deletions, admin actions).
- MFA required for admin and staff accounts.
- Field-level encryption for especially sensitive columns; secrets in a secrets manager rather than plain environment files.
- An SBOM per release (for example Syft) and blocking dependency and container scans.
- ZAP baseline on every release and an external penetration test before launch.
- An incident response plan with contacts and breach notification steps (GDPR: 72 hours to the supervisory authority).
