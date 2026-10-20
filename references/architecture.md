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
- Domain modules talk to each other only through their public API (one index file per module). A boundary lint rule (for example eslint-plugin-boundaries or dependency-cruiser) blocks imports of another module's internals, and imports that break the UI's component levels (`docs/DESIGN.md`).
- Composition over inheritance: behaviour is built from small functions, modules and components that each do one job and are combined by the code that uses them, so a new feature mostly combines existing parts. Plain functions and modules over classes, unless the framework is class-based.
- No speculative abstractions (YAGNI): no generic base classes, no repositories for a single use, no microservices, Kubernetes or distributed caches before a measured need.
- Shared code is extracted on its third repetition, not before: until then the copies may still grow apart, and a wrong shared abstraction costs more than a little duplication. It moves into the module that owns the concept, or into a shared module when several domains use it.
- Errors are explicit and typed (`docs/LOGGING.md`). Never swallow them.
- Every new dependency is justified: what it replaces, maintenance status, adoption, known vulnerabilities and malicious-package reports, checked in the trusted sources (`docs/SOURCES.md`). Prefer the standard library or framework built-ins.

## Request flow

Describe the real flow in the project file, for example:

1. Server hook: request id, session, security headers, rate limits and route breakers.
2. Route: validate input with the schema, check the permission through the guard (`docs/security/SAFEGUARDS.md`).
3. Service: business rules; throws catalogued errors.
4. Repository: parameterized queries; returns rows.
5. Service or repository maps rows to DTOs; only DTOs reach the client.
6. Response, with user feedback through the `notify` module (`docs/DESIGN.md`).

Record where state lives (database, object storage, cache) as described in `docs/SCALING.md`.

## Diagrams

This file keeps two diagrams as Mermaid text, so they show up in git diffs, render on GitHub and cost an AI reader few tokens:

- System: the users, the app's parts (web app, workers), the data stores and every outside service (auth provider, email, object storage, payments, analytics), with what crosses each arrow. Drawn top-down (`flowchart TB`), so it stays readable on a phone and in a narrow editor pane.
- Main flow: a sequence diagram of the app's main task, from the browser through route, service and repository to the database and back, including the feedback the user sees.

Each stays at about a dozen boxes: detail lives in the folder docs and the code map, and a diagram that shows every file goes stale. The database diagram is generated from the schema (`docs/DATABASE.md`), never drawn by hand. A change that adds or removes a part, a data store or an outside service, or changes the main flow, updates the diagrams in the same PR.

### Draft before code (scaffold-time)

The plan is approved together with a draft on one page (`templates/plan-preview.html`), before any code exists, because changing a draft takes minutes and changing built code can take days:

- the two diagrams above;
- the data model: entities, key fields and relationships as a Mermaid ER diagram, which checkpoint B turns into the first migration;
- example payloads for the main actions, in the format of Planned actions below;
- for apps with screens, the colors, the look and rough mockups of the main screens (`docs/DESIGN.md`).

After approval, the diagrams go into this file and the payloads into Planned actions.

## Planned actions

The main actions approved in the draft and not built yet, one entry each: who may call it, the input, the success result and the error codes it can return. For example:

```markdown
### Create marker (signed-in users)
- Input: `title` (1-80 characters), `lat`, `lng`, `photo` (optional image, at most 5 MB)
- Success: `MarkerDTO` `{ id, title, lat, lng, photoUrl, createdAt }`
- Errors: field errors for invalid input; `UPLOAD_TOO_LARGE`, `MARKER_QUOTA_EXCEEDED`
```

The feature that builds an action turns its entry into the validation schema, the DTO and the first tests, and deletes the entry in the same PR, so the schemas stay the only source of truth.

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
