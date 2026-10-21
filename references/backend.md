# Backend: data, auth, APIs and caching

Becomes `docs/DATABASE.md` (data store, modeling, types, ORM, local and test databases) and the Auth (including roles and permissions), APIs and Caching sections of `docs/ARCHITECTURE.md`. Keep what applies, replace scaffold-time tables with the decision and its reason, drop the rest.

## Choosing the data store (scaffold-time)

Recommend from the app's data shape and needs, preferring open-source or self-hostable options and services with a usable free tier. For every hosted service, state after checking with a web search: the free-tier limits, what happens when they are exceeded (pausing, throttling, billing), the lock-in, and the exit path (export, self-hosting). Record the choice in an ADR.

| Data shape or need | Default | Alternatives and caveats |
|---|---|---|
| Relational data with constraints, reporting, geo or full-text search (most web apps) | PostgreSQL, self-hosted in Compose or managed (Supabase, Neon, the host's managed Postgres); PostGIS for geo | SQLite or libSQL (Turso) for small single-node apps |
| Database, auth, storage and realtime managed together with low lock-in | Supabase (open-source Postgres, self-hostable later) | Free-tier limits and pausing rules apply |
| Mobile-first apps with offline sync and realtime documents | Firebase (Firestore, Auth, Functions) | Proprietary; limited queries (including geo); costs grow per read and write |
| Document-shaped data with highly variable fields and few relations | MongoDB (Atlas or self-hosted) | Postgres JSONB covers many of these cases |

Moving between stores is scriptable only within one family, so the family is chosen here and recorded, with its exit path, in the data-and-auth ADR:

- Postgres-compatible (self-hosted Postgres, Supabase, Neon, the host's managed Postgres): the same schema and migrations run on all of them, so a move is a new connection string, the migrations and a dump and restore of the data.
- Firebase, and other platforms with a local emulator: local and hosted projects differ only in configuration, and the platform's CLI deploys between them.
- Across families (Postgres and Firestore, or either and MongoDB): the queries, access rules, auth and data shape all change. That is a rewrite of the repositories plus a data migration, never a script; the repository layer keeps it to one layer of the code.
- Platform auth (Supabase Auth, Firebase Auth) ties the user accounts to that platform; an in-app auth library with users in Postgres moves with the database.

Offline-first apps need an explicit sync design whatever the store: local storage on the device, a queue of pending writes (including media uploads), conflict rules (last write wins, per-field merge or manual resolution) and a visible sync state for the user. Firestore offline persistence, PowerSync or ElectricSQL on Postgres, and CouchDB/PouchDB replication are common options; compare them for the case at hand.

## Auth

### Choosing the approach (scaffold-time), in order of default preference

1. A maintained auth library inside the app, with users in the app's own database (Better Auth or Auth.js for TypeScript, the framework's built-in auth for Django or Rails, FastAPI-Users): free, no lock-in, full control.
2. The platform's auth (Supabase Auth, Firebase Auth) when that platform is already the data store.
3. A hosted identity provider (Clerk, Auth0) or a self-hosted identity server (Keycloak, Zitadel, Authentik) for enterprise SSO, one login across several apps, or compliance needs.

### Rules for every approach

- Email verification; password reset with single-use, expiring tokens; rate limiting with backoff on login, signup and reset.
- Passwords hashed through the library with Argon2id, or scrypt where Argon2id is not available, with at least the parameters in OWASP's Password Storage Cheat Sheet; bcrypt only in existing systems, with input limited to 72 bytes; never hand-rolled crypto.
- Optional MFA (TOTP) and passkeys for users; MFA required for admin and support accounts, meaning any role that can see or change other people's data (in the lean profile, recommended).
- Social login through OAuth or OIDC with state and PKCE.
- Sessions rotate on login and privilege change and are revoked on the server at logout and password change.

### Roles and permissions

- Every app starts with three roles: `anonymous` (visitors without an account), `user` (signed in) and `admin`. Further roles and admin levels (for example `support`, `moderator` or `owner`) are decided in the plan from what the app needs (scaffold-time), and can be added later without changing the code that checks access. Multi-tenant apps also have roles inside each tenant (for example `owner` and `member`), held per membership, next to the platform's own `admin`.
- Code checks permissions, never role names: `can(actor, 'marker.delete', marker)`, on the server, in every entry point (`docs/security/SAFEGUARDS.md`). Permissions are named `resource.action` and listed in one typed catalog in code (for example `$lib/server/auth/permissions.ts`), together with the map from each role to its permissions, so an unknown permission fails type checking. A new role is an entry in that map, reviewed and tested like any other code. Roles that admins define in the running app are added only when customers need their own, as an architecture change with an ADR.
- Who holds which role lives in the database (a `user_roles` table, or the membership in a multi-tenant app). A user can hold several roles, and gets the permissions of all of them. Roles inside a tenant are named for it (`association_admin`, `clinic_admin`) and held on the membership, so they never mix with the platform's own `admin`.
- `anonymous` has its permissions listed like every other role, starting from none, so what visitors can do is written down and tested.
- Ownership is a separate check: `marker.delete` lets a user delete their own markers, `marker.delete.any` lets a moderator delete anyone's.
- Costly features need a verified account (`docs/security/SAFEGUARDS.md`).
- The first admin is created with a command run on the server (for example `admin:grant <email>`), never through sign-up, a default password, or an environment variable that grants admin at start.
- Changing roles needs the `roles.manage` permission. Nobody can grant a permission they do not hold or change their own roles, and the last admin cannot be removed. A role change rotates the user's sessions, goes into the audit log, and notifies the user and the admins (by email, or in the app when it sends no email).
- The admin area has its own routes (for example `/admin`), which are `noindex` and check permissions in every entry point like any other route.
- Tests: the permission matrix and route coverage tests (`docs/TESTING.md`).

### Sessions by approach

- In-app library: server-side sessions stored in the database (or the library's adapter), referenced by an httpOnly, Secure, SameSite=Lax cookie, so they work across instances.
- Platform auth: use the platform's server-side helpers so tokens travel in httpOnly cookies (for example Supabase's SSR package, or Firebase session cookies minted with the Admin SDK); verify the token on the server for every request; keep access tokens short-lived with refresh; never trust claims read in the browser for authorization.
- Hosted identity provider: OIDC authorization code flow with PKCE; the app then keeps its own session as above.

### Platform security

- Supabase: Row Level Security on every table with tested policies; the service-role key only on the server.
- Firebase: default-deny security rules tested in the Emulator Suite; the Admin SDK only on the server.
- MongoDB: validate input types to block operator injection (`$ne`, `$where` and similar); restrict network access, never open to all addresses.

## Data modeling conventions

- The schema is defined in code (the ORM schema) and changes only through generated, reviewed migrations. Applied migrations are never edited; breaking changes use expand, migrate, contract (`docs/SCALING.md`).
- Naming: snake_case tables and columns, one convention for plural or singular table names, `<entity>_id` foreign keys.
- Keys: UUIDv7 (time-ordered) or bigint identity primary keys; no guessable sequential ids in URLs where enumeration matters.
- Every table has `created_at` and `updated_at` (timestamptz, UTC). Soft delete (`deleted_at`) where undo, restore or audit is needed, with partial indexes that exclude deleted rows; hard delete for personal-data erasure.
- Integrity lives in the database: NOT NULL by default, CHECK and UNIQUE constraints, foreign keys with a deliberate ON DELETE behaviour. The database is the last line of defense.
- Normalize by default (3NF); denormalize only for a measured read need. JSONB only for genuinely flexible attributes, never for core relations.
- Indexes on every foreign key and on every query's filter and sort columns; GiST for geo; EXPLAIN on realistic data for hot queries.
- Money as integer minor units or numeric; enums as CHECK constraints or lookup tables; geo as PostGIS geography (SRID 4326).
- Multi-tenant apps, including one that starts with a single organization but is planned for more: `tenant_id` on every tenant-owned row from the first migration, because adding it later touches every table and query. Repositories always filter by tenant, and integration tests prove that one tenant cannot read or change another's rows.
- Row Level Security is a second layer wherever the database has it. On self-hosted Postgres: the app connects as a role that does not own the tables, so the policies apply to it (migrations run as the owner); each request's transaction sets the tenant with `set_config('app.tenant_id', $1, true)`, which ends with the transaction, so a pooled connection never carries it into the next request; each tenant-owned table has a policy comparing `tenant_id` with `current_setting('app.tenant_id', true)`, which matches no rows when the setting is missing. Work that spans tenants (a worker, a cross-tenant report) uses its own role, never the request handlers'. The policies have their own tests.
- Document databases: model around access patterns, decide embed or reference per relationship, validate documents with a schema, index every query.
- `docs/DATABASE.md` holds these conventions, a generated ERD (Mermaid) and per-table notes on personal data and retention.

## One source of truth for types (database -> server -> UI)

- Types flow from the schema: the ORM infers row types, input validation schemas are derived from or aligned with them (drizzle-valibot, drizzle-zod), and the framework's generated route types (SvelteKit `./$types`) carry them to components. Strict type checking (`tsc`, plus `svelte-check` in SvelteKit) runs in `check`, so a mismatch between database, server and UI fails the build. Svelte components use TypeScript like any other code (`<script lang="ts">`).
- Raw database rows never reach the client: repositories or services map them to explicit DTO types (for example `toMarkerDTO`) that list only safe fields, so password hashes and internal flags cannot leak.
- A schema-drift check (generating a migration yields no changes) runs in `check`.
- Other languages: Python uses Django models with django-stubs, or SQLAlchemy models with Pydantic schemas, with strict mypy or pyright; Go uses sqlc-generated code; a separate frontend gets a typed client generated from OpenAPI.

## ORM and query layer (scaffold-time)

Verify current versions and support for special types such as PostGIS with a web search.

| Situation | Recommendation |
|---|---|
| TypeScript with SQL; SQL-like control, lightweight, Bun-friendly | Drizzle ORM with drizzle-kit migrations |
| TypeScript; a higher-level API and tooling preferred | Prisma (raw SQL may be needed for types such as geo) |
| TypeScript; complex dynamic SQL without an ORM | Kysely (type-safe query builder) |
| Python with Django | Django's ORM and migrations |
| Python with FastAPI or another framework | SQLAlchemy 2 with Alembic (SQLModel for simple FastAPI apps) |
| Go | sqlc with goose or Atlas migrations |
| MongoDB | The official driver with schema validation, or Mongoose |
| Supabase or Firebase | A server-side ORM or SDK with generated types; client SDKs only with RLS or security rules in place |

## Local and test databases

- Development: the database runs in docker-compose with the same major version and extensions as production (for example Postgres with PostGIS). `db:reset` recreates it, `migrate` applies migrations, `db:seed` loads realistic fake data (for example Faker) and one development account per role on `.test` addresses, a reserved domain, so no mail reaches anyone. They share the password in `.env`'s `DEV_SEED_PASSWORD`, which is random on each machine and never committed; agents sign in with them for browser checks (`docs/TESTING.md`). The seed refuses to run when that password is empty or the database is not local, and the first admin of a hosted environment is still created by command (`docs/ARCHITECTURE.md`, Roles and permissions). Platforms use their local stacks: `supabase start` runs the whole Supabase stack in Docker, and the Firebase Emulator Suite keeps seed data with `--import` and `--export-on-exit`.
- Development never uses a hosted project, free tier included. Hosted projects are only for staging and production, so local work does not use up free-tier limits, keep a paused project awake or need a network, and fake data never reaches a hosted project.
- Everything a hosted project needs is defined in the repository: migrations, Row Level Security policies and `supabase/config.toml` for Supabase; security rules, indexes and `firebase.json` for Firebase; functions for either. A change made in a hosted dashboard is copied back into the repository the same day, and the promote script (`docs/DEPLOYMENT.md`) applies the repository's version to each environment.
- Tests: a separate test database, never the development one. Integration tests are isolated (a transaction rolled back per test, or a fresh database per worker with Testcontainers) and build data with factories rather than shared fixtures; e2e runs against a freshly migrated and seeded database (`docs/TESTING.md`).
- Production data never goes to development or test machines; when realistic data is needed, use an anonymized dump.

## APIs

- Inside a full-stack framework, prefer its own data loading and form actions; add JSON endpoints only for client-fetched data.
- JSON endpoints share one error shape (`{ code, message, ref }` from the error catalog), cursor-based pagination with a maximum page size, idempotency keys on create and payment endpoints, rate limits (`docs/security/SAFEGUARDS.md`) and schema validation. Cross-origin access and incoming webhooks follow `docs/security/THREAT-MODEL.md`.
- A public or mobile API gets a version prefix (`/api/v1`) and an OpenAPI description generated from the validation schemas.

## Caching

Add layers only when measurements show the need.

1. Database first: correct indexes and query shape.
2. HTTP caching: hashed static assets cached for a year; public pages with a short `s-maxage` and `stale-while-revalidate`; every authenticated or personalized response marked `Cache-Control: private, no-store`, so a CDN or proxy never serves one user's data to another.
3. Application cache: an in-process LRU only for small, rarely changing, per-instance data; a shared Redis or Valkey cache behind the cache module (`docs/SCALING.md`) for anything shared across instances.
4. Every cache entry has an owner, a TTL and an invalidation rule written next to the code that changes the data.
