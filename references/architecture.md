# Architecture

Becomes `docs/ARCHITECTURE.md`, together with the auth, API and caching sections of `backend.md`. Keep the rules that apply to the chosen stack and profile, replace each scaffold-time table with the decision and its reason, and drop what does not apply.

## Framework idioms first

Use the framework's own conventions: its tooling, documentation and community answers are built around them. Start as a modular monolith: one deployable app, split internally by domain (markers, comments, accounts). Add a layer only when it removes real duplication or makes testing possible.

### Structure by stack (scaffold-time)

| Stack | Structure | Tests | Logger |
|---|---|---|---|
| SvelteKit (TypeScript) | Thin routes (`+page.server.ts` load and actions; `+server.ts` only for client-fetched JSON) -> `$lib/server/services` (business logic) -> `$lib/server/repositories` (database access). Validation schemas in `$lib/schemas` (Valibot or Zod). UI in `$lib/components`. Svelte 5 runes for state. | Vitest for services, utilities and components, integration tests for repositories against a real database in Docker, Playwright for critical flows | pino |
| Hono or Elysia API | routes -> services -> repositories; schema validation at the routes | bun test, integration tests against a real database | pino |
| Python FastAPI | routers -> services -> repositories; Pydantic models | pytest with httpx, real database in Docker | structlog |
| Go | `cmd/<app>`, `internal/<domain>/{handler,service,store}` | go test, table-driven, real database in Docker | log/slog |
| Anything else | Research the framework's official conventions first and follow them | The ecosystem's standard runner | The ecosystem's standard structured logger |

Verify current versions and maintenance status with a web search before recommending any of these.

## Principles

- Routes and handlers stay thin: parse, validate, authorize, call a service, return.
- Business logic lives in services as plain functions. Dependencies (database, storage, cache, queue, logger, analytics, clock) are passed in, so tests can swap them and infrastructure can change without touching business logic.
- Domain modules talk to each other only through their public API (one index file per module). A boundary lint rule (for example eslint-plugin-boundaries or dependency-cruiser) blocks imports of another module's internals.
- Plain functions and modules over classes, unless the framework is class-based.
- No speculative abstractions (YAGNI): no generic base classes, no repositories for a single use, no microservices, Kubernetes or distributed caches before a measured need.
- Errors are explicit and typed (`docs/LOGGING.md`). Never swallow them.
- Every new dependency is justified: what it replaces, maintenance status, adoption, known vulnerabilities. Prefer the standard library or framework built-ins.

## Request flow

Describe the real flow in the project file, for example:

1. Server hook: request id, session, security headers, rate limits.
2. Route: validate input with the schema, check authorization.
3. Service: business rules; throws catalogued errors.
4. Repository: parameterized queries; returns rows.
5. Service or repository maps rows to DTOs; only DTOs reach the client.
6. Response, with user feedback through the `notify` module (`docs/DESIGN.md`).

Record where state lives (database, object storage, cache) as described in `docs/SCALING.md`.

## Evolving the architecture

Check these triggers while planning each feature. Adopt a pattern only when its trigger appears, record it in an ADR (trigger, alternatives, consequences) and update this file.

| Trigger | Pattern |
|---|---|
| One action causes side effects in several modules, or a side effect (email, notification, indexing) must never be lost | Domain events written to an outbox table in the same transaction, delivered by a worker |
| A domain accumulates complex rules or several external integrations | A rich domain module with ports and adapters (hexagonal) for that domain only |
| Read shapes differ sharply from write shapes, or reads dominate a hot path | Read models: materialized views or denormalized tables kept current by events (CQRS-lite) |
| Measured slow reads that indexes and query changes cannot fix | A caching layer (see Caching) |
| A component needs a different scaling profile, release cadence or isolation (for example video processing) | Extract it as a separate service or worker, keeping one owning module per table |
| Several people or teams work in the same codebase | Stricter module boundaries and CODEOWNERS per module |

## Decisions

Significant decisions are recorded as ADRs in `docs/decisions/NNNN-short-title.md` from the kit's `templates/adr.md`: the first ones cover the stack, hosting, branching, the design system, and data and auth. Later ADRs record pattern adoptions, security and scaling trade-offs, and conventions kept from an existing codebase.
