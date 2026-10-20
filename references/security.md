# Security

Becomes `docs/security/THREAT-MODEL.md` (threat model, defaults in force, audit log, scanning and severity policy), `docs/security/findings.md` (open and accepted risks) and the root `SECURITY.md` (from `templates/SECURITY.md`). Keep what applies to the chosen stack and profile.

Security comes right after correctness. When two options are otherwise comparable, take the more secure one and say so.

## Threat model

`docs/security/THREAT-MODEL.md` lists the assets (accounts, personal data, media, secrets), the actors (visitors, users, admins, attackers, third parties), the trust boundaries (browser to server, server to database, storage, external APIs, workers) and the main threats with their controls. Every feature's threat-model step (Feature workflow, step 3) updates it when something new crosses a boundary.

## Application defaults

- Input: validate every external input at the boundary with a schema; reject unknown fields; enforce length and size limits.
- Authorization: deny by default; check permissions, never role names, in every server entry point (`docs/ARCHITECTURE.md`, Roles and permissions); check ownership on the server on every read and write of a user-owned resource (prevents IDOR); never trust ids, roles or prices from the client.
- Authentication and sessions: follow `docs/ARCHITECTURE.md` (Auth); rate limits on login, signup and password reset.
- Database: parameterized queries or a query builder only; a least-privilege database user, never a superuser; never on a public port.
- Output: framework escaping; never render user content as raw HTML (`{@html}`, `dangerouslySetInnerHTML`, `v-html`); sanitize rich text on the server with a maintained sanitizer.
- Headers: strict Content-Security-Policy, HSTS, X-Content-Type-Options, Referrer-Policy, frame-ancestors; CSRF protection on every state-changing request.
- Uploads: size limits, type checked by magic bytes, random file names, private object storage (never local disk), short-lived signed URLs, EXIF and GPS metadata stripped.
- Outbound requests: never fetch user-supplied URLs without an allowlist (SSRF).
- Cross-origin requests (CORS): same-origin by default, with no CORS headers. When another origin must call the API (for example a separate frontend), allow an explicit list of origins per environment from configuration; never `*` together with credentials, never echo the request's `Origin` back unchecked, and allow only the methods and headers in use. Native mobile apps do not need CORS. CORS is not access control: authorization still runs on every request.
- Incoming webhooks: verify the provider's signature over the raw request body with a constant-time comparison (the provider's SDK where it has one); reject events whose signed timestamp is older than about five minutes; store each event id and ignore repeats, because providers deliver at least once; answer 2xx quickly and do the work in a background job. The payload is untrusted input: for state that matters, such as payments and subscriptions, fetch the object from the provider's API instead of trusting the event body. Each environment has its own webhook secret.
- Outgoing webhooks, if the app sends them: signed (HMAC over a timestamp and the body), and each target URL resolved and rejected when it points to a private, loopback or link-local address (SSRF).
- Abuse, cost and leaks: limits, quotas, spending caps, circuit breakers, security events and who is alerted follow `docs/security/SAFEGUARDS.md`. Public forms add a hidden honeypot field; sign-up, password reset and other public forms add a privacy-friendly challenge (for example Cloudflare Turnstile, hCaptcha or ALTCHA) once the app is public or abuse appears, verified on the server for every submission. Its cookies are listed in the cookie policy with their category (`docs/PRIVACY.md`).
- Configuration: environment variables validated with a schema at startup so the app fails fast on missing or invalid values; secrets only in server-only modules (SvelteKit `$env/static/private`); `.env` gitignored, `.env.example` committed with placeholders.
- Health endpoints: the public liveness endpoint returns only a status; readiness details, version and commit are available only on the internal network or behind auth.
- Logs: no secrets or personal data (`docs/LOGGING.md`).
- Audit log: an append-only table of security-relevant actions (sign-ins, role and permission changes, exports, deletions, admin actions, blocks and locks, breaker trips and resets), kept apart from application logs; the app can insert into it but never update or delete. It holds ids rather than personal details where it can, and is in the data inventory with its retention period (`docs/PRIVACY.md`).

## Servers and deployment

- Host firewall allows only 80, 443 and SSH. SSH accepts keys only (no root login, no passwords), ideally restricted to known IPs or a VPN (Tailscale, WireGuard); fail2ban or equivalent; automatic security updates.
- Only the reverse proxy publishes ports. Databases, object storage and workers stay on internal Docker networks or bind to 127.0.0.1, because ports Docker publishes bypass host firewall rules such as ufw.
- Edge protection: public apps sit behind an edge proxy or CDN with DDoS protection and a web application firewall (for example Cloudflare, Bunny or the host's equivalent), with its managed rules on and rate rules for sign-in and sign-up. TLS runs end to end, with the proxy verifying the origin's certificate. The origin accepts web traffic only from the proxy, through a firewall allowlist of the proxy's address ranges or an outbound tunnel with no open web ports (for example Cloudflare Tunnel), so calling the server's IP directly cannot bypass the protection. An edge provider outside the EU is allowed for EU users under the conditions in `docs/PRIVACY.md`.
- Client IP: the app reads the client's address only from the header its trusted proxy sets (for example `CF-Connecting-IP`, or the hop the proxy adds to `X-Forwarded-For`), and only on requests that came through that proxy. Rate limits, logs and abuse checks use that address, never a header the client can set.
- Deploys run as a non-root user; that user's Docker access is root-equivalent, so its key is protected like a root key.
- CI deploy credentials are environment-scoped secrets with approval required for production: dedicated deploy keys or least-privilege platform tokens, rotated, never in the repo.
- Containers: pinned base images, non-root user, minimal image.
- Backups are encrypted and stored off the server.

## Supply chain

- Lockfiles are committed, and CI and image builds install exactly what they pin (`bun install --frozen-lockfile`, `npm ci`, `pnpm install --frozen-lockfile`, `uv sync --locked`).
- New releases wait before they are installed, because most malicious versions are found and removed within hours or days: a minimum release age of at least one day in the package manager where it supports one (for example pnpm `minimumReleaseAge`, Bun `install.minimumReleaseAge`; check the current option and its unit in the trusted sources), and a cooldown of 3-7 days in Renovate (`minimumReleaseAge`) or Dependabot (`cooldown`), with security updates exempt.
- Dependencies' install scripts do not run unless the package is named as trusted (for example Bun `trustedDependencies` or pnpm `onlyBuiltDependencies`).
- A new dependency is checked before it is added: advisories and malicious-package reports, maintenance and adoption, and the exact name, since look-alike names are a common attack (`docs/SOURCES.md`).
- When a supply-chain attack hits a package the project uses: stop installs and deploys, compare the lockfile with the published affected versions, and if an affected version was installed anywhere (developer machines, CI, images), treat every secret it could reach as exposed and rotate it through the Hotfix workflow.

## Scanning

Layered, because no single tool or review catches everything. Verify each tool's current support for the stack (for example the lockfile format) with a web search during setup.

| Layer | Tool (pick what supports the stack) | When | Phase |
|---|---|---|---|
| Secrets in code | gitleaks | pre-commit (staged) and CI (full history) | 1 |
| Dependency vulnerabilities | the ecosystem audit (`bun audit`, `npm audit`, `pip-audit`, `govulncheck`) plus OSV-Scanner or Trivy | `check:security`, CI, weekly scheduled run | 1 |
| Static analysis | Semgrep (community and framework rules) and security lint rules | `check:security` and CI | 1 |
| Security tests | authorization negative tests, the permission matrix and route coverage tests, validation tests, rate-limit, quota and breaker tests, CORS and webhook-signature tests; RLS policy or security-rule tests where they are used, and cross-tenant tests for multi-tenant apps | every `check` | 1 |
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

## Lean profile

An internal tool reachable only through a VPN or an access proxy (for example Tailscale or Cloudflare Access) can skip the web application firewall and the bot challenge. Everything else applies.

## Strict profile additions

- A second reviewer, or the user's explicit sign-off recorded in the PR, for changes to auth, permissions, payments or personal data.
- The audit log is also copied to storage the app cannot change or delete (for example object storage with a retention lock), and access to it is itself logged.
- Field-level encryption for especially sensitive columns; secrets in a secrets manager rather than plain environment files.
- An SBOM per release (for example Syft) and blocking dependency and container scans.
- ZAP baseline on every release and an external penetration test before launch.
- An incident response plan with contacts and breach notification steps (GDPR: 72 hours to the supervisory authority).
