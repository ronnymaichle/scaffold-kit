# Logging, errors and debugging

Becomes `docs/LOGGING.md`. Goal: in production, any error can be traced from what the user saw to the exact log lines and the exact commit; in development, the user and Claude can follow what the app is doing.

## One logger, levels instead of deleting logs

- All logging goes through one structured logger module (for example `$lib/server/log.ts`); a lint rule bans raw `console.*` (or `print`) everywhere else.
- Levels: `debug` (step-by-step flow), `info` (meaningful events), `warn` (recoverable problems, rejected requests, failed authorization), `error` (failures that need attention).
- `LOG_LEVEL` is `debug` in development, `warn` in tests and `info` elsewhere. Debug logs stay in the code and are silent in production.
- Development: readable terminal output, plus JSON lines appended to `logs/dev.log` (gitignored) so Claude can read and filter it while debugging.
- Production: one JSON line per event to stdout. Where logs live and how to query them is in `docs/OPERATIONS.md`.
- Browser: a small client logger that prints in development and sends only `warn` and `error` to the error tracker in production; production bundles drop `console` and `debugger`.

## Context on every line

- `requestId` (from the server hook, or the proxy's `X-Request-Id`), kept on a child logger in the request context, returned as a response header and passed into background jobs.
- `version`, `commit`, `env`, `instance` (hostname), `userId` when authenticated, and `module`.
- The request-completed line carries `durationMs`, the route and the status. Job lines carry the job name, `jobId` and the originating `requestId`.

## Redaction and security events

- The logger configuration redacts passwords, tokens, cookies, authorization headers, API keys and emails; a test asserts the redaction.
- Log ids, not personal data; log raw user-supplied content only as far as debugging needs, because log readers (people and agents) treat it as untrusted (`docs/OPERATIONS.md`).
- Security events are logged at `warn` or above: failed logins, authorization denials, rate-limit hits, failed bot challenges, rejected webhook signatures, rejected uploads and validation rejections on sensitive endpoints. Each is an entry in the security event catalog, with its severity, automatic response and alert (`docs/security/SAFEGUARDS.md`), and is also written to the audit log (`docs/security/THREAT-MODEL.md`).

## Errors

- Error codes are stable named strings in `DOMAIN_REASON` form (`MARKER_NOT_FOUND`, `UPLOAD_TOO_LARGE`), defined in one typed catalog file in code (for example `$lib/errors.ts`), which is the only list of codes. Each entry holds the HTTP status, the user-safe message (or its i18n message key), the level (`warn` for expected 4xx, `error` for unexpected 5xx) and `likelyCause`: one line on what usually triggers it and where to look. Unknown codes fail type checking.
- Services throw a typed `AppError(code, { cause, context })`, where `cause` is the underlying error.
- The global error hook (SvelteKit: `handleError` in `hooks.server.ts` and `hooks.client.ts`; Next.js: `onRequestError` in `instrumentation.ts` for server errors, with `error.tsx` and `global-error.tsx` showing the ref; FastAPI: exception handlers; Django: a middleware's `process_exception` and the `handler500` view; Go: middleware) logs the full error with stack, code, requestId and context, reports unexpected errors to the error tracker, and returns only the user-safe message plus "Error ref: <requestId>". The UI shows it through `notify.fromError` (`docs/DESIGN.md`). Stack traces never reach the client.
- JSON endpoints return the same `{ code, message, ref }` shape (`docs/ARCHITECTURE.md`).
- A new code enters the catalog in the same commit as the code that throws it, with a test that triggers it.
- Errors are never swallowed: catch only to add context, to translate, or to recover deliberately, and log at the matching level.

## Error tracking (Phase 2)

Self-hosted GlitchTip (Sentry-compatible) or hosted Sentry through the framework's Sentry SDK: tagged with the release (version and commit) and environment, PII scrubbing on, source maps uploaded to the tracker rather than served publicly, and disabled when no DSN is set.

## Debugging (rules for Claude)

- `log.debug` goes at entry points, branch decisions and external calls, with the relevant ids. These lines stay in the code.
- Temporary investigation lines carry the marker `DEBUG-TEMP` in a comment on the same line. `python3 scripts/quality/debug_leftovers.py` runs in `check` and in the pre-commit hook (with `--staged`) and fails on any marker, `debugger` statement, `breakpoint()` or `pdb.set_trace()`.
- When debugging, read `logs/dev.log` (filter by requestId) before guessing, and cite the log lines behind the conclusion.
- For a production problem, start from the error ref: find the requestId in the logs and the error tracker (`docs/OPERATIONS.md`), then the commit from the log line.

## Strict profile additions

- Log retention and access are defined in `docs/PRIVACY.md`, and access to production logs is itself logged.
